"""
keyword_api_probe.py

keywordstool API 응답에 어떤 필드가 있는지 확인하는 테스트 코드.
실행: python keyword_api_probe.py
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
API_KEY     = os.getenv("NAVER_API_KEY")
SECRET_KEY  = os.getenv("NAVER_SECRET_KEY")
CUSTOMER_ID = os.getenv("NAVER_CUSTOMER_ID")

# ── 테스트할 키워드 (다양한 경쟁도로 확인) ──────────────────
TEST_KEYWORDS = [
    "프레데릭말",          # 브랜드 (경쟁도 낮음)
    "향수",               # 일반 (경쟁도 높음)
    "차량용방향제",        # 일반 (중간)
    "프레데릭말 포트레이트 오브 어 레이디",  # 긴 키워드
]


def _sign(timestamp, method, uri):
    msg = f"{timestamp}.{method}.{uri}"
    sig = base64.b64encode(
        hmac.new(SECRET_KEY.encode(), msg.encode(), hashlib.sha256).digest()
    )
    return sig.decode()


def call_keywordstool(keyword: str) -> dict:
    uri       = "/keywordstool"
    timestamp = str(int(time.time() * 1000))
    headers   = {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Timestamp":  timestamp,
        "X-API-KEY":    API_KEY,
        "X-Customer":   str(CUSTOMER_ID),
        "X-Signature":  _sign(timestamp, "GET", uri),
    }
    params = {"hintKeywords": keyword.replace(" ", ""), "showDetail": 1}
    r = requests.get(BASE_URL + uri, headers=headers, params=params, timeout=10)
    return {"status": r.status_code, "body": r.json() if r.ok else r.text}


def main():
    print("=" * 60)
    print("keywordstool API 응답 필드 확인")
    print("=" * 60)

    for kw in TEST_KEYWORDS:
        print(f"\n▶ 키워드: [{kw}]")
        print("-" * 60)

        resp = call_keywordstool(kw)
        print(f"  HTTP status: {resp['status']}")

        if resp["status"] != 200:
            print(f"  ERROR: {resp['body']}")
            continue

        kw_list = resp["body"].get("keywordList", [])
        if not kw_list:
            print("  ⚠ keywordList 비어있음 (검색량 없음)")
            continue

        item = kw_list[0]

        print(f"\n  ── 전체 필드 목록 ({len(item)}개) ──")
        for key, val in item.items():
            print(f"    {key:45s} = {val}")

        # 우리가 관심 있는 핵심 필드만 따로 출력
        print(f"\n  ── 핵심 필드 ──")
        targets = [
            "relKeyword",
            "monthlyPcQcCnt",
            "monthlyMobileQcCnt",
            "monthlyAvePcClkCnt",
            "monthlyAveMobileClkCnt",
            "monthlyAvePcCtr",
            "monthlyAveMobileCtr",
            "compIdx",
            "plAvgDepth",           # 있으면 평균 게재 순위
            "rkwKwdId",             # 키워드 ID
        ]
        for t in targets:
            val = item.get(t, "❌ 없음")
            print(f"    {t:45s} = {val}")

        # topOfPageBid 계열 필드 별도 확인
        print(f"\n  ── topOfPageBid / bid 관련 필드 ──")
        bid_fields = [k for k in item.keys() if "bid" in k.lower() or "Bid" in k]
        if bid_fields:
            for k in bid_fields:
                print(f"    {k:45s} = {item[k]}")
        else:
            print("    ❌ bid 관련 필드 없음")

        time.sleep(0.3)

    print("\n" + "=" * 60)
    print("완료")
    print("=" * 60)


if __name__ == "__main__":
    main()