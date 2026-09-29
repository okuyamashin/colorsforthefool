#!/usr/bin/env python3
"""Generate the missing major-arcana faces from the Sun card's format."""

import base64
import json
import shutil
import sys
import time
import uuid
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = "gpt-image-2.5-sunburst"
SIZE = "1024x1536"
QUALITY = "high"

SCENES = {
    "the-fool": (
        "0",
        "THE FOOL",
        "A light-footed youth in ivory and spring green steps toward open air, a white rose in one hand, a small bundle on a staff, and a little dog at the heel. A soft cliff, bright empty sky, and spring flowers. Joyful and weightless. No fall, no fear.",
    ),
    "the-magician": (
        "I",
        "THE MAGICIAN",
        "A standing figure in a red outer robe and a white inner robe behind a garden table holding a wand, a cup, a sword, and a round pentacle. One hand is raised and the other points toward the earth. Roses and lilies grow around the table. A floral loop suggests infinity, with no written symbol.",
    ),
    "the-high-priestess": (
        "II",
        "THE HIGH PRIESTESS",
        "A seated woman in pale blue and silver between two pillars, a veil of still water behind her, a closed scroll in her lap, a crescent at her brow, and pomegranates along the frame. Quiet night, not darkness. No extra letters on the scroll.",
    ),
    "the-empress": (
        "III",
        "THE EMPRESS",
        "A seated woman crowned with stars among wheat, roses, and myrtle, wearing a gown the color of ripe grain. A waterfall, cushioned seat, and abundant garden. A small Venus emblem is an ornament, not a letter.",
    ),
    "the-emperor": (
        "IV",
        "THE EMPEROR",
        "A calm ruler seated on a stone throne carved with rams, a crimson cloak over armor, mountains behind him, and an ankh-shaped scepter held as an ornament. Stern daylight, Art Deco stone and gold. Not a photograph.",
    ),
    "the-hierophant": (
        "V",
        "THE HIEROPHANT",
        "A seated teacher in ceremonial ivory and crimson robes on a temple throne, two small acolytes before him, and crossed keys at his feet. A triple crown drawn as ornament. Quiet ritual, warm stone, no extra words.",
    ),
    "the-lovers": (
        "VI",
        "THE LOVERS",
        "Two clothed figures stand in a flowering garden while an angel above them opens both arms. Fruit trees behind one figure and a mountain behind the other. Tender daylight. No extra words.",
    ),
    "the-chariot": (
        "VII",
        "THE CHARIOT",
        "A standing armored figure under a starry canopy in an ornate chariot, with a black sphinx and a white sphinx resting before it and a walled city behind. A crescent on the shoulder. Victory and poise, not battle.",
    ),
    "strength": (
        "VIII",
        "STRENGTH",
        "A calm woman in a white gown and a flower garland gently closes a lion's mouth. Flowers form a soft infinity above her head, with no written symbol. A warm garden. Courage without violence.",
    ),
    "the-hermit": (
        "IX",
        "THE HERMIT",
        "An elder in a long taupe cloak stands on a high mountain path, holding a lantern that contains one bright star, and a wooden staff. Distant peaks and dusk blue air. Solitary and kind, not pitch black.",
    ),
    "wheel-of-fortune": (
        "X",
        "WHEEL OF FORTUNE",
        "A great ornate wheel turns in the clouds. A sphinx rests at the top. Small rising and descending figures circle it. Four winged creatures occupy quiet roundels around the wheel. No letters anywhere on the wheel.",
    ),
    "justice": (
        "XI",
        "JUSTICE",
        "A seated figure in a crimson robe holds an upright sword in one hand and balanced scales in the other. A pale veil hangs between two pillars. Clear daylight, calm and exact.",
    ),
    "the-hanged-man": (
        "XII",
        "THE HANGED MAN",
        "A serene clothed figure hangs upside down by one ankle from a living green tree, the other leg crossed, with a halo of soft light and a calm face. Peaceful suspension over still water. No suffering, no rope cutting the body.",
    ),
    "death": (
        "XIII",
        "DEATH",
        "A pale horse carries an armored rider with a white banner bearing a single white rose. Sunrise glows between two towers. A fallen crown lies in the flowers. Elegant transformation. No skeleton close-up, no blood, no gore.",
    ),
    "temperance": (
        "XIV",
        "TEMPERANCE",
        "An angel with one foot on stone and one foot in a clear pool pours water between two cups. Irises line the bank. A path leads toward a crown of light on a far hill. Luminous and balanced.",
    ),
    "the-devil": (
        "XV",
        "THE DEVIL",
        "An ornamental horned figure stands on a pedestal with a small torch, above two clothed figures whose decorative gold chains rest loosely and could be lifted off. Night colors inside the same floral frame. No gore, no horror, no nudity.",
    ),
    "the-tower": (
        "XVI",
        "THE TOWER",
        "A stone tower is struck by one gold lightning bolt. A crown falls. Two small clothed figures leap clear into the night. Firelight and dark blue sky, still inside the cream floral border. No blood.",
    ),
    "the-star": (
        "XVII",
        "THE STAR",
        "A woman in a pale gown kneels by a pool and pours water from two jugs, one onto the land and one into the water. One great eight-pointed star and seven smaller stars shine. A bird rests in a tree. Dawn-blue and hopeful. The figure is clothed.",
    ),
    "judgement": (
        "XX",
        "JUDGEMENT",
        "An angel in the clouds blows a long trumpet hung with a plain banner. Below, clothed people rise from open stone coffins with their arms lifted toward the light. Sea and mountains behind them. Hopeful, not grim. No text on the banner.",
    ),
    "the-world": (
        "XXI",
        "THE WORLD",
        "A dancing clothed figure stands inside a green laurel wreath tied with a flowing ribbon, holding two wands. Four small roundels in the scene show an angel, an eagle, a lion, and a bull. Joy, completion, and a bright sky.",
    ),
}


