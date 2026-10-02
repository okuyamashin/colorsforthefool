"""日本時間のその日のリールを1本、Instagram の公式APIで出す。"""

import html
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

import boto3

JST = timezone(timedelta(hours=9))
GRAPH = "https://graph.facebook.com/v26.0"
BUCKET = os.environ["BUCKET"]
SCHEDULE_KEY = os.environ.get("SCHEDULE_KEY", "instagram/schedule.json")
SECRET_ID = os.environ.get("SECRET_ID", "colorsofthefool/instagram")
OPENAI_SECRET_ID = os.environ.get("OPENAI_SECRET_ID", "colorsofthefool/openai")
PUBLIC_BASE = os.environ.get(
    "PUBLIC_BASE", "https://colorsofthefool.engawa5656.com"
).rstrip("/")

s3 = boto3.client("s3")
secrets = boto3.client("secretsmanager")


NOTES = {
    "the-fool": ("崖の前の軽い一歩、無垢、旅の始まり、白い花と小さな犬。", "確認を省いた軽さ。足元が見えないまま跳ぼうとする。"),
    "the-magician": ("意志と四つの道具。杖、杯、剣、円盤。庭の卓で、上と下をつなぐ。", "道具が手元にありながら、使い方がすり替わる。手本がまやかしになる。"),
    "the-high-priestess": ("二本の柱、ベール、閉じた巻物、静かな水面。秘密はまだ守られている。", "秘密が壁になる。巻物は閉じたまま、水面は答えない。"),
    "the-emperor": ("石の座、境界、山、決められた手順。秩序が道を守る。", "手順だけが残り、座が空になる。硬さが目的になる。"),
    "the-empress": ("麦と薔薇と庭。実り、席、滝。豊かなものがすでに周囲にある。", "庭が手放される。庇護が重く、実りが卓に届かない。"),
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


def handler(event, context):
    event = event or {}
    schedule = load_schedule()
    day = target_day(event)
    index = (day - datetime.fromisoformat(schedule["start"]).date()).days
    if index < 0 or index >= len(schedule["items"]):
        return {"posted": False, "reason": "outside the 440-day schedule", "date": iso(day)}

    item = schedule["items"][index]
    if event.get("pageOnly"):
        page = ensure_day_page(day, item, datetime.fromisoformat(schedule["start"]).date())
        return {"posted": False, "reason": "page only", "date": iso(day), "page": page}

    marker = f"instagram/posted/{iso(day)}.json"
    if marker_exists(marker):
        return {"posted": False, "reason": "already posted", "date": iso(day), "day": item["day"]}

    caption = f"西暦{day.year}年{day.month}月{day.day}日\n{item['caption'].strip()}"
    video_url = f"{PUBLIC_BASE}/{item['reelKey']}"
    ensure_video(video_url)
    token, user_id = instagram_secret()
    published = publish_reel(user_id, token, video_url, caption, context)
    record = {
        "date": iso(day),
        "day": item["day"],
        "card": item["card"],
        "orientation": item["orientation"],
        "color": item["color"],
        "mediaId": published["id"],
        "permalink": published.get("permalink"),
        "videoUrl": video_url,
    }
    s3.put_object(
        Bucket=BUCKET,
        Key=marker,
        Body=json.dumps(record, ensure_ascii=False).encode(),
        ContentType="application/json",
    )
    return {"posted": True, **record}


def load_schedule():
    response = s3.get_object(Bucket=BUCKET, Key=SCHEDULE_KEY)
    return json.loads(response["Body"].read())


def target_day(event):
    if event.get("date"):
        return datetime.fromisoformat(event["date"]).date()
    return datetime.now(JST).date()


def iso(day):
    return day.isoformat()


def marker_exists(key):
    response = s3.list_objects_v2(Bucket=BUCKET, Prefix=key, MaxKeys=1)
    return any(item["Key"] == key for item in response.get("Contents", []))


def ensure_video(url):
    request = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            kind = response.headers.get("Content-Type", "")
            if response.status != 200 or "video" not in kind:
                raise RuntimeError(f"reel URL is not a video ({response.status}, {kind})")
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"reel URL returned {error.code}") from error


def instagram_secret():
    response = secrets.get_secret_value(SecretId=SECRET_ID)
    payload = json.loads(response["SecretString"])
    user_id = payload.get("igUserId") or ""
    token = payload.get("accessToken") or ""
    if not user_id or not token:
        raise RuntimeError("instagram secret needs igUserId and accessToken")
    return token, user_id


