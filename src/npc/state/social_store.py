"""Initial SQLite social-state slice; not a production game delivery outbox."""

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from time import time

from npc.behavior.appraisal import relationship_effect
from npc.context.conversation import advance, default_similarity, read_turn
from npc.contracts.context import ConversationState, DialogueMemory, Persona, PlayerInput, Relationship, Scope, TurnReading


class StoreFailure(Exception):
    pass


class StateConflict(StoreFailure):
    pass


class SocialStore:
    def __init__(self, path: Path, *, clock=time, max_bytes=250 * 1024 * 1024, memory_source="console_display", similarity=None):
        if memory_source not in {"console_display", "game_completed"}:
            raise ValueError("unsupported dialogue memory provenance")
        self.memory_source = memory_source
        self.similarity = similarity  # None: chosen per turn (MiniLM only if already loaded, else token overlap)
        self.path, self.clock, self.max_bytes = Path(path), clock, max_bytes
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1, 2):
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
                CREATE TABLE IF NOT EXISTS conversation_state (scope_key TEXT PRIMARY KEY, state TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS conversation_turn (
                    scope_key TEXT NOT NULL, request_id TEXT NOT NULL, reading TEXT NOT NULL,
                    move TEXT, reply TEXT, evidence TEXT, PRIMARY KEY(scope_key, request_id));
                PRAGMA user_version=2;
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
        conv = db.execute("SELECT state FROM conversation_state WHERE scope_key=?", (key,)).fetchone()
        try:
            conversation = ConversationState.model_validate_json(conv["state"]) if conv else ConversationState()
        except ValueError:
            conversation = ConversationState()
        return dict(relationship=Relationship.model_validate_json(row["relationship"]), mood=row["mood"],
                    revision=row["revision"], last_gain=row["last_gain"], conversation=conversation, reading=None,
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
                state["reading"] = self._reading(db, key, request_id)
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
            reading = read_turn(player.text, state["conversation"], self.similarity or default_similarity())
            audit = dict(turn_type=reading.type, before=state["relationship"].model_dump(), after=after.model_dump(), delta=delta,
                         stimulus=appraisal.stimulus, reasons=list(appraisal.reasons), positive_cooldown_applied=not positive_allowed,
                         policy_version=appraisal.policy_version)
            db.execute("UPDATE social_state SET relationship=?,mood=?,revision=revision+1,last_gain=? WHERE scope_key=?",
                       (after.model_dump_json(), mood, now if gain_used else state["last_gain"], key))
            db.execute("INSERT INTO social_turn(scope_key,request_id,digest,player_text,audit) VALUES(?,?,?,?,?)",
                       (key, request_id, digest, player.text, json.dumps(audit)))
            db.execute("INSERT OR REPLACE INTO conversation_turn(scope_key,request_id,reading) VALUES(?,?,?)", (key, request_id, reading.model_dump_json()))
            state = self._read(db, key)
            state["reading"] = reading
            return state, audit, None

    @staticmethod
    def _reading(db, key, request_id):
        row = db.execute("SELECT reading FROM conversation_turn WHERE scope_key=? AND request_id=?", (key, request_id)).fetchone()
        try:
            return TurnReading.model_validate_json(row["reading"]) if row else None
        except ValueError:
            return None

    def stage_preview(self, key, request_id, result, expected_revision, *, move=None, evidence_ids=None):
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
            # Reply, move and evidence IDs wait here; conversation state changes only when `displayed` confirms.
            inner = result["result"]
            move = move or (inner.get("plan") or {}).get("move") or result.get("move")
            if evidence_ids is None:
                evidence_ids = result.get("evidence_ids") or (response or {}).get("evidence_ids") or inner.get("evidence_used") or ()
            db.execute("UPDATE conversation_turn SET move=?,reply=?,evidence=? WHERE scope_key=? AND request_id=?",
                       (move, response["text"] if response else None, json.dumps(list(evidence_ids)), key, request_id))

    def displayed(self, key, request_id):
        with self._transaction() as db:
            cursor = db.execute("UPDATE social_turn SET displayed=1 WHERE scope_key=? AND request_id=? AND displayed=0 AND result IS NOT NULL AND mode IS NOT NULL AND cancelled=0", (key, request_id))
            changed = bool(cursor.rowcount)
            if not changed:  # repeat receipt: fine if it was already displayed
                cursor = db.execute("SELECT 1 FROM social_turn WHERE scope_key=? AND request_id=? AND displayed=1", (key, request_id))
                if cursor.fetchone():
                    return self._read(db, key)
                raise StateConflict("display_conflict")
            if changed:  # a duplicate receipt never counts twice
                self._advance(db, key, request_id)
            return self._read(db, key)

    def _advance(self, db, key, request_id):
        state = self._read(db, key)["conversation"]
        row = db.execute("SELECT player_text,npc_text FROM social_turn WHERE scope_key=? AND request_id=?", (key, request_id)).fetchone()
        extra = db.execute("SELECT move,evidence FROM conversation_turn WHERE scope_key=? AND request_id=?", (key, request_id)).fetchone()
        if extra is None:
            return
        try:
            ids = tuple(str(i)[:128] for i in json.loads(extra["evidence"] or "[]"))
        except ValueError:
            ids = ()
        reading = self._reading(db, key, request_id)
        new = advance(state, reading, row["player_text"], row["npc_text"] or "", extra["move"], ids)
        db.execute("INSERT OR REPLACE INTO conversation_state VALUES(?,?)", (key, new.model_dump_json()))

    def cancel(self, key, request_id):
        with self._transaction() as db:
            db.execute("UPDATE social_turn SET cancelled=1 WHERE scope_key=? AND request_id=? AND displayed=0", (key, request_id))
