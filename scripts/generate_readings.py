#!/usr/bin/env python3
"""Write one card-color essay per assigned color. Skips files that already exist."""

import argparse
import json
import sys
import threading
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = "gpt-4.1"
LOCK = threading.Lock()

NOTES = {
    "the-fool": ("崖の前の軽い一歩、無垢、旅の始まり、白い花と小さな犬。", "確認を省いた軽さ。足元が見えないまま跳ぼうとする。"),
    "the-magician": ("意志と四つの道具。杖、杯、剣、円盤。庭の卓で、上と下をつなぐ。", "道具が手元にありながら、使い方がすり替わる。手本がまやかしになる。"),
    "the-high-priestess": ("二本の柱、ベール、閉じた巻物、静かな水面。秘密はまだ守られている。", "秘密が壁になる。巻物は閉じたまま、水面は答えない。"),
    "the-empress": ("麦と薔薇と庭。実り、席、滝。豊かなものがすでに周囲にある。", "庭が手放される。庇護が重く、実りが卓に届かない。"),
    "the-emperor": ("石の座、境界、山、決められた手順。秩序が道を守る。", "手順だけが残り、座が空になる。硬さが目的になる。"),
    "the-hierophant": ("鍵、式服、神殿、二人の侍者。受け継がれたやり方が、今夜の手順になる。", "式だけが繰り返され、意味が席を外す。型への反発。"),
    "the-lovers": ("二人、庭、開かれた選択。結びは、選ぶことで始まる。", "選ばないまま並んでいる。言葉が相手に届く前に乾く。"),
    "the-chariot": ("天蓋、二つの獣、城門。手綱が揃っているときの前進。", "二つの獣が別々の方向を向く。進むことだけが目的になる。"),
    "strength": ("花の冠、獅子の口をそっと閉じる手。力は音を立てない。", "力ずくになる。獅子を抑えようとするほど、手が強ばる。"),
    "the-hermit": ("高い道、杖、一つの灯。孤独は、照らす範囲を手元に限ること。", "灯を消したまま山に残る。人を拒むことが道になる。"),
    "wheel-of-fortune": ("回る輪、季節、昇ることと降ることが同じ軸にある。", "下向きの回り。止めたがり、回りきる前に手を置く。"),
    "justice": ("剣と秤、垂れ幕、はっきりした昼。原因と結果が同じ卓に並ぶ。", "秤が傾いたまま放置される。正しい手順が、誰かの不在で空回りする。"),
    "the-hanged-man": ("生きた木、逆さの静止、光の輪。止まることが、見方を変える。", "止まれない。あるいは、止まったまま意味を拒む。"),
    "death": ("白い花を掲げた騎手、二つの塔のあいだの夜明け。終わりが次の輪郭を作る。", "終わらせない。古い冠を握ったまま、夜明けを見ない。"),
    "temperance": ("二つの杯のあいだを移る水、池、尾根への道。混ぜることが仕事。", "水が杯の外にこぼれる。混ぜる前に、どちらかへ傾く。"),
    "the-devil": ("台座、松明、緩めば外れる鎖。欲望は、見えているあいだは道具である。", "鎖がすでに緩んでいる。影を否定するか、鎖を飾りにしたまま座る。"),
    "the-tower": ("一本の落雷、落ちる冠、夜の塔。崩れることで、中に残っていたものが出る。", "崩れを先送りする。瓦礫を塔だと言い続ける。"),
    "the-star": ("池、二つの水差し、大きな星と小さな星。希望は、水を地面に返すこと。", "池の縁が乾く。星はあっても、水差しを置いたままになる。"),
    "the-moon": ("半分だけ見える道、犬と狼、潮、塔。輪郭は薄い光の側に残る。", "道の上にもう一枚の夜が降りる。犬と狼の区別が消え、霧が名前を回収する。"),
    "the-sun": ("光はもう来ている。見えていなかった輪郭が、手元に戻る。", "光が強すぎて、道も布も色褪せる。乾き、砂、長く歩いた靴。"),
    "judgement": ("雲の上の角笛、開いた棺、立ち上がる人々。呼び声は、すでに鳴っている。", "呼び声を聞いたまま、棺の縁に座る。返事を翌日に回す。"),
    "the-world": ("葉の輪、踊る人、四つの生きもの。一巡が閉じ、リボンが結ばれる。", "輪が半開きのまま。終わりの直前で、結び目から手が離れる。"),
}


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
        for orientation, label in (("upright", "正位置"), ("reversed", "逆位置")):
            for color in data[orientation]:
                if color.get("text"):
                    continue
                found.append(
                    {
                        "id": data["id"],
                        "name": data["name"],
                        "nameJa": data["nameJa"],
                        "orientation": orientation,
                        "label": label,
                        "note": NOTES[data["id"]][0 if orientation == "upright" else 1],
                        "color": color["name"],
                        "hex": color["hex"],
                        "colorJa": color["nameJa"],
                        "file": color["name"].lower() + ".txt",
                    }
                )
    return found


