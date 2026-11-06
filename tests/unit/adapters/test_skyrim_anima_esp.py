import importlib.util
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


dump = _load("dump_esp")
gen = _load("build_anima_esp")
MANTELLA = Path("D:/MO2/mods/Mantella/Mantella.esp")


def groups(items):
    return {g.label.decode(): g for g in items if isinstance(g, dump.Group)}


@pytest.fixture(scope="module")
def parsed():
    data = gen.build_esp()
    return data, dump.parse_esp(data)


def test_generation_is_deterministic():
    assert gen.build_esp() == gen.build_esp()


def test_header_masters_flags_and_form_version(parsed):
    _data, items = parsed
    header = items[0]
    assert header.type == "TES4" and header.version == 44
    assert header.flags == 0, "plain ESP like Mantella: not light (ESL), so voice-file form IDs are predictable"
    assert [dump.cstring(m) for m in header.sub("MAST")] == ["Skyrim.esm"]
    assert len(header.sub("DATA")) == 1
    assert struct.unpack("<f", header.sub("HEDR")[0][:4])[0] == pytest.approx(1.7)


def test_group_nesting_and_sizes(parsed):
    data, items = parsed
    assert [g.label for g in items[1:]] == [b"DIAL", b"QUST", b"DLBR"]
    for group in items[1:]:
        assert group.group_type == 0
    top = groups(items)
    topic, children = top["DIAL"].children[:2]
    assert topic.type == "DIAL" and children.group_type == 7
    assert children.label == struct.pack("<I", topic.form_id)
    assert [c.type for c in children.children] == ["INFO"]
    pairs = list(zip(top["DIAL"].children[::2], top["DIAL"].children[1::2]))
    assert len(pairs) == 3 and all(t.type == "DIAL" and g.group_type == 7 and g.label == struct.pack("<I", t.form_id)
                                   and [c.type for c in g.children] == ["INFO"] for t, g in pairs)
    # Sizes: parse_block verifies exact consumption; also the header sizes add up to the file length.
    assert 71 + 24 + sum(g.size for g in items[1:]) == len(data)
    assert top["DIAL"].size == 24 + sum((24 + t.size) + g.size for t, g in pairs)
    assert children.size == 24 + 24 + children.children[0].size


def test_records_are_all_in_the_light_range(parsed):
    _data, items = parsed
    ids = [r.form_id for g in items[1:] for r in g.walk() if isinstance(r, dump.Record)]
    assert len(ids) == len(set(ids)) == 8
    for form_id in ids:
        assert form_id >> 24 == 1 and 0x800 <= form_id & 0xFFFFFF <= 0xFFF


def test_quest_dialogue_and_script_links(parsed):
    _data, items = parsed
    top = groups(items)
    quest = top["QUST"].children[0]
    flags, priority, _version, _unknown, _kind = struct.unpack("<HBBII", quest.sub("DNAM")[0])
    assert flags & 0x0001, "Start Game Enabled"
    topic = top["DIAL"].children[0]
    branch = top["DLBR"].children[0]
    info = top["DIAL"].children[1].children[0]
    u32 = lambda blob: struct.unpack("<I", blob)[0]
    assert u32(topic.sub("QNAM")[0]) == quest.form_id == u32(branch.sub("QNAM")[0])
    assert u32(topic.sub("BNAM")[0]) == branch.form_id and u32(branch.sub("SNAM")[0]) == topic.form_id
    assert u32(branch.sub("DNAM")[0]) & 1, "top-level branch"
    assert topic.sub("DATA")[0] == b"\0\0\0\0" and topic.sub("SNAM")[0] == b"CUST"
    assert dump.cstring(topic.sub("FULL")[0]) == "Talk with me." == dump.cstring(info.sub("RNAM")[0])
    assert u32(info.sub("ENAM")[0]) & 1, "Goodbye closes the menu after starting the conversation"
    assert not info.sub("CTDA") and not info.sub("TRDT"), "no conditions, response comes from the shared info"
    assert u32(info.sub("DNAM")[0]) == 0x000DBA22
    vmad = info.sub("VMAD")[0]
    version, object_format, count = struct.unpack_from("<hhH", vmad)
    assert (version, object_format, count) == (5, 2, 1)
    assert vmad.count(b"AnimaStartDialogue") == 3 and vmad.endswith(b"\x0a\x00Fragment_0")
    assert b"AnimaNative" not in vmad


def test_papyrus_fragment_calls_the_registered_native():
    root = ROOT / "src/npc/adapters/skyrim"
    assert "AnimaNative.OpenConversation()" in (root / "papyrus/AnimaStartDialogue.psc").read_text(encoding="utf-8")
    assert "Function OpenConversation() Global Native" in (root / "papyrus/AnimaNative.psc").read_text(encoding="utf-8")
    plugin = (root / "native/plugin.cpp").read_text(encoding="utf-8")
    assert 'RegisterFunction("OpenConversation", "AnimaNative"' in plugin