def publish_reel(user_id, token, video_url, caption, context):
    created = graph(
        f"{user_id}/media",
        token,
        {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "share_to_feed": "true",
        },
    )
    container = created["id"]
    deadline = time.time() + max(30, (context.get_remaining_time_in_millis() / 1000) - 20)
    while time.time() < deadline:
        status = graph(container, token, query={"fields": "status_code,status"})
        code = status.get("status_code")
        if code == "FINISHED":
            published = graph(
                f"{user_id}/media_publish",
                token,
                {"creation_id": container},
            )
            media_id = published["id"]
            permalink = None
            try:
                info = graph(media_id, token, query={"fields": "permalink"})
                permalink = info.get("permalink")
            except RuntimeError:
                permalink = None
            return {"id": media_id, "permalink": permalink}
        if code in {"ERROR", "EXPIRED"}:
            raise RuntimeError(f"instagram container {code}: {status.get('status')}")
        time.sleep(5)
    raise RuntimeError("instagram container was not finished before timeout")


def graph(path, token, payload=None, query=None):
    url = f"{GRAPH}/{path}"
    data = None
    if payload is not None:
        body = dict(payload)
        body["access_token"] = token
        data = urllib.parse.urlencode(body).encode()
    else:
        params = dict(query or {})
        params["access_token"] = token
        url = f"{url}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")
        raise RuntimeError(f"instagram API {error.code}: {redact(detail, token)}") from error


def redact(text, token):
    return text.replace(token, "[token]")


def ensure_day_page(day, item, start):
    key = f"days/{iso(day)}/index.html"
    if marker_exists(key):
        return {"key": key, "wrote": False}
    label = "正位置" if item["orientation"] == "upright" else "逆位置"
    note = NOTES[item["card"]][0 if item["orientation"] == "upright" else 1]
    facts = day_facts(day)
    essay = compose(item, label, note, facts)
    body = page_html(day, item, label, essay, start)
    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=body.encode(),
        ContentType="text/html; charset=utf-8",
        CacheControl="public, max-age=300",
    )
    stitch_forward(day)
    return {"key": key, "wrote": True, "card": item["card"], "color": item["color"]}


def dated(day):
    return f"西暦{day.year}年{day.month}月{day.day}日"


def stitch_forward(day):
    prev = day - timedelta(days=1)
    key = f"days/{iso(prev)}/index.html"
    if not marker_exists(key):
        return
    body = s3.get_object(Bucket=BUCKET, Key=key)["Body"].read().decode()
    href = f"/days/{iso(day)}/"
    if href in body:
        return
    line = f'<p><a href="{href}">{dated(day)}</a></p>\n      '
    body = body.replace('<p class="share"', line + '<p class="share"', 1)
    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=body.encode(),
        ContentType="text/html; charset=utf-8",
        CacheControl="public, max-age=300",
    )


def day_facts(day):
    weather = tokyo_weather(day)
    market = nikkei_direction(day)
    rates = ecb_rates(day - timedelta(days=1))
    return {"weather": weather, "market": market, "usdJpy": rates["USDJPY"], "eurJpy": rates["EURJPY"]}


def tokyo_weather(day):
    url = (
        "https://api.open-meteo.com/v1/forecast?latitude=35.6762&longitude=139.6503"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum"
        f"&timezone=Asia%2FTokyo&start_date={iso(day)}&end_date={iso(day)}"
    )
    payload = fetch_json(url)
    code = payload["daily"]["weather_code"][0]
    high = payload["daily"]["temperature_2m_max"][0]
    low = payload["daily"]["temperature_2m_min"][0]
    rain = payload["daily"]["precipitation_sum"][0]
    return f"東京の空は{sky(code)}。最高気温は{round(high)}度、最低気温は{round(low)}度。降水量は{rain}ミリ。"


def sky(code):
    if code == 0:
        return "晴れ"
    if code in {1, 2}:
        return "薄曇り"
    if code == 3:
        return "曇り"
    if code in {45, 48}:
        return "霧"
    if code in {51, 53, 55, 56, 57}:
        return "霧雨"
    if code in {61, 63, 65, 66, 67, 80, 81, 82}:
        return "雨"
    if code in {71, 73, 75, 77, 85, 86}:
        return "雪"
    if code in {95, 96, 99}:
        return "雷"
    return "変わりやすい空"


