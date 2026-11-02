# Architecture

The service receives a PNG/JPEG from manual upload or the Skyrim connector and validates its bytes/dimensions before decoding. Default VLM-only mode supplies an empty detector result explicitly. The retained optional YOLO wrapper can supply detections when independently configured. The bounded RGB image and detector evidence go to local Ollama; JSON is validated into `SceneDescriptor` v1.0. One admitted analysis at a time prevents inference queues; cancelling a caller retains admission until native work settles. Annotated output retains at most 100 images.

Synchronous YOLO inference is dispatched to a worker thread so the FastAPI event loop can continue serving requests. VLM network I/O is asynchronous. The system never automatically downloads weights or pulls Ollama models.

Annotated outputs are saved beneath `datasets/annotated` with generated UUID filenames and retrieved only through `GET /api/v1/artifacts/{name}`. The artifact route rejects paths and extensions other than generated JPEGs.
