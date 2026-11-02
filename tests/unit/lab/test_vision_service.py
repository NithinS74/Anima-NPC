import asyncio
from datetime import datetime, timezone

from npc.generation.provider import OfflineProvider
from npc.vision import VisualContext
from tools.npc_lab.service import LabService, LabTurn


class FakeCV:
    async def analyze(self, image, content_type):
        assert image == b"png" and content_type == "image/png"
        return VisualContext(id="cv-scene", captured_at=datetime.now(timezone.utc), environment="A visible forge", uncertainties=("Not NPC knowledge",))


def test_visual_selection_is_memory_only_and_must_be_explicitly_attached():
    async def run():
        service = LabService(OfflineProvider(), cv_client=FakeCV())
        selected = await service.analyze_visual(b"png", "image/png")
        assert selected["visual"]["id"] == "cv-scene"
        profile = service.profiles["mira"]
        turn = LabTurn(request_id="cv-turn", persona_id="mira", text="What do you see?", relationship=profile.relationship, mood=profile.mood, visual_id="cv-scene")
        result = await service.turn(turn)
        assert result["visual_context"]["environment"] == "A visible forge"
        assert result["context"]["visual_context"]["id"] == "cv-scene"
        assert all(fact["id"] != "cv-scene" for fact in result["context"]["perceived_facts"])
    asyncio.run(run())


def test_unknown_visual_id_is_rejected():
    async def run():
        service = LabService(OfflineProvider(), cv_client=FakeCV())
        profile = service.profiles["mira"]
        turn = LabTurn(request_id="cv-turn", persona_id="mira", text="Hello", relationship=profile.relationship, mood=profile.mood, visual_id="cv-missing")
        try:
            await service.turn(turn)
        except ValueError as error:
            assert str(error) == "unknown visual context"
        else:
            raise AssertionError("unknown visual ID must fail")
    asyncio.run(run())
