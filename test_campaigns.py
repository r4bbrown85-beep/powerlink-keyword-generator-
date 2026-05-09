import os, json
from dotenv import load_dotenv
load_dotenv()
import sys; sys.path.insert(0, ".")
from modules.naver_estimate_api import _request

# 우리 계정의 캠페인 목록 조회
result = _request("GET", "/ncc/campaigns", params={})
print("status:", result["status_code"])
data = result["data"]
if isinstance(data, list):
    for c in data[:3]:
        print(json.dumps(c, ensure_ascii=False, indent=2)[:200])
else:
    print(json.dumps(data, ensure_ascii=False, indent=2)[:500])
