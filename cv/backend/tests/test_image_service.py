from io import BytesIO
import pytest
from PIL import Image
from app.services.image_service import ImageValidationError, validate_image

def png_bytes():
    out=BytesIO(); Image.new("RGB", (20, 10), "red").save(out, "PNG"); return out.getvalue()

def test_accepts_png():
    image=validate_image(png_bytes(), "image/png", 10000, 100)
    assert (image.width, image.height, image.image.mode)==(20,10,"RGB")

@pytest.mark.parametrize("data,content_type", [(b"not image", "image/png"),(png_bytes(), "text/plain")])
def test_rejects_invalid_content(data, content_type):
    with pytest.raises(ImageValidationError): validate_image(data, content_type, 10000, 100)

def test_rejects_oversized_byte_upload():
    with pytest.raises(ImageValidationError): validate_image(png_bytes(), "image/png", 2, 100)


def test_rejects_large_dimensions_before_decoding(monkeypatch):
    raw = png_bytes()
    def load(*args, **kwargs): raise AssertionError("pixel decoding must not run")
    monkeypatch.setattr(Image.Image, "load", load)
    with pytest.raises(ImageValidationError): validate_image(raw, "image/png", 10000, 5)
