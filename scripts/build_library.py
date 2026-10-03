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
ORIGIN = "https://colorsforthefool.engawa5656.com"
LANGUAGES = json.loads((DATA / "languages.json").read_text())
REQUIRED = (
    "id", "htmlLang", "hreflang", "prefix", "switchLabel", "cookie", "session",
    "ogLocale", "data", "meanings", "cardName", "colorName", "textField", "textSuffix",
    "punctuation", "lineLimit", "introLimit", "descriptionLimit", "titlePattern",
    "revealPrefixes", "fonts", "shareText", "footer", "share", "copy", "pages",
)
for language in LANGUAGES:
    missing = [key for key in REQUIRED if key not in language]
    if missing:
        raise SystemExit(f"language {language.get('id', '?')} missing {missing}")
if sum(1 for language in LANGUAGES if language.get("default")) != 1:
    raise SystemExit("languages.json needs exactly one default language")
if sum(1 for language in LANGUAGES if language["prefix"] == "") != 1:
    raise SystemExit("languages.json needs exactly one language at the site root")

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

def head_links(lang):
    return f"""    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?{lang['fonts']}&display=swap" rel="stylesheet">"""


def esc(value):
    return html.escape(str(value), quote=True)


def fill(template, **values):
    text = str(template)
    for key, value in values.items():
        text = text.replace("{" + key + "}", str(value))
    return text


def nested(lang):
    return bool(lang["prefix"])


def card_root(lang):
    return CARDS if not nested(lang) else PUBLIC / lang["prefix"] / "cards"


def home_path(lang):
    return PUBLIC / "index.html" if not nested(lang) else PUBLIC / lang["prefix"] / "index.html"


def home_url(lang):
    return f"{ORIGIN}/" if not nested(lang) else f"{ORIGIN}/{lang['prefix']}/"


def first_sentence(text, limit, lang):
    text = re.sub(r"\s+", " ", text).strip()
    mark = lang["punctuation"]
    cut = text.find(mark)
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


def load_meanings(lang):
    import subprocess

    source = (PUBLIC / lang["meanings"]).read_text()
    result = subprocess.run(
        ["node", "-e", "let window={}; eval(require('fs').readFileSync(0,'utf8')); process.stdout.write(JSON.stringify(window.MEANINGS))"],
        input=source,
        text=True,
        check=True,
        capture_output=True,
    )
    return json.loads(result.stdout)


def paragraphs(text, lang):
    lines = text.replace("\r\n", "\n").split("\n")
    title = lang["titlePattern"]
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
        prefixes = tuple(lang["revealPrefixes"])
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


def color_line(close, body, lang):
    prefixes = tuple(lang["revealPrefixes"])
    lines = [line for line in close if not line.startswith(prefixes)]
    source = " ".join(lines).strip()
    if not source and body:
        source = body[0][0]
    sentence = first_sentence(source, lang["lineLimit"], lang)
    if sentence in {"", "。", "."}:
        return ""
    return sentence


def library_url(card_id, slug=""):
    tail = f"cards/{card_id}/" + (f"{slug}/" if slug else "")
    urls = {}
    for lang in LANGUAGES:
        prefix = f"{lang['prefix']}/" if nested(lang) else ""
        urls[lang["id"]] = f"{ORIGIN}/{prefix}{tail}index.html"
    return urls


def hreflang(urls):
    default = next(lang for lang in LANGUAGES if lang.get("default"))
    lines = [
        f'    <link rel="alternate" hreflang="{lang["hreflang"]}" href="{esc(urls[lang["id"]])}">'
        for lang in LANGUAGES
    ]
    lines.append(f'    <link rel="alternate" hreflang="x-default" href="{esc(urls[default["id"]])}">')
    return "\n".join(lines)


def footer_links(lang):
    links = " ".join(
        f'<a href="{esc(item["href"])}">{esc(item["label"])}</a>' for item in lang["footer"]
    )
    github = '<a href="https://github.com/okuyamashin/colorsforthefool">GitHub</a>'
    return f"{links} {github}"


