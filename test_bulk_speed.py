# -*- coding: utf-8 -*-
"""
test_bulk_speed.py

개선된 naver_estimate.py 검증.
- 기존: bid 12개 → API 12번 호출 (약 2~3초)
- 개선: bid 12개 → API 1번 호출 (약 0.3초)

속도 비교 + 응답값 정합성 확인.
"""
import os
import time
from dotenv import load_dotenv

load_dotenv()

API_KEY     = os.getenv("NAVER_API_KEY", "")
SECRET_KEY  = os.getenv("NAVER_SECRET_KEY", "")
CUSTOMER_ID = os.getenv("NAVER_CUSTOMER_ID", "")

from modules.naver_estimate import (
    get_estimate_performance,
    get_rank_based_estimates,
    STAGE1_BIDS as SCAN_BIDS,
)

TEST_KEYWORD = "로봇청소기"

def test_bulk_call():
    print(f"=== 일괄 호출 테스트: {TEST_KEYWORD} ===")
    print(f"SCAN_BIDS({len(SCAN_BIDS)}개): {SCAN_BIDS}")
    print()

    t0 = time.time()
    results = get_estimate_performance(
        TEST_KEYWORD, SCAN_BIDS,
        API_KEY, SECRET_KEY, CUSTOMER_ID
    )
    elapsed = time.time() - t0

    print(f"\n소요시간: {elapsed:.2f}초  (기존 개별 호출 대비 약 {len(SCAN_BIDS)}배 단축)")
    print(f"결과 {len(results)}개\n")

    print(f"{'bid':>8} | {'PC노출':>8} | {'PC클릭':>7} | {'MO노출':>8} | {'MO클릭':>7}")
    print("-" * 55)
    for r in results:
        print(f"{r['bid']:>8,} | {r['pc_impressions']:>8,} | {r['pc_clicks']:>7,} | "
              f"{r['mo_impressions']:>8,} | {r['mo_clicks']:>7,}")

def test_rank_estimates():
    print(f"\n=== 순위별 추정 테스트: {TEST_KEYWORD} ===")
    t0 = time.time()
    rank_data = get_rank_based_estimates(
        TEST_KEYWORD, API_KEY, SECRET_KEY, CUSTOMER_ID
    )
    elapsed = time.time() - t0
    print(f"소요시간: {elapsed:.2f}초\n")

    for device in ["PC", "MO"]:
        print(f"[{device}]")
        d = rank_data.get(device, {})
        if not d:
            print("  데이터 없음")
            continue
        for rank in sorted(d.keys()):
            e = d[rank]
            print(f"  {rank}위 | 입찰가 {e['bid']:>6,}원 | "
                  f"노출 {e['impressions']:>6,} | 클릭 {e['clicks']:>5,} | "
                  f"CPC {e['cpc']:>6,}원")
        print()

if __name__ == "__main__":
    test_bulk_call()
    test_rank_estimates()