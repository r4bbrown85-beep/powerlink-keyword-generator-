# -*- coding: utf-8 -*-
import base64, hashlib, hmac, os, time
import requests
from dotenv import load_dotenv
load_dotenv()

API_KEY     = os.getenv("NAVER_API_KEY", "").strip()
SECRET_KEY  = os.getenv("NAVER_SECRET_KEY", "").strip()
CUSTOMER_ID = os.getenv("NAVER_CUSTOMER_ID", "").strip()

def call(keyword, bids, device):
    uri = "/estimate/performance/keyword"
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
        headers=headers,
        json={"device": device, "key": keyword, "bids": bids},
        timeout=60
    )
    if not resp.ok:
        print(f"에러: {resp.text[:200]}")
        return []
    return resp.json().get("estimate", [])

# 로그스케일 98개 bid
lo, hi, n = 70, 100000, 100
bids = sorted(set(
    int(round(lo * (hi/lo) ** (i/(n-1)) / 10) * 10)
    for i in range(n)
))
bids[0] = 70

TEST_KW = "드리미로봇청소기"

for device in ["PC", "MOBILE"]:
    print(f"\n=== {TEST_KW} / {device} ===")
    estimates = call(TEST_KW, bids, device)

    print(f"{'입찰가':>8} | {'노출':>8} | {'클릭':>6} | 변화")
    print("-" * 50)
    prev_clicks, prev_impr = -1, 0
    max_clicks = max((e["clicks"] for e in estimates), default=0)

    for e in estimates:
        bid    = e["bid"]
        impr   = e["impressions"]
        clicks = e["clicks"]
        if impr > 0 or (impr == 0 and prev_impr > 0):
            marker = ""
            if clicks != prev_clicks and clicks > 0:
                marker = " ◀ 클릭변화"
            if clicks == max_clicks and prev_clicks != max_clicks:
                marker = " ◀◀ 포화(1위)"
            print(f"{bid:>8,} | {impr:>8,} | {clicks:>6,} |{marker}")
        prev_clicks = clicks
        prev_impr   = impr

    # 포화점 찾기
    sat = next((e for e in estimates if e["clicks"] == max_clicks), None)
    if sat:
        print(f"\n포화점: bid={sat['bid']:,}원 / 노출={sat['impressions']:,} / 클릭={max_clicks}")

print("\n에이스퀘어 1위:")
print("  PC: 노출 5,435 / 클릭 164")
print("  MO: 노출 26,808 / 클릭 657")