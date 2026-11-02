"""Run: python yolo_only.py /path/to/screenshot.png"""
import json, sys
from pathlib import Path
from PIL import Image
from app.config import settings
from app.detection.yolo_detector import YoloDetector
from app.services.image_service import save_jpeg
if len(sys.argv) != 2: raise SystemExit("usage: python yolo_only.py IMAGE")
image = Image.open(sys.argv[1]).convert("RGB")
result = YoloDetector(settings.yolo_model, settings.yolo_confidence, settings.yolo_image_size, settings.device).detect(image)
out = settings.artifact_dir / "yolo-preview.jpg"; save_jpeg(result.annotated_image, out)
print(json.dumps({"device": result.device, "duration_ms": result.duration_ms, "detections": [x.model_dump() for x in result.detections], "annotated_image": str(out)}, indent=2))
