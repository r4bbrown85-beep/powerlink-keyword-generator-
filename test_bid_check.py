import os, json, time
from dotenv import load_dotenv
load_dotenv()
import sys; sys.path.insert(0, ".")
from modules.naver_estimate_api import _request

kw_id = "nkw-a001-01-000008056485201"
kw_text = "로봇청소기"

# 응답 구조 확인
for device in ["PC", "MOBILE"]:
    res = _request("POST", "/npc-estimate/average-position-bid/id", payload={
        "device": device,
        "items": [{"key": kw_id, "position": p} for p in range(1, 6)]
    })
    print(f"[{device}] status={res['status_code']}")
    print(json.dumps(res["data"], ensure_ascii=False, indent=2))
    print()
