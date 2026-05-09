# -*- coding: utf-8 -*-
import base64, hashlib, hmac, os, time, json
import requests
from dotenv import load_dotenv
load_dotenv()

API_KEY     = os.getenv("NAVER_API_KEY", "").strip()
SECRET_KEY  = os.getenv("NAVER_SECRET_KEY", "").strip()
CUSTOMER_ID = os.getenv("NAVER_CUSTOMER_ID", "").strip()

def call(uri, payload):
    ts  = str(int(time.time() * 1000))
    msg = f"{ts}.POST.{uri}"
    sig = base64.b64encode(
        hmac.new(SECRET_KEY.encode(), msg.encode(), hashlib.sha256).digest()
    ).decode()
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Timestamp": ts, "X-API-KEY": API_KEY,
        "X-Customer": CUSTOMER_ID, "X-Signature": sig,
    }
    resp = requests.post(
        f"https://api.searchad.naver.com{uri}",
        headers=headers, json=payload, timeout=60
    )
    print(f"HTTP {resp.status_code}")
    if not resp.ok:
        print(f"에러: {resp.text[:300]}")
        return None
    return resp.json()

TEST_KW = "강남임플란트"

# ── 1. average-position-bid/keyword ───────────────────────────
# items: [{key: keyword, position: 1~5}]
print("=== /estimate/average-position-bid/keyword ===")
for device in ["PC", "MOBILE"]:
    print(f"\n[{device}]")
    payload = {
        "device": device,
        "items": [
            {"key": TEST_KW, "position": 1},
            {"key": TEST_KW, "position": 2},
            {"key": TEST_KW, "position": 3},
            {"key": TEST_KW, "position": 4},
            {"key": TEST_KW, "position": 5},
        ]
    }
    result = call("/estimate/average-position-bid/keyword", payload)
    if result:
        print(json.dumps(result, ensure_ascii=False, indent=2))

# ── 2. median-bid/keyword ──────────────────────────────────────
# items: [keyword, ...] (단순 string 배열) + period: DAY or MONTH
print("\n=== /estimate/median-bid/keyword ===")
for device in ["PC", "MOBILE"]:
    for period in ["DAY", "MONTH"]:
        print(f"\n[{device} / {period}]")
        payload = {
            "device": device,
            "period": period,
            "items": [TEST_KW],
        }
        result = call("/estimate/median-bid/keyword", payload)
        if result:
            print(json.dumps(result, ensure_ascii=False, indent=2))