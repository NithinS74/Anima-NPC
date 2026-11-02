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
    with pytest.raises(PipelineError, match="bad json"):
        await PerceptionPipeline(FakeDetector(),BadVLM(),tmp_path).analyze(valid_image())

@pytest.mark.asyncio
async def test_pipeline_normalizes_malformed_environment(tmp_path):
    # ContractBreakingVLM returns string for environment; normalization should handle it
    result = await PerceptionPipeline(FakeDetector(),ContractBreakingVLM(),tmp_path).analyze(valid_image())
    assert result.scene_descriptor.environment.description is None
    assert result.scene_descriptor.environment.visible_conditions == []
