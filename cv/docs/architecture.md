# Architecture

The standalone service receives a manually uploaded PNG/JPEG, verifies its bytes and decoded dimensions, then runs the configured Ultralytics YOLO model. The original RGB image and raw detection evidence are passed sequentially to Ollama. The VLM is instructed to return only evidence-conscious JSON. That JSON is validated into a provider-independent `SceneDescriptor` (v1.0); detector output remains separately available in the response.

Synchronous YOLO inference is dispatched to a worker thread so the FastAPI event loop can continue serving requests. VLM network I/O is asynchronous. The system never automatically downloads weights or pulls Ollama models.

Annotated outputs are saved beneath `datasets/annotated` with generated UUID filenames and retrieved only through `GET /api/v1/artifacts/{name}`. The artifact route rejects paths and extensions other than generated JPEGs.
