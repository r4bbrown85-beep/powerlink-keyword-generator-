# -*- coding: utf-8 -*-
"""
test_single_bid.py
강남임플란트 MO 47,000원 직접 호출 → 에이스퀘어 값과 비교
"""
import base64, hashlib, hmac, json, os, time
import requests
from dotenv import load_dotenv
load_dotenv()

API_KEY     = os.getenv("NAVER_API_KEY", "").strip()
SECRET_KEY  = os.getenv("NAVER_SECRET_KEY", "").strip()
CUSTOMER_ID = os.getenv("NAVER_CUSTOMER_ID", "").strip()

def call(keyword, bids):
    uri = "/estimate/performance-bulk"
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
    items = []
    for b in bids:
        items.append({"keyword": keyword, "bid": b, "device": "PC"})
        items.append({"keyword": keyword, "bid": b, "device": "MOBILE"})

    resp = requests.post(f"https://api.searchad.naver.com{uri}",
                         headers=headers, json={"items": items}, timeout=60)
    return resp.json().get("items", [])

# 테스트: 강남임플란트, 에이스퀘어 1위 입찰가 근처 집중 스캔
TEST_KW  = "강남임플란트"
TEST_BIDS = [33000, 38000, 40000, 43000, 45000, 47000, 50000, 55000, 60000, 70000, 100000]

print(f"키워드: {TEST_KW}")
print(f"{'입찰가':>8} | {'PC노출':>8} | {'PC클릭':>7} | {'MO노출':>8} | {'MO클릭':>7}")
print("-" * 55)

items = call(TEST_KW, TEST_BIDS)
for bid in TEST_BIDS:
    pc = next((x for x in items if x.get("device")=="PC"     and int(x.get("bid",0))==bid), {})
    mo = next((x for x in items if x.get("device")=="MOBILE" and int(x.get("bid",0))==bid), {})
    print(f"{bid:>8,} | {int(pc.get('impressions',0)):>8,} | {int(pc.get('clicks',0)):>7,} | "
          f"{int(mo.get('impressions',0)):>8,} | {int(mo.get('clicks',0)):>7,}")

print()
print("에이스퀘어 정답값:")
print("  PC 1위: 노출 514  / 클릭 16 / CPC 39,773")
print("  MO 1위: 노출 1,430 / 클릭 32 / CPC 47,077")