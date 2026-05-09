import os, json
from dotenv import load_dotenv
load_dotenv()
import sys; sys.path.insert(0, ".")
from modules.naver_estimate_api import _request

kw_id = "nkw-a001-01-000008056389517"

# DELETE 방식 변경 시도
result = _request("DELETE", "/ncc/keywords", params={"ids": kw_id})
print(f"status: {result['status_code']}")
print(json.dumps(result["data"], ensure_ascii=False, indent=2))