def nikkei_direction(day):
    end = int(datetime(day.year, day.month, day.day, tzinfo=JST).timestamp())
    start = end - 20 * 86400
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/%5EN225"
        f"?interval=1d&period1={start}&period2={end}"
    )
    payload = fetch_json(url, {"User-Agent": "Mozilla/5.0"})
    result = payload["chart"]["result"][0]
    quote = result["indicators"]["quote"][0]
    closes = []
    for stamp, close in zip(result.get("timestamp") or [], quote["close"]):
        if close is None:
            continue
        when = datetime.fromtimestamp(stamp, JST).date()
        if when < day:
            closes.append((when, close))
    if len(closes) < 2:
        raise RuntimeError("nikkei closes were not available")
    previous, before = closes[-1][1], closes[-2][1]
    ratio = (previous - before) / before
    if abs(ratio) < 0.002:
        word = "かわらない"
    elif ratio > 0:
        word = "上がった"
    else:
        word = "下がった"
    return f"前日の日経平均は、その前の終値より{word}"


def ecb_rates(day):
    payload = fetch_json(f"https://api.frankfurter.app/{iso(day)}?from=USD&to=JPY,EUR")
    usd_jpy = payload["rates"]["JPY"]
    usd_eur = payload["rates"]["EUR"]
    return {"USDJPY": usd_jpy, "EURJPY": round(usd_jpy / usd_eur, 2)}


def compose(item, label, note, facts):
    title = f"{item['name']} \u2015 {label}"
    reveal = f"今日のラッキーカラーは、{item['colorJa']}です。"
    lucky = f"Lucky Color: {item['color']} \u2014 {item['hex']}"
    prompt = f"""あなたはタロットのラッキーカラー文章を書く。見本と同じ静かな説明調で、日本語だけを使う。

カード: {item['name']}（{item['nameJa']}）
向き: {label}
この向きの核: {note}
着地させる色: {item['color']} / {item['colorJa']} / {item['hex']}
色名が英語として指す物・土地・食物・布・植物・職業・天気を、物語の具体物にする。色味の近さの話はしない。

その日の材料。神話や地理や歴史と同じ一つの流れに織る。市況の箇条書きにはしない。次の語は言い換えず本文に置く。
- 天候: {facts['weather']}
- 株価: {facts['market']}。「{facts['market'].split('より')[-1]}」という語を使う。
- 為替: 1ドルは{facts['usdJpy']}円、1ユーロは{facts['eurJpy']}円。「{facts['usdJpy']}円」と「{facts['eurJpy']}円」をそのまま書く。

規則:
- 1行目はちょうど「{title}」
- 一つの流れで書く。最後に明かす色名が指す物だけをたどる。途中で「この色は」と名指ししない
- 色名の日常語（黒、白、赤、青、金、銀、緑、黄、紫、灰、桃）も、最後の色名の行より前では使わない。煤、墨、夜、亜麻、帆、薔薇、霧のように物の名で書く
- カードの象徴から入り、その流れの中に神話、地理、歴史、天候、生活の道具を織る
- 今日できる小さな動作は、物語に出た道具の延長として三つか四つ
- 色の名前（{item['colorJa']} と {item['color']}）は、本文の途中と題に出さない
- 他のCSS色名も、その日本語名も出さない
- 結びは次の2行で、この文言をそのまま置く。ダッシュは「\u2014」
{reveal}
{lucky}
- そのあと、色名を繰り返さない短い結びを2行まで書いてよい
- 長さは900字から1400字。見出し、箇条書き、太字、「しましょう」は使わない
"""
    last = ""
    reason = "未生成"
    for _attempt in range(3):
        ask = prompt if reason == "未生成" else prompt + f"\n直前の出力は不採用。理由: {reason}。欠ける語は言い換えず、そのまま入れる。"
        last = "\n".join(line.rstrip() for line in complete(ask).strip().splitlines())
        reason = essay_error(last, item, title, reveal, lucky, facts)
        if reason is None:
            return last
    raise RuntimeError(f"essay was not accepted: {reason}")


