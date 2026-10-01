#!/usr/bin/env python3
"""Write card and color library pages from data/ and public/meanings.js."""

import html
import json
import re
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PUBLIC = ROOT / "public"
CARDS = PUBLIC / "cards"
ORIGIN = "https://colorsofthefool.engawa5656.com"
ORIENTATION = {"upright": "正位置", "reversed": "逆位置"}

SHARE_ICON = """          <svg viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="18" cy="5" r="2.2" fill="none" stroke="currentColor" stroke-width="1.6"/>
            <circle cx="6" cy="12" r="2.2" fill="none" stroke="currentColor" stroke-width="1.6"/>
            <circle cx="18" cy="19" r="2.2" fill="none" stroke="currentColor" stroke-width="1.6"/>
            <path d="M8.2 13.1 15.7 17.4M15.7 6.6 8.2 10.9" fill="none" stroke="currentColor" stroke-width="1.6"/>
          </svg>"""
X_ICON = """          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path fill="currentColor" d="M14.2 10.4 21.5 2h-1.7l-6.3 7.2L8.4 2H2.2l7.6 11L2.2 22h1.7l6.7-7.6L15.3 22h6.2l-7.3-11.6Zm-2.4 2.7-.8-1.1L4.7 3.5h2.7l5 7.1.8 1.1 6.5 9.2h-2.7l-5.2-7.8Z"/>
          </svg>"""
LINE_ICON = """          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path fill="#06C755" d="M12 3.2C6.8 3.2 2.6 6.7 2.6 11c0 3.8 3.4 7 8 7.7.3.1.7.2.8.5.1.3.1.7 0 1l-.3 1.6c-.1.4.3.7.7.5l2.2-1.3c.2-.1.4-.1.6-.1 4.8-.2 8.8-3.6 8.8-7.9 0-4.3-4.2-7.8-9.4-7.8Z"/>
          </svg>"""

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


def first_sentence(text, limit=90, lang="ja"):
    text = re.sub(r"\s+", " ", text).strip()
    mark = "。" if lang == "ja" else ". "
    cut = text.find(mark)
    if cut != -1:
        text = text[: cut + (1 if lang == "ja" else 1)]
        if lang == "en":
            text = text[: cut + 1]
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    return text


def clip(text, limit=120):
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def load_meanings(lang="ja"):
    import subprocess

    source = (PUBLIC / ("meanings.js" if lang == "ja" else "meanings.en.js")).read_text()
    result = subprocess.run(
        ["node", "-e", "let window={}; eval(require('fs').readFileSync(0,'utf8')); process.stdout.write(JSON.stringify(window.MEANINGS))"],
        input=source,
        text=True,
        check=True,
        capture_output=True,
    )
    return json.loads(result.stdout)


def paragraphs(text, lang="ja"):
    lines = text.replace("\r\n", "\n").split("\n")
    title = r"[―—-]\s*(正位置|逆位置)\s*$" if lang == "ja" else r"[―—-]\s*(Upright|Reversed)\s*$"
    if lines and re.search(title, lines[0] or ""):
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
        prefixes = ("今日のラッキーカラー", "Lucky Color:") if lang == "ja" else ("Today's lucky color", "Lucky Color:")
        reveal = any(line.startswith(prefixes) for line in block)
        if reveal or seen:
            seen = True
            close.extend(block)
        else:
            body.append(block)
    return body, close


def meaning_html(text):
    parts = [part.strip() for part in text.split("\n\n") if part.strip()]
    return "\n".join(f"        <p>{esc(part)}</p>" for part in parts)


def close_paragraph(close):
    parts = []
    skip_break = False
    for index, line in enumerate(close):
        if index and not skip_break:
            parts.append("<br>")
        skip_break = False
        parts.append(esc(line))
        matched = re.match(r"^Lucky Color:\s*.*(#[0-9A-Fa-f]{6})\s*$", line)
        if matched:
            parts.append(
                f'<span class="color-chip" style="background-color:{matched.group(1)}" aria-hidden="true"></span>'
            )
            skip_break = True
    return '        <p class="close">' + "".join(parts) + "</p>"


