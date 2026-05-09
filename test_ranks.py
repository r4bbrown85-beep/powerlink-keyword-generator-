import os, json
from dotenv import load_dotenv
load_dotenv()
import sys; sys.path.insert(0, ".")
from modules.naver_estimate_api import _request

kw_id = "nkw-a001-01-000007663031270"
kw_text = "마케팅회사"

for device in ["PC", "MOBILE"]:
    res = _request("POST", "/npc-estimate/average-position-bid/id", payload={
        "device": device,
        "items": [{"key": kw_id, "position": p} for p in range(1, 11)]
    })
    print(f"[{kw_text}] {device} 순위별 입찰가:")
    for item in res["data"]["estimate"]:
        bid = item["bid"]
        flag = "" if bid > 70 else " ← 경쟁자 없음(최소값)"
        print(f"  {item['position']}위: {bid:,}원{flag}")
    print()
