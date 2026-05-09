# -*- coding: utf-8 -*-
"""
test_performance_keyword.py

POST /estimate/performance/keyword 테스트
- key: 키워드
- bids[]: 최대 100개
- device: PC / MOBILE / BOTH
"""
import base64, hashlib, hmac, os, time, json
import requests
from dotenv import load_dotenv
load_dotenv()

API_KEY     = os.getenv("NAVER_API_KEY", "").strip()
SECRET_KEY  = os.getenv("NAVER_SECRET_KEY", "").strip()
CUSTOMER_ID = os.getenv("NAVER_CUSTOMER_ID", "").strip()

def call(keyword, bids, device="BOTH"):
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
    payload = {
        "device": device,
        "key": keyword,
        "bids": bids,
    }
    resp = requests.post(
        f"https://api.searchad.naver.com{uri}",
        headers=headers, json=payload, timeout=60
    )
    print(f"HTTP {resp.status_code}")
    if not resp.ok:
        print(f"에러: {resp.text}")
        return None
    return resp.json()

lo, hi, n = 70, 100000, 100
bids = sorted(set(
    int(round(lo * (hi/lo) ** (i/(n-1)) / 10) * 10)
    for i in range(n)
))
bids[0] = 70

for device in ["PC", "MOBILE"]:
    print(f"\n=== 강남임플란트 / {device} / {len(bids)}개 bid ===")
    t0 = time.time()
    result = call("강남임플란트", bids, device=device)
    elapsed = time.time() - t0
    print(f"소요시간: {elapsed:.2f}초")
    if not result:
        continue
    estimates = result.get("estimate", [])
    print(f"estimate 항목 수: {len(estimates)}개")
    print(f"{'입찰가':>8} | {'노출':>8} | {'클릭':>6} | 변화")
    print("-" * 45)
    prev_clicks, prev_impr = -1, -1
    for e in estimates:
        bid, impr, clicks = e["bid"], e["impressions"], e["clicks"]
        if impr > 0 or (impr == 0 and prev_impr > 0):
            marker = " ◀ 클릭변화" if prev_clicks >= 0 and clicks != prev_clicks and clicks > 0 else ""
            print(f"{bid:>8,} | {impr:>8,} | {clicks:>6,} |{marker}")
        prev_clicks, prev_impr = clicks, impr
    max_e = max(estimates, key=lambda x: x["clicks"]) if estimates else {}
    print(f"최대클릭: bid={max_e.get('bid',0):,}원 / 노출={max_e.get('impressions',0):,} / 클릭={max_e.get('clicks',0):,}")

print("\n에이스퀘어 정답:")
print("  PC 1위: 노출 514 / 클릭 16")
print("  MO 1위: 노출 1,430 / 클릭 32")