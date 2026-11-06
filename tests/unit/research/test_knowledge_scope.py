import importlib.util
import json
import shutil
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[3] / "research/cs3235_paper/experiments/knowledge_scope.py"
spec = importlib.util.spec_from_file_location("knowledge_scope", PATH)
ks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ks)


def row(level="low", route="generate", exposed=(), own=True, kind="direct"):
    return dict(level=level, route=route, exposed=list(exposed), own_marker_present=own, kind=kind)


def test_published_study_data_is_valid():
    ks.validate_study(ks.load_study())


def test_marker_match_ignores_case_and_reports_only_hits():
    assert ks.markers_in("the OPERATION greywater file", ["Operation Greywater", "Black Lantern"]) == ["Operation Greywater"]
    assert ks.markers_in("nothing here", ["Black Lantern"]) == []


def test_non_generated_turns_leave_every_denominator():
    summary = ks.summarize([row(), row(route="authored", exposed=["x"], own=False)])
    assert summary["turns"] == 2 and summary["non_generated_turns"] == 1
    assert summary["restricted_exposure"] == {"n": 0, "of": 1, "rate": 0.0}
    assert summary["own_knowledge_available"] == {"n": 1, "of": 1, "rate": 1.0}


def test_top_role_is_excluded_from_exposure_but_counts_for_availability():
    summary = ks.summarize([row(level="top", own=False), row(level="mid", exposed=["secret"], own=True)])
    assert summary["restricted_exposure"] == {"n": 1, "of": 1, "rate": 1.0}
    assert summary["own_knowledge_available"] == {"n": 1, "of": 2, "rate": 0.5}
    assert summary["top"]["own_knowledge_available"]["n"] == 0


def test_empty_subset_has_no_rate_instead_of_a_false_zero():
    assert ks.summarize([])["restricted_exposure"] == {"n": 0, "of": 0, "rate": None}


def test_bindings_separate_conditions():
    study = ks.load_study()
    merged = {name: f"merged_{name}.md" for name in study["worlds"]}
    assert {b["source"] for b in ks.bindings(study, merged, "unscoped")} == set(merged.values())
    scoped = ks.bindings(study, merged, "scoped")
    assert len({b["source"] for b in scoped}) == 6
    assert not {b["source"] for b in scoped} & set(merged.values())


@pytest.fixture
def copied(tmp_path):
    target = tmp_path / "data"
    shutil.copytree(ks.DATA, target)
    return target


def test_validation_rejects_query_that_supplies_a_restricted_marker(copied):
    study = json.loads((copied / "study.json").read_text(encoding="utf-8"))
    study["worlds"]["kingdom"]["queries"][0]["text"] = "Tell me about Operation Greywater."
    with pytest.raises(ValueError, match="K01"):
        ks.validate_study(study, copied)


def test_validation_rejects_role_file_holding_its_own_restricted_fact(copied):
    file = copied / "kingdom/peasant.md"
    file.write_text(file.read_text(encoding="utf-8") + "\nThe Black Lantern pays for it.", encoding="utf-8")
    with pytest.raises(ValueError, match="peasant.md"):
        ks.validate_study(ks.load_study(copied), copied)


def test_validation_rejects_role_file_missing_its_answer(copied):
    file = copied / "kingdom/peasant.md"
    file.write_text(file.read_text(encoding="utf-8").replace("old river road", "other road"), encoding="utf-8")
    with pytest.raises(ValueError, match="old river road"):
        ks.validate_study(ks.load_study(copied), copied)


def test_scoped_retrieval_cannot_expose_higher_role_text(tmp_path):
    """End-to-end through the real runner with a fake retrieval backend that honours source."""
    import asyncio

    study = ks.load_study()
    merged = ks.build_corpus(study, tmp_path)
    corpus = tmp_path / "corpus"

    class Backend:
        def retrieve(self, query, top_k, max_chars, source):
            from types import SimpleNamespace

            # Return each file's tail, where a merged file holds its highest-standing role section.
            text = (corpus / source).read_text(encoding="utf-8")[-900:]
            match = dict(id="chunk-0", source=source, text=text, chunk_index=0, distance=0.1, truncated=False)
            return SimpleNamespace(model_dump=lambda: dict(query=query, context="", matches=[match]))

    rows = asyncio.run(ks.run_condition(study, merged, "scoped", Backend()))
    generated = [r for r in rows if r["route"] == "generate"]
    assert generated and all(r["evidence_chunks"] for r in generated)
    assert not any(r["exposed"] for r in generated)
    baseline = asyncio.run(ks.run_condition(study, merged, "unscoped", Backend()))
    assert any(r["exposed"] for r in baseline if r["route"] == "generate")
