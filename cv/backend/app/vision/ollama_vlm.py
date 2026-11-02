from __future__ import annotations
import base64, json, time
from io import BytesIO
import httpx
from PIL import Image
from app.schemas.scene_descriptor import Detection


class VLMUnavailableError(RuntimeError): pass
class VLMValidationError(RuntimeError): pass

PROMPT = """Analyze this Skyrim gameplay screenshot. YOLO detections below are supporting evidence only and may be wrong. Return ONLY JSON with keys: environment (object: description, location_guess, visible_conditions), characters (array: description, identity, position, visible_attributes, confidence_or_certainty where certainty is certain/likely/uncertain), objects (array: label, description, position), player_actions (array), spatial_relationships (array), events (array), uncertainties (array). Report only visible facts; use null or empty values when unknown. Never claim exact NPC identity, player intent, game state, or an action unless visually clear. Detections: """


class OllamaVLM:
    def __init__(self, host: str, model: str, timeout_seconds: float):
        self.host, self.model, self.timeout_seconds = host.rstrip("/"), model, timeout_seconds

    async def readiness(self) -> tuple[bool, str]:
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                response = await client.get(f"{self.host}/api/tags")
                response.raise_for_status()
                names = {m.get("name") for m in response.json().get("models", [])}
            return (self.model in names, "model available" if self.model in names else f"model '{self.model}' is not pulled")
        except httpx.HTTPError as exc:
            return False, f"Ollama unavailable: {exc.__class__.__name__}"

    async def analyze(self, image: Image.Image, detections: list[Detection]) -> tuple[dict, float]:
        buffer = BytesIO(); image.save(buffer, format="JPEG", quality=90)
        evidence = [d.model_dump(mode="json") for d in detections]
        payload = {"model": self.model, "prompt": PROMPT + json.dumps(evidence), "images": [base64.b64encode(buffer.getvalue()).decode()], "stream": False, "format": "json", "options": {"temperature": 0}}
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(f"{self.host}/api/generate", json=payload)
                response.raise_for_status()
                content = response.json().get("response", "")
        except httpx.TimeoutException as exc:
            raise VLMUnavailableError("Ollama request timed out.") from exc
        except httpx.HTTPError as exc:
            raise VLMUnavailableError("Configured local VLM provider is unavailable.") from exc
        try:
            parsed = json.loads(content)
            if not isinstance(parsed, dict): raise ValueError("not an object")
        except (json.JSONDecodeError, ValueError) as exc:
            raise VLMValidationError("VLM returned invalid JSON; no scene descriptor was fabricated.") from exc
        return parsed, (time.perf_counter() - started) * 1000
