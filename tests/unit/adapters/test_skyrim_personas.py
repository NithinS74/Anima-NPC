"""Default characters, scene context and session-start openings for the Skyrim adapter. Offline only."""

import asyncio
import json
import time
from pathlib import Path

from npc.adapters.skyrim.bridge import Bridge
from npc.adapters.skyrim.personas import build_scene, derive_persona, load_rules
from npc.adapters.skyrim.protocol import (
    ActorData, Form, GameEvent, GameSnapshot, NpcProfile, Settings, SpeechInput, canonical_scenario, profile_for,
)
from npc.behavior.lines import pools
from npc.behavior.policy import choose_plan
from npc.context import build_situation
from npc.contracts.context import Persona
from npc.generation.prompt import build_prompt

RULES = load_rules(Path(__file__).resolve().parents[3] / "configs" / "skyrim" / "role_rules.json")


def form(identifier="00013478", name="", plugin="Skyrim.esm"):
    return Form(form_id=identifier, local_id=identifier, name=name, plugin=plugin)


def snapshot(base="Villager", factions=(), equipment=(), ref="000D15B0", race="Nord", location="Whiterun",
             sees=True, player_gear=("Iron Sword",), weather="raining", interior=False, **npc_changes):
    npc = ActorData(reference=form(ref), base=form("00013B9F", base), race=form("00013746", race), in_combat=False, dead=False,
                    weapon_drawn=False, sees_player=sees,
                    factions=tuple(form(i, n) for i, n in factions), equipment=tuple(form("0001398A", n) for n in equipment),
                    **npc_changes)
    player = ActorData(reference=form("00000014", "Player"), base=form("00000007", "Player"), in_combat=False, dead=False,
                       weapon_drawn=True, equipment=tuple(form("00012EB7", n) for n in player_gear))
    return GameSnapshot(npc=npc, player=player, hour=14.0, game_days=2.0, interior=interior, weather_label=weather,
                        location=form("00016772", location) if location else None)


def persona(**kwargs):
    return derive_persona(snapshot(**kwargs), RULES)


def test_real_shaped_snapshots_map_to_roles():
    guard = persona(base="Whiterun Guard", factions=[("0002BE39", "Whiterun Guard"), ("00086EEE", "GuardFaction (makes an actor a guard)")],
                    equipment=["Imperial Sword"])
    assert guard.occupation == "city guard"
    assert persona(base="Courier").occupation == "courier"
    smith = persona(base="Ulfberth War-Bear", factions=[("0009CAFF", "Warmaidens")], equipment=["Steel Warhammer"])
    assert smith.occupation == "blacksmith" and smith.service_role and smith.services
    merc = persona(base="Jenassa", factions=[("000BCC9A", "Hireling")])
    assert merc.occupation == "mercenary"
    assert persona(base="Olava the Feeble", race="Old People Race").occupation == "elder"
    # Faction ID alone matches when the engine gave no faction name.
    assert persona(base="Someone", factions=[("00086EEE", "")]).occupation == "city guard"
    assert persona(base="Bjorn", equipment=["Pickaxe"]).occupation == "miner"


def test_unknown_npc_is_a_townsperson_not_unknown():
    p = persona(base="Amren", factions=[("000267EA", "Whiterun")])
    assert (p.occupation, p.social_role) == ("townsperson", "local resident")
    assert p.goals and p.boundaries and not p.services


def test_authored_profile_wins():
    snap = snapshot(base="Whiterun Guard")
    authored = NpcProfile(persona=Persona(name="Custom", occupation="poet", social_role="dreamer"))
    assert profile_for(snap, {snap.npc.base.definition_key: authored}, RULES).persona.occupation == "poet"
    assert profile_for(snap, {}, RULES).persona.occupation == "city guard"
    assert profile_for(snap, {}).persona.occupation == "unknown"  # no rules file: old behaviour


def test_traits_vary_deterministically_by_id():
    a1, a2 = persona(ref="000D15B0"), persona(ref="000D15B0")
    assert a1 == a2
    others = {persona(ref=f"000D{i:04X}").model_dump_json() for i in range(1, 8)}
    assert len(others) > 3
    for item in (persona(ref=f"000E{i:04X}") for i in range(8)):
        assert all(0 <= v <= 1 for v in (item.warmth, item.caution, item.patience, item.assertiveness))


