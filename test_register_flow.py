import os, json, time
from dotenv import load_dotenv
load_dotenv()
import sys; sys.path.insert(0, ".")
from modules.naver_estimate_api import _request

# 기존 일반 키워드 그룹에 테스트 키워드 등록
# grp-a001-01-000000057394354 = 005.일반 그룹
adgroup_id = "grp-a001-01-000000057394354"
test_keywords = ["로봇청소기", "무선청소기", "헤어드라이기"]

# 1단계: 키워드 등록
print("=== 1단계: 키워드 등록 ===")
result = _request("POST", "/ncc/keywords", payload=[
    {"nccAdgroupId": adgroup_id, "keyword": kw, "bidAmt": 70, "useGroupBidAmt": True}
    for kw in test_keywords
])
print(f"status: {result['status_code']}")
registered = result["data"] if isinstance(result["data"], list) else []
for kw in registered:
    print(f"  등록완료: {kw.get('keyword')} → ID: {kw.get('nccKeywordId')}")

time.sleep(1)

# 2단계: 순위별 입찰가 조회
print("\n=== 2단계: 순위별 입찰가 조회 ===")
for device in ["PC", "MOBILE"]:
    items = [{"key": kw["nccKeywordId"], "position": p}
             for kw in registered for p in range(1, 6)]
    res = _request("POST", "/npc-estimate/average-position-bid/id", payload={
        "device": device, "items": items
    })
    print(f"\n[{device}]")
    for item in res["data"].get("estimate", []):
        bid = item["bid"]
        flag = " ← 경쟁없음" if bid <= 70 else ""
        print(f"  {item['keyword']} {item['position']}위: {bid:,}원{flag}")

# 3단계: 등록 키워드 삭제
print("\n=== 3단계: 키워드 삭제 ===")
ids = [kw["nccKeywordId"] for kw in registered]
del_result = _request("DELETE", f"/ncc/keywords?ids={','.join(ids)}")
print(f"삭제 status: {del_result['status_code']}")
print("완료!")