def load_key() -> str:
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("OPENAI_API_KEY="):
            key = line.split("=", 1)[1].strip().strip('"').strip("'")
            if key:
                return key
    sys.exit("OPENAI_API_KEY が .env にありません")


def prompt_for(numeral: str, title: str, scene: str) -> str:
    return (
        "Create a new vertical tarot card, using the reference image only as the format and craft guide. "
        "Match its Art Deco linework, cream paper margin, ornamental density, gold-green floral frame, "
        "watercolor illustration, and the placement of the numeral and the title banner. "
        "Do not copy the sun, the sunflowers, the woman in yellow, or the daylight landscape.\n\n"
        f"Top center, in the same small elegant lettering as the reference: {numeral}\n"
        f"Bottom center, on a cream banner, the English title exactly: {title}\n"
        "If the title is long, use smaller letters so the full title fits on one line inside the banner.\n\n"
        f"Inner scene, Art Deco illustration: {scene}\n\n"
        "No extra words, no watermark, no signature."
    )


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


def generate(card_id: str, prompt: str, reference: bytes, key: str) -> None:
    output_path = ROOT / "data" / card_id / "face.jpg"
    body, boundary = multipart(
        [
            ("model", MODEL),
            ("prompt", prompt),
            ("size", SIZE),
            ("quality", QUALITY),
            ("output_format", "jpeg"),
        ],
        [("image[]", "thesun.jpg", reference)],
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
    output_path.write_bytes(base64.b64decode(payload["data"][0]["b64_json"]))
    print(f"DONE {output_path.relative_to(ROOT)}", flush=True)


def main() -> None:
    sun_face = ROOT / "data" / "the-sun" / "face.jpg"
    shutil.copyfile(ROOT / "data" / "thesun.jpg", sun_face)
    print(f"COPIED {sun_face.relative_to(ROOT)}", flush=True)

    reference = (ROOT / "data" / "thesun.jpg").read_bytes()
    key = load_key()
    prompt_dir = ROOT / "prompts"
    prompt_dir.mkdir(exist_ok=True)
    failures: list[str] = []

    for card_id, (numeral, title, scene) in SCENES.items():
        output_path = ROOT / "data" / card_id / "face.jpg"
        if output_path.exists():
            print(f"SKIP {card_id}", flush=True)
            continue
        text = prompt_for(numeral, title, scene)
        (prompt_dir / f"{card_id}-face.txt").write_text(text + "\n", encoding="utf-8")
        print(f"START {card_id}", flush=True)
        for attempt in range(3):
            try:
                generate(card_id, text, reference, key)
                break
            except urllib.error.HTTPError as error:
                detail = error.read().decode("utf-8", errors="replace")[:500]
                print(f"ERROR {card_id} attempt {attempt + 1}: {error.code} {detail}", flush=True)
                if error.code in {429, 500, 503} and attempt < 2:
                    time.sleep(15 * (attempt + 1))
                    continue
                failures.append(card_id)
                break
            except Exception as error:  # noqa: BLE001
                print(f"ERROR {card_id} attempt {attempt + 1}: {error}", flush=True)
                if attempt < 2:
                    time.sleep(10)
                    continue
                failures.append(card_id)
                break
    if failures:
        sys.exit("failed: " + ", ".join(failures))


if __name__ == "__main__":
    main()
