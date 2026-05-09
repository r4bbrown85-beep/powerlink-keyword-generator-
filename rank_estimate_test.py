# -*- coding: utf-8 -*-
"""
rank_estimate_test.py
keywordstool 기반 순위별 추정 결과를 에이스퀘어와 비교 검증.
실행: python rank_estimate_test.py
"""
import os
from dotenv import load_dotenv
from modules.naver_estimate import get_rank_based_estimates
from modules.naver_keyword_api import get_keyword_stats

load_dotenv()
api_key     = os.getenv("NAVER_API_KEY")
secret      = os.getenv("NAVER_SECRET_KEY")
customer_id = os.getenv("NAVER_CUSTOMER_ID")

# 에이스퀘어 기준값 (노출, 클릭, CPC)
ACE_DATA = {
    "프레데릭말": {
        "PC": {1:(3385,100,402), 2:(3385,92,344), 3:(3385,53,269), 4:(3385,13,194)},
        "MO": {1:(19599,332,424), 2:(19599,173,374), 3:(19599,42,244)},
    },
    "딥디크": {
        "PC": {1:(9733,1209,652), 2:(9733,422,591), 3:(9733,370,516), 4:(9733,333,462), 5:(9733,178,237)},
        "MO": {1:(55541,446,508), 3:(54820,237,341)},
    },
    "니치향수": {
        "PC": {1:(2299,118,3962), 2:(2299,118,2729), 3:(2299,118,2143), 4:(2299,101,2016)},
        "MO": {1:(9964,693,3735), 3:(8653,578,2337)},
    },
    "르라보": {
        "PC": {1:(8472,61,660), 2:(8472,61,455), 3:(8472,61,366), 4:(8472,61,261)},
        "MO": {1:(42135,650,605), 3:(41697,252,363), 4:(32463,204,277)},
    },
}

TEST_KEYWORDS = ["프레데릭말", "딥디크", "니치향수", "르라보"]

print("=" * 100)
print("순위별 추정 결과 vs 에이스퀘어 비교 (keywordstool 기반)")
print("=" * 100)

# keywordstool에서 검색량 가져오기
print("\n[keywordstool 검색량 조회 중...]")
kt_stats = get_keyword_stats(TEST_KEYWORDS, api_key, secret, customer_id)
for kw, stat in kt_stats.items():
    print(f"  {kw}: PC={stat['pc_impr']:,} / MO={stat['mo_impr']:,}")

total_match = 0
total_compare = 0
impr_diffs = []
clk_diffs  = []

for kw in TEST_KEYWORDS:
    print(f"\n【 {kw} 】")
    kt = kt_stats.get(kw, {})
    kt_pc = kt.get("pc_impr", 0)
    kt_mo = kt.get("mo_impr", 0)

    result = get_rank_based_estimates(
        kw, api_key, secret, customer_id,
        target_ranks=[1,2,3,4,5],
        kt_pc_impr=kt_pc,
        kt_mo_impr=kt_mo
    )

    for dev in ["PC", "MO"]:
        dev_data = result.get(dev, {})
        ace_dev  = ACE_DATA.get(kw, {}).get(dev, {})
        if not dev_data and not ace_dev:
            continue

        kt_impr = kt_pc if dev == "PC" else kt_mo
        print(f"\n  [{dev}] keywordstool 검색량={kt_impr:,}")
        print(f"  {'순위':3s} | {'우리입찰가':7s} | {'우리노출':7s} | {'우리클릭':6s} | {'클릭비율':7s} || {'A/S CPC':7s} | {'A/S노출':7s} | {'A/S클릭':6s} | 노출차이   클릭차이")
        print(f"  {'-'*100}")

        for rank in [1,2,3,4,5]:
            our = dev_data.get(rank)
            ace = ace_dev.get(rank)

            if our:
                our_str = f"{our['bid']:6,}원 | {our['impressions']:7,} | {our['clicks']:6,} | {our['click_ratio']*100:6.3f}%"
            else:
                our_str = f"{'데이터없음':^42s}"

            if ace:
                a_impr, a_clk, a_cpc = ace
                ace_str = f"{a_cpc:6,}원 | {a_impr:7,} | {a_clk:6,}"
                if our and a_impr > 0:
                    total_compare += 1
                    impr_diff = (our['impressions'] - a_impr) / a_impr * 100
                    clk_diff  = (our['clicks'] - a_clk) / a_clk * 100 if a_clk > 0 else 0
                    impr_diffs.append(abs(impr_diff))
                    clk_diffs.append(abs(clk_diff))
                    if abs(impr_diff) <= 5 and abs(clk_diff) <= 15:
                        flag = "✅"
                        total_match += 1
                    elif abs(impr_diff) <= 10 and abs(clk_diff) <= 25:
                        flag = "🔶"
                    else:
                        flag = "⚠"
                    diff_str = f"{impr_diff:+6.1f}%  {clk_diff:+7.1f}% {flag}"
                else:
                    diff_str = ""
            else:
                ace_str  = f"{'에이스퀘어없음':^28s}"
                diff_str = ""

            print(f"  {rank}위  | {our_str} || {ace_str} | {diff_str}")

print("\n" + "=" * 100)
print(f"✅ 일치(±5%/±15%): {total_match}/{total_compare}건")
if impr_diffs:
    print(f"노출수 평균오차: {sum(impr_diffs)/len(impr_diffs):.1f}%  |  클릭수 평균오차: {sum(clk_diffs)/len(clk_diffs):.1f}%")
print("=" * 100)