def test_common_knowledge_and_location():
    p = persona(base="Amren", factions=[("000267EA", "Whiterun")])
    assert p.location == "Whiterun"
    assert 3 <= len(p.common_knowledge) <= 6
    joined = " ".join(p.common_knowledge)
    assert "Tamriel" in joined and "Balgruuf" in joined and "dragons" in joined.lower()
    nowhere = persona(location=None)
    assert nowhere.location is None and not any("Jarl is" in line for line in nowhere.common_knowledge)
    assert all("quest" not in line.lower() for line in p.common_knowledge)


def scenario_for(snap, text="Where am I?", social=None):
    event = GameEvent(kind="start", sequence=1, event_id="e1", session_id="s1", game_epoch="g", game_pid=1,
                      captured_at_ms=int(time.time() * 1000), snapshot=snap)
    profile = profile_for(snap, {}, RULES)
    return canonical_scenario(event, SpeechInput(session_id="s1", input_id="i1", text=text), profile, "w", 1)


def test_knowledge_and_scene_reach_prompt_within_connector_budget_and_quest_data_does_not():
    snap = snapshot(base="Whiterun Guard", factions=[("0002BE39", "Whiterun Guard")], equipment=["Imperial Sword"])
    from npc.adapters.skyrim.protocol import DialogueOption
    quest = DialogueOption(topic=form("00099999", "SECRETQUESTTOPIC"), player_text="THE SECRET LINE", quest=form("0001AAAA", "SECRETQUEST"), quest_stage=40)
    snap = snap.model_copy(update={"dialogue": (quest,)})
    sc = scenario_for(snap)
    situation = build_situation(sc.turn, sc.snapshot, sc.now)
    prompt = build_prompt(situation, choose_plan(situation), max_input_bytes=12000)
    text = " ".join(m.content for m in prompt.messages)
    assert prompt.budget_bytes <= 12000 and not prompt.sections_dropped
    assert "Tamriel" in text and "Balgruuf" in text and '"location":"Whiterun"' in text
    assert "raining" in text and "Imperial Sword" in text and "Iron Sword" in text and "drawn" in text and "afternoon" in text
    for hidden in ("SECRET", "quest_stage", "THE SECRET LINE"):
        assert hidden not in text


def test_scene_is_bounded_and_dropped_before_identity_when_budget_is_tight():
    snap = snapshot(base="Whiterun Guard", factions=[("0002BE39", "Whiterun Guard")],
                    equipment=["A" * 400], player_gear=("B" * 400,))
    scene = build_scene(snap)
    assert len(scene) <= 8 and all(len(i.value) <= 80 and len(i.label) <= 32 for i in scene)
    sc = scenario_for(snap)
    situation = build_situation(sc.turn, sc.snapshot, sc.now)
    plan = choose_plan(situation)
    full = build_prompt(situation, plan, max_input_bytes=12000)
    tight = build_prompt(situation, plan, max_input_bytes=full.budget_bytes - 300)
    assert "scene" in tight.sections_dropped or "common_knowledge" in tight.sections_dropped
    assert tight.messages[0].content.count("NPC_CONTEXT") == 1 and '"name":' in tight.messages[0].content


def test_scene_hides_player_details_when_npc_cannot_see_player():
    labels = {i.label for i in build_scene(snapshot(sees=False))}
    assert "place" in labels and "time" in labels
    assert not labels & {"player_gear", "player_weapon"}


# ---- openings -------------------------------------------------------------------------------------------------

def start_event(snap=None, direct=True):
    return GameEvent(kind="start", direct=direct, sequence=1, state_revision=1, event_id="e1", session_id="s1", game_epoch="g", game_pid=1,
                     captured_at_ms=int(time.time() * 1000), snapshot=snap or snapshot(base="Whiterun Guard"))


