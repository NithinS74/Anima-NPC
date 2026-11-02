import pytest
from pydantic import ValidationError
from app.schemas.scene_descriptor import Detection, ImageMetadata, PerformanceMs

def test_detection_mapping():
    assert Detection(class_id=0,label="person",confidence=.5,bbox_xyxy=(1,2,3,4)).label=="person"

def test_detection_confidence_validation():
    with pytest.raises(ValidationError): Detection(class_id=0,label="person",confidence=1.1,bbox_xyxy=(1,2,3,4))

def test_image_coordinate_contract():
    assert ImageMetadata(width=1,height=1).coordinate_convention=="xyxy_pixels_original_image"
