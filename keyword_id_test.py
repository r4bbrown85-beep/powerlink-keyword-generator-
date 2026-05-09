import os
import time
import hmac
import hashlib
import base64
import re
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL    = "https://api.searchad.naver.com"
api_key     = os.getenv("NAVER_API_KEY")
secret      = os.getenv("NAVER_SECRET_KEY")
customer_id = os.getenv("NAVER_CUSTOMER_ID")


def make_headers(method, uri):
    timestamp = str(int(time.time() * 1000))
    message   = f"{timestamp}.{method}.{uri}"
    signature = base64.b64encode(
        hmac.new(secret.encode(), message.encode(), hashlib.sha256).digest()
    ).decode()
    return {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Timestamp":  timestamp,
        "X-API-KEY":    api_key,
        "X-Customer":   str(customer_id),
        "X-Signature":  signature,
    }


def estimate_both(keyword, bid):
    kw  = re.sub(r"\s+", "", keyword)
    uri = "/estimate/performance-bulk"
    headers = make_headers("POST", uri)
    payload = {
        "items": [
            {"keyword": kw, "bid": bid, "device": "PC"},
            {"keyword": kw, "bid": bid, "device": "MOBILE"},
        ]
    }
    resp  = requests.post(BASE_URL + uri, json=payload, headers=headers, timeout=30)
    if not resp.ok:
        return None
    items = resp.json().get("items", [])
    pc = next((x for x in items if x.get("device") == "PC"),     {})
    mo = next((x for x in items if x.get("device") == "MOBILE"), {})
    return {
        "bid":        bid,
        "pc_clicks":  pc.get("clicks", 0),
        "pc_cost":    pc.get("cost", 0),
        "mo_clicks":  mo.get("clicks", 0),
        "mo_cost":    mo.get("cost", 0),
    }


def find_rank_boundaries(keyword):
    """
    입찰가별 클릭 변화로 PC/MO 각각 순위 경계 입찰가 목록 생성.
    클릭이 증가하는 구간의 '상단 입찰가' = 해당 순위 진입 입찰가.
    """
    coarse_bids = [70, 100, 200, 300, 500, 700, 1000, 1200,
                   1500, 2000, 2500, 3000, 4000, 5000, 7000, 10000]

    results = []
    for bid in coarse_bids:
        r = estimate_both(keyword, bid)
        if r:
            results.append(r)

    if not results:
        return [], []

    # PC 순위 경계 입찰가 찾기
    pc_rank_bids = []
    for i in range(1, len(results)):
        if results[i]["pc_clicks"] > results[i-1]["pc_clicks"]:
            pc_rank_bids.append(results[i]["bid"])  # 상단 입찰가

    # MO 순위 경계 입찰가 찾기
    mo_rank_bids = []
    for i in range(1, len(results)):
        if results[i]["mo_clicks"] > results[i-1]["mo_clicks"]:
            mo_rank_bids.append(results[i]["bid"])

    return pc_rank_bids, mo_rank_bids, results


print("=" * 60)
print("순위 경계 입찰가 검증")
print("=" * 60)

# 에이스퀘어 기준값
# 니치향수: PC 2위 → 클릭 118, CPC 2750
# 남자향수: PC 3위 → 클릭 44, CPC 1990
# 바이레도향수: PC 5위 → 클릭 2, CPC 677

test_cases = [
    ("니치향수",    2, 7, 118, 693),   # 목표PC순위, 목표MO순위, 에이스퀘어PC클릭, 에이스퀘어MO클릭
    ("남자향수",    3, 4,  44,  81),
    ("바이레도향수", 5, 5,   2,   0),
]

for kw, pc_rank, mo_rank, ace_pc_clk, ace_mo_clk in test_cases:
    print(f"\n{'='*50}")
    print(f"키워드: {kw}")
    print(f"에이스퀘어 기준: PC {pc_rank}위 → 클릭 {ace_pc_clk} / MO {mo_rank}위 → 클릭 {ace_mo_clk}")

    pc_bids, mo_bids, results = find_rank_boundaries(kw)

    print(f"PC 순위별 입찰가: {pc_bids}")
    print(f"MO 순위별 입찰가: {mo_bids}")

    # 목표 순위의 입찰가 선택
    target_pc_bid = pc_bids[pc_rank-1] if len(pc_bids) >= pc_rank else (pc_bids[-1] if pc_bids else 1000)
    target_mo_bid = mo_bids[mo_rank-1] if len(mo_bids) >= mo_rank else (mo_bids[-1] if mo_bids else 1000)

    print(f"목표 PC {pc_rank}위 입찰가: {target_pc_bid}원")
    print(f"목표 MO {mo_rank}위 입찰가: {target_mo_bid}원")

    # 해당 입찰가로 최종 조회
    pc_result = estimate_both(kw, target_pc_bid)
    mo_result = estimate_both(kw, target_mo_bid)

    if pc_result:
        print(f"\nPC {pc_rank}위 결과: 입찰가={target_pc_bid} | 클릭={pc_result['pc_clicks']} (에이스퀘어: {ace_pc_clk})")
    if mo_result:
        print(f"MO {mo_rank}위 결과: 입찰가={target_mo_bid} | 클릭={mo_result['mo_clicks']} (에이스퀘어: {ace_mo_clk})")

print("\n완료")