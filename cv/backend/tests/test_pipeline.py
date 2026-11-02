from io import BytesIO
from pathlib import Path
import pytest
from PIL import Image
from app.detection.yolo_detector import DetectionResult
from app.perception.pipeline import PerceptionPipeline, PipelineError
from app.schemas.scene_descriptor import Detection
from app.services.image_service import validate_image
from app.vision.ollama_vlm import VLMValidationError

class FakeDetector:
    model_name="fake-yolo"
    def detect(self, image): return DetectionResult([Detection(class_id=0,label="person",confidence=.9,bbox_xyxy=(1,2,8,9))], image.copy(), 2, "cpu")
class FakeVLM:
    model="fake-vlm"
    async def analyze(self, image, detections): return ({"environment":{"description":"an interior"},"characters":[],"objects":[],"uncertainties":["still image"],"player_actions":[],"spatial_relationships":[],"events":[]}, 3)
class BadVLM:
    model="fake-vlm"
    async def analyze(self, image, detections): raise VLMValidationError("bad json")
class ContractBreakingVLM:
    model="fake-vlm"
    async def analyze(self, image, detections): return ({"environment":"not an object"}, 1)

class InvalidCharacterVLM:
    model="fake-vlm"
    async def analyze(self, image, detections): return ({"characters": [{"description": None}]}, 1)

class EmptyVLM:
    model="fake-vlm"
    async def analyze(self, image, detections): return ({}, 1)

def valid_image():
    out=BytesIO(); Image.new("RGB",(10,10)).save(out,"PNG"); return validate_image(out.getvalue(),"image/png",1000,100)

@pytest.mark.asyncio
async def test_pipeline_produces_descriptor_and_artifact(tmp_path):
    result=await PerceptionPipeline(FakeDetector(),FakeVLM(),tmp_path).analyze(valid_image())
    assert result.scene_descriptor.provenance.detector_model=="fake-yolo"
    assert (tmp_path / f"{result.request_id}.jpg").is_file()

@pytest.mark.asyncio
async def test_pipeline_rejects_malformed_vlm_output(tmp_path):
    with pytest.raises(PipelineError, match="bad json"):
        await PerceptionPipeline(FakeDetector(),BadVLM(),tmp_path).analyze(valid_image())

@pytest.mark.asyncio
async def test_pipeline_rejects_vlm_json_that_breaks_schema(tmp_path):
    with pytest.raises(PipelineError, match="did not conform"):
        await PerceptionPipeline(FakeDetector(),InvalidCharacterVLM(),tmp_path).analyze(valid_image())

@pytest.mark.asyncio
async def test_pipeline_normalizes_malformed_environment(tmp_path):
    # ContractBreakingVLM returns string for environment; normalization should handle it
    result = await PerceptionPipeline(FakeDetector(),ContractBreakingVLM(),tmp_path).analyze(valid_image())
    assert result.scene_descriptor.environment.description is None
    assert result.scene_descriptor.environment.visible_conditions == []


@pytest.mark.asyncio
async def test_cancelled_request_keeps_native_inference_slot_until_settled(tmp_path):
    import asyncio
    import threading
    class SlowDetector(FakeDetector):
        started = threading.Event()
        release = threading.Event()
        def detect(self, image):
            self.started.set()
            assert self.release.wait(5)
            return super().detect(image)
    detector = SlowDetector()
    pipeline = PerceptionPipeline(detector, FakeVLM(), tmp_path)
    task = asyncio.create_task(pipeline.analyze(valid_image()))
    try:
        assert await asyncio.to_thread(detector.started.wait, 2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError): await task
        with pytest.raises(PipelineError, match="already being analyzed"):
            await pipeline.analyze(valid_image())
    finally:
        detector.release.set()
    for _ in range(200):
        if not pipeline._slot.locked(): break
        await asyncio.sleep(.005)
    assert not pipeline._slot.locked()
    assert (await pipeline.analyze(valid_image())).scene_descriptor.environment.description == "an interior"


@pytest.mark.asyncio
async def test_vlm_only_mode_and_artifact_retention(tmp_path):
    from app.detection.yolo_detector import NoDetector
    for index in range(100):
        (tmp_path / f"{index}.jpg").write_bytes(b"old")
    result = await PerceptionPipeline(NoDetector(), FakeVLM(), tmp_path).analyze(valid_image())
    assert result.detections == []
    assert result.scene_descriptor.provenance.detector_provider == "none"
    assert len(list(tmp_path.glob("*.jpg"))) == 100
