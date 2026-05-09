import os, json
from dotenv import load_dotenv
load_dotenv()
import sys; sys.path.insert(0, ".")
from modules.naver_estimate_api import _request

adgroup_id = "grp-a001-01-000000057394354"

# 에러 상세 확인
result = _request("POST", "/ncc/keywords", payload=[
    {"nccAdgroupId": adgroup_id, "keyword": "로봇청소기", "bidAmt": 70, "useGroupBidAmt": True}
])
print(f"status: {result['status_code']}")
print(json.dumps(result["data"], ensure_ascii=False, indent=2))