def page(title, description, canonical, image, css, json_ld, body, icon, lang, alternates="", extra=""):
    ld = ""
    if json_ld:
        ld = (
            '    <script type="application/ld+json">\n'
            + json.dumps(json_ld, ensure_ascii=False, indent=2)
            + "\n    </script>\n"
        )
    return f"""<!DOCTYPE html>
<html lang="{lang['htmlLang']}">
  <head>
{GA}
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{esc(title)}</title>
    <meta name="description" content="{esc(description)}">
    <link rel="canonical" href="{esc(canonical)}">
{alternates}
    <meta property="og:type" content="article">
    <meta property="og:locale" content="{lang['ogLocale']}">
    <meta property="og:title" content="{esc(title.split(' — ')[0])}">
    <meta property="og:description" content="{esc(description)}">
    <meta property="og:url" content="{esc(canonical)}">
    <meta property="og:image" content="{esc(image)}">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
    <meta name="twitter:card" content="summary_large_image">
    <link rel="icon" href="{esc(icon)}" type="image/jpeg">
{head_links(lang)}
    <link rel="stylesheet" href="{css}">
{ld}  </head>
  <body>
{body}
    <footer class="colophon">
      <p>© 2026 Engawa Inc.</p>
      <p>{footer_links(lang)}</p>
    </footer>
{extra}  </body>
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
        for lang in LANGUAGES:
            if lang["cardName"] not in card:
                raise SystemExit(f"{card['id']} missing {lang['cardName']}")
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
                image_path = path.parent / color["image"]
                stories = {}
                for lang in LANGUAGES:
                    if lang["colorName"] not in color:
                        raise SystemExit(f"{card['id']} {slug} missing {lang['colorName']}")
                    name = color.get(lang["textField"]) or ""
                    story_path = path.parent / name
                    if Path(name).stem != f"{slug}{lang['textSuffix']}" or not story_path.is_file():
                        raise SystemExit(f"missing {lang['textField']} for {card['id']} {slug}")
                    stories[lang["id"]] = story_path
                if not image_path.is_file():
                    raise SystemExit(f"missing {image_path}")
                share_path = image_path.with_name(f"{image_path.stem}.share.jpg")
                if not share_path.is_file():
                    raise SystemExit(f"missing {share_path}")
                ensure_thumb(image_path)
                color["_slug"] = slug
                color["_texts"] = {
                    lang["id"]: paragraphs(stories[lang["id"]].read_text(), lang) for lang in LANGUAGES
                }
                color["_lines"] = {}
                for lang in LANGUAGES:
                    body, close = color["_texts"][lang["id"]]
                    color["_lines"][lang["id"]] = color_line(close, body, lang)
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
    color["_body"], color["_close"] = color["_texts"][lang["id"]]
    color["_line"] = color["_lines"][lang["id"]]


def subtitle_html(secondary):
    if not secondary:
        return ""
    return f'      <p class="en">{esc(secondary)}</p>\n'


def fields(card, color, lang, **extra):
    label = extra.get("label", "")
    values = {
        "card": card[lang["cardName"]],
        "color": color[lang["colorName"]] if color else "",
        "label": label,
        "labelLower": label.lower(),
        "latin": card["name"],
        "latinColor": color["name"] if color else "",
        "numeral": card["numeral"],
        "hex": color["hex"] if color else "",
        "intro": extra.get("intro", ""),
        "opening": extra.get("opening", ""),
    }
    return {key: fill(value, **values) for key, value in lang["pages"].items()}


def visible_name(color, lang):
    return color[lang["colorName"]]


def color_item(color, lang):
    bind(color, lang)
    line = f'\n            <span class="line">{esc(color["_line"])}</span>' if color["_line"] else ""
    thumb = thumb_name(color["image"])
    text = fields(color["_card_obj"], color, lang)
    return f"""        <li>
          <a href="{color['_slug']}/index.html">
            <img src="/data/{color['_card']}/{esc(thumb)}" alt="{esc(text['colorAlt'])}">
            <span class="name"><span class="swatch" style="background:{esc(color['hex'])}"></span>{esc(color[lang['colorName']])}</span>
            <span class="meta">{esc(text['colorMeta'])}</span>{line}
          </a>
        </li>"""


def write_card(card, meanings, lang, root):
    upright = meanings[card["id"]]["upright"]
    reversed_text = meanings[card["id"]]["reversed"]
    urls = library_url(card["id"])
    canonical = urls[lang["id"]]
    image = f"{ORIGIN}/data/{card['id']}/share.jpg"
    for side in ("upright", "reversed"):
        for color in card[side]:
            color["_card"] = card["id"]
            color["_card_obj"] = card
    upright_items = "\n".join(color_item(color, lang) for color in card["upright"])
    reversed_items = "\n".join(color_item(color, lang) for color in card["reversed"])
    films = {
        "the-devil": ("vQpHR7ydbIQ?si=YiSh7kW68tVFco0D", "The Chain Is Loose"),
        "the-fool": ("a3v-rALmRnU?si=br1pwZZYi3QcWCSI", "No Map, No Name"),
    }
    film = ""
    if card["id"] in films:
        src, title = films[card["id"]]
        film = f"""        <div class="film-frame">
          <iframe src="https://www.youtube.com/embed/{src}" title="{title}" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>
        </div>"""
    intro = first_sentence(upright.split("\n\n", 1)[0], lang["introLimit"], lang)
    text = fields(card, None, lang, intro=intro)
    description = clip(text["cardDescription"], lang["descriptionLimit"])
    upright_label = lang["copy"]["upright"]
    reversed_label = lang["copy"]["reversed"]
    face_alt = fill(lang["pages"]["faceAlt"], card=card[lang["cardName"]], label=upright_label, labelLower=upright_label.lower())
    face_alt_reversed = fill(lang["pages"]["faceAlt"], card=card[lang["cardName"]], label=reversed_label, labelLower=reversed_label.lower())
    css = ("../library.css" if not nested(lang) else "../../../cards/library.css") + "?v=3"
    depth = library_depth(lang, False)
    nav = library_nav(lang, depth, f"cards/{card['id']}/")
    secondary = subtitle_html(text["cardSecondary"])
    body = f"""    <header class="top">
      <p class="brand"><a href="../../">Colors for the Fool</a></p>
{nav}
      <p class="tagline">{esc(text['tagline'])}</p>
    </header>
    <main>
      <p class="crumb"><a href="../../">{esc(text['draw'])}</a></p>
      <img class="face" src="/data/{esc(card['id'])}/face.jpg" alt="{esc(face_alt)}">
      <h1>{esc(card[lang['cardName']])}</h1>
{secondary}      <section>
        <h2>{esc(upright_label)}</h2>
        <div class="meaning">
{meaning_html(upright)}
        </div>
{film}
        <ul class="colors">
{upright_items}
        </ul>
      </section>
      <section>
        <h2>{esc(reversed_label)}</h2>
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
            text["cardTitle"],
            description,
            canonical,
            image,
            css,
            None,
            body,
            f"/data/{card['id']}/circle.jpg",
            lang,
            hreflang(urls),
            library_script(depth),
        )
    )
    return target


