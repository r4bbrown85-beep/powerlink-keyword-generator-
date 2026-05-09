"""
네이버스 클릭수 vs keywordstool monthlyAvePcClkCnt 비교 검증
실행: python verify_click_source.py
"""
import os, sys, json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))

from modules.naver_keyword_api import get_keyword_stats

# 네이버스 데이터 (직접 입력 - 아까 분석한 값)
NAVERS_DATA = {
    # 키워드: (NS_1위_PC노출, NS_1위_PC클릭, NS_1위_MO노출, NS_1위_MO클릭)
    '로봇청소기':       (25719,  626,  103450, 3380),
    '무선청소기':       (30265,  494,   82373, 1408),
    '물걸레청소기':     ( 6509,   87,   23723,  478),
    '헤어드라이기':     ( 4189,  110,   17700,  402),
    '스틱청소기':       (   74,    1,    1095,   22),
    '핸디청소기':       ( 1899,   14,    6640,   85),
    '로봇청소기 추천':  ( 2794,   40,   11000,  350),
    '무선청소기 추천':  ( 2995,   48,    8200,  376),
    '스팀청소기':       ( 9718,  339,   23000,  460),
    '무선청소기 가격':  (   11,    1,     400,   16),
    '로봇청소기 가격':  (  149,    3,    1800,   80),
}

API_KEY     = os.getenv("NAVER_API_KEY", "")
SECRET_KEY  = os.getenv("NAVER_SECRET_KEY", "")
CUSTOMER_ID = os.getenv("NAVER_CUSTOMER_ID", "")

if not all([API_KEY, SECRET_KEY, CUSTOMER_ID]):
    print("❌ .env 파일에 NAVER_API_KEY, NAVER_SECRET_KEY, NAVER_CUSTOMER_ID 필요")
    sys.exit(1)

print("keywordstool API 호출 중...")
keywords = list(NAVERS_DATA.keys())
kt_data = get_keyword_stats(keywords, API_KEY, SECRET_KEY, CUSTOMER_ID)

print()
print("=" * 90)
print(f"{'키워드':15s} | {'[KT]노출':>10s} | {'[NS]노출':>10s} | {'일치':4s} || {'[KT]클릭':>8s} | {'[NS]1위클릭':>10s} | {'일치':4s}")
print("-" * 90)

pc_impr_match = 0
pc_click_match = 0
total = 0

for kw, (ns_pc_impr, ns_pc_clk, ns_mo_impr, ns_mo_clk) in NAVERS_DATA.items():
    kt = kt_data.get(kw, {})
    kt_pc_impr = kt.get('pc_impr', 0)
    kt_pc_clk  = kt.get('pc_click', 0)

    impr_ok  = "✅" if kt_pc_impr == ns_pc_impr else "❌"
    click_ok = "✅" if abs(kt_pc_clk - ns_pc_clk) <= 2 else "❌"  # ±2 허용

    if kt_pc_impr == ns_pc_impr: pc_impr_match += 1
    if abs(kt_pc_clk - ns_pc_clk) <= 2: pc_click_match += 1
    total += 1

    print(f"{kw:15s} | {kt_pc_impr:>10,} | {ns_pc_impr:>10,} | {impr_ok:4s} || {kt_pc_clk:>8.1f} | {ns_pc_clk:>10,} | {click_ok:4s}")

print("=" * 90)
print(f"\n결과: 노출수 일치 {pc_impr_match}/{total} | 클릭수 일치 {pc_click_match}/{total}")
print()

if pc_impr_match == total:
    print("✅ 노출수 = keywordstool monthlyPcQcCnt 로 확정!")
else:
    print("⚠️  노출수 일부 불일치 → 네이버S가 다른 데이터소스 사용 가능성")

if pc_click_match == total:
    print("✅ 클릭수 = keywordstool monthlyAvePcClkCnt 로 확정!")
    print("   → CTR 테이블 불필요, keywordstool 값 직접 사용하면 됨")
elif pc_click_match > total // 2:
    print("⚠️  클릭수 부분 일치 → 추가 분석 필요")
else:
    print("❌ 클릭수 불일치 → Estimate API 직접 사용 가능성 높음")

print()
print("=== 추가 정보: keywordstool CTR vs 역산 CTR ===")
for kw, (ns_pc_impr, ns_pc_clk, _, _) in NAVERS_DATA.items():
    kt = kt_data.get(kw, {})
    kt_ctr = kt.get('pc_ctr', 0) * 100
    ns_ctr = ns_pc_clk / ns_pc_impr * 100 if ns_pc_impr > 0 else 0
    print(f"  {kw:15s}: KT_CTR={kt_ctr:.2f}%  NS역산CTR={ns_ctr:.2f}%  {'✅' if abs(kt_ctr-ns_ctr)<0.5 else '❌'}")