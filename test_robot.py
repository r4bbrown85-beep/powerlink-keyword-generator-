import os, json, time
from dotenv import load_dotenv
load_dotenv()
import sys; sys.path.insert(0, ".")
from modules.naver_estimate_api import _request

adgroup_id = "grp-a001-01-000000064952619"

# 키워드 등록
result = _request("POST", "/ncc/keywords",
    params={"nccAdgroupId": adgroup_id},
    payload=[{"keyword": "로봇청소기", "bidAmt": 70, "useGroupBidAmt": True}]
)
kw_id = result["data"][0]["nccKeywordId"]
print(f"등록: 로봇청소기 → {kw_id}")
time.sleep(1)

# 순위별 입찰가 조회
for device in ["PC", "MOBILE"]:
    res = _request("POST", "/npc-estimate/average-position-bid/id", payload={
        "device": device,
        "items": [{"key": kw_id, "position": p} for p in range(1, 11)]
    })
    print(f"\n[{device}] 로봇청소기 순위별 입찰가:")
    for item in res["data"].get("estimate", []):
        bid = item["bid"]
        flag = " ← 경쟁없음" if bid <= 70 else ""
        print(f"  {item['position']}위: {bid:,}원{flag}")

# 삭제
del_result = _request("DELETE", "/ncc/keywords", params={"ids": kw_id})
print(f"\n삭제: {del_result['status_code']}")
