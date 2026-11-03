# Scene Descriptor schema v1.0

`SceneDescriptor` is a Pydantic v2 contract intended to remain independent of Ultralytics and Ollama. `bbox_xyxy` is `(left, top, right, bottom)` in pixels relative to the original uploaded image. `detections` in the API response is raw detector evidence. `objects` in the descriptor may include copies of that evidence plus VLM descriptions; VLM-only content never receives invented detector confidence.

Fields for actions, events, identity and location are intentionally nullable/empty. `uncertainties` must preserve limitations in the source image or model interpretation.
