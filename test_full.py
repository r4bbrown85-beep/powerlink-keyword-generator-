import os, json, time
from dotenv import load_dotenv
load_dotenv()
import sys; sys.path.insert(0, ".")
from modules.naver_estimate_api import _request

kw_id = "nkw-a001-01-000008056389517"
kw_text = "로봇청소기"

# 1단계: 순위별 입찰가 조회
print("=== 순위별 입찰가 ===")
rank_bids = {}
for device in ["PC", "MOBILE"]:
    res = _request("POST", "/npc-estimate/average-position-bid/id", payload={
        "device": device,
        "items": [{"key": kw_id, "position": p} for p in range(1, 6)]
    })
    print(f"\n[{device}]")
    rank_bids[device] = {}
    for item in res["data"].get("estimate", []):
        bid = item["bid"]
        rank_bids[device][item["position"]] = bid
        flag = " ← 경쟁없음" if bid <= 70 else ""
        print(f"  {item['position']}위: {bid:,}원{flag}")

# 2단계: 각 순위 입찰가로 performance-bulk 호출
print("\n=== 순위별 예상 성과 ===")
print(f"{'순위':4s} | {'PC입찰':8s} | {'PC노출':8s} | {'PC클릭':6s} | {'MO입찰':8s} | {'MO노출':8s} | {'MO클릭':6s}")
print("-" * 70)

for pos in range(1, 6):
    pc_bid = rank_bids["PC"].get(pos, 70)
    mo_bid = rank_bids["MOBILE"].get(pos, 70)
    
    res = _request("POST", "/estimate/performance-bulk", payload={
        "items": [
            {"keyword": kw_text, "bid": pc_bid, "device": "PC"},
            {"keyword": kw_text, "bid": mo_bid, "device": "MOBILE"},
        ]
    })
    items = res["data"].get("items", [])
    pc = next((x for x in items if x.get("device") == "PC"), {})
    mo = next((x for x in items if x.get("device") == "MOBILE"), {})
    print(f"{pos}위   | {pc_bid:8,} | {pc.get('impressions',0):8,} | {pc.get('clicks',0):6,} | {mo_bid:8,} | {mo.get('impressions',0):8,} | {mo.get('clicks',0):6,}")

# 3단계: 키워드 삭제
print("\n=== 키워드 삭제 ===")
del_result = _request("DELETE", f"/ncc/keywords?ids={kw_id}")
print(f"삭제 status: {del_result['status_code']}")