def share_html(card, color, lang):
    page_url = library_url(card["id"], color["_slug"])[lang["id"]].removesuffix("index.html")
    text = fill(lang["shareText"], color=color[lang["colorName"]])
    script = "../../share.js" if not nested(lang) else "../../../../cards/share.js"
    tweet = "https://twitter.com/intent/tweet?text=" + quote(text, safe="") + "&url=" + quote(page_url, safe="")
    line = "https://social-plugins.line.me/lineit/share?url=" + quote(page_url, safe="")
    labels = lang["share"]
    return f"""      <p class="share" data-url="{esc(page_url)}">
        <button type="button" id="share-copy" aria-label="{esc(labels['copy'])}">
{SHARE_ICON}
        </button>
        <a id="share-x" href="{esc(tweet)}" target="_blank" rel="noopener noreferrer" aria-label="{esc(labels['x'])}">
{X_ICON}
        </a>
        <a id="share-line" href="{esc(line)}" target="_blank" rel="noopener noreferrer" aria-label="{esc(labels['line'])}">
{LINE_ICON}
        </a>
      </p>
      <p class="copied" id="copied" hidden role="status">{esc(labels['notice'])}</p>
      <script src="{script}"></script>"""


def write_color(card, side, color, lang, root):
    bind(color, lang)
    label = lang["copy"][side]
    body, close = color["_body"], color["_close"]
    urls = library_url(card["id"], color["_slug"])
    canonical = urls[lang["id"]]
    scene = f"{ORIGIN}/data/{card['id']}/{color['image']}"
    image = f"{ORIGIN}/data/{card['id']}/{Path(color['image']).stem}.share.jpg"
    opening = first_sentence(body[0][0], lang["introLimit"], lang) if body else ""
    text = fields(card, color, lang, label=label, opening=opening)
    description = clip(text["colorDescription"], lang["descriptionLimit"])
    css = ("../../library.css" if not nested(lang) else "../../../../cards/library.css") + "?v=3"
    depth = library_depth(lang, True)
    nav = library_nav(lang, depth, f"cards/{card['id']}/{color['_slug']}/")
    siblings = []
    for other_color in card[side]:
        if other_color is color:
            continue
        siblings.append(
            f'        <li><a href="../{other_color["_slug"]}/index.html"><span class="swatch" style="background:{esc(other_color["hex"])}"></span>{esc(visible_name(other_color, lang))}</a></li>'
        )
    sibling_html = "\n".join(siblings)
    day_html = ""
    if lang.get("days"):
        for item in day_links():
            if item["card"] == card["id"] and item["color"] == color["_slug"]:
                day_html += f'      <p class="day"><a href="../../../days/{item["date"]}/">西暦{item["label"]}</a></p>\n'
    body_html = f"""    <header class="top">
      <p class="brand"><a href="../../../">Colors for the Fool</a></p>
{nav}
      <p class="tagline">{esc(text['tagline'])}</p>
    </header>
    <main>
      <p class="crumb"><a href="../../../">{esc(text['draw'])}</a> / <a href="../index.html">{esc(card[lang['cardName']])}</a></p>
      <img class="scene" src="/data/{esc(card['id'])}/{esc(color['image'])}" alt="{esc(text['colorAlt'])}">
      <h1>{esc(color[lang['colorName']])}</h1>
{subtitle_html(text['colorSecondary'])}      <p class="orientation">{esc(label)} · {esc(color['hex'])}</p>
{day_html}      <article class="story">
{story_html(body, close)}
      </article>
{share_html(card, color, lang)}
      <a class="back" href="../index.html">{esc(text['back'])}</a>
      <ul class="siblings">
{sibling_html}
      </ul>
    </main>"""
    target = root / card["id"] / color["_slug"] / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        page(
            f"{text['colorTitle']} — Colors for the Fool",
            description,
            canonical,
            image,
            css,
            {
                "@context": "https://schema.org",
                "@type": "Article",
                "headline": text["colorTitle"],
                "inLanguage": lang["htmlLang"],
                "image": scene,
                "description": description,
                "mainEntityOfPage": canonical,
                "publisher": {"@type": "Organization", "name": "Colors for the Fool"},
            },
            body_html,
            f"/data/{card['id']}/circle.jpg",
            lang,
            hreflang(urls),
            library_script(depth),
        )
    )
    return target


