#!/usr/bin/env python3
"""One mirror-scene card per orientation, using the Sun color cards as the format."""

import argparse
import base64
import json
import sys
import threading
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_card import MODEL, QUALITY, ROOT, SIZE, load_key, multipart

TEXT_MODEL = "gpt-4.1-mini"
LOCK = threading.Lock()
BASIC = {
    "Black", "White", "Red", "Green", "Blue", "Yellow", "Orange", "Pink", "Purple",
    "Brown", "Gray", "Grey", "Gold", "Silver", "Tan", "Cyan", "Aqua", "Magenta",
    "Fuchsia", "Lime", "Navy", "Teal", "Indigo", "Maroon", "Olive",
}


def jobs() -> list[dict]:
    found = []
    for path in sorted((ROOT / "data").glob("*/card.json")):
        data = json.loads(path.read_text())
        for orientation, label in (("upright", "正位置"), ("reversed", "逆位置")):
            colors = [color for color in data[orientation] if not color.get("image")]
            if not colors:
                continue
            chosen = next((color for color in colors if color["name"] not in BASIC), colors[0])
            essay_path = path.parent / chosen["text"]
            found.append(
                {
                    "id": data["id"],
                    "card": data["name"],
                    "label": label,
                    "orientation": orientation,
                    "color": chosen["name"],
                    "hex": chosen["hex"],
                    "colorJa": chosen["nameJa"],
                    "essay": essay_path.read_text(encoding="utf-8"),
                    "file": chosen["name"].lower() + ".jpg",
                }
            )
    return found


def post_json(key: str, url: str, payload: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.load(response)


def brief(key: str, job: dict) -> dict:
    ask = f"""Read this Japanese essay and return JSON only.
Keys: mirror, objects.
mirror: one English sentence describing the night or day landscape seen inside an oval mirror. The light in that landscape is {job["color"]} {job["hex"]}, shown as illumination on things, not as a flat fill. No people unless the essay's action needs one small distant figure. No written words.
objects: an array of exactly 5 physical objects that appear in the essay, in English, suitable for an ornamental frame and a foreground still life.
Card: {job["card"]} {job["label"]}
Essay:
{job["essay"][:1800]}
"""
    payload = post_json(
        key,
        "https://api.openai.com/v1/chat/completions",
        {
            "model": TEXT_MODEL,
            "temperature": 0.4,
            "messages": [
                {"role": "system", "content": "Return one JSON object and nothing else."},
                {"role": "user", "content": ask},
            ],
        },
    )
    text = payload["choices"][0]["message"]["content"].strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    data = json.loads(text)
    objects = [str(item) for item in data["objects"]][:5]
    if len(objects) < 3 or not data.get("mirror"):
        raise ValueError("brief incomplete")
    return {"mirror": str(data["mirror"]), "objects": objects}


def scene_prompt(job: dict, scene: dict) -> str:
    objects = ", ".join(scene["objects"])
    return (
        "Create a vertical illustrated card in the exact format of the reference images. "
        "Use them only as the format guide: cream paper margin, dense Art Deco floral frame, "
        "and a large ornate oval mirror in the center that opens onto a landscape. "
        "Do not copy their sunlit harbor, lemons, maps, compass, boots, satchel, canteen, "
        "yellow daylight, or any lettering.\n\n"
        f"This card's light is {job['color']} ({job['hex']}). Show it as light on the landscape and objects. "
        "Do not paint the whole card one flat color. No words, no letters, no numbers, no watermark.\n\n"
        f"Inside the mirror: {scene['mirror']}\n\n"
        f"Around the mirror and in the foreground, weave only these objects into the frame, "
        f"at the same density as the references: {objects}. Keep the cream outer margin.\n\n"
        "No text, no signature."
    )


def generate_image(key: str, prompt: str, references: list[tuple[str, bytes]]) -> bytes:
    body, boundary = multipart(
        [
            ("model", MODEL),
            ("prompt", prompt),
            ("size", SIZE),
            ("quality", QUALITY),
            ("output_format", "jpeg"),
        ],
        [("image[]", name, data) for name, data in references],
    )
    request = urllib.request.Request(
        "https://api.openai.com/v1/images/edits",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        payload = json.load(response)
    return base64.b64decode(payload["data"][0]["b64_json"])


def attach(job: dict) -> None:
    path = ROOT / "data" / job["id"] / "card.json"
    with LOCK:
        data = json.loads(path.read_text())
        for color in data[job["orientation"]]:
            if color["name"] == job["color"]:
                color["image"] = job["file"]
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def one(key: str, job: dict, references: list[tuple[str, bytes]]) -> str:
    output = ROOT / "data" / job["id"] / job["file"]
    if output.exists():
        attach(job)
        return f"SKIP {job['id']} {job['orientation']} {job['color']}"
    last = "未生成"
    for _attempt in range(3):
        try:
            scene = brief(key, job)
            image = generate_image(key, scene_prompt(job, scene), references)
            output.write_bytes(image)
            attach(job)
            return f"DONE {job['id']} {job['orientation']} {job['color']}"
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:300]
            last = f"API {error.code} {detail}"
        except Exception as error:  # noqa: BLE001
            last = str(error)
    return f"FAIL {job['id']} {job['orientation']} {job['color']} {last}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--card", default="")
    args = parser.parse_args()
    pending = jobs()
    if args.card:
        pending = [job for job in pending if job["id"] == args.card]
    if args.limit:
        pending = pending[: args.limit]
    print(f"PENDING {len(pending)}", flush=True)
    for job in pending:
        print(f"PLAN {job['id']} {job['orientation']} {job['color']}", flush=True)
    if not pending:
        return
    key = load_key()
    references = [
        ("thesun_cornsilk.jpg", (ROOT / "data" / "thesun_cornsilk.jpg").read_bytes()),
        ("thesun_darkkhaki.jpg", (ROOT / "data" / "thesun_darkkhaki.jpg").read_bytes()),
    ]
    failures = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(one, key, job, references) for job in pending]
        for future in as_completed(futures):
            line = future.result()
            print(line, flush=True)
            if line.startswith("FAIL"):
                failures += 1
    if failures:
        sys.exit(f"failed {failures}")


if __name__ == "__main__":
    main()