def essay_error(text, item, title, reveal, lucky, facts):
    lines = text.strip().splitlines()
    if not lines or lines[0].strip() != title:
        return "題名"
    if text.count(reveal) != 1 or text.count(lucky) != 1:
        return "結び"
    head = text.partition(reveal)[0]
    if item["colorJa"] in head or item["color"] in head or "この色は" in head:
        return "途中で色名"
    spoilers = ("黒い", "黒は", "黒の", "白い", "白は", "赤い", "赤は", "青い", "青は", "金色", "銀色", "緑の", "黄色い", "紫の", "灰色", "ピンク")
    if any(word in head for word in spoilers):
        return "途中で色の日常語"
    after = text.split(lucky, 1)[1]
    if item["colorJa"] in after or item["color"] in after:
        return "結びで色名を反復"
    if not 900 <= len(text.replace("\n", "")) <= 1400:
        return f"長さ{len(text.replace(chr(10), ''))}"
    direction = facts["market"].split("より")[-1]
    sky_word = facts["weather"].split("は", 1)[1].split("。", 1)[0]
    missing = [word for word in (direction, sky_word, f"{facts['usdJpy']}円", f"{facts['eurJpy']}円") if word not in text]
    if missing:
        return "欠落:" + ",".join(missing)
    return None


def complete(text):
    response = secrets.get_secret_value(SecretId=OPENAI_SECRET_ID)
    payload = json.loads(response["SecretString"])
    key = payload.get("apiKey") or ""
    if not key:
        raise RuntimeError("openai secret needs apiKey")
    body = json.dumps(
        {
            "model": "gpt-4.1",
            "temperature": 0.7,
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
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as result:
            data = json.load(result)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace").replace(key, "[key]")
        raise RuntimeError(f"openai API {error.code}: {detail}") from error
    return data["choices"][0]["message"]["content"].strip()


def sun_sign(day):
    spans = (
        ((1, 1), (1, 19), "山羊座"),
        ((1, 20), (2, 18), "水瓶座"),
        ((2, 19), (3, 20), "魚座"),
        ((3, 21), (4, 19), "牡羊座"),
        ((4, 20), (5, 20), "牡牛座"),
        ((5, 21), (6, 21), "双子座"),
        ((6, 22), (7, 22), "蟹座"),
        ((7, 23), (8, 22), "獅子座"),
        ((8, 23), (9, 22), "乙女座"),
        ((9, 23), (10, 23), "天秤座"),
        ((10, 24), (11, 22), "蠍座"),
        ((11, 23), (12, 21), "射手座"),
        ((12, 22), (12, 31), "山羊座"),
    )
    for start, end, name in spans:
        if start <= (day.month, day.day) <= end:
            return name
    return "山羊座"


def page_html(day, item, label, essay, start):
    date = f"西暦{day.year}年{day.month}月{day.day}日"
    when = f"{date} {sun_sign(day)}"
    reveal = f"今日のラッキーカラーは、{item['colorJa']}です。"
    lucky = f"Lucky Color: {item['color']} \u2014 {item['hex']}"
    head = essay.partition(reveal)[0].strip()
    if head.startswith(item["name"]):
        head = head.split("\n", 1)[1].strip()
    paragraphs = "".join(f"<p>{html.escape(block.strip())}</p>" for block in head.split("\n\n") if block.strip())
    closing = essay.split(lucky, 1)[1].strip()
    chip = f'<span class="color-chip" style="background-color:{item["hex"]}" aria-hidden="true"></span>'
    close = html.escape(closing).replace("\n", "<br>")
    url = f"{PUBLIC_BASE}/days/{iso(day)}/"
    card_url = f"{PUBLIC_BASE}/cards/{item['card']}/"
    color_url = f"{PUBLIC_BASE}/cards/{item['card']}/{item['color'].lower()}/"
    image = f"/data/{item['card']}/{item['color'].lower()}.jpg"
    face = f"/data/{item['card']}/face.jpg"
    turned = "face reversed" if item["orientation"] == "reversed" else "face"
    title = f"{date}のラッキーカラー、{item['colorJa']}"
    description = f"{date}。{item['nameJa']}の{label}、{item['colorJa']}。"
    share = urllib.parse.quote(f"今日のラッキーカラーは、{item['colorJa']}です。")
    page = urllib.parse.quote(url, safe="")
    prev = day - timedelta(days=1)
    earlier = ""
    if prev >= start:
        earlier = f'<p><a href="/days/{iso(prev)}/">{dated(prev)}</a></p>\n      '
    return f"""<!DOCTYPE html>
<html lang="ja">
  <head>
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-NQ38VZSM7B"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());
      gtag('config', 'G-NQ38VZSM7B');
    </script>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{html.escape(title)} — Colors for the Fool</title>
    <meta name="description" content="{html.escape(description)}">
    <link rel="canonical" href="{url}">
    <meta property="og:type" content="article">
    <meta property="og:locale" content="ja_JP">
    <meta property="og:title" content="{html.escape(title)}">
    <meta property="og:description" content="{html.escape(description)}">
    <meta property="og:url" content="{url}">
    <meta property="og:image" content="{PUBLIC_BASE}/data/{item['card']}/{item['color'].lower()}.share.jpg">
    <meta name="twitter:card" content="summary_large_image">
    <link rel="icon" href="/data/{item['card']}/circle.jpg" type="image/jpeg">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@500;700&family=Shippori+Mincho:wght@400;500;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="/cards/library.css">
  </head>
  <body>
    <header class="top">
      <p class="brand"><a href="/">Colors for the Fool</a></p>
      <p class="tagline">タロットで占う、今日のラッキーカラー</p>
    </header>
    <main>
      <p class="crumb"><a href="/">カードを引く</a> / <a href="{card_url}">{html.escape(item['nameJa'])}</a></p>
      <img class="{turned}" src="{face}" alt="{html.escape(item['nameJa'])}、{html.escape(label)}">
      <h1>{html.escape(item['colorJa'])}</h1>
      <p class="en">{html.escape(item['name'])} · {html.escape(item['color'])}</p>
      <p class="orientation">{html.escape(label)} · {html.escape(item['hex'])}</p>
      <article class="story">
        <p>{html.escape(when)}</p>
        {paragraphs}
        <p class="close">{html.escape(reveal)}<br>{html.escape(lucky)}{chip}{close}</p>
      </article>
      <img class="scene" src="{image}" alt="{html.escape(item['nameJa'])}の{html.escape(item['colorJa'])}。中央の鏡に色が映る絵">
      {earlier}<p class="share" data-url="{url}">
        <button type="button" id="share-copy" aria-label="リンクをコピー">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="18" cy="5" r="2.2" fill="none" stroke="currentColor" stroke-width="1.6"/>
            <circle cx="6" cy="12" r="2.2" fill="none" stroke="currentColor" stroke-width="1.6"/>
            <circle cx="18" cy="19" r="2.2" fill="none" stroke="currentColor" stroke-width="1.6"/>
            <path d="M8.2 13.1 15.7 17.4M15.7 6.6 8.2 10.9" fill="none" stroke="currentColor" stroke-width="1.6"/>
          </svg>
        </button>
        <a id="share-x" href="https://twitter.com/intent/tweet?text={share}&amp;url={page}" target="_blank" rel="noopener noreferrer" aria-label="Xでシェア">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path fill="currentColor" d="M14.2 10.4 21.5 2h-1.7l-6.3 7.2L8.4 2H2.2l7.6 11L2.2 22h1.7l6.7-7.6L15.3 22h6.2l-7.3-11.6Zm-2.4 2.7-.8-1.1L4.7 3.5h2.7l5 7.1.8 1.1 6.5 9.2h-2.7l-5.2-7.8Z"/>
          </svg>
        </a>
        <a id="share-line" href="https://social-plugins.line.me/lineit/share?url={page}" target="_blank" rel="noopener noreferrer" aria-label="LINEでシェア">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path fill="#06C755" d="M12 3.2C6.8 3.2 2.6 6.7 2.6 11c0 3.8 3.4 7 8 7.7.3.1.7.2.8.5.1.3.1.7 0 1l-.3 1.6c-.1.4.3.7.7.5l2.2-1.3c.2-.1.4-.1.6-.1 4.8-.2 8.8-3.6 8.8-7.9 0-4.3-4.2-7.8-9.4-7.8Z"/>
          </svg>
        </a>
      </p>
      <p class="copied" id="copied" hidden role="status">クリップボードにコピーしました</p>
      <script src="/cards/share.js"></script>
      <a class="back" href="{color_url}">{html.escape(item['nameJa'])}の{html.escape(item['colorJa'])}へ</a>
    </main>
    <footer class="colophon">
      <p>© 2026 Engawa Inc.</p>
      <p>連絡先 <a href="https://github.com/okuyamashin/colorsforthefool">GitHub</a></p>
    </footer>
  </body>
</html>
"""


def fetch_json(url, headers=None):
    sent = {"User-Agent": "ColorsForTheFool/1.0"}
    sent.update(headers or {})
    request = urllib.request.Request(url, headers=sent)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)