def link_top(cards):
    root_lang = next(lang for lang in LANGUAGES if not nested(lang))
    path = home_path(root_lang)
    text = path.read_text()
    for card in cards:
        name = card[root_lang["cardName"]]
        pattern = re.compile(
            rf'<h3>(?:<a href="cards/{re.escape(card["id"])}/index.html">)?{re.escape(name)}<span class="latin">([^<]*)</span>(?:</a>)?</h3>'
        )
        replacement = (
            f'<h3><a href="cards/{card["id"]}/index.html">{name}'
            r'<span class="latin">\1</span></a></h3>'
        )
        text, count = pattern.subn(replacement, text, count=1)
        if count != 1:
            raise SystemExit(f"top heading not found for {name}")
    path.write_text(text)


def day_links():
    path = ROOT / "data" / "day-links.json"
    if not path.is_file():
        return []
    return json.loads(path.read_text())


DESIGN_STYLES = (
    "ancient-egypt",
    "art-nouveau",
    "botanical-art",
    "brutalist-graphic",
    "chess-pieces",
    "classic-tarot",
    "colored-pencil",
    "cubism",
    "cyber-mysticism",
    "editorial-luxury",
    "engraving",
    "french-doll",
    "gear-engine-robotics",
    "glass-and-chrome",
    "greek-sculpture",
    "japanese-contemporary-poster",
    "luxury-ui",
    "mezzotint",
    "minimal-geometric",
    "neo-deco",
    "neo-symbolism",
    "plastic-model-diorama",
    "rorschach",
    "ruler-compass-pen",
    "stained-glass",
    "suit-and-dress",
    "sumi-e",
    "surreal-photography",
    "tile-mosaic",
    "unkei-kaikei",
    "watercolor",
    "wayang-kulit",
)


