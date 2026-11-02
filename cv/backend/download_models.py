"""Explicitly download/check the configured YOLO weight; never runs at API startup."""

from app.config import settings


def main() -> int:
    try:
        from ultralytics import YOLO
        model = YOLO(settings.yolo_model)
        print(f"YOLO model ready: {settings.yolo_model} ({getattr(model, 'ckpt_path', 'managed by Ultralytics')})")
        return 0
    except Exception as error:
        print(f"Could not prepare YOLO model '{settings.yolo_model}': {error}")
        print("If yolo26n.pt is unavailable, set SKYRIM_CV_YOLO_MODEL=yolo11n.pt in backend\\.env and rerun.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
