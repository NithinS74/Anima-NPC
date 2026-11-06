"""Capture a real game snapshot, the exact provider-bound prompt and the expected reply. No API calls.

Run from the repository root:
    .venv/Scripts/python.exe -X utf8 research/cs3235_paper/experiments/capture_prompt_example.py
"""
from __future__ import annotations

import asyncio
import glob
import json
import tempfile
import time
from pathlib import Path

from npc.adapters.skyrim.personas import load_rules
from npc.adapters.skyrim.protocol import GameEvent, GameSnapshot, SpeechInput, canonical_scenario, profile_for
from npc.contracts.context import PlayerInput, Relationship, Scope
from npc.contracts.dialogue import ProviderReply
from npc.runtime.preview import PreviewLimits, PreviewRunner
from npc.state.social_store import SocialStore

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).with_name("results") / "prompt_example.json"
QUESTION = "Do you know what the Jarl plans to do about the war?"
REPLIES = [{"mode": "speech", "text": "War plans are for the Jarl, not a guard on patrol, stranger.", "cue": None, "evidence_ids": []},
           {"mode": "speech", "text": "You asked me that already, so why does it matter to you?", "cue": None, "evidence_ids": []}]


class Recorder:
    def __init__(self):
        self.prompts = []
        self.reply = REPLIES[0]

    async def generate(self, prompt, timeout_s):
        self.prompts.append(prompt)
        return ProviderReply(content=json.dumps(self.reply), model="scripted-example", finish_reason="stop")


def latest_snapshot() -> dict:
    latest = None
    for path in sorted(glob.glob(str(ROOT / "output/skyrim/inbox/*.json"))):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("kind") == "player_turn":
            latest = data
    if latest is None:
        raise SystemExit("No captured player_turn in output/skyrim/inbox")
    return latest["game"]


def trim(game: dict) -> dict:
    """Keep the example readable: real values, shortened lists."""
    shown = json.loads(json.dumps(game))
    for actor in ("npc", "player"):
        shown[actor]["factions"] = shown[actor]["factions"][:2]
    shown["dialogue"] = shown["dialogue"][:1]
    shown["player"]["base"]["name"] = "PlayerName"
    for item in shown["dialogue"]:
        item["responses"] = item["responses"][:1]
    return shown


async def main() -> None:
    game = latest_snapshot()
    snapshot = GameSnapshot.model_validate(game)
    event = GameEvent(event_id="e1", session_id="s1", game_epoch="epoch", sequence=1, captured_at_ms=int(time.time() * 1000), game_pid=1, kind="start", snapshot=snapshot)
    rules = load_rules(ROOT / "configs/skyrim/role_rules.json")
    profile = profile_for(snapshot, {}, rules)
    recorder = Recorder()
    runner = PreviewRunner(recorder, PreviewLimits(response_timeout_ms=30000, model_cutoff_ms=29000, max_input_bytes=12000, max_output_tokens=160))
    turns = []
    with tempfile.TemporaryDirectory() as folder:
        store = SocialStore(Path(folder) / "s.sqlite3", memory_source="game_completed")
        key = store.key(Scope(game_id="skyrim", world_id="local-skyrim", save_branch_id="example"), "npc", "player")
        store.ensure(key, Relationship(), "neutral")
        for number in (1, 2):
            request = f"r{number}"
            recorder.reply = REPLIES[number - 1]
            first = len(recorder.prompts)
            state = store.load(key)
            state, _, _ = store.begin_turn(key, request, PlayerInput(text=QUESTION), profile.persona, state["revision"])
            speech = SpeechInput(session_id="s1", input_id=request, text=QUESTION)
            scenario = canonical_scenario(event, speech, profile, "local-skyrim", 0, social_state=state)
            result = await runner.run(scenario)
            prompt = recorder.prompts[first]
            turns.append({"turn": number, "player": QUESTION, "turn_type": getattr(result.plan, "turn_type", None), "move": result.plan.move,
                          "route": result.plan.route, "max_words": result.plan.max_words, "system": prompt.messages[0].content,
                          "data": json.loads(prompt.messages[1].content), "prompt_bytes": prompt.budget_bytes})
            store.stage_preview(key, request, {"result": {"response": recorder.reply}}, state["revision"])
            store.displayed(key, request)
        close = getattr(store, "close", None)
        if close:
            close()
    report = {"game_input": trim(game), "persona_from_rules": profile.persona.model_dump(mode="json"), "turns": turns, "expected_output": REPLIES[0]}
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"move": [t["move"] for t in turns], "route": [t["route"] for t in turns], "bytes": [t["prompt_bytes"] for t in turns]}))
    print("SYSTEM 2:\n" + turns[1]["system"])
    print("DATA 2:\n" + json.dumps(turns[1]["data"], ensure_ascii=False)[:1500])
    print("GAME:\n" + json.dumps(report["game_input"], ensure_ascii=False)[:1400])
    print("PERSONA:\n" + json.dumps(report["persona_from_rules"], ensure_ascii=False)[:900])


if __name__ == "__main__":
    asyncio.run(main())
