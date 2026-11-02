# Models, portability, and licensing notes

Default: VLM-only (`SKYRIM_CV_ENABLE_DETECTOR=false`), using `qwen2.5vl:3b` through local Ollama. Pull explicitly: `ollama pull qwen2.5vl:3b`. No detector dependency or weight download is required. The incoming legacy YOLO wrapper remains optional; enable it only after a separately reviewed pinned dependency/weights setup and resource check. Its configured model name is `SKYRIM_CV_YOLO_MODEL`.

COCO-pretrained YOLO is a general-object baseline; it cannot reliably recognize Skyrim-specific NPC identities, factions, weapons, quests, or game state. The VLM likewise must be treated as uncertain visual interpretation.

Before distributing weights or using this in a commercial product, the owner must review current Ultralytics licensing (AGPL/commercial terms), each selected model's license and acceptable-use terms, and Ollama's distribution terms. This project makes no legal conclusion and does not bundle model weights.
