import os, json, time
from dotenv import load_dotenv
load_dotenv()
import sys; sys.path.insert(0, ".")
from modules.naver_estimate_api import _request

adgroup_id = "grp-a001-01-000000064952619"
test_keywords = ["로봇청소기", "무선청소기", "헤어드라이기", "물걸레청소기"]

# 1단계: 키워드 등록
print("=== 1단계: 키워드 등록 ===")
result = _request("POST", "/ncc/keywords",
    params={"nccAdgroupId": adgroup_id},
    payload=[{"keyword": kw, "bidAmt": 70, "useGroupBidAmt": True} for kw in test_keywords]
)
print(f"status: {result['status_code']}")
registered = result["data"] if isinstance(result["data"], list) else []
kw_map = {}
for kw in registered:
    kw_map[kw.get("keyword")] = kw.get("nccKeywordId")
    print(f"  {kw.get('keyword')} → {kw.get('nccKeywordId')}")

time.sleep(1)

# 2단계: 순위별 입찰가 + 성과 조회
print("\n=== 2단계: 순위별 예상 성과 ===")
for kw_text, kw_id in kw_map.items():
    print(f"\n[{kw_text}]")
    print(f"{'순위':4s} | {'PC입찰':8s} | {'PC노출':8s} | {'PC클릭':6s} | {'MO입찰':8s} | {'MO노출':8s} | {'MO클릭':6s}")
    print("-" * 70)

    # 순위별 입찰가
    pc_bids = {}
    mo_bids = {}
    for device, bids_dict in [("PC", pc_bids), ("MOBILE", mo_bids)]:
        res = _request("POST", "/npc-estimate/average-position-bid/id", payload={
            "device": device,
            "items": [{"key": kw_id, "position": p} for p in range(1, 6)]
        })
        for item in res["data"].get("estimate", []):
            bids_dict[item["position"]] = item["bid"]

    # performance-bulk
    for pos in range(1, 6):
        pc_bid = pc_bids.get(pos, 70)
        mo_bid = mo_bids.get(pos, 70)
        res = _request("POST", "/estimate/performance-bulk", payload={
            "items": [
                {"keyword": kw_text, "bid": pc_bid, "device": "PC"},
                {"keyword": kw_text, "bid": mo_bid, "device": "MOBILE"},
            ]
        })
        items = res["data"].get("items", [])
        pc = next((x for x in items if x.get("device") == "PC"), {})
        mo = next((x for x in items if x.get("device") == "MOBILE"), {})
        flag = " ← 경쟁없음" if pc_bid <= 70 else ""
        print(f"{pos}위   | {pc_bid:8,} | {pc.get('impressions',0):8,} | {pc.get('clicks',0):6,} | {mo_bid:8,} | {mo.get('impressions',0):8,} | {mo.get('clicks',0):6,}{flag}")

# 3단계: 키워드 삭제
print("\n=== 3단계: 키워드 삭제 ===")
ids = ",".join(kw_map.values())
del_result = _request("DELETE", "/ncc/keywords", params={"ids": ids})
print(f"삭제 status: {del_result['status_code']} ({'성공' if del_result['status_code'] == 204 else '실패'})")
