from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_ROOT / ".env", env_prefix="SKYRIM_CV_", extra="ignore")
    yolo_model: str = "yolo26n.pt"
    enable_detector: bool = False
    yolo_confidence: float = 0.25
    yolo_image_size: int = 640
    device: str = "auto"
    ollama_host: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5vl:3b"
    ollama_timeout_seconds: float = 90.0
    max_upload_bytes: int = 10 * 1024 * 1024
    max_image_dimension: int = 8192
    artifact_ttl_seconds: int = 3600
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    artifact_dir: Path = PROJECT_ROOT / "datasets/annotated"

    @property
    def origins(self) -> list[str]:
        return [v.strip() for v in self.allowed_origins.split(",") if v.strip()]


settings = Settings()
