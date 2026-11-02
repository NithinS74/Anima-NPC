# Models, portability, and licensing notes

Default detector: `yolo26n.pt`, configured via `SKYRIM_CV_YOLO_MODEL`. If it is unavailable with the installed Ultralytics release, use `yolo11n.pt` and record the change. Default VLM: `qwen2.5vl:3b` served by local Ollama. Pull manually: `ollama pull qwen2.5vl:3b`.

COCO-pretrained YOLO is a general-object baseline; it cannot reliably recognize Skyrim-specific NPC identities, factions, weapons, quests, or game state. The VLM likewise must be treated as uncertain visual interpretation.

Before distributing weights or using this in a commercial product, the owner must review current Ultralytics licensing (AGPL/commercial terms), each selected model's license and acceptable-use terms, and Ollama's distribution terms. This project makes no legal conclusion and does not bundle model weights.
