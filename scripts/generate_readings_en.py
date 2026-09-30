#!/usr/bin/env python3
"""Write one English card-color essay per assigned color. Skips files that already exist."""

import argparse
import json
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = "gpt-4.1"
LOCK = threading.Lock()

NOTES = {
    "the-fool": (
        "A light step at the cliff's edge, innocence, the start of a journey, a rose and a small dog.",
        "Lightness that skips the check. A leap while the footing is still unseen.",
    ),
    "the-magician": (
        "Will, and four tools: wand, cup, sword, and coin. At a garden table, above joins below.",
        "The tools are in hand, and their uses get switched. The model becomes a trick.",
    ),
    "the-high-priestess": (
        "Two pillars, a veil, a closed scroll, still water. The secret is still kept.",
        "The secret becomes a wall. The scroll stays closed, and the water does not answer.",
    ),
    "the-empress": (
        "Wheat, roses, and a garden. Fruit, a seat, a waterfall. Abundance is already around.",
        "The garden is let go. Shelter grows heavy, and the harvest does not reach the table.",
    ),
    "the-emperor": (
        "A stone seat, a boundary, mountains, a settled procedure. Order keeps the road.",
        "Only the procedure remains, and the seat is empty. Hardness becomes the purpose.",
    ),
    "the-hierophant": (
        "Keys, vestments, a temple, two attendants. An inherited way becomes tonight's procedure.",
        "Only the rite is repeated, and the meaning leaves its seat. A push against the form.",
    ),
    "the-lovers": (
        "Two people, a garden, an open choice. The bond begins in the choosing.",
        "They stand side by side without choosing. Words dry before they reach the other.",
    ),
    "the-chariot": (
        "A canopy, two beasts, a city gate. Forward motion when the reins are paired.",
        "The two beasts face different ways. Moving itself becomes the only aim.",
    ),
    "strength": (
        "A flower crown, a hand gently closing a lion's mouth. Force makes no noise.",
        "Force turns into forcing. The more the lion is pinned, the stiffer the hand.",
    ),
    "the-hermit": (
        "A high road, a staff, one lamp. Solitude keeps the lit range close to the hand.",
        "Staying on the mountain with the lamp put out. Refusal of people becomes the road.",
    ),
    "wheel-of-fortune": (
        "A turning wheel, the seasons, rising and falling on the same axle.",
        "The turn faces downward. A wish to stop it, a hand set on it before the turn completes.",
    ),
    "justice": (
        "A sword and scales, a hanging cloth, a clear noon. Cause and result sit at the same table.",
        "The scales are left tilted. A correct procedure spins empty because someone is absent.",
    ),
    "the-hanged-man": (
        "A living tree, stillness turned upside down, a halo. Stopping changes the view.",
        "Unable to stop. Or stopped, and refusing what the stop means.",
    ),
    "death": (
        "A rider holding a pale flower, dawn between two towers. An ending makes the next outline.",
        "Refusing to let it end. An old crown kept in the hand, the dawn unseen.",
    ),
    "temperance": (
        "Water passing between two cups, a pool, a path to the ridge. Mixing is the work.",
        "Water spills outside the cup. Before the mix, the balance tips to one side.",
    ),
    "the-devil": (
        "A pedestal, a torch, chains that come loose when slackened. Desire is a tool while it is seen.",
        "The chains are already loose. Either the shadow is denied, or one sits still wearing the chain as ornament.",
    ),
    "the-tower": (
        "One stroke of lightning, a falling crown, a tower at night. What was kept inside comes out by the collapse.",
        "The collapse is postponed. The rubble is still called a tower.",
    ),
    "the-star": (
        "A pool, two pitchers, one great star and smaller stars. Hope is returning water to the ground.",
        "The pool's edge dries. The stars are there, and the pitchers are left where they were set down.",
    ),
    "the-moon": (
        "A path only half visible, a dog and a wolf, the tide, towers. The outline stays on the side of thin light.",
        "Another night settles on the path. Dog and wolf can no longer be told apart, and mist takes the names back.",
    ),
    "the-sun": (
        "The light has already come. Outlines that were unseen return to the hand.",
        "The light is too strong, and the road and the cloth lose their depth. Dryness, sand, shoes from a long walk.",
    ),
    "judgement": (
        "A horn above the clouds, open coffins, people standing up. The call is already sounding.",
        "The call has been heard, and someone still sits on the coffin's edge. The answer is put off until tomorrow.",
    ),
    "the-world": (
        "A wreath of leaves, a dancer, four living creatures. One circuit closes, and a ribbon is tied.",
        "The wreath stays half open. Just before the end, the hand leaves the knot.",
    ),
}

