#!/usr/bin/env python3
"""440日分のリール順を一度だけ作り、data/instagram-schedule.json に書く。"""

import json
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = DATA / "instagram-schedule.json"
SEED = 20261001
START = "2026-10-01"


def load_cards():
    cards = []
    for path in sorted(DATA.glob("*/card.json")):
        card = json.loads(path.read_text())
        sides = {}
        for side in ("upright", "reversed"):
            colors = []
            for color in card[side]:
                slug = Path(color["image"]).stem
                reel = path.parent / f"{slug}.instagram.mp4"
                text = path.parent / f"{slug}.instagram.txt"
                if not reel.is_file():
                    raise SystemExit(f"missing {reel}")
                if not text.is_file():
                    raise SystemExit(f"missing {text}")
                colors.append(
                    {
                        "color": color["name"],
                        "colorJa": color["nameJa"],
                        "hex": color["hex"],
                        "slug": slug,
                        "caption": text.read_text().strip(),
                    }
                )
            if len(colors) != 10:
                raise SystemExit(f"{card['id']} {side} has {len(colors)} colors")
            sides[side] = colors
        cards.append(
            {
                "card": card["id"],
                "name": card["name"],
                "nameJa": card["nameJa"],
                "numeral": card["numeral"],
                "sides": sides,
            }
        )
    if len(cards) != 22:
        raise SystemExit(f"expected 22 cards, found {len(cards)}")
    return cards


def card_sequence(cards, rng):
    ids = [card["card"] for card in cards]
    sequence = []
    for _ in range(20):
        deck = ids[:]
        rng.shuffle(deck)
        if sequence and sequence[-1] == deck[0]:
            deck[0], deck[1] = deck[1], deck[0]
        sequence.extend(deck)
    return sequence


def orientations(sequence, rng):
    positions = defaultdict(list)
    for index, card in enumerate(sequence):
        positions[card].append(index)
    orient = [None] * len(sequence)
    for indexes in positions.values():
        sides = ["upright"] * 10 + ["reversed"] * 10
        rng.shuffle(sides)
        for index, side in zip(indexes, sides):
            orient[index] = side

    def run_at(index):
        return (
            2 <= index < len(orient)
            and orient[index] == orient[index - 1] == orient[index - 2]
        )

    for _ in range(20000):
        bad = next((i for i in range(2, len(orient)) if run_at(i)), None)
        if bad is None:
            return orient
        card = sequence[bad]
        want = "reversed" if orient[bad] == "upright" else "upright"
        candidates = [j for j in positions[card] if orient[j] == want]
        rng.shuffle(candidates)
        fixed = False
        for other in candidates:
            orient[bad], orient[other] = orient[other], orient[bad]
            touched = [bad, other]
            if not any(run_at(k) or run_at(k + 1) or run_at(k + 2) for k in touched):
                fixed = True
                break
            orient[bad], orient[other] = orient[other], orient[bad]
        if fixed:
            continue
        sides = [orient[index] for index in positions[card]]
        rng.shuffle(sides)
        for index, side in zip(positions[card], sides):
            orient[index] = side
    raise SystemExit("could not place orientations")


def build():
    rng = random.Random(SEED)
    cards = load_cards()
    by_id = {card["card"]: card for card in cards}
    sequence = card_sequence(cards, rng)
    sides = orientations(sequence, rng)
    pools = {
        card["card"]: {
            side: card["sides"][side][:]
            for side in ("upright", "reversed")
        }
        for card in cards
    }
    for pool in pools.values():
        for colors in pool.values():
            rng.shuffle(colors)
    used = {card["card"]: {"upright": 0, "reversed": 0} for card in cards}
    items = []
    for index, (card_id, side) in enumerate(zip(sequence, sides)):
        card = by_id[card_id]
        color = pools[card_id][side].pop()
        used[card_id][side] += 1
        items.append(
            {
                "day": index + 1,
                "card": card_id,
                "name": card["name"],
                "nameJa": card["nameJa"],
                "numeral": card["numeral"],
                "orientation": side,
                "color": color["color"],
                "colorJa": color["colorJa"],
                "hex": color["hex"],
                "reelKey": f"instagram/reels/{card_id}/{color['slug']}.instagram.mp4",
                "caption": color["caption"],
            }
        )
    check(items, used)
    payload = {
        "start": START,
        "timezone": "Asia/Tokyo",
        "seed": SEED,
        "days": len(items),
        "items": items,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return payload


def check(items, used):
    if len(items) != 440:
        raise SystemExit(f"expected 440 days, found {len(items)}")
    keys = [item["reelKey"] for item in items]
    if len(set(keys)) != 440:
        raise SystemExit("a reel is scheduled more than once")
    adjacent = sum(
        1 for prev, curr in zip(items, items[1:]) if prev["card"] == curr["card"]
    )
    if adjacent:
        raise SystemExit(f"same card on consecutive days: {adjacent}")
    longest = run = 1
    for prev, curr in zip(items, items[1:]):
        if prev["orientation"] == curr["orientation"]:
            run += 1
            longest = max(longest, run)
        else:
            run = 1
    if longest > 2:
        raise SystemExit(f"orientation runs for {longest} days")
    for card, counts in used.items():
        if counts != {"upright": 10, "reversed": 10}:
            raise SystemExit(f"{card} counts {counts}")


def label(item):
    side = "正位置" if item["orientation"] == "upright" else "逆位置"
    return f"{item['day']:3}日目  {item['nameJa']}・{side}・{item['colorJa']}"


if __name__ == "__main__":
    payload = build()
    print(f"wrote {OUT}")
    print(f"seed {payload['seed']}  start {payload['start']}  days {payload['days']}")
    print("--- head ---")
    for item in payload["items"][:14]:
        print(label(item))
    print("--- tail ---")
    for item in payload["items"][-2:]:
        print(label(item))
