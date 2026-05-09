# -*- coding: utf-8 -*-
"""
test_performance_single.py

/estimate/performance 엔드포인트 탐색 테스트.
키워드 1개 + 입찰가 N개를 한 번에 조회하는 API.

네이버 답변: "API 공개되어 있음, 호출 주소 확인 필요"
현재 상태: /estimate/performance-bulk 는 동작 확인됨
           /estimate/performance 는 404

가능한 패턴을 모두 시도해서 어떤 구조가 동작하는지 확인.
"""

import base64
import hashlib
import hmac
import json
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL    = "https://api.searchad.naver.com"
API_KEY     = os.getenv("NAVER_API_KEY", "").strip()
SECRET_KEY  = os.getenv("NAVER_SECRET_KEY", "").strip()
CUSTOMER_ID = os.getenv("NAVER_CUSTOMER_ID", "").strip()

TEST_KEYWORD = "로봇청소기"
TEST_BIDS    = [200, 500, 1000, 2000, 5000, 10000]


def _sign(method, uri):
    ts  = str(int(time.time() * 1000))
    msg = f"{ts}.{method}.{uri}"
    sig = base64.b64encode(
        hmac.new(SECRET_KEY.encode(), msg.encode(), hashlib.sha256).digest()
    ).decode()
    return ts, sig


def _headers(method, uri):
    ts, sig = _sign(method, uri)
    return {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Timestamp":  ts,
        "X-API-KEY":    API_KEY,
        "X-Customer":   CUSTOMER_ID,
        "X-Signature":  sig,
    }


def call(method, uri, payload=None, params=None):
    url  = f"{BASE_URL}{uri}"
    hdrs = _headers(method, uri)
    resp = requests.request(method, url, headers=hdrs, json=payload,
                            params=params, timeout=30)
    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text}
    return resp.status_code, resp.ok, data


def run():
    print(f"키워드: {TEST_KEYWORD}")
    print(f"입찰가: {TEST_BIDS}")
    print("=" * 60)

    patterns = [
        # ── 패턴 1: bids 배열로 한 번에 ──────────────────────────────
        {
            "name": "P1_performance_bids_array_pc",
            "method": "POST",
            "uri": "/estimate/performance",
            "payload": {
                "keyword": TEST_KEYWORD,
                "device":  "PC",
                "bids":    TEST_BIDS,
            },
        },
        {
            "name": "P2_performance_bids_array_mobile",
            "method": "POST",
            "uri": "/estimate/performance",
            "payload": {
                "keyword": TEST_KEYWORD,
                "device":  "MOBILE",
                "bids":    TEST_BIDS,
            },
        },
        # ── 패턴 3: items 배열 구조 (bulk 스타일) ────────────────────
        {
            "name": "P3_performance_items_bids",
            "method": "POST",
            "uri": "/estimate/performance",
            "payload": {
                "items": [
                    {"keyword": TEST_KEYWORD, "device": "PC",     "bid": b}
                    for b in TEST_BIDS
                ]
            },
        },
        # ── 패턴 4: keyword + bids (device 없음) ─────────────────────
        {
            "name": "P4_performance_no_device",
            "method": "POST",
            "uri": "/estimate/performance",
            "payload": {
                "keyword": TEST_KEYWORD,
                "bids":    TEST_BIDS,
            },
        },
        # ── 패턴 5: GET + query params ───────────────────────────────
        {
            "name": "P5_performance_GET_params",
            "method": "GET",
            "uri": "/estimate/performance",
            "payload": None,
            "params": {
                "keyword": TEST_KEYWORD,
                "device":  "PC",
                "bids":    ",".join(str(b) for b in TEST_BIDS),
            },
        },
        # ── 패턴 6: npc-estimate 경로 ────────────────────────────────
        {
            "name": "P6_npc_performance_bids",
            "method": "POST",
            "uri": "/npc-estimate/performance",
            "payload": {
                "keyword": TEST_KEYWORD,
                "device":  "PC",
                "bids":    TEST_BIDS,
            },
        },
        # ── 패턴 7: 복수 keyword 구조 확인용 (bulk 비교) ─────────────
        {
            "name": "P7_performance_bulk_multi_bids_same_kw",
            "method": "POST",
            "uri": "/estimate/performance-bulk",
            "payload": {
                "items": [
                    {"keyword": TEST_KEYWORD, "device": "PC", "bid": b}
                    for b in TEST_BIDS
                ]
            },
        },
    ]

    success = []
    for p in patterns:
        params  = p.get("params")
        payload = p.get("payload")
        status, ok, data = call(p["method"], p["uri"], payload=payload, params=params)

        mark = "✅" if ok else "❌"
        print(f"\n{mark} [{p['name']}]  HTTP {status}")

        if ok:
            print(f"   응답: {json.dumps(data, ensure_ascii=False)[:300]}")
            success.append(p["name"])
        else:
            err = data.get("title") or data.get("message") or data.get("raw") or ""
            print(f"   에러: {str(err)[:120]}")

        time.sleep(0.3)

    print("\n" + "=" * 60)
    if success:
        print(f"성공 패턴: {success}")
    else:
        print("성공 패턴 없음 → /estimate/performance-bulk 다중 bid 조합이 현재 최선")


if __name__ == "__main__":
    run()