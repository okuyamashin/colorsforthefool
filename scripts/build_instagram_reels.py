#!/usr/bin/env python3
"""15秒の「今日のカラー」リールを、data/ の各色について書き出す。"""

import json
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FFMPEG = "/tmp/ffmpeg-bin/ffmpeg"
FONT = "/System/Library/Fonts/ヒラギノ明朝 ProN.ttc"
WORK = Path("/tmp/ig-reels")
W, H = 1080, 1920
CREAM = (248, 243, 221, 255)
SCROLL = (248, 243, 221, 235)
SHADOW = (28, 22, 14, 170)
INK = (42, 33, 24, 255)
NO_START = set("、。，．！？）」』】")
NO_END = set("「（『【")
FIRST = DATA / "The First Turn — Arcana 0 to X.mp3"
SECOND = DATA / "The Second Turn — Arcana XI to XXI.mp3"
# 歌い出し。15秒に足りなければ、そのまま次のカードへ入る。
CUE = {
    "the-fool": (FIRST, 11.0),
    "the-magician": (FIRST, 31.6),
    "the-high-priestess": (FIRST, 50.8),
    "the-empress": (FIRST, 75.1),
    "the-emperor": (FIRST, 91.4),
    "the-hierophant": (FIRST, 109.5),
    "the-lovers": (FIRST, 146.0),
    "the-chariot": (FIRST, 163.0),
    "strength": (FIRST, 179.3),
    "the-hermit": (FIRST, 199.3),
    "wheel-of-fortune": (FIRST, 216.7),
    "justice": (SECOND, 16.6),
    "the-hanged-man": (SECOND, 50.4),
    "death": (SECOND, 67.4),
    "temperance": (SECOND, 82.0),
    "the-devil": (SECOND, 96.8),
    "the-tower": (SECOND, 113.7),
    "the-star": (SECOND, 131.6),
    "the-moon": (SECOND, 147.8),
    "the-sun": (SECOND, 165.6),
    "judgement": (SECOND, 182.6),
    "the-world": (SECOND, 198.8),
}
ZOOM = (
    "z='1.02+0.06*on/119'"
    ":x='iw/2-(iw/zoom/2)-18+36*on/119'"
    ":y='ih/2-(ih/zoom/2)+10-20*on/119'"
    ":d=120:s=1080x1920:fps=30"
)


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-2000:])