def write_sitemap(paths):
    urls = [home_url(lang) for lang in LANGUAGES]
    design_roots = [PUBLIC / "design"]
    for lang in LANGUAGES:
        if not lang["prefix"]:
            continue
        root = PUBLIC / lang["prefix"] / "design"
        if (root / "index.html").is_file():
            design_roots.append(root)
    for root in design_roots:
        rel = root.relative_to(PUBLIC).as_posix()
        urls.append(f"{ORIGIN}/{rel}/")
        for style in DESIGN_STYLES:
            if (root / style / "index.html").is_file():
                urls.append(f"{ORIGIN}/{rel}/{style}/")
    urls.extend(f"{ORIGIN}/{path.relative_to(PUBLIC).as_posix()}" for path in paths)
    urls.extend(f"{ORIGIN}/days/{item['date']}/" for item in day_links())
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


CLIENT_KEYS = (
    "id", "htmlLang", "prefix", "cookie", "session", "data", "cardName", "colorName",
    "textField", "textSuffix", "latinSubtitle", "titlePattern", "shareText", "copy",
)


def write_client():
    packs = []
    for lang in LANGUAGES:
        pack = {key: lang[key] for key in CLIENT_KEYS if key in lang}
        pack.setdefault("latinSubtitle", True)
        packs.append(pack)
    (PUBLIC / "languages.js").write_text(
        "window.LANG_PACKS = "
        + json.dumps(packs, ensure_ascii=False, indent=2)
        + ";\n"
    )


def write_fonts():
    rules = [
        f'html[lang="{lang["htmlLang"]}"] body {{\n  font-family: {lang["fontFamily"]};\n}}'
        for lang in LANGUAGES
        if lang.get("fontFamily")
    ]
    (PUBLIC / "lang.css").write_text(
        "/* Generated from data/languages.json. */\n" + "\n\n".join(rules) + ("\n" if rules else "")
    )


NAV_LABEL = {
    "ja": "言語",
    "en": "Languages",
    "zh": "語言",
    "es": "Idiomas",
    "nl": "Talen",
}


def library_depth(lang, color):
    return (1 if nested(lang) else 0) + (3 if color else 2)


def library_href(other, depth, tail):
    prefix = f"{other['prefix']}/" if nested(other) else ""
    return f"{'../' * depth}{prefix}{tail}"


def library_nav(lang, depth, tail):
    items = "\n".join(
        f'            <li><a href="{library_href(other, depth, tail)}">{esc(other["switchLabel"])}</a></li>'
        for other in LANGUAGES
        if other["id"] != lang["id"]
    )
    label = esc(lang["switchLabel"])
    nav = esc(NAV_LABEL.get(lang["id"], lang["switchLabel"]))
    return (
        f'      <nav class="mast" aria-label="{nav}">\n'
        '        <div class="lang-menu">\n'
        f'          <button type="button" class="lang" aria-expanded="false" aria-haspopup="true" aria-controls="lang-list">{label}<span class="lang-mark" aria-hidden="true"></span></button>\n'
        '          <ul class="lang-list" id="lang-list" hidden>\n'
        f"{items}\n"
        "          </ul>\n"
        "        </div>\n"
        "      </nav>"
    )


