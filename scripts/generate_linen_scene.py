#!/usr/bin/env python3
"""One Moon linen scene card, using the Sun color cards as format references."""

import base64
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_card import MODEL, QUALITY, ROOT, SIZE, load_key, multipart


def main() -> None:
    prompt = (ROOT / "prompts" / "the-moon-linen-scene.txt").read_text().strip()
    references = [
        ROOT / "data" / "thesun_cornsilk.jpg",
        ROOT / "data" / "thesun_darkkhaki.jpg",
    ]
    output_path = ROOT / "data" / "the-moon" / "linen.jpg"
    body, boundary = multipart(
        [
            ("model", MODEL),
            ("prompt", prompt),
            ("size", SIZE),
            ("quality", QUALITY),
            ("output_format", "jpeg"),
        ],
        [("image[]", path.name, path.read_bytes()) for path in references],
    )
    request = urllib.request.Request(
        "https://api.openai.com/v1/images/edits",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {load_key()}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        sys.exit(f"API error {error.code}: {detail[:2000]}")
    output_path.write_bytes(base64.b64decode(payload["data"][0]["b64_json"]))
    print(output_path)


if __name__ == "__main__":
    main()
