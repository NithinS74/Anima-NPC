from __future__ import annotations
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from PIL import Image, UnidentifiedImageError

ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg"}
ALLOWED_FORMATS = {"PNG", "JPEG"}


class ImageValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ValidatedImage:
    image: Image.Image
    width: int
    height: int
    content_type: str


def validate_image(data: bytes, content_type: str | None, max_bytes: int, max_dimension: int) -> ValidatedImage:
    if not data:
        raise ImageValidationError("Image upload is empty.")
    if len(data) > max_bytes:
        raise ImageValidationError(f"Image exceeds the {max_bytes} byte upload limit.")
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ImageValidationError("Only PNG and JPEG images are accepted.")
    try:
        with Image.open(BytesIO(data)) as candidate:
            candidate.verify()
        image = Image.open(BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ImageValidationError("Upload is not a valid decodable image.") from exc
    if image.format not in ALLOWED_FORMATS:
        raise ImageValidationError("Decoded image format must be PNG or JPEG.")
    if image.width > max_dimension or image.height > max_dimension:
        raise ImageValidationError(f"Image dimensions must not exceed {max_dimension}px.")
    # RGB avoids unsupported palette/alpha inputs downstream without changing original dimensions.
    return ValidatedImage(image.convert("RGB"), image.width, image.height, content_type)


def resize_for_model(image: Image.Image, max_edge: int) -> Image.Image:
    if max(image.size) <= max_edge:
        return image
    result = image.copy()
    result.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
    return result


def save_jpeg(image: Image.Image, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="JPEG", quality=88, optimize=True)
