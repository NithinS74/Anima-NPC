from contextlib import asynccontextmanager
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.config import settings
from app.detection.yolo_detector import YoloDetector
from app.perception.pipeline import PerceptionPipeline
from app.vision.ollama_vlm import OllamaVLM

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Deliberately lazy: /ready reports availability without forcing model download/startup inference.
    settings.artifact_dir.mkdir(parents=True, exist_ok=True)
    cutoff = time.time() - settings.artifact_ttl_seconds
    for output in settings.artifact_dir.glob("*.jpg"):
        if output.stat().st_mtime < cutoff: output.unlink(missing_ok=True)
    app.state.pipeline = PerceptionPipeline(YoloDetector(settings.yolo_model, settings.yolo_confidence, settings.yolo_image_size, settings.device), OllamaVLM(settings.ollama_host, settings.ollama_model, settings.ollama_timeout_seconds), settings.artifact_dir)
    yield

app = FastAPI(title="Skyrim CV", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.origins, allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
app.include_router(router)