def library_script(depth):
    return f'    <script src="{"../" * depth}design/lang.js"></script>\n'


def switch_href(here, other):
    if not nested(here):
        return f"{other['prefix']}/"
    if not nested(other):
        return "../"
    return f"../{other['prefix']}/"


def language_switch(lang):
    items = "\n".join(
        f'            <li><a href="{switch_href(lang, other)}">{esc(other["switchLabel"])}</a></li>'
        for other in LANGUAGES
        if other["id"] != lang["id"]
    )
    label = esc(lang["switchLabel"])
    return (
        '        <div class="lang-menu">\n'
        f'          <button type="button" class="lang" aria-expanded="false" aria-haspopup="true" aria-controls="lang-list">{label}<span class="lang-mark" aria-hidden="true"></span></button>\n'
        '          <ul class="lang-list" id="lang-list" hidden>\n'
        f"{items}\n"
        "          </ul>\n"
        "        </div>"
    )


def refresh_homes():
    urls = {lang["id"]: home_url(lang) for lang in LANGUAGES}
    block = "    <!-- hreflang -->\n" + hreflang(urls) + "\n    <!-- /hreflang -->"
    for lang in LANGUAGES:
        path = home_path(lang)
        if not path.is_file():
            print(f"skip home {lang['id']}: {path}")
            continue
        text = path.read_text()
        if "<!-- hreflang -->" in text:
            text = re.sub(
                r"    <!-- hreflang -->.*?    <!-- /hreflang -->",
                block,
                text,
                count=1,
                flags=re.S,
            )
        else:
            text, count = re.subn(
                r'(?:    <link rel="alternate" hreflang="[^"]+" href="[^"]+">\n)+',
                block + "\n",
                text,
                count=1,
            )
            if count != 1:
                raise SystemExit(f"hreflang block not found in {path}")
        text = re.sub(r'\n[ \t]*<div class="lang-menu">.*?</div>', "", text, count=1, flags=re.S)
        text = re.sub(r'\n[ \t]*<a class="lang" href="[^"]*">[^<]*</a>', "", text)
        text, count = re.subn(
            r"\n[ \t]*</nav>",
            "\n" + language_switch(lang) + "\n      </nav>",
            text,
            count=1,
        )
        if count != 1:
            raise SystemExit(f"nav not found in {path}")
        script = "languages.js" if not nested(lang) else "../languages.js"
        app = "app.js" if not nested(lang) else "../app.js"
        if "languages.js" not in text:
            text = text.replace(
                f'<script src="{app}"></script>',
                f'<script src="{script}"></script>\n    <script src="{app}"></script>',
                1,
            )
        font_href = f"https://fonts.googleapis.com/css2?{lang['fonts']}&display=swap"
        text, count = re.subn(
            r"https://fonts\.googleapis\.com/css2\?[^\"']+",
            font_href,
            text,
            count=1,
        )
        if count != 1:
            raise SystemExit(f"font link not found in {path}")
        path.write_text(text)


def main():
    meanings = {lang["id"]: load_meanings(lang) for lang in LANGUAGES}
    cards = load_cards()
    if len(cards) != 22:
        raise SystemExit(f"expected 22 cards, found {len(cards)}")
    for lang in LANGUAGES:
        missing = [card["id"] for card in cards if card["id"] not in meanings[lang["id"]]]
        if missing:
            raise SystemExit(f"missing {lang['id']} meanings {missing}")
    written = set()
    for lang in LANGUAGES:
        root = card_root(lang)
        for card in cards:
            written.add(write_card(card, meanings[lang["id"]], lang, root))
            for side in ("upright", "reversed"):
                for color in card[side]:
                    written.add(write_color(card, side, color, lang, root))
        remove_stale(written, root)
    link_top(cards)
    write_sitemap(sorted(written))
    write_client()
    write_fonts()
    refresh_homes()
    print(f"cards {len(cards)} pages {len(written)} languages {len(LANGUAGES)}")


if __name__ == "__main__":
    main()
