#!/usr/bin/env python3
"""Write 1200×630 share images.

Card pages use data/<card>/share.jpg (the face, titled with the card).
Color pages use data/<card>/<color>.share.jpg (that color's picture).
"""

import json
import re
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FONT_DIR = Path("/tmp/share-fonts")
CINZEL = FONT_DIR / "Cinzel-Medium.ttf"
CINZEL_URL = "https://github.com/google/fonts/raw/main/ofl/cinzel/Cinzel%5Bwght%5D.ttf"

W, H = 2400, 1260
INK = (42, 33, 24)
GOLD = (122, 92, 42)
GOLD_LINE = (166, 132, 61)
GOLD_SOFT = (196, 170, 112)
BRAND = "COLORS FOR THE FOOL"
MUTED = (109, 92, 72)


def ensure_font():
    if CINZEL.exists():
        return
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(CINZEL_URL, CINZEL)


def tracked_width(text, font, tracking):
    return sum(font.getlength(ch) for ch in text) + tracking * (len(text) - 1)


def draw_tracked(draw, text, font, cx, top, fill, tracking):
    cursor = cx - tracked_width(text, font, tracking) / 2
    for ch in text:
        draw.text((cursor, top), ch, font=font, fill=fill)
        cursor += font.getlength(ch) + tracking


def color_label(name):
    name = name.replace("AquaMarine", "Aquamarine").replace("GoldenRod", "Goldenrod")
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name).upper()


def fit_title(name, max_width):
    size = 132
    tracking = 14
    while size >= 56:
        font = ImageFont.truetype(CINZEL, size)
        font.set_variation_by_axes([600])
        if tracked_width(name, font, tracking) <= max_width:
            return font, tracking
        size -= 4
        tracking = max(4, tracking - 1)
    font = ImageFont.truetype(CINZEL, 56)
    font.set_variation_by_axes([600])
    return font, 4


def stage(image_path):
    grad = Image.new("RGB", (1, H))
    top = (251, 246, 236)
    bot = (226, 212, 190)
    pixels = grad.load()
    for y in range(H):
        t = y / (H - 1)
        pixels[0, y] = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3))
    canvas = grad.resize((W, H), Image.Resampling.BILINEAR).convert("RGBA")

    card = Image.open(image_path).convert("RGB")
    margin_y = 78
    card_h = H - margin_y * 2
    card_w = round(card_h * card.width / card.height)
    card = card.resize((card_w, card_h), Image.Resampling.LANCZOS)
    x = 84

    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [x + 8, margin_y + 18, x + card_w + 14, margin_y + card_h + 22],
        radius=8,
        fill=(42, 33, 24, 78),
    )
    canvas = Image.alpha_composite(canvas, shadow.filter(ImageFilter.GaussianBlur(22)))
    canvas.paste(card, (x, margin_y))

    draw = ImageDraw.Draw(canvas)
    inset = 30
    draw.rectangle([inset, inset, W - 1 - inset, H - 1 - inset], outline=GOLD_LINE, width=3)
    draw.rectangle(
        [inset + 10, inset + 10, W - 1 - inset - 10, H - 1 - inset - 10],
        outline=GOLD_SOFT,
        width=2,
    )
    right_l = x + card_w + 48
    right_r = W - 96
    cx = (x + card_w + (W - 72)) / 2
    return canvas, draw, cx, right_r - right_l


def render(card_dir, name):
    canvas, draw, cx, max_width = stage(card_dir / "face.jpg")
    brand_font = ImageFont.truetype(CINZEL, 36)
    brand_font.set_variation_by_axes([500])
    title_font, title_track = fit_title(name, max_width)

    brand_track = 8
    brand_box = brand_font.getbbox(BRAND)
    title_box = title_font.getbbox(name)
    brand_h = brand_box[3] - brand_box[1]
    title_h = title_box[3] - title_box[1]
    gap_brand = 48
    gap_rule = 46
    rule = 148
    block = brand_h + gap_brand + title_h + gap_rule + 3
    top0 = (H - block) / 2 - brand_box[1]

    draw_tracked(draw, BRAND, brand_font, cx, top0, GOLD, brand_track)
    title_top = top0 + brand_h + gap_brand - title_box[1]
    draw_tracked(draw, name, title_font, cx, title_top, INK, title_track)
    rule_y = title_top + title_box[3] + gap_rule
    draw.line([(cx - rule, rule_y), (cx + rule, rule_y)], fill=GOLD_LINE, width=3)

    out = card_dir / "share.jpg"
    canvas.convert("RGB").resize((1200, 630), Image.Resampling.LANCZOS).save(
        out, "JPEG", quality=88, optimize=True, subsampling=1
    )
    return out, title_font.size


def render_color(card_dir, card_name, color):
    label = color_label(color["name"])
    image = card_dir / color["image"]
    canvas, draw, cx, max_width = stage(image)
    brand_font = ImageFont.truetype(CINZEL, 36)
    brand_font.set_variation_by_axes([500])
    card_font = ImageFont.truetype(CINZEL, 42)
    card_font.set_variation_by_axes([500])
    title_font, title_track = fit_title(label, max_width)

    brand_box = brand_font.getbbox(BRAND)
    title_box = title_font.getbbox(label)
    card_box = card_font.getbbox(card_name)
    brand_h = brand_box[3] - brand_box[1]
    title_h = title_box[3] - title_box[1]
    card_h = card_box[3] - card_box[1]
    gap_brand, gap_card, gap_rule, rule = 44, 28, 42, 148
    block = brand_h + gap_brand + title_h + gap_card + card_h + gap_rule + 3
    top0 = (H - block) / 2 - brand_box[1]

    draw_tracked(draw, BRAND, brand_font, cx, top0, GOLD, 8)
    title_top = top0 + brand_h + gap_brand - title_box[1]
    draw_tracked(draw, label, title_font, cx, title_top, INK, title_track)
    card_top = title_top + title_box[3] + gap_card - card_box[1]
    draw_tracked(draw, card_name, card_font, cx, card_top, MUTED, 8)
    rule_y = card_top + card_box[3] + gap_rule
    draw.line([(cx - rule, rule_y), (cx + rule, rule_y)], fill=GOLD_LINE, width=3)

    out = image.with_suffix(".share.jpg")
    canvas.convert("RGB").resize((1200, 630), Image.Resampling.LANCZOS).save(
        out, "JPEG", quality=88, optimize=True, subsampling=1
    )
    return out, title_font.size


def main():
    ensure_font()
    for path in sorted(DATA.glob("*/card.json")):
        card = json.loads(path.read_text())
        render(path.parent, card["name"])
        count = 0
        for side in ("upright", "reversed"):
            for color in card[side]:
                render_color(path.parent, card["name"], color)
                count += 1
        print(f"{card['id']:22} {count} colors")


if __name__ == "__main__":
    main()
