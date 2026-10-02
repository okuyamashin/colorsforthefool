#!/usr/bin/env python3
"""Build a 1920x1080 video of one card's design studies over a song."""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "design"
SONGS = {
    "the-devil": ROOT / "audio" / "The Chain Is Loose.mp3",
    "the-fool": ROOT / "audio" / "No Map, No Name.mp3",
}
STYLES = [
    "editorial-luxury",
    "minimal-geometric",
    "neo-deco",
    "cyber-mysticism",
    "brutalist-graphic",
    "surreal-photography",
    "glass-and-chrome",
    "japanese-contemporary-poster",
    "neo-symbolism",
    "luxury-ui",
    "wayang-kulit",
    "greek-sculpture",
    "cubism",
    "plastic-model-diorama",
    "french-doll",
    "botanical-art",
    "gear-engine-robotics",
    "rorschach",
    "ruler-compass-pen",
    "suit-and-dress",
    "unkei-kaikei",
    "stained-glass",
    "tile-mosaic",
    "chess-pieces",
    "art-nouveau",
    "classic-tarot",
    "ancient-egypt",
    "engraving",
    "mezzotint",
    "colored-pencil",
    "watercolor",
    "sumi-e",
]
FADE = 0.8
FPS = 30
PAPER = "0xF4EAD8"
TIME = re.compile(r"time=(\d+):(\d+):(\d+(?:\.\d+)?)")


def song_length(ffmpeg, song):
    result = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", str(song), "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    matches = TIME.findall(result.stderr)
    if result.returncode != 0 or not matches:
        raise SystemExit(result.stderr[-1500:] or "could not read the song length")
    hours, minutes, seconds = matches[-1]
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def clip_durations(spans):
    durations = []
    for index, span in enumerate(spans):
        if span <= FADE:
            raise SystemExit(f"segment {index} is {span:.3f}s, shorter than the fade")
        durations.append(span if index == 0 else span + FADE)
    return durations


def build(until, output, ffmpeg, card, song):
    images = [DESIGN / style / f"{card}.png" for style in STYLES]
    for image in images:
        if not image.is_file():
            raise SystemExit(f"missing image: {image}")
    full = song_length(ffmpeg, song)
    span = full / len(images)
    if until is not None:
        if until <= span:
            raise SystemExit("--until must pass the first card")
        starts = [index * span for index in range(len(images)) if index * span < until]
        while len(starts) > 1 and until - starts[-1] <= FADE:
            starts.pop()
        images = images[: len(starts)]
        spans = [starts[index + 1] - starts[index] for index in range(len(starts) - 1)]
        spans.append(until - starts[-1])
        total = until
    else:
        spans = [span] * len(images)
        total = full
    durations = clip_durations(spans)

    filters = []
    for index in range(len(images)):
        filters.append(
            f"[{index}:v]scale=720:1080:flags=lanczos,"
            f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color={PAPER},"
            f"setsar=1,fps={FPS},format=yuv420p[v{index}]"
        )
    current = "v0"
    elapsed = 0.0
    for index in range(len(images) - 1):
        elapsed += durations[index]
        offset = elapsed - (index + 1) * FADE
        nxt = f"x{index + 1}"
        filters.append(
            f"[{current}][v{index + 1}]xfade=transition=fade:"
            f"duration={FADE}:offset={offset:.3f}[{nxt}]"
        )
        current = nxt
    audio_index = len(images)
    filters.append(f"[{audio_index}:a]atrim=0:{total:.3f},asetpts=PTS-STARTPTS[a]")

    command = [ffmpeg, "-y", "-hide_banner"]
    for image, duration in zip(images, durations):
        command.extend(
            ["-loop", "1", "-framerate", str(FPS), "-t", f"{duration:.3f}", "-i", str(image)]
        )
    command.extend(["-i", str(song)])
    command.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            f"[{current}]",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(FPS),
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            "-shortest",
            str(output),
        ]
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    print(f"segments {len(images)}  each {span:.3f}s  length {total:.3f}s  -> {output}")
    subprocess.run(command, check=True)


def default_ffmpeg():
    local = ROOT / "video" / "ffmpeg"
    if local.is_file():
        return str(local)
    return shutil.which("ffmpeg") or "ffmpeg"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--card", choices=tuple(SONGS), default="the-devil")
    parser.add_argument("--song", type=Path, help="audio file; defaults to the song for --card")
    parser.add_argument("--until", type=float, help="stop at this many seconds, for a short check")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--ffmpeg", default=default_ffmpeg())
    args = parser.parse_args()
    song = args.song or SONGS[args.card]
    names = {"the-devil": "the-chain-is-loose.mp4", "the-fool": "no-map-no-name.mp4"}
    output = args.output or ROOT / "video" / names[args.card]
    try:
        build(args.until, output, args.ffmpeg, args.card, song)
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)


if __name__ == "__main__":
    main()
