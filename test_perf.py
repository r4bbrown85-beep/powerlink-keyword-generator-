import os, json
from dotenv import load_dotenv
load_dotenv()
import sys; sys.path.insert(0, ".")
from modules.naver_estimate_api import _request

# /estimate/performance - 키워드 하나에 여러 bid
# 로봇청소기에 bid 1000~10000원 구간으로 한번에 조회
bids = [1000, 2000, 3000, 4000, 5000, 6000, 7000, 7230, 8000, 9000, 10000]

result = _request("POST", "/estimate/performance", payload={
    "device": "PC",
    "keyword": "로봇청소기",
    "bids": bids
})
print(f"status={result['status_code']}")
print(json.dumps(result["data"], ensure_ascii=False, indent=2)[:1000])