def make_bridge(tmp_path, **changes):
    options = dict(opening_delay_s=0.0, state_db=str(tmp_path / "social.sqlite3"))
    s = Settings(game_directory=str(tmp_path / "game"), output_directory=str(tmp_path / "output"), audio_root=str(tmp_path / "audio"),
                 capture_screenshots=False, **{**options, **changes})
    return Bridge(s, root=Path(__file__).resolve().parents[3])


def test_opening_delivered_once_not_a_player_turn(tmp_path):
    async def run():
        bridge = make_bridge(tmp_path, opening_lines=True)
        try:
            await bridge.game_event(start_event())
            await bridge.session.opening_task
            command = bridge.command("s1")
            allowed = {line for table in pools()["opening"].values() for line in table}
            assert command["kind"] == "speak" and command["text"] in allowed
            assert command["request_id"].startswith("opening-")
            assert bridge.command("s1")["text"] == command["text"]
            # Once: no second opening, no player memory.
            assert bridge.session.opening_task.done()
            assert bridge.session.social_state is None and bridge.session.social_key is None
            await bridge.game_event(GameEvent(kind="delivery", sequence=2, event_id="e2", session_id="s1", game_epoch="g", game_pid=1,
                                              captured_at_ms=1, delivery_id=command["delivery_id"], status="completed"))
            assert bridge.state_store is not None
            key = bridge.state_store.key(__import__("npc.contracts.context", fromlist=["Scope"]).Scope(
                game_id="skyrim", world_id="local-skyrim", save_branch_id="g"), "ref:000d15b0", "ref:00000014")
            assert not bridge.state_store.ensure(key, __import__("npc.contracts.context", fromlist=["Relationship"]).Relationship(), "neutral")["history"]
        finally:
            await bridge.close()
    asyncio.run(run())


def test_opening_off_by_default_and_skipped_when_hostile(tmp_path):
    async def run():
        bridge = make_bridge(tmp_path)
        try:
            await bridge.game_event(start_event())
            assert bridge.session.opening_task is None and bridge.command("s1")["kind"] == "idle"
        finally:
            await bridge.close()
        hostile = snapshot(base="Whiterun Guard", hostile_to_player=True)
        bridge = make_bridge(tmp_path, opening_lines=True)
        try:
            await bridge.game_event(start_event(hostile))
            await bridge.session.opening_task
            assert bridge.command("s1")["kind"] == "idle"
        finally:
            await bridge.close()
    asyncio.run(run())


def test_player_input_cancels_pending_opening_and_replaces_staged_one(tmp_path):
    async def run():
        bridge = make_bridge(tmp_path, opening_lines=True, state_db=None)
        bridge.settings = bridge.settings.model_copy(update={"opening_delay_s": 5})
        try:
            await bridge.game_event(start_event())
            task = bridge.session.opening_task
            await bridge.player_input(SpeechInput(session_id="s1", input_id="in1", text="Hello"))
            await asyncio.sleep(0)
            assert task.cancelled() or task.done()
            assert bridge.command("s1")["kind"] == "idle"
        finally:
            await bridge.close()
        # Staged opening: speaking replaces it with a stop instead of a busy error.
        bridge = make_bridge(tmp_path, opening_lines=True, state_db=None)
        try:
            await bridge.game_event(start_event())
            await bridge.session.opening_task
            assert bridge.command("s1")["kind"] == "speak"
            await bridge.player_input(SpeechInput(session_id="s1", input_id="in2", text="Hello"))
            assert bridge.command("s1")["kind"] == "stop"
        finally:
            await bridge.close()
    asyncio.run(run())


def test_vanilla_menu_session_gets_no_opening(tmp_path):
    async def run():
        bridge = make_bridge(tmp_path, opening_lines=True)
        try:
            await bridge.game_event(start_event(direct=False))
            assert bridge.session.opening_task is None and bridge.command("s1")["kind"] == "idle"
        finally:
            await bridge.close()
    asyncio.run(run())


def test_direct_flag_is_optional_and_defaults_false():
    assert start_event().direct is True
    plain = GameEvent.model_validate({k: v for k, v in start_event().model_dump(mode="json").items() if k != "direct"})
    assert plain.direct is False
