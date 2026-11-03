"""Run: python vlm_only.py /path/to/screenshot.png"""
import asyncio, json, sys
from PIL import Image
from app.config import settings
from app.vision.ollama_vlm import OllamaVLM
if len(sys.argv) != 2: raise SystemExit("usage: python vlm_only.py IMAGE")
async def run():
 result, ms = await OllamaVLM(settings.ollama_host, settings.ollama_model, settings.ollama_timeout_seconds).analyze(Image.open(sys.argv[1]).convert("RGB"), [])
 print(json.dumps({"duration_ms": ms, "result": result}, indent=2))
asyncio.run(run())
