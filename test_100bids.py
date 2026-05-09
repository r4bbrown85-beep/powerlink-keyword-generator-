# -*- coding: utf-8 -*-
"""
test_100bids.py

로그스케일 100개 bid를 한 번에 호출할 때:
1. API가 정상 응답하는지 (items 200개 = PC+MO 쌍)
2. 응답값이 완전한지 (누락 없는지)
3. 노출 커브가 얼마나 정교해지는지
"""
import base64
import hashlib
import hmac
import json
import math
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY     = os.getenv("NAVER_API_KEY", "").strip()
SECRET_KEY  = os.getenv("NAVER_SECRET_KEY", "").strip()
CUSTOMER_ID = os.getenv("NAVER_CUSTOMER_ID", "").strip()

TEST_KEYWORD = "로봇청소기"


def make_log_bids(lo=70, hi=100000, n=100):
    """로그스케일 n개 bid, 10원 단위"""
    bids = sorted(set(
        int(round(lo * (hi / lo) ** (i / (n - 1)) / 10) * 10)
        for i in range(n)
    ))
    bids[0] = lo
    return bids


def sign(method, uri):
    ts  = str(int(time.time() * 1000))
    msg = f"{ts}.{method}.{uri}"
    sig = base64.b64encode(
        hmac.new(SECRET_KEY.encode(), msg.encode(), hashlib.sha256).digest()
    ).decode()
    return ts, sig


def call_bulk(keyword, bids):
    uri  = "/estimate/performance-bulk"
    ts, sig = sign("POST", uri)
    hdrs = {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Timestamp":  ts,
        "X-API-KEY":    API_KEY,
        "X-Customer":   CUSTOMER_ID,
        "X-Signature":  sig,
    }
    items = []
    for b in bids:
        items.append({"keyword": keyword, "bid": int(b), "device": "PC"})
        items.append({"keyword": keyword, "bid": int(b), "device": "MOBILE"})

    resp = requests.post(
        f"https://api.searchad.naver.com{uri}",
        headers=hdrs,
        json={"items": items},
        timeout=60,
    )
    return resp.status_code, resp.ok, resp.json() if resp.ok else {"error": resp.text}


def run():
    bids = make_log_bids()
    print(f"bid {len(bids)}개, items {len(bids)*2}개 (PC+MO)")
    print(f"범위: {bids[0]}원 ~ {bids[-1]:,}원")
    print()

    t0 = time.time()
    status, ok, data = call_bulk(TEST_KEYWORD, bids)
    elapsed = time.time() - t0

    print(f"HTTP {status} / {'OK' if ok else 'FAIL'} / {elapsed:.2f}초")

    if not ok:
        print(f"에러: {data}")
        return

    resp_items = data.get("items", [])
    print(f"응답 items: {len(resp_items)}개 (기대: {len(bids)*2}개)")
    print()

    # PC 기준으로 커브 출력
    pc_results = {
        int(x["bid"]): int(x.get("impressions", 0))
        for x in resp_items if x.get("device") == "PC"
    }

    print(f"{'bid':>8} | {'PC노출':>10} | 변화율")
    print("-" * 40)
    prev_impr = 0
    for b in bids:
        impr = pc_results.get(b, 0)
        ratio = f"+{((impr/prev_impr)-1)*100:.0f}%" if prev_impr > 0 and impr > prev_impr else "-"
        marker = " ◀ 순위경계 추정" if prev_impr > 0 and impr > prev_impr * 1.5 else ""
        print(f"{b:>8,} | {impr:>10,} | {ratio}{marker}")
        prev_impr = impr if impr > 0 else prev_impr

    # 노출 있는 구간 요약
    active = [(b, pc_results.get(b,0)) for b in bids if pc_results.get(b,0) > 0]
    print(f"\n노출 발생 구간: {active[0][0]:,}원 ~ {active[-1][0]:,}원 ({len(active)}개 포인트)")


if __name__ == "__main__":
    run()