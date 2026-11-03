from io import BytesIO
from fastapi.testclient import TestClient
from PIL import Image
from app.main import app

def image_bytes():
    out=BytesIO(); Image.new("RGB",(2,2)).save(out,"PNG");return out.getvalue()

def test_health(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "enable_detector", False)
    with TestClient(app) as client:
        assert client.get("/health").json()=={"status":"ok"}
        assert app.state.pipeline.detector.model_name == "disabled"

def test_bad_upload_rejected():
    with TestClient(app) as client:
        response=client.post("/api/v1/analyze",files={"image":("bad.txt",b"x","text/plain")})
    assert response.status_code==422 and response.json()["detail"]["code"]=="INVALID_IMAGE"