def story_html(body, close):
    chunks = []
    for block in body:
        chunks.append("        <p>" + "<br>".join(esc(line) for line in block) + "</p>")
    if close:
        chunks.append(close_paragraph(close))
    return "\n".join(chunks)


def color_line(close, body, lang="ja"):
    prefixes = ("今日のラッキーカラー", "Lucky Color:") if lang == "ja" else ("Today's lucky color", "Lucky Color:")
    lines = [line for line in close if not line.startswith(prefixes)]
    source = " ".join(lines).strip()
    if not source and body:
        source = body[0][0]
    sentence = first_sentence(source, 48 if lang == "ja" else 90, lang)
    if sentence in {"", "。", "."}:
        return ""
    return sentence


def hreflang(ja_url, en_url):
    return (
        f'    <link rel="alternate" hreflang="ja" href="{esc(ja_url)}">\n'
        f'    <link rel="alternate" hreflang="en" href="{esc(en_url)}">\n'
        f'    <link rel="alternate" hreflang="x-default" href="{esc(ja_url)}">'
    )


def page(title, description, canonical, image, css, json_ld, body, icon, lang="ja", alternates=""):
    ld = ""
    if json_ld:
        ld = (
            '    <script type="application/ld+json">\n'
            + json.dumps(json_ld, ensure_ascii=False, indent=2)
            + "\n    </script>\n"
        )
    return f"""<!DOCTYPE html>
<html lang="{lang}">
  <head>
{GA}
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{esc(title)}</title>
    <meta name="description" content="{esc(description)}">
    <link rel="canonical" href="{esc(canonical)}">
{alternates}
    <meta property="og:type" content="article">
    <meta property="og:locale" content="{"ja_JP" if lang == "ja" else "en_US"}">
    <meta property="og:title" content="{esc(title.split(' — ')[0])}">
    <meta property="og:description" content="{esc(description)}">
    <meta property="og:url" content="{esc(canonical)}">
    <meta property="og:image" content="{esc(image)}">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
    <meta name="twitter:card" content="summary_large_image">
    <link rel="icon" href="{esc(icon)}" type="image/jpeg">
{HEAD_LINKS}
    <link rel="stylesheet" href="{css}">
{ld}  </head>
  <body>
{body}
    <footer class="colophon">
      <p>© 2026 Engawa Inc.</p>
      <p><a href="{"/contact/" if lang == "ja" else "/en/contact/"}">{"問い合わせ" if lang == "ja" else "Contact"}</a> <a href="https://github.com/okuyamashin/colorsforthefool">GitHub</a></p>
    </footer>
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
                en_name = color.get("textEn") or ""
                en_path = path.parent / en_name
                if Path(en_name).stem != f"{slug}.en" or not en_path.is_file():
                    raise SystemExit(f"missing English text for {card['id']} {slug}")
                if not image_path.is_file():
                    raise SystemExit(f"missing {image_path}")
                share_path = image_path.with_name(f"{image_path.stem}.share.jpg")
                if not share_path.is_file():
                    raise SystemExit(f"missing {share_path}")
                ensure_thumb(image_path)
                color["_slug"] = slug
                color["_texts"] = {
                    "ja": paragraphs(text_path.read_text(), "ja"),
                    "en": paragraphs(en_path.read_text(), "en"),
                }
                color["_lines"] = {}
                for lang in ("ja", "en"):
                    body, close = color["_texts"][lang]
                    color["_lines"][lang] = color_line(close, body, lang)
        if not (path.parent / "face.jpg").is_file():
            raise SystemExit(f"missing face {card['id']}")
        if not (path.parent / "share.jpg").is_file():
            raise SystemExit(f"missing share image {card['id']}")
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


def bind(color, lang):
    color["_body"], color["_close"] = color["_texts"][lang]
    color["_line"] = color["_lines"][lang]


def visible_name(color, lang):
    return color["nameJa"] if lang == "ja" else color["name"]


def color_item(color, lang):
    bind(color, lang)
    line = f'\n            <span class="line">{esc(color["_line"])}</span>' if color["_line"] else ""
    thumb = thumb_name(color["image"])
    if lang == "ja":
        alt = f"{color['_card_ja']}の{color['nameJa']}。中央の鏡に色が映る絵"
        visible = color["nameJa"]
        meta = f"{color['name']} · {color['hex']}"
    else:
        alt = f"{color['_card_en']}, {color['name']}. The color appears in the mirror at the center."
        visible = color["name"]
        meta = f"{color['nameJa']} · {color['hex']}"
    return f"""        <li>
          <a href="{color['_slug']}/index.html">
            <img src="/data/{color['_card']}/{esc(thumb)}" alt="{esc(alt)}">
            <span class="name"><span class="swatch" style="background:{esc(color['hex'])}"></span>{esc(visible)}</span>
            <span class="meta">{esc(meta)}</span>{line}
          </a>
        </li>"""


def pair(canonical, other, lang):
    return hreflang(canonical if lang == "ja" else other, other if lang == "ja" else canonical)


def write_card(card, meanings, lang, root):
    upright = meanings[card["id"]]["upright"]
    reversed_text = meanings[card["id"]]["reversed"]
    prefix = "" if lang == "ja" else "en/"
    canonical = f"{ORIGIN}/{prefix}cards/{card['id']}/index.html"
    other = f"{ORIGIN}/en/cards/{card['id']}/index.html" if lang == "ja" else f"{ORIGIN}/cards/{card['id']}/index.html"
    image = f"{ORIGIN}/data/{card['id']}/share.jpg"
    for side in ("upright", "reversed"):
        for color in card[side]:
            color["_card"] = card["id"]
            color["_card_ja"] = card["nameJa"]
            color["_card_en"] = card["name"]
    upright_items = "\n".join(color_item(color, lang) for color in card["upright"])
    reversed_items = "\n".join(color_item(color, lang) for color in card["reversed"])
    if lang == "ja":
        intro = first_sentence(upright.split("\n\n", 1)[0], 70, "ja")
        description = clip(f"大アルカナの{card['nameJa']}。正位置と逆位置、それぞれ十のラッキーカラー。{intro}")
        title = f"{card['nameJa']}のラッキーカラー — Colors for the Fool"
        tagline = "タロットで占う、今日のラッキーカラー"
        draw = "カードを引く"
        heading = card["nameJa"]
        secondary = f"{card['name']} · {card['numeral']}"
        upright_label, reversed_label = "正位置", "逆位置"
        face_alt = f"{card['nameJa']}、正位置"
        face_alt_reversed = f"{card['nameJa']}、逆位置"
        css = "../library.css"
    else:
        intro = first_sentence(upright.split("\n\n", 1)[0], 110, "en")
        description = clip(f"{card['name']}. Ten lucky colors for upright, and ten for reversed. {intro}", 160)
        title = f"Lucky colors for {card['name']} — Colors for the Fool"
        tagline = "Today's lucky color, drawn from the tarot"
        draw = "Draw a card"
        heading = card["name"]
        secondary = f"{card['nameJa']} · {card['numeral']}"
        upright_label, reversed_label = "Upright", "Reversed"
        face_alt = f"{card['name']}, upright"
        face_alt_reversed = f"{card['name']}, reversed"
        css = "../../../cards/library.css"
    body = f"""    <header class="top">
      <p class="brand"><a href="../../">Colors for the Fool</a></p>
      <p class="tagline">{tagline}</p>
    </header>
    <main>
      <p class="crumb"><a href="../../">{draw}</a></p>
      <img class="face" src="/data/{esc(card['id'])}/face.jpg" alt="{esc(face_alt)}">
      <h1>{esc(heading)}</h1>
      <p class="en">{esc(secondary)}</p>
      <section>
        <h2>{upright_label}</h2>
        <div class="meaning">
{meaning_html(upright)}
        </div>
        <ul class="colors">
{upright_items}
        </ul>
      </section>
      <section>
        <h2>{reversed_label}</h2>
        <img class="face reversed" src="/data/{esc(card['id'])}/face.jpg" alt="{esc(face_alt_reversed)}">
        <div class="meaning">
{meaning_html(reversed_text)}
        </div>
        <ul class="colors">
{reversed_items}
        </ul>
      </section>
    </main>"""
    target = root / card["id"] / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        page(
            title,
            description,
            canonical,
            image,
            css,
            None,
            body,
            f"/data/{card['id']}/circle.jpg",
            lang,
            pair(canonical, other, lang),
        )
    )
    return target


def share_html(card, color, lang):
    prefix = "" if lang == "ja" else "en/"
    page_url = f"{ORIGIN}/{prefix}cards/{card['id']}/{color['_slug']}/"
    if lang == "ja":
        text = f"今日のラッキーカラーは、{color['nameJa']}です。"
        copy_label = "リンクをコピー"
        x_label = "Xでシェア"
        line_label = "LINEでシェア"
        notice = "クリップボードにコピーしました"
        script = "../../share.js"
    else:
        text = f"Today's lucky color is {color['name']}."
        copy_label = "Copy link"
        x_label = "Share on X"
        line_label = "Share on LINE"
        notice = "Copied to the clipboard"
        script = "../../../../cards/share.js"
    tweet = "https://twitter.com/intent/tweet?text=" + quote(text, safe="") + "&url=" + quote(page_url, safe="")
    line = "https://social-plugins.line.me/lineit/share?url=" + quote(page_url, safe="")
    return f"""      <p class="share" data-url="{esc(page_url)}">
        <button type="button" id="share-copy" aria-label="{esc(copy_label)}">
{SHARE_ICON}
        </button>
        <a id="share-x" href="{esc(tweet)}" target="_blank" rel="noopener noreferrer" aria-label="{esc(x_label)}">
{X_ICON}
        </a>
        <a id="share-line" href="{esc(line)}" target="_blank" rel="noopener noreferrer" aria-label="{esc(line_label)}">
{LINE_ICON}
        </a>
      </p>
      <p class="copied" id="copied" hidden role="status">{esc(notice)}</p>
      <script src="{script}"></script>"""


def write_color(card, side, color, lang, root):
    bind(color, lang)
    label = ORIENTATION[side] if lang == "ja" else {"upright": "Upright", "reversed": "Reversed"}[side]
    body, close = color["_body"], color["_close"]
    prefix = "" if lang == "ja" else "en/"
    canonical = f"{ORIGIN}/{prefix}cards/{card['id']}/{color['_slug']}/index.html"
    other = (
        f"{ORIGIN}/en/cards/{card['id']}/{color['_slug']}/index.html"
        if lang == "ja"
        else f"{ORIGIN}/cards/{card['id']}/{color['_slug']}/index.html"
    )
    scene = f"{ORIGIN}/data/{card['id']}/{color['image']}"
    image = f"{ORIGIN}/data/{card['id']}/{Path(color['image']).stem}.share.jpg"
    if lang == "ja":
        opening = first_sentence(body[0][0], 70, "ja") if body else ""
        description = clip(f"{card['nameJa']}の{label}、{color['nameJa']}。{opening}")
        title_name = card["nameJa"]
        tagline = "タロットで占う、今日のラッキーカラー"
        draw = "カードを引く"
        heading = color["nameJa"]
        secondary = f"{card['name']} · {color['name']}"
        alt = f"{card['nameJa']}の{color['nameJa']}。中央の鏡に色が映る絵"
        back = f"{card['nameJa']}へ戻る"
        css = "../../library.css"
        headline = f"{card['nameJa']}のラッキーカラー、{color['nameJa']}"
    else:
        opening = first_sentence(body[0][0], 110, "en") if body else ""
        description = clip(f"{card['name']}, {label.lower()}. {color['name']}. {opening}", 160)
        title_name = card["name"]
        tagline = "Today's lucky color, drawn from the tarot"
        draw = "Draw a card"
        heading = color["name"]
        secondary = f"{card['nameJa']} · {color['nameJa']}"
        alt = f"{card['name']}, {color['name']}. The color appears in the mirror at the center."
        back = f"Back to {card['name']}"
        css = "../../../../cards/library.css"
        headline = f"Lucky color for {card['name']}: {color['name']}"
    siblings = []
    for other_color in card[side]:
        if other_color is color:
            continue
        siblings.append(
            f'        <li><a href="../{other_color["_slug"]}/index.html"><span class="swatch" style="background:{esc(other_color["hex"])}"></span>{esc(visible_name(other_color, lang))}</a></li>'
        )
    sibling_html = "\n".join(siblings)
    body_html = f"""    <header class="top">
      <p class="brand"><a href="../../../">Colors for the Fool</a></p>
      <p class="tagline">{tagline}</p>
    </header>
    <main>
      <p class="crumb"><a href="../../../">{draw}</a> / <a href="../index.html">{esc(title_name)}</a></p>
      <img class="scene" src="/data/{esc(card['id'])}/{esc(color['image'])}" alt="{esc(alt)}">
      <h1>{esc(heading)}</h1>
      <p class="en">{esc(secondary)}</p>
      <p class="orientation">{esc(label)} · {esc(color['hex'])}</p>
      <article class="story">
{story_html(body, close)}
      </article>
{share_html(card, color, lang)}
      <a class="back" href="../index.html">{esc(back)}</a>
      <ul class="siblings">
{sibling_html}
      </ul>
    </main>"""
    target = root / card["id"] / color["_slug"] / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        page(
            f"{headline} — Colors for the Fool",
            description,
            canonical,
            image,
            css,
            {
                "@context": "https://schema.org",
                "@type": "Article",
                "headline": headline,
                "inLanguage": "ja" if lang == "ja" else "en",
                "image": scene,
                "description": description,
                "mainEntityOfPage": canonical,
                "publisher": {"@type": "Organization", "name": "Colors for the Fool"},
            },
            body_html,
            f"/data/{card['id']}/circle.jpg",
            lang,
            pair(canonical, other, lang),
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
    urls = [f"{ORIGIN}/", f"{ORIGIN}/en/"]
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


def remove_stale(written, root):
    if not root.is_dir():
        return
    for path in root.rglob("index.html"):
        if path not in written:
            path.unlink()
    for path in sorted(root.rglob("*"), reverse=True):
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()


def main():
    meanings = {lang: load_meanings(lang) for lang in ("ja", "en")}
    cards = load_cards()
    if len(cards) != 22:
        raise SystemExit(f"expected 22 cards, found {len(cards)}")
    for lang, table in meanings.items():
        missing = [card["id"] for card in cards if card["id"] not in table]
        if missing:
            raise SystemExit(f"missing {lang} meanings {missing}")
    written = set()
    for lang, root in (("ja", CARDS), ("en", PUBLIC / "en" / "cards")):
        for card in cards:
            written.add(write_card(card, meanings[lang], lang, root))
            for side in ("upright", "reversed"):
                for color in card[side]:
                    written.add(write_color(card, side, color, lang, root))
        remove_stale(written, root)
    link_top(cards)
    write_sitemap(sorted(written))
    print(f"cards {len(cards)} pages {len(written)}")


if __name__ == "__main__":
    main()