def prompt_for(job: dict) -> str:
    return f"""あなたはタロットのラッキーカラー文章を書く。見本と同じ静かな説明調で、日本語だけを使う。

カード: {job["name"]}（{job["nameJa"]}）
向き: {job["label"]}
この向きの核: {job["note"]}
着地させる色: {job["color"]} / {job["colorJa"]} / {job["hex"]}
色名が英語として指す物・土地・食物・布・植物・職業・天気を、物語の具体物にする。色味の近さの話はしない。

規則:
- 1行目はちょうど「{job["name"]} ― {job["label"]}」
- 一つの流れで書く。最後に明かす色名が指す物だけをたどる。途中で「この色は」と名指ししない
- 色名の日常語（黒、白、赤、青、金、銀、緑、黄、紫、灰、桃）も、最後の色名の行より前では使わない。煤、墨、夜、亜麻、帆、薔薇、霧のように物の名で書く
- カードの象徴から入り、その流れの中に神話、地理、歴史、天候、生活の道具を織る
- 今日できる小さな動作は、物語に出た道具の延長として三つか四つ
- 色の名前（{job["colorJa"]} と {job["color"]}）は、本文の途中と題に出さない
- 他のCSS色名も、その日本語名も出さない
- 結びは次の2行で、この文言をそのまま置く。ダッシュは「—」
今日のラッキーカラーは、{job["colorJa"]}です。
Lucky Color: {job["color"]} — {job["hex"]}
- そのあと、色名を繰り返さない短い結びを2行まで書いてよい
- 長さは900字から1400字。見出し、箇条書き、太字、「しましょう」は使わない
"""


def complete(key: str, text: str) -> str:
    body = json.dumps(
        {
            "model": MODEL,
            "temperature": 0.8,
            "messages": [
                {"role": "system", "content": "指示された形式だけを返す。前置きを付けない。"},
                {"role": "user", "content": text},
            ],
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
    return payload["choices"][0]["message"]["content"].strip() + "\n"


def valid(job: dict, text: str) -> str | None:
    lines = text.strip().splitlines()
    if not lines or lines[0].strip() != f"{job['name']} ― {job['label']}":
        return "題名"
    reveal = f"今日のラッキーカラーは、{job['colorJa']}です。"
    lucky = f"Lucky Color: {job['color']} — {job['hex']}"
    if text.count(reveal) != 1:
        return "日本語の色名"
    if text.count(lucky) != 1:
        return "Lucky Color行"
    head, _, _tail = text.partition(reveal)
    if job["colorJa"] in head or job["color"] in head:
        return "途中で色名"
    spoilers = ("黒い", "黒は", "黒の", "白い", "白は", "白い", "赤い", "赤は", "青い", "青は", "金色", "銀色", "緑の", "黄色い", "紫の", "灰色", "ピンク")
    if any(word in head for word in spoilers):
        return "途中で色の日常語"
    after = text.split(lucky, 1)[1]
    if job["colorJa"] in after or job["color"] in after:
        return "結びで色名を反復"
    return None


def attach(job: dict) -> None:
    path = ROOT / "data" / job["id"] / "card.json"
    with LOCK:
        data = json.loads(path.read_text())
        for color in data[job["orientation"]]:
            if color["name"] == job["color"]:
                color["text"] = job["file"]
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def one(key: str, job: dict) -> str:
    folder = ROOT / "data" / job["id"]
    target = folder / job["file"]
    last_error = "未生成"
    for _attempt in range(3):
        try:
            text = complete(key, prompt_for(job))
            text = "\n".join(line.rstrip() for line in text.strip().splitlines()) + "\n"
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:300]
            last_error = f"API {error.code} {detail}"
            continue
        except Exception as error:  # noqa: BLE001
            last_error = str(error)
            continue
        problem = valid(job, text)
        if problem:
            last_error = problem
            continue
        target.write_text(text, encoding="utf-8")
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
        return
    key = load_key()
    failures = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(one, key, job) for job in pending]
        for future in as_completed(futures):
            line = future.result()
            print(line, flush=True)
            if line.startswith("FAIL"):
                failures += 1
    if failures:
        sys.exit(f"failed {failures}")


if __name__ == "__main__":
    main()
