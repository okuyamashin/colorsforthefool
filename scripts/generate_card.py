#!/usr/bin/env python3
"""Generate one tarot face with the OpenAI Images API.

Reads OPENAI_API_KEY from .env in the project root. Never prints the key.
"""

import base64
import json
import sys
import uuid
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = "gpt-image-2.5-sunburst"
SIZE = "1024x1536"
QUALITY = "high"


def load_key() -> str:
    env_path = ROOT / ".env"
    for line in env_path.read_text().splitlines():
        if line.startswith("OPENAI_API_KEY="):
            key = line.split("=", 1)[1].strip().strip('"').strip("'")
            if key:
                return key
    sys.exit("OPENAI_API_KEY が .env にありません")


def multipart(fields: list[tuple[str, str]], files: list[tuple[str, str, bytes]]) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    chunks: list[bytes] = []
    for name, value in fields:
        chunks.append(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n".encode()
        )
    for name, filename, data in files:
        chunks.append(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
            f"Content-Type: image/jpeg\r\n\r\n".encode()
        )
        chunks.append(data)
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), boundary


def main() -> None:
    prompt_path = ROOT / "prompts" / "the-moon-face.txt"
    reference_path = ROOT / "data" / "thesun.jpg"
    output_path = ROOT / "data" / "the-moon" / "face.jpg"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    body, boundary = multipart(
        [
            ("model", MODEL),
            ("prompt", prompt_path.read_text().strip()),
            ("size", SIZE),
            ("quality", QUALITY),
            ("output_format", "jpeg"),
        ],
        [("image[]", reference_path.name, reference_path.read_bytes())],
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
