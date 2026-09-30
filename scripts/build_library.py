#!/usr/bin/env python3
"""Write card and color library pages from data/ and public/meanings.js."""

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PUBLIC = ROOT / "public"
CARDS = PUBLIC / "cards"
ORIGIN = "https://colorsofthefool.engawa5656.com"
ORIENTATION = {"upright": "正位置", "reversed": "逆位置"}

GA = """    <!-- Google tag (gtag.js) -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-NQ38VZSM7B"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){dataLayer.push(arguments);}
      gtag('js', new Date());

      gtag('config', 'G-NQ38VZSM7B');
    </script>"""

HEAD_LINKS = """    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@500;700&family=Shippori+Mincho:wght@400;500;600&display=swap" rel="stylesheet">"""


def esc(value):
    return html.escape(str(value), quote=True)


def first_sentence(text, limit=90):
    text = re.sub(r"\s+", " ", text).strip()
    cut = text.find("。")
    if cut != -1:
        text = text[: cut + 1]
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    return text


def clip(text, limit=120):
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def load_meanings():
    import subprocess

    source = (PUBLIC / "meanings.js").read_text()
    result = subprocess.run(
        ["node", "-e", "let window={}; eval(require('fs').readFileSync(0,'utf8')); process.stdout.write(JSON.stringify(window.MEANINGS))"],
        input=source,
        text=True,
        check=True,
        capture_output=True,
    )
    return json.loads(result.stdout)


def paragraphs(text):
    lines = text.replace("\r\n", "\n").split("\n")
    if lines and re.search(r"[―—-]\s*(正位置|逆位置)\s*$", lines[0] or ""):
        lines = lines[1:]
    blocks = []
    buffer = []
    for line in lines:
        if line.strip() == "":
            if buffer:
                blocks.append(buffer)
                buffer = []
        else:
            buffer.append(line)
    if buffer:
        blocks.append(buffer)
    body = []
    close = []
    seen = False
    for block in blocks:
        reveal = any(
            line.startswith("今日のラッキーカラー") or line.startswith("Lucky Color:")
            for line in block
        )
        if reveal or seen:
            seen = True
            close.extend(block)
        else:
            body.append(block)
    return body, close


def meaning_html(text):
    parts = [part.strip() for part in text.split("\n\n") if part.strip()]
    return "\n".join(f"        <p>{esc(part)}</p>" for part in parts)


def story_html(body, close):
    chunks = []
    for block in body:
        chunks.append("        <p>" + "<br>".join(esc(line) for line in block) + "</p>")
    if close:
        chunks.append(
            '        <p class="close">' + "<br>".join(esc(line) for line in close) + "</p>"
        )
    return "\n".join(chunks)


def color_line(close, body):
    lines = [
        line
        for line in close
        if not line.startswith("今日のラッキーカラー") and not line.startswith("Lucky Color:")
    ]
    source = " ".join(lines).strip()
    if not source and body:
        source = body[0][0]
    sentence = first_sentence(source, 48)
    if sentence in {"", "。"}:
        return ""
    return sentence


def page(title, description, canonical, image, css, json_ld, body, icon):
    ld = ""
    if json_ld:
        ld = (
            '    <script type="application/ld+json">\n'
            + json.dumps(json_ld, ensure_ascii=False, indent=2)
            + "\n    </script>\n"
        )
    return f"""<!DOCTYPE html>
<html lang="ja">
  <head>
{GA}
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{esc(title)}</title>
    <meta name="description" content="{esc(description)}">
    <link rel="canonical" href="{esc(canonical)}">
    <meta property="og:type" content="article">
    <meta property="og:locale" content="ja_JP">
    <meta property="og:title" content="{esc(title.split(' — ')[0])}">
    <meta property="og:description" content="{esc(description)}">
    <meta property="og:url" content="{esc(canonical)}">
    <meta property="og:image" content="{esc(image)}">
    <link rel="icon" href="{esc(icon)}" type="image/jpeg">
{HEAD_LINKS}
    <link rel="stylesheet" href="{css}">
{ld}  </head>
  <body>
{body}
  </body>
</html>
"""


def slug_of(color):
    stem = Path(color["text"]).stem
    if not re.fullmatch(r"[a-z0-9]+", stem):
        raise SystemExit(f"unexpected color file {color['text']}")
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", color["hex"]):
        raise SystemExit(f"unexpected hex {color['hex']}")
    return stem


