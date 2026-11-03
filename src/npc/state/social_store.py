"""Initial SQLite social-state slice; not a production game delivery outbox."""

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from time import time

from npc.behavior.appraisal import relationship_effect
from npc.contracts.context import DialogueMemory, Persona, PlayerInput, Relationship, Scope


class StoreFailure(Exception):
    pass


class StateConflict(StoreFailure):
    pass


class SocialStore:
    def __init__(self, path: Path, *, clock=time, max_bytes=250 * 1024 * 1024, memory_source="console_display"):
        if memory_source not in {"console_display", "game_completed"}:
            raise ValueError("unsupported dialogue memory provenance")
        self.memory_source = memory_source
        self.path, self.clock, self.max_bytes = Path(path), clock, max_bytes
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise StoreFailure("unsupported_state_version")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS social_state (
                    scope_key TEXT PRIMARY KEY, relationship TEXT NOT NULL, mood TEXT NOT NULL,
                    revision INTEGER NOT NULL, last_gain REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS social_turn (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT, scope_key TEXT NOT NULL,
                    request_id TEXT NOT NULL, digest TEXT NOT NULL, player_text TEXT NOT NULL,
                    audit TEXT NOT NULL, result TEXT, npc_text TEXT, mode TEXT,
                    displayed INTEGER NOT NULL DEFAULT 0, cancelled INTEGER NOT NULL DEFAULT 0,
                    UNIQUE(scope_key, request_id));
                CREATE INDEX IF NOT EXISTS social_history ON social_turn(scope_key, displayed, sequence DESC);
                PRAGMA user_version=1;
            """)

    @staticmethod
    def key(scope: Scope, npc_id: str, player_id: str):
        return json.dumps([scope.game_id, scope.world_id, scope.save_branch_id, npc_id, player_id], separators=(",", ":"))

    @contextmanager
    def _connection(self):
        db = None
        try:
            if self.path.exists() and self.path.stat().st_size >= self.max_bytes:
                raise StoreFailure("state_capacity")
            db = sqlite3.connect(self.path, timeout=0.05, isolation_level=None)
            db.row_factory = sqlite3.Row
            yield db
        except (sqlite3.Error, OSError, ValueError, TypeError):
            raise StoreFailure("state_unavailable") from None
        finally:
            if db is not None:
                db.close()

    @contextmanager
    def _transaction(self):
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise

    def _read(self, db, key):
        row = db.execute("SELECT * FROM social_state WHERE scope_key=?", (key,)).fetchone()
        if row is None:
            raise StoreFailure("state_missing")
        history = db.execute("SELECT request_id,player_text,npc_text,mode FROM social_turn WHERE scope_key=? AND displayed=1 ORDER BY sequence DESC LIMIT 8", (key,)).fetchall()
        return dict(relationship=Relationship.model_validate_json(row["relationship"]), mood=row["mood"],
                    revision=row["revision"], last_gain=row["last_gain"],
                    history=tuple(DialogueMemory(request_id=r["request_id"], player_text=r["player_text"], npc_text=r["npc_text"] or "", mode=r["mode"], source=self.memory_source) for r in reversed(history)))

    def ensure(self, key: str, initial: Relationship, mood: str):
        with self._transaction() as db:
            db.execute("INSERT OR IGNORE INTO social_state VALUES(?,?,?,?,?)", (key, initial.model_dump_json(), mood, 1, 0))
            return self._read(db, key)

    def load(self, key: str):
        with self._connection() as db:
            return self._read(db, key)

    def override(self, key: str, relationship: Relationship, mood: str, expected_revision: int):
        if mood not in {"neutral", "calm", "angry", "tired", "fearful"}:
            raise StoreFailure("invalid_mood")
        with self._transaction() as db:
            state = self._read(db, key)
            if state["revision"] != expected_revision:
                raise StateConflict("state_conflict")
            db.execute("UPDATE social_state SET relationship=?,mood=?,revision=revision+1 WHERE scope_key=?", (relationship.model_dump_json(), mood, key))
            return self._read(db, key)

    def begin_turn(self, key: str, request_id: str, player: PlayerInput, persona: Persona, expected_revision: int):
        digest = hashlib.sha256(player.model_dump_json().encode()).hexdigest()
        with self._transaction() as db:
            state = self._read(db, key)
            old = db.execute("SELECT digest,audit,result,cancelled FROM social_turn WHERE scope_key=? AND request_id=?", (key, request_id)).fetchone()
            if old:
                if old["digest"] != digest or old["cancelled"]:
                    raise StateConflict("request_conflict")
                return state, json.loads(old["audit"]), json.loads(old["result"]) if old["result"] else None
            if state["revision"] != expected_revision:
                raise StateConflict("state_conflict")
            now = self.clock()
            positive_allowed = now - state["last_gain"] >= 60
            after, delta, appraisal = relationship_effect(player, persona, state["relationship"], positive_allowed=positive_allowed)
            mood = state["mood"]
            if appraisal.stimulus == "directed_insult" and (after.irritation >= 40 or persona.patience < 0.5): mood = "angry"
            elif appraisal.stimulus == "threat": mood = "fearful" if persona.assertiveness < 0.5 else "angry"
            elif appraisal.stimulus == "apology" and after.irritation < 30 and positive_allowed: mood = "calm"
            gain_used = delta["familiarity"] > 0 or appraisal.stimulus in {"gratitude", "apology"} and positive_allowed
            audit = dict(before=state["relationship"].model_dump(), after=after.model_dump(), delta=delta,
                         stimulus=appraisal.stimulus, reasons=list(appraisal.reasons), positive_cooldown_applied=not positive_allowed,
                         policy_version=appraisal.policy_version)
            db.execute("UPDATE social_state SET relationship=?,mood=?,revision=revision+1,last_gain=? WHERE scope_key=?",
                       (after.model_dump_json(), mood, now if gain_used else state["last_gain"], key))
            db.execute("INSERT INTO social_turn(scope_key,request_id,digest,player_text,audit) VALUES(?,?,?,?,?)",
                       (key, request_id, digest, player.text, json.dumps(audit)))
            return self._read(db, key), audit, None

    def stage_preview(self, key, request_id, result, expected_revision):
        encoded = json.dumps(result, ensure_ascii=False)
        if len(encoded.encode()) > 128 * 1024:
            raise StoreFailure("preview_size_limit")
        response = result["result"]["response"]
        with self._transaction() as db:
            state = self._read(db, key)
            if state["revision"] != expected_revision:
                raise StateConflict("state_conflict")
            row = db.execute("SELECT cancelled,result FROM social_turn WHERE scope_key=? AND request_id=?", (key, request_id)).fetchone()
            if row is None or row["cancelled"] or row["result"] is not None:
                raise StateConflict("turn_conflict")
            db.execute("UPDATE social_turn SET result=?,npc_text=?,mode=? WHERE scope_key=? AND request_id=?",
                       (encoded, response["text"] if response else None, response["mode"] if response else None, key, request_id))

    def displayed(self, key, request_id):
        with self._transaction() as db:
            cursor = db.execute("UPDATE social_turn SET displayed=1 WHERE scope_key=? AND request_id=? AND result IS NOT NULL AND mode IS NOT NULL AND cancelled=0", (key, request_id))
            if not cursor.rowcount:
                raise StateConflict("display_conflict")
            return self._read(db, key)

    def cancel(self, key, request_id):
        with self._transaction() as db:
            db.execute("UPDATE social_turn SET cancelled=1 WHERE scope_key=? AND request_id=? AND displayed=0", (key, request_id))
