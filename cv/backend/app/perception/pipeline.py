from __future__ import annotations
import time
import asyncio
from pathlib import Path
from uuid import uuid4
from app.detection.yolo_detector import YoloDetector
from app.schemas.scene_descriptor import (AnalysisResponse, Character, Environment, ImageMetadata, PerformanceMs, Provenance, SceneDescriptor, SceneObject)
from app.services.image_service import ValidatedImage, save_jpeg
from app.vision.ollama_vlm import OllamaVLM, VLMValidationError
from starlette.concurrency import run_in_threadpool
from pydantic import ValidationError


class PipelineError(RuntimeError):
    def __init__(self, code: str, message: str): self.code, self.message = code, message; super().__init__(message)


class PerceptionPipeline:
    def __init__(self, detector: YoloDetector, vlm: OllamaVLM, artifact_dir: Path):
        self.detector, self.vlm, self.artifact_dir = detector, vlm, artifact_dir
        self._slot = asyncio.Lock()

    async def analyze(self, validated: ValidatedImage, preprocessing_ms: float = 0) -> AnalysisResponse:
        if self._slot.locked():
            raise PipelineError("CV_BUSY", "One image is already being analyzed.")
        await self._slot.acquire()
        task = asyncio.create_task(self._analyze(validated, preprocessing_ms))
        def settled(done):
            if not done.cancelled():
                done.exception()
            self._slot.release()
        task.add_done_callback(settled)
        # A disconnected/cancelled caller cannot release admission while a native
        # detector is still running in a worker thread.
        return await asyncio.shield(task)

    async def _analyze(self, validated: ValidatedImage, preprocessing_ms: float) -> AnalysisResponse:
        # Detector is synchronous; routes call this method from a worker thread for its blocking section.
        started = time.perf_counter()
        detected = await run_in_threadpool(self.detector.detect, validated.image)
        try:
            interpretation, vlm_ms = await self.vlm.analyze(validated.image, detected.detections)
        except VLMValidationError as exc:
            raise PipelineError("VLM_INVALID_OUTPUT", str(exc)) from exc
        except Exception as exc:
            raise PipelineError("VLM_UNAVAILABLE", str(exc)) from exc
        total_ms = (time.perf_counter() - started) * 1000
        request_id = str(uuid4())
        artifact_name = f"{request_id}.jpg"
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        # Keep at most 100 annotated frames; admission serializes retention/writes.
        old = sorted(self.artifact_dir.glob("*.jpg"), key=lambda p: p.stat().st_mtime)
        while len(old) >= 100:
            old.pop(0).unlink(missing_ok=True)
        save_jpeg(detected.annotated_image, self.artifact_dir / artifact_name)
        perf = PerformanceMs(preprocessing=preprocessing_ms, detection=detected.duration_ms, vlm=vlm_ms, total=total_ms + preprocessing_ms)
        def model_list(key: str, model):
            value = interpretation.get(key, [])
            return [model.model_validate(v) for v in value] if isinstance(value, list) else []

        def normalize_environment(env: dict) -> dict:
            if not isinstance(env, dict):
                return {}
            normalized = dict(env)
            vc = normalized.get("visible_conditions")
            if isinstance(vc, str):
                normalized["visible_conditions"] = [vc]
            elif not isinstance(vc, list):
                normalized["visible_conditions"] = []
            return normalized

        def normalize_character(char: dict) -> dict:
            if not isinstance(char, dict):
                return {}
            normalized = dict(char)
            va = normalized.get("visible_attributes")
            if isinstance(va, str):
                normalized["visible_attributes"] = [va]
            elif not isinstance(va, list):
                normalized["visible_attributes"] = []
            cc = normalized.get("confidence_or_certainty")
            if isinstance(cc, str):
                normalized["confidence_or_certainty"] = cc.lower()
            return normalized

        def safe_model_list(key: str, model, normalizer=None):
            value = interpretation.get(key, [])
            if not isinstance(value, list):
                return []
            if normalizer:
                value = [normalizer(v) for v in value]
            return [model.model_validate(v) for v in value]

        def extract_strings(key: str) -> list[str]:
            value = interpretation.get(key, [])
            if not isinstance(value, list):
                return []
            result = []
            for item in value:
                if isinstance(item, str):
                    result.append(item)
                elif isinstance(item, dict):
                    # Try common description fields
                    for field in ("description", "label", "text", "summary"):
                        if field in item and isinstance(item[field], str):
                            result.append(item[field])
                            break
            return result

        try:
            descriptor = SceneDescriptor(
                image=ImageMetadata(width=validated.width, height=validated.height),
                environment=Environment.model_validate(normalize_environment(interpretation.get("environment", {}))),
                characters=safe_model_list("characters", Character, normalize_character),
                objects=[SceneObject(label=d.label, description=d.label, detector_class=d.label, detector_confidence=d.confidence, bbox_xyxy=d.bbox_xyxy) for d in detected.detections] + model_list("objects", SceneObject),
                player_actions=extract_strings("player_actions"),
                spatial_relationships=extract_strings("spatial_relationships"),
                events=extract_strings("events"),
                uncertainties=extract_strings("uncertainties"),
                provenance=Provenance(detector_provider="none" if self.detector.model_name == "disabled" else "ultralytics", detector_model=self.detector.model_name, vlm_model=self.vlm.model), performance_ms=perf,
            )
        except ValidationError as exc:
            raise PipelineError("VLM_INVALID_OUTPUT", "VLM JSON did not conform to the scene descriptor contract.") from exc
        return AnalysisResponse(request_id=request_id, detections=detected.detections, scene_descriptor=descriptor, artifacts={"annotated_image": f"/api/v1/artifacts/{artifact_name}"}, performance_ms=perf)