def load_cards():
    cards = []
    for path in sorted(DATA.glob("*/card.json")):
        card = json.loads(path.read_text())
        card["_dir"] = path.parent
        seen = {}
        for side in ("upright", "reversed"):
            colors = card[side]
            if len(colors) != 10:
                raise SystemExit(f"{card['id']} {side} has {len(colors)} colors")
            for color in colors:
                slug = slug_of(color)
                if slug in seen:
                    raise SystemExit(f"{card['id']} reuses {slug} on both sides")
                seen[slug] = side
                text_path = path.parent / color["text"]
                image_path = path.parent / color["image"]
                if not text_path.is_file():
                    raise SystemExit(f"missing {text_path}")
                if not image_path.is_file():
                    raise SystemExit(f"missing {image_path}")
                ensure_thumb(image_path)
                color["_slug"] = slug
                color["_body"], color["_close"] = paragraphs(text_path.read_text())
                color["_line"] = color_line(color["_close"], color["_body"])
        if not (path.parent / "face.jpg").is_file():
            raise SystemExit(f"missing face {card['id']}")
        cards.append(card)
    return cards


THUMB_WIDTH = 240
THUMB_QUALITY = 70


def thumb_name(image_name):
    return f"{Path(image_name).stem}.thumb.jpg"


def ensure_thumb(image_path):
    dest = image_path.with_name(thumb_name(image_path.name))
    if dest.is_file() and dest.stat().st_mtime >= image_path.stat().st_mtime:
        return dest
    from PIL import Image

    with Image.open(image_path) as image:
        image = image.convert("RGB")
        width = min(THUMB_WIDTH, image.width)
        height = max(1, round(image.height * width / image.width))
        if (width, height) != image.size:
            image = image.resize((width, height), Image.Resampling.LANCZOS)
        image.save(dest, "JPEG", quality=THUMB_QUALITY, optimize=True, progressive=True)
    return dest


def color_item(color):
    line = f'\n            <span class="line">{esc(color["_line"])}</span>' if color["_line"] else ""
    thumb = thumb_name(color["image"])
    return f"""        <li>
          <a href="{color['_slug']}/index.html">
            <img src="/data/{color['_card']}/{esc(thumb)}" alt="{esc(color['_card_ja'])}の{esc(color['nameJa'])}。中央の鏡に色が映る絵">
            <span class="name"><span class="swatch" style="background:{esc(color['hex'])}"></span>{esc(color['nameJa'])}</span>
            <span class="meta">{esc(color['name'])} · {esc(color['hex'])}</span>{line}
          </a>
        </li>"""


def write_card(card, meanings):
    upright = meanings[card["id"]]["upright"]
    reversed_text = meanings[card["id"]]["reversed"]
    intro = first_sentence(upright.split("\n\n", 1)[0], 70)
    description = clip(f"大アルカナの{card['nameJa']}。正位置と逆位置、それぞれ十のラッキーカラー。{intro}")
    canonical = f"{ORIGIN}/cards/{card['id']}/index.html"
    image = f"{ORIGIN}/data/{card['id']}/face.jpg"
    for side in ("upright", "reversed"):
        for color in card[side]:
            color["_card"] = card["id"]
            color["_card_ja"] = card["nameJa"]
    upright_items = "\n".join(color_item(color) for color in card["upright"])
    reversed_items = "\n".join(color_item(color) for color in card["reversed"])
    body = f"""    <header class="top">
      <p class="brand"><a href="../../">Colors for the Fool</a></p>
      <p class="tagline">タロットで占う、今日のラッキーカラー</p>
    </header>
    <main>
      <p class="crumb"><a href="../../">カードを引く</a></p>
      <img class="face" src="/data/{esc(card['id'])}/face.jpg" alt="{esc(card['nameJa'])}、正位置">
      <h1>{esc(card['nameJa'])}</h1>
      <p class="en">{esc(card['name'])} · {esc(card['numeral'])}</p>
      <section>
        <h2>正位置</h2>
        <div class="meaning">
{meaning_html(upright)}
        </div>
        <ul class="colors">
{upright_items}
        </ul>
      </section>
      <section>
        <h2>逆位置</h2>
        <img class="face reversed" src="/data/{esc(card['id'])}/face.jpg" alt="{esc(card['nameJa'])}、逆位置">
        <div class="meaning">
{meaning_html(reversed_text)}
        </div>
        <ul class="colors">
{reversed_items}
        </ul>
      </section>
    </main>"""
    target = CARDS / card["id"] / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        page(
            f"{card['nameJa']}のラッキーカラー — Colors for the Fool",
            description,
            canonical,
            image,
            "../library.css",
            None,
            body,
            f"/data/{card['id']}/circle.jpg",
        )
    )
    return target