COLOR_WORDS = re.compile(
    r"\b(gold|golden|black|white|red|blue|silver|green|yellow|purple|gray|grey|pink|orange|brown)\b",
    re.I,
)


def load_key() -> str:
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("OPENAI_API_KEY="):
            key = line.split("=", 1)[1].strip().strip('"').strip("'")
            if key:
                return key
    sys.exit("OPENAI_API_KEY が .env にありません")


def jobs() -> list[dict]:
    found = []
    for path in sorted((ROOT / "data").glob("*/card.json")):
        data = json.loads(path.read_text())
        for orientation, label in (("upright", "Upright"), ("reversed", "Reversed")):
            for color in data[orientation]:
                if not color.get("text"):
                    continue
                filename = color["name"].lower() + ".en.txt"
                target = path.parent / filename
                if color.get("textEn") == filename and target.exists():
                    continue
                found.append(
                    {
                        "id": data["id"],
                        "name": data["name"],
                        "orientation": orientation,
                        "label": label,
                        "note": NOTES[data["id"]][0 if orientation == "upright" else 1],
                        "color": color["name"],
                        "hex": color["hex"],
                        "file": filename,
                    }
                )
    return found


def prompt_for(job: dict) -> str:
    return f"""You write one tarot lucky-color essay in English. Quiet, concrete, explanatory prose. This is an original English essay, not a translation and not a retelling of any other essay.

Card: {job["name"]}
Orientation: {job["label"]}
The core of this orientation: {job["note"]}
The color to land on: {job["color"]} / {job["hex"]}
Turn what the English name {job["color"]} refers to — an object, place, food, cloth, plant, trade, or kind of weather — into the story's concrete things. Do not discuss hue or how close it is to another color.

Rules:
- The first line is exactly: {job["name"]} ― {job["label"]}
- One movement. Follow only the things that name refers to. Do not point at the color midway with phrases like "this color is".
- Do not use the color's name, or these everyday color words, anywhere before the closing color lines: black, white, red, blue, silver, green, yellow, purple, gray, grey, pink, orange, brown, gold, golden. Name things instead.
- Do not use other CSS color names.
- Open from the card's symbols, then weave myth, geography, history, weather, and household tools into that same movement.
- Three or four small things a person can do today, as extensions of objects already in the story. Write them as sentences, not a list.
- The name {job["color"]} appears only in the two closing lines below, never in the title or the body. Do not split that name with a space.
- A few paragraphs, separated by blank lines. No headings, no bullets, no bold, no "let's".
- Length of the body, before the closing lines: 480 to 700 words.
- End with these two lines copied exactly, including the ASCII apostrophe and the em dash. Do not change the color name's spelling or spacing:
Today's lucky color is {job["color"]}.
Lucky Color: {job["color"]} — {job["hex"]}
- After that, you may add up to two short lines that do not repeat the color name.
- Return only the essay. No preamble.
"""


def complete(key: str, messages: list[dict]) -> str:
    body = json.dumps(
        {
            "model": MODEL,
            "temperature": 0.8,
            "messages": messages,
        }
    ).encode()
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        payload = json.load(response)
    text = payload["choices"][0]["message"]["content"].strip()
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    text = re.sub(r"^```[a-zA-Z]*\n", "", text)
    text = re.sub(r"\n```$", "", text)
    return "\n".join(line.rstrip() for line in text.strip().splitlines()) + "\n"


def closing(job: dict) -> tuple[str, str]:
    reveal = f"Today's lucky color is {job['color']}."
    lucky = f"Lucky Color: {job['color']} — {job['hex']}"
    return reveal, lucky