@pytest.mark.skipif(not MANTELLA.is_file(), reason="Mantella.esp reference not installed")
def test_structure_matches_the_mantella_control_line(parsed):
    _data, items = parsed
    reference = dump.parse_esp(MANTELLA.read_bytes())
    ref_header = reference[0]
    assert (ref_header.version, [dump.cstring(m) for m in ref_header.sub("MAST")][0]) == (items[0].version, "Skyrim.esm")
    ref = groups(reference)
    ref_topic = next(r for r in ref["DIAL"].children if isinstance(r, dump.Record) and dump.cstring(r.sub("EDID")[0]) == "MantellaConversationControlTopic")
    ref_quest = next(r for r in ref["QUST"].children if dump.cstring(r.sub("EDID")[0]) == "MantellaDialogue")
    ref_branch = next(r for r in ref["DLBR"].children if dump.cstring(r.sub("EDID")[0]) == "MantellaConversationControl")
    ref_info = next(r for r in ref["DIAL"].walk() if isinstance(r, dump.Record) and r.type == "INFO" and r.sub("ENAM") and r.sub("RNAM") and b"Start Mantella" in r.sub("RNAM")[0])
    mine = groups(items)
    topic, info = mine["DIAL"].children[0], mine["DIAL"].children[1].children[0]
    quest, branch = mine["QUST"].children[0], mine["DLBR"].children[0]
    assert topic.sub("DATA") == ref_topic.sub("DATA") and topic.sub("SNAM") == ref_topic.sub("SNAM") and topic.sub("PNAM") == ref_topic.sub("PNAM")
    assert quest.sub("DNAM") == ref_quest.sub("DNAM") and quest.sub("ANAM") == ref_quest.sub("ANAM")
    assert branch.sub("DNAM") == ref_branch.sub("DNAM") and branch.sub("TNAM") == ref_branch.sub("TNAM")
    for tag in ("ENAM", "PNAM", "CNAM", "DNAM"):
        assert info.sub(tag) == ref_info.sub(tag), tag
    assert [k for k, _ in info.subrecords if k != "CTDA"][:1] == [k for k, _ in ref_info.subrecords][:1] == ["VMAD"]
    assert [k for k, _ in quest.subrecords] == [k for k, _ in ref_quest.subrecords]
    assert dict(items[0].subrecords)["INTV"] == dict(ref_header.subrecords)["INTV"]


def test_speech_topics_match_the_bridge_file_names_and_are_unconditional(parsed):
    from npc.adapters.skyrim.say_output import INFO_FORM_IDS, QUEST_PREFIX, TOPIC_PREFIX, voice_stem
    _data, items = parsed
    top = groups(items)
    quest = top["QUST"].children[0]
    assert dump.cstring(quest.sub("EDID")[0])[:10] == QUEST_PREFIX
    children = top["DIAL"].children
    for index, (topic, group) in enumerate(zip(children[2::2], children[3::2]), start=1):
        info = group.children[0]
        name = dump.cstring(topic.sub("EDID")[0])
        assert name == f"AnimaSpeechLine{index}" and name[:15] == TOPIC_PREFIX
        assert topic.form_id & 0xFFFFFF == 0x804 + 2 * (index - 1)
        assert info.form_id & 0xFFFFFF == INFO_FORM_IDS[index]
        assert struct.unpack("<I", topic.sub("QNAM")[0])[0] == quest.form_id
        assert struct.unpack("<I", info.sub("TPIC")[0])[0] == topic.form_id
        assert not info.sub("CTDA") and dump.cstring(info.sub("NAM1")[0]) == "..."
        assert voice_stem(index) == f"AnimaDialo_AnimaSpeechLine_{INFO_FORM_IDS[index]:08X}_1"
        assert len(voice_stem(index).split("_")[0]) == 10 and len(voice_stem(index).split("_")[1]) == 15
    assert struct.unpack("<fII", items[0].sub("HEDR")[0])[2] == 0x808


@pytest.mark.skipif(not MANTELLA.is_file(), reason="Mantella.esp reference not installed")
def test_speech_topics_copy_the_mantella_line_topics(parsed):
    _data, items = parsed
    reference = groups(dump.parse_esp(MANTELLA.read_bytes()))["DIAL"].children
    ref = {dump.cstring(r.sub("EDID")[0]): r for r in reference if isinstance(r, dump.Record) and r.type == "DIAL"}
    ref_info = [r for r in reference[0:] if isinstance(r, dump.Group)]
    mine = groups(items)["DIAL"].children
    for topic, theirs in ((mine[2], ref["MantellaDialogueLine"]), (mine[4], ref["MantellaDialogueLine2"])):
        for tag in ("PNAM", "DATA", "SNAM", "TIFC"):
            assert topic.sub(tag) == theirs.sub(tag), tag
    theirs_info = next(r for g in ref_info for r in g.children if r.form_id & 0xFFFFFF == 0x1D8B)
    mine_info = mine[3].children[0]
    for tag in ("ENAM", "PNAM", "CNAM", "TRDT", "NAM1", "NAM2", "NAM3"):
        assert mine_info.sub(tag) == theirs_info.sub(tag), tag
