import os, json
from dotenv import load_dotenv
load_dotenv()
import sys; sys.path.insert(0, ".")
from modules.naver_estimate_api import _request

# 1단계: 순위별 입찰가 조회
kw_id = "nkw-a001-01-000007663031270"
kw_text = "마케팅회사"

res_bid = _request("POST", "/npc-estimate/average-position-bid/id", payload={
    "device": "PC",
    "items": [{"key": kw_id, "position": p} for p in [1,2,3,4,5]]
})
rank_bids = {item["position"]: item["bid"] for item in res_bid["data"]["estimate"]}
print(f"[{kw_text}] 순위별 입찰가: {rank_bids}")

# 2단계: 각 순위 입찰가로 performance-bulk 호출
print(f"\n순위별 예상 성과:")
print(f"{'순위':4s} | {'입찰가':8s} | {'PC노출':8s} | {'PC클릭':8s} | {'PC비용':10s}")
print("-" * 50)
for position, bid in rank_bids.items():
    if bid == 70:
        print(f"{position}위   | {bid:8,} | 경쟁없음")
        continue
    res = _request("POST", "/estimate/performance-bulk", payload={
        "items": [
            {"keyword": kw_text, "bid": bid, "device": "PC"},
            {"keyword": kw_text, "bid": bid, "device": "MOBILE"},
        ]
    })
    items = res["data"].get("items", [])
    pc = next((x for x in items if x.get("device") == "PC"), {})
    print(f"{position}위   | {bid:8,} | {pc.get('impressions',0):8,} | {pc.get('clicks',0):8,} | {pc.get('cost',0):10,}")