def mentions_name(color: str, head: str) -> bool:
    spaced = re.sub(r"(?<!^)(?=[A-Z])", " ", color)
    for form in {color, spaced}:
        if re.search(rf"\b{re.escape(form)}\b", head, re.I):
            return True
    return False


def valid(job: dict, text: str) -> str | None:
    reveal, lucky = closing(job)
    lines = text.strip().splitlines()
    if not lines or lines[0].strip() != f"{job['name']} ― {job['label']}":
        return "title"
    if text.count(reveal) != 1:
        return "reveal"
    if text.count(lucky) != 1:
        return "lucky"
    if re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", text):
        return "japanese"
    head = text.partition(reveal)[0]
    if mentions_name(job["color"], head) or COLOR_WORDS.search(head):
        found = COLOR_WORDS.search(head)
        return "color-word" + (f":{found.group(0)}" if found else "")
    after = text.split(lucky, 1)[1]
    if mentions_name(job["color"], after) or COLOR_WORDS.search(after):
        return "repeat"
    tail = [line for line in after.splitlines() if line.strip()]
    if len(tail) > 2:
        return "tail"
    words = re.findall(r"[A-Za-z']+", head)
    if not 480 <= len(words) <= 700:
        return f"words:{len(words)}"
    return None


def attach(job: dict) -> None:
    path = ROOT / "data" / job["id"] / "card.json"
    with LOCK:
        data = json.loads(path.read_text())
        for color in data[job["orientation"]]:
            if color["name"] == job["color"]:
                color["textEn"] = job["file"]
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def one(key: str, job: dict) -> str:
    target = ROOT / "data" / job["id"] / job["file"]
    if target.exists():
        existing = target.read_text(encoding="utf-8")
        if valid(job, existing) is None:
            attach(job)
            return f"SKIP {job['id']} {job['orientation']} {job['color']}"
    messages = [
        {"role": "system", "content": "Return only the requested essay. No preamble."},
        {"role": "user", "content": prompt_for(job)},
    ]
    last_error = "unwritten"
    draft = ""
    for attempt in range(4):
        try:
            draft = complete(key, messages)
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:300]
            last_error = f"API {error.code} {detail}"
            if error.code in {429, 500, 502, 503}:
                time.sleep(min(30, 2 ** attempt))
            continue
        except Exception as error:  # noqa: BLE001
            last_error = str(error)
            time.sleep(2)
            continue
        problem = valid(job, draft)
        if problem:
            extra = ""
            if problem == "reveal":
                hits = [line for line in draft.splitlines() if "ucky" in line or "Color" in line]
                extra = " " + " | ".join(hits[:3])
            last_error = problem + extra
            messages = [
                {"role": "system", "content": "Return only the requested essay. No preamble."},
                {"role": "user", "content": prompt_for(job)},
                {"role": "assistant", "content": draft},
                {
                    "role": "user",
                    "content": (
                        f"That draft failed a check: {problem}. Rewrite the whole essay so it passes. "
                        "The closing lines must be copied exactly, with the color name unbroken:\n"
                        f"Today's lucky color is {job['color']}.\n"
                        f"Lucky Color: {job['color']} — {job['hex']}"
                    ),
                },
            ]
            continue
        target.write_text(draft, encoding="utf-8")
        attach(job)
        return f"DONE {job['id']} {job['orientation']} {job['color']}"
    return f"FAIL {job['id']} {job['orientation']} {job['color']} {last_error}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    pending = jobs()
    if args.limit:
        pending = pending[: args.limit]
    print(f"PENDING {len(pending)}", flush=True)
    if not pending:
        print("FINISHED failures=0", flush=True)
        return
    key = load_key()
    failures = 0
    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(one, key, job) for job in pending]
        for future in as_completed(futures):
            line = future.result()
            print(line, flush=True)
            if line.startswith("FAIL"):
                failures += 1
            else:
                done += 1
            if (done + failures) % 20 == 0:
                print(f"PROGRESS {done + failures}/{len(pending)}", flush=True)
    print(f"FINISHED failures={failures}", flush=True)
    if failures:
        sys.exit(f"failed {failures}")


if __name__ == "__main__":
    main()
