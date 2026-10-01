"""日本時間のその日のリールを1本、Instagram の公式APIで出す。"""

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
PUBLIC_BASE = os.environ.get(
    "PUBLIC_BASE", "https://colorsofthefool.engawa5656.com"
).rstrip("/")

s3 = boto3.client("s3")
secrets = boto3.client("secretsmanager")


def handler(event, context):
    event = event or {}
    schedule = load_schedule()
    day = target_day(event)
    index = (day - datetime.fromisoformat(schedule["start"]).date()).days
    if index < 0 or index >= len(schedule["items"]):
        return {"posted": False, "reason": "outside the 440-day schedule", "date": iso(day)}

    item = schedule["items"][index]
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
