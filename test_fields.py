import os, json
from dotenv import load_dotenv
load_dotenv()
import sys; sys.path.insert(0, ".")
from modules.naver_estimate_api import _request

res = _request("POST", "/estimate/performance-bulk", payload={
    "items": [
        {"keyword": "로봇청소기", "bid": 3000, "device": "PC"},
        {"keyword": "로봇청소기", "bid": 3000, "device": "MOBILE"},
    ]
})
print(json.dumps(res["data"], ensure_ascii=False, indent=2))
