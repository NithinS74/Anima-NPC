"""Opt-in real-service smoke test: CV screenshot -> Anima bridge -> Context Builder.

Start the CV API on 8000 and CV-enabled Anima on 8766 before running this.
No provider credentials are required: Anima's offline provider is sufficient.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

CV_ROOT = Path(__file__).resolve().parents[1]


def request_json(url: str, *, body: bytes | None = None, headers: dict[str, str] | None = None, timeout: int = 130):
    request = Request(url, data=body, headers=headers or {}, method="POST" if body is not None else "GET")
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, default=CV_ROOT / "samples" / "sky1.jpeg")
    parser.add_argument("--cv-url", default="http://127.0.0.1:8000")
    parser.add_argument("--anima-url", default="http://127.0.0.1:8766")
    args = parser.parse_args()
    if not args.image.is_file() or args.image.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
        print("Image must be an existing PNG/JPEG.", file=sys.stderr)
        return 2
    content_type = "image/png" if args.image.suffix.lower() == ".png" else "image/jpeg"
    try:
        health = request_json(f"{args.cv_url}/health", timeout=5)
        if health != {"status": "ok"}:
            raise RuntimeError("CV health response was unexpected")
        with urlopen(f"{args.anima_url}/", timeout=5) as response:
            page = response.read().decode("utf-8")
        token_match = re.search(r'<meta name="lab-token" content="([^"]+)">', page)
        if not token_match:
            raise RuntimeError("could not read Anima local session token")
        token = token_match.group(1)
        info = request_json(f"{args.anima_url}/api/info", timeout=5)
        if not info.get("cv_enabled"):
            raise RuntimeError("Anima was not started with --cv-url")
        headers = {"Content-Type": content_type, "Origin": args.anima_url, "X-Lab-Token": token}
        visual_result = request_json(f"{args.anima_url}/api/vision/analyze", body=args.image.read_bytes(), headers=headers)
        visual = visual_result["visual"]
        mira = next(profile for profile in info["profiles"] if profile["id"] == "mira")
        turn = {
            # Greeting uses Anima's deterministic authored route so this test
            # remains independent of an optional RAG index or paid model.
            "request_id": f"e2e-{uuid.uuid4()}", "persona_id": "mira", "text": "Hello",
            "relationship": mira["relationship"], "mood": mira["mood"], "state": "available", "weapon_drawn": False,
            "state_revision": mira["state_revision"], "visual_id": visual["id"],
        }
        result = request_json(f"{args.anima_url}/api/turn", body=json.dumps(turn).encode("utf-8"),
                              headers={"Content-Type": "application/json", "Origin": args.anima_url, "X-Lab-Token": token})
    except (HTTPError, URLError, KeyError, RuntimeError, json.JSONDecodeError) as error:
        print(f"E2E FAILED: {error}", file=sys.stderr)
        return 1
    context_visual = result.get("context", {}).get("visual_context")
    if context_visual != visual or result.get("visual_context") != visual:
        print("E2E FAILED: Scene Descriptor did not reach Anima Context Builder.", file=sys.stderr)
        return 1
    if any(fact.get("id") == visual["id"] for fact in result["context"].get("perceived_facts", [])):
        print("E2E FAILED: CV descriptor was incorrectly promoted to trusted ObservedFact.", file=sys.stderr)
        return 1
    if result["result"]["status"] not in {"model_success", "repair_success", "authored_success"}:
        print(f"E2E FAILED: dialogue turn did not complete successfully ({result['result']['status']}).", file=sys.stderr)
        return 1
    print("E2E PASSED")
    print(json.dumps({"visual_id": visual["id"], "environment": visual.get("environment"),
                      "context_visual_id": context_visual["id"], "turn_status": result["result"]["status"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
