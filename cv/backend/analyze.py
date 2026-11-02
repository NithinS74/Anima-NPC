"""Run: python analyze.py /path/to/screenshot.png"""
import asyncio, json, sys
from pathlib import Path
from app.config import settings
from app.detection.yolo_detector import YoloDetector, NoDetector
from app.perception.pipeline import PerceptionPipeline
from app.services.image_service import validate_image
from app.vision.ollama_vlm import OllamaVLM
if len(sys.argv) != 2: raise SystemExit("usage: python analyze.py IMAGE")
path = Path(sys.argv[1]); kind = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
image = validate_image(path.read_bytes(), kind, settings.max_upload_bytes, settings.max_image_dimension)
async def run():
 detector = YoloDetector(settings.yolo_model, settings.yolo_confidence, settings.yolo_image_size, settings.device) if settings.enable_detector else NoDetector()
 p = PerceptionPipeline(detector, OllamaVLM(settings.ollama_host, settings.ollama_model, settings.ollama_timeout_seconds), settings.artifact_dir)
 print((await p.analyze(image)).model_dump_json(indent=2))
asyncio.run(run())
