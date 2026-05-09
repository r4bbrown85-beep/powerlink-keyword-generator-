# -*- coding: utf-8 -*-
"""
test_two_api_combo.py

두 API 조합 검증:
1. average-position-bid/keyword → 순위별 입찰가 획득
2. performance/keyword → 그 bid로 노출/클릭/비용 획득

10개 키워드 전체 테스트 후 에이스퀘어 비교값 출력
"""
import base64, hashlib, hmac, os, time, json
import requests
from dotenv import load_dotenv
load_dotenv()

API_KEY     = os.getenv("NAVER_API_KEY", "").strip()
SECRET_KEY  = os.getenv("NAVER_SECRET_KEY", "").strip()
CUSTOMER_ID = os.getenv("NAVER_CUSTOMER_ID", "").strip()

TEST_KEYWORDS = [
    "강남임플란트", "실손보험비교", "헬로키티케이크", "인테리어견적",
    "강남피부과추천", "법인세신고대행", "남자헤어스타일",
    "제주도펜션추천", "파이썬학원", "드리미로봇청소기"
]
TARGET_RANKS = [1, 2, 3, 4, 5]

def sign(uri):
    ts  = str(int(time.time() * 1000))
    msg = f"{ts}.POST.{uri}"
    sig = base64.b64encode(
        hmac.new(SECRET_KEY.encode(), msg.encode(), hashlib.sha256).digest()
    ).decode()
    return ts, sig

def call(uri, payload):
    ts, sig = sign(uri)
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Timestamp": ts, "X-API-KEY": API_KEY,
        "X-Customer": CUSTOMER_ID, "X-Signature": sig,
    }
    resp = requests.post(
        f"https://api.searchad.naver.com{uri}",
        headers=headers, json=payload, timeout=60
    )
    if not resp.ok:
        return None
    return resp.json()

def get_rank_bids(keyword, device):
    """average-position-bid로 순위별 입찰가 획득"""
    payload = {
        "device": device,
        "items": [{"key": keyword, "position": r} for r in TARGET_RANKS]
    }
    result = call("/estimate/average-position-bid/keyword", payload)
    if not result:
        return {}
    return {e["position"]: e["bid"] for e in result.get("estimate", [])}

def get_performance(keyword, bids, device):
    """performance/keyword로 bid별 노출/클릭/비용 획득"""
    payload = {
        "device": device,
        "key": keyword,
        "bids": bids,
    }
    result = call("/estimate/performance/keyword", payload)
    if not result:
        return {}
    return {e["bid"]: e for e in result.get("estimate", [])}

# 에이스퀘어 정답 (1위만 있는 것 제외, 있는 것만)
ACE_DATA = {
    ("강남임플란트","PC",1): (514,16), ("강남임플란트","PC",2): (514,16),
    ("강남임플란트","PC",3): (514,16), ("강남임플란트","PC",4): (472,16),
    ("강남임플란트","PC",5): (372,10),
    ("강남임플란트","MO",1): (1430,32), ("강남임플란트","MO",2): (1015,18),
    ("강남임플란트","MO",3): (857,13), ("강남임플란트","MO",4): (684,7),
    ("강남임플란트","MO",5): (531,2),
    ("실손보험비교","PC",1): (1511,113), ("실손보험비교","MO",1): (3863,428),
    ("남자헤어스타일","PC",1): (2019,18), ("남자헤어스타일","MO",1): (10217,101),
    ("드리미로봇청소기","PC",1): (5435,164), ("드리미로봇청소기","MO",1): (26808,657),
    ("강남피부과추천","PC",1): (417,7), ("강남피부과추천","MO",1): (906,22),
    ("인테리어견적","PC",1): (873,89), ("인테리어견적","MO",1): (1711,213),
    ("제주도펜션추천","PC",1): (340,31), ("제주도펜션추천","MO",1): (1231,135),
    ("파이썬학원","PC",1): (141,5), ("파이썬학원","MO",1): (442,19),
    ("법인세신고대행","PC",1): (120,7), ("법인세신고대행","MO",1): (140,4),
    ("헬로키티케이크","PC",1): (99,0), ("헬로키티케이크","MO",1): (780,11),
}

results = []

for kw in TEST_KEYWORDS:
    print(f"\n▶ {kw}")
    for device, dev_label in [("PC","PC"), ("MOBILE","MO")]:

        # 1단계: 순위별 입찰가
        rank_bids = get_rank_bids(kw, device)
        time.sleep(0.2)

        if not rank_bids:
            print(f"  [{dev_label}] average-position-bid 데이터 없음 (Fallback)")
            for rank in TARGET_RANKS:
                results.append({
                    "kw": kw, "device": dev_label, "rank": rank,
                    "bid": 0, "impr": 0, "clicks": 0, "cost": 0,
                    "note": "Fallback"
                })
            continue

        # 2단계: bid로 성과 조회
        bids_to_query = list(set(rank_bids.values()))
        perf = get_performance(kw, bids_to_query, device)
        time.sleep(0.2)

        print(f"  [{dev_label}] 순위별 bid: {rank_bids}")
        for rank in TARGET_RANKS:
            bid = rank_bids.get(rank, 0)
            p   = perf.get(bid, {})
            impr   = p.get("impressions", 0)
            clicks = p.get("clicks", 0)
            cost   = p.get("cost", 0)

            # 에이스퀘어 비교
            ace = ACE_DATA.get((kw, dev_label, rank))
            if ace:
                ace_impr, ace_clicks = ace
                impr_diff  = f"{(impr-ace_impr)/ace_impr*100:+.1f}%" if ace_impr > 0 else "N/A"
                click_diff = f"{(clicks-ace_clicks)/ace_clicks*100:+.1f}%" if ace_clicks > 0 else "N/A"
                match = "✅" if abs(impr-(ace_impr or 0)) <= ace_impr*0.1 and clicks == ace_clicks else "❌"
                print(f"    {rank}위 | bid {bid:>7,} | 노출 {impr:>6,}(에:{ace_impr:>6,} {impr_diff}) | 클릭 {clicks:>4,}(에:{ace_clicks:>4,} {click_diff}) | {match}")
            else:
                print(f"    {rank}위 | bid {bid:>7,} | 노출 {impr:>6,} | 클릭 {clicks:>4,} | 비용 {cost:>10,}")

            results.append({
                "kw": kw, "device": dev_label, "rank": rank,
                "bid": bid, "impr": impr, "clicks": clicks, "cost": cost,
                "note": ""
            })

print("\n" + "="*70)
print("검증 완료")