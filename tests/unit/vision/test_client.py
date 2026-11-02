from datetime import datetime, timezone

import pytest

from npc.vision.client import CVFailure, VisualContext, normalize_scene_response, validate_cv_url


def payload():
    return {"request_id": "request-1", "scene_descriptor": {"scene_id": "scene-1", "captured_at": "2026-11-01T00:00:00Z",
        "environment": {"description": "A dim tavern"}, "characters": [{"description": "A person at a counter"}],
        "objects": [{"description": "A wooden table"}], "uncertainties": ["Identity is unknown"],
        "provenance": {"detector_model": "yolo26n", "vlm_model": "qwen2.5vl-3b"}}}


def test_normalizes_only_compact_visual_reference_fields():
    visual = normalize_scene_response(payload())
    assert visual.id == "cv-scene-1"
    assert visual.prompt_payload()["environment"] == "A dim tavern"
    assert visual.prompt_payload()["objects"] == ("A wooden table",)


@pytest.mark.parametrize("url", ["https://127.0.0.1:8000", "http://example.com", "http://user@127.0.0.1:8000", "http://127.0.0.1:8000/path"])
def test_rejects_non_loopback_or_non_origin_cv_urls(url):
    with pytest.raises(ValueError):
        validate_cv_url(url)


def test_rejects_malformed_upstream_payload():
    with pytest.raises(CVFailure, match="cv_invalid_response"):
        normalize_scene_response({"scene_descriptor": {"environment": {}}})
