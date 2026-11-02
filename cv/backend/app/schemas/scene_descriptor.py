from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4
from pydantic import BaseModel, Field, ConfigDict

SCHEMA_VERSION = "1.0"


class ImageMetadata(BaseModel):
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    coordinate_convention: Literal["xyxy_pixels_original_image"] = "xyxy_pixels_original_image"


class Detection(BaseModel):
    class_id: int = Field(ge=0)
    label: str = Field(min_length=1, max_length=120)
    confidence: float = Field(ge=0, le=1)
    bbox_xyxy: tuple[float, float, float, float]


class Environment(BaseModel):
    description: str | None = None
    location_guess: str | None = None
    visible_conditions: list[str] = Field(default_factory=list)


class Character(BaseModel):
    description: str
    identity: str | None = None
    position: str | None = None
    visible_attributes: list[str] = Field(default_factory=list)
    confidence_or_certainty: Literal["certain", "likely", "uncertain"] = "uncertain"


class SceneObject(BaseModel):
    label: str
    description: str | None = None
    position: str | None = None
    detector_class: str | None = None
    detector_confidence: float | None = Field(default=None, ge=0, le=1)
    bbox_xyxy: tuple[float, float, float, float] | None = None


class Provenance(BaseModel):
    detector_provider: str = "ultralytics"
    detector_model: str
    vlm_provider: str = "ollama"
    vlm_model: str


class PerformanceMs(BaseModel):
    preprocessing: float = Field(ge=0)
    detection: float = Field(ge=0)
    vlm: float = Field(ge=0)
    total: float = Field(ge=0)


class SceneDescriptor(BaseModel):
    """Provider-independent interpretation. Fields are visual claims, not game state."""
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    scene_id: str = Field(default_factory=lambda: str(uuid4()))
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    image: ImageMetadata
    environment: Environment = Field(default_factory=Environment)
    characters: list[Character] = Field(default_factory=list)
    objects: list[SceneObject] = Field(default_factory=list)
    player_actions: list[str] = Field(default_factory=list)
    spatial_relationships: list[str] = Field(default_factory=list)
    events: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    provenance: Provenance
    performance_ms: PerformanceMs


class AnalysisResponse(BaseModel):
    request_id: str
    status: Literal["completed"] = "completed"
    detections: list[Detection]
    scene_descriptor: SceneDescriptor
    artifacts: dict[str, str | None]
    performance_ms: PerformanceMs