def luminance(hex_color):
    h = hex_color.lstrip("#")
    rgb = [int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)]

    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (lin(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def wrap(text, font, width):
    rows, buf = [], ""
    for ch in text:
        trial = buf + ch
        if font.getlength(trial) <= width:
            buf = trial
            continue
        if ch in NO_START and buf:
            buf += ch
            continue
        if buf and buf[-1] in NO_END:
            rows.append(buf[:-1] or buf)
            buf = buf[-1] + ch
            continue
        if buf:
            rows.append(buf)
        buf = ch
    if buf:
        rows.append(buf)
    while len(rows) >= 2 and len(rows[-1]) <= 2 and rows[-2]:
        prev = rows[-2]
        rows[-2] = prev[:-1]
        rows[-1] = prev[-1] + rows[-1]
        if not rows[-2]:
            rows.pop(-2)
    return rows


def name_font(name):
    limit = W - 120
    size = 118
    while size > 40:
        font = ImageFont.truetype(FONT, size, index=0)
        if font.getlength(name) <= limit:
            return font, size
        size -= 2
    return ImageFont.truetype(FONT, 40, index=0), 40


def build_opening(card_dir, reversed_card, dest):
    if dest.exists() and dest.stat().st_size > 10000:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    flip = "hflip,vflip," if reversed_card else ""
    face_mp4 = card_dir / "face.mp4"
    if face_mp4.exists():
        vf = (
            f"{flip}trim=start=0:end=4,setpts=PTS-STARTPTS,"
            "scale=1080:1920:flags=lanczos,fps=30,setsar=1,format=yuv420p"
        )
        run([
            FFMPEG, "-y", "-i", str(face_mp4), "-vf", vf, "-an", "-t", "4",
            "-c:v", "h264_videotoolbox", "-b:v", "10M", "-pix_fmt", "yuv420p",
            str(dest),
        ])
        return
    vf = f"{flip}scale=1440:2160:flags=lanczos,zoompan={ZOOM},setsar=1,format=yuv420p"
    run([
        FFMPEG, "-y", "-loop", "1", "-i", str(card_dir / "face.jpg"),
        "-vf", vf, "-an", "-frames:v", "120",
        "-c:v", "h264_videotoolbox", "-b:v", "10M", "-pix_fmt", "yuv420p",
        str(dest),
    ])


def build_stills(text_path, hex_color, name, work):
    work.mkdir(parents=True, exist_ok=True)
    body = ImageFont.truetype(FONT, 54, index=0)
    head = ImageFont.truetype(FONT, 44, index=2)
    end_line = ImageFont.truetype(FONT, 60, index=0)
    lines = [
        line.rstrip()
        for line in text_path.read_text().splitlines()
        if not line.startswith("Lucky Color")
    ]
    text_w = W - 160
    blocks = []
    for i, line in enumerate(lines):
        if not line.strip():
            blocks.append(("gap", 36))
            continue
        font = head if i == 0 else body
        gap = 74 if i == 0 else 84
        blocks.append((font, wrap(line, font, text_w), gap, i == 0))
    height = 120
    for block in blocks:
        if block[0] == "gap":
            height += block[1]
        else:
            height += block[2] * len(block[1])
    scroll = Image.new("RGBA", (W, max(height + 180, H + 2)), (0, 0, 0, 0))
    draw = ImageDraw.Draw(scroll)
    y = 120
    for block in blocks:
        if block[0] == "gap":
            y += block[1]
            continue
        font, rows, gap, is_head = block
        center = is_head or len(rows) == 1
        for row in rows:
            x = (W - font.getlength(row)) / 2 if center else 80
            draw.text((x + 2, y + 3), row, font=font, fill=SHADOW)
            draw.text((x, y), row, font=font, fill=SCROLL)
            y += gap
    scroll.save(work / "scroll.png")

    ink = INK if luminance(hex_color) > 0.5 else CREAM
    label, size = name_font(name)
    base = Image.new("RGBA", (W, H), tuple(int(hex_color.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)) + (255,))
    bd = ImageDraw.Draw(base)
    line1 = "今日のラッキーカラーは"
    top = (H - (80 + size + 30)) / 2
    bd.text(((W - end_line.getlength(line1)) / 2, top), line1, font=end_line, fill=ink)
    bd.text(((W - label.getlength(name)) / 2, top + 100), name, font=label, fill=ink)
    base.save(work / "base.png")


def build_reel(card_dir, color, opening, audio, start, dest):
    work = WORK / card_dir.name / color["image"].replace(".jpg", "")
    build_stills(card_dir / color["text"], color["hex"], color["nameJa"], work)
    pad = "0x" + color["hex"].lstrip("#").upper()
    scene = card_dir / color["image"]
    run([
        FFMPEG, "-y",
        "-loop", "1", "-framerate", "30", "-t", "15", "-i", str(work / "base.png"),
        "-i", str(opening),
        "-loop", "1", "-framerate", "30", "-t", "11.8", "-i", str(scene),
        "-loop", "1", "-framerate", "30", "-i", str(work / "scroll.png"),
        "-ss", str(start), "-t", "15", "-i", str(audio),
        "-filter_complex",
        ";".join([
            "[1:v]fps=30,scale=1080:1920,setsar=1,format=yuv420p[face]",
            f"[2:v]scale=1080:1920:force_original_aspect_ratio=decrease:flags=lanczos,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color={pad},fps=30,setsar=1,format=yuv420p[scene]",
            "[face][scene]xfade=transition=fade:duration=0.8:offset=3.2,format=rgba,fade=t=out:st=8:d=7:alpha=1[pic]",
            "[3:v]format=rgba,crop=1080:1920:0:'(ih-1920)*min(t/5\\,1)',trim=start=0:end=5,setpts=PTS-STARTPTS,fade=t=in:st=0:d=1:alpha=1,fade=t=out:st=4:d=1:alpha=1,setpts=PTS-STARTPTS+4.4/TB,fps=30,setsar=1[scr]",
            "[0:v]format=rgba[base]",
            "[base][pic]overlay=eof_action=pass:format=auto[mid]",
            "[mid][scr]overlay=eof_action=pass:format=auto,format=yuv420p[v]",
            "[4:a]afade=t=in:st=0:d=0.03,afade=t=out:st=14.55:d=0.45,aformat=sample_rates=48000:channel_layouts=stereo[a]",
        ]),
        "-map", "[v]", "-map", "[a]", "-t", "15",
        "-c:v", "h264_videotoolbox", "-b:v", "10M", "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart",
        str(dest.with_suffix(".part.mp4")),
    ])
    dest.with_suffix(".part.mp4").replace(dest)


def jobs(only=None):
    found = []
    for card_dir in sorted(p for p in DATA.iterdir() if (p / "card.json").exists()):
        meta = json.loads((card_dir / "card.json").read_text())
        for orientation, reversed_card in (("upright", False), ("reversed", True)):
            for color in meta[orientation]:
                key = f"{card_dir.name}/{color['image'].replace('.jpg', '')}"
                if only and key not in only and card_dir.name not in only:
                    continue
                dest = card_dir / color["image"].replace(".jpg", ".instagram.mp4")
                found.append((card_dir, color, reversed_card, dest))
    return found


def main():
    only = set(sys.argv[1:])
    pending = [item for item in jobs(only) if not (item[3].exists() and item[3].stat().st_size > 500_000)]
    print(f"todo {len(pending)}", flush=True)
    started = time.time()
    openings = {}
    failed = []
    for index, (card_dir, color, reversed_card, dest) in enumerate(pending, 1):
        try:
            key = (card_dir.name, reversed_card)
            if key not in openings:
                opening = WORK / "open" / f"{card_dir.name}-{'rev' if reversed_card else 'up'}.mp4"
                build_opening(card_dir, reversed_card, opening)
                openings[key] = opening
            audio, start = CUE[card_dir.name]
            build_reel(card_dir, color, openings[key], audio, start, dest)
        except Exception as error:
            failed.append(f"{card_dir.name}/{color['image']}: {error}")
            print("FAIL", failed[-1][:300], flush=True)
            continue
        elapsed = time.time() - started
        rate = elapsed / index
        left = rate * (len(pending) - index)
        print(f"{index}/{len(pending)} {dest.relative_to(DATA)} {elapsed:.0f}s left {left/60:.1f}min", flush=True)
    print(f"done failed {len(failed)}", flush=True)
    if failed:
        (WORK / "failed.txt").write_text("\n".join(failed))


if __name__ == "__main__":
    main()