def write_color(card, side, color):
    label = ORIENTATION[side]
    body, close = color["_body"], color["_close"]
    opening = first_sentence(body[0][0], 70) if body else ""
    description = clip(f"{card['nameJa']}の{label}、{color['nameJa']}。{opening}")
    canonical = f"{ORIGIN}/cards/{card['id']}/{color['_slug']}/index.html"
    image = f"{ORIGIN}/data/{card['id']}/{color['image']}"
    siblings = []
    for other in card[side]:
        if other is color:
            continue
        siblings.append(
            f'        <li><a href="../{other["_slug"]}/index.html"><span class="swatch" style="background:{esc(other["hex"])}"></span>{esc(other["nameJa"])}</a></li>'
        )
    sibling_html = "\n".join(siblings)
    body_html = f"""    <header class="top">
      <p class="brand"><a href="../../../">Colors for the Fool</a></p>
      <p class="tagline">タロットで占う、今日のラッキーカラー</p>
    </header>
    <main>
      <p class="crumb"><a href="../../../">カードを引く</a> / <a href="../index.html">{esc(card['nameJa'])}</a></p>
      <img class="scene" src="/data/{esc(card['id'])}/{esc(color['image'])}" alt="{esc(card['nameJa'])}の{esc(color['nameJa'])}。中央の鏡に色が映る絵">
      <h1>{esc(color['nameJa'])}</h1>
      <p class="en">{esc(card['name'])} · {esc(color['name'])}</p>
      <p class="orientation">{esc(label)} · {esc(color['hex'])}</p>
      <article class="story">
{story_html(body, close)}
      </article>
      <a class="back" href="../index.html">{esc(card['nameJa'])}へ戻る</a>
      <ul class="siblings">
{sibling_html}
      </ul>
    </main>"""
    target = CARDS / card["id"] / color["_slug"] / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    headline = f"{card['nameJa']}のラッキーカラー、{color['nameJa']}"
    target.write_text(
        page(
            f"{headline} — Colors for the Fool",
            description,
            canonical,
            image,
            "../../library.css",
            {
                "@context": "https://schema.org",
                "@type": "Article",
                "headline": headline,
                "inLanguage": "ja",
                "image": image,
                "description": description,
                "mainEntityOfPage": canonical,
                "publisher": {"@type": "Organization", "name": "Colors for the Fool"},
            },
            body_html,
            f"/data/{card['id']}/circle.jpg",
        )
    )
    return target


def link_top(cards):
    path = PUBLIC / "index.html"
    text = path.read_text()
    for card in cards:
        pattern = re.compile(
            rf'<h3>(?:<a href="cards/{re.escape(card["id"])}/index.html">)?{re.escape(card["nameJa"])}<span class="latin">([^<]*)</span>(?:</a>)?</h3>'
        )
        replacement = (
            f'<h3><a href="cards/{card["id"]}/index.html">{card["nameJa"]}'
            r'<span class="latin">\1</span></a></h3>'
        )
        text, count = pattern.subn(replacement, text, count=1)
        if count != 1:
            raise SystemExit(f"top heading not found for {card['nameJa']}")
    path.write_text(text)


def write_sitemap(paths):
    urls = [f"{ORIGIN}/"]
    urls.extend(f"{ORIGIN}/{path.relative_to(PUBLIC).as_posix()}" for path in paths)
    body = "\n".join(f"  <url><loc>{esc(url)}</loc></url>" for url in urls)
    (PUBLIC / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n"
        "</urlset>\n"
    )
    (PUBLIC / "robots.txt").write_text(
        "User-agent: *\n"
        "Allow: /\n"
        f"Sitemap: {ORIGIN}/sitemap.xml\n"
    )


def remove_stale(written):
    for path in CARDS.rglob("index.html"):
        if path not in written:
            path.unlink()
    for path in sorted(CARDS.rglob("*"), reverse=True):
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()


def main():
    meanings = load_meanings()
    cards = load_cards()
    if len(cards) != 22:
        raise SystemExit(f"expected 22 cards, found {len(cards)}")
    missing = [card["id"] for card in cards if card["id"] not in meanings]
    if missing:
        raise SystemExit(f"missing meanings {missing}")
    written = set()
    for card in cards:
        written.add(write_card(card, meanings))
        for side in ("upright", "reversed"):
            for color in card[side]:
                written.add(write_color(card, side, color))
    remove_stale(written)
    link_top(cards)
    write_sitemap(sorted(written))
    print(f"cards {len(cards)} pages {len(written)}")


if __name__ == "__main__":
    main()
