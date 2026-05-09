import os, json
from dotenv import load_dotenv
load_dotenv()
import sys; sys.path.insert(0, ".")
from modules.naver_estimate_api import _request

# average-position-bid 엔드포인트 시도
# 키워드 ID가 필요할 수 있으므로 keyword 방식으로 시도
payloads = [
    {"device": "PC", "items": [{"keyword": "로봇청소기", "position": 1}, {"keyword": "로봇청소기", "position": 3}, {"keyword": "로봇청소기", "position": 5}]},
    {"device": "PC", "items": [{"keyword": "로봇청소기", "rank": 1}, {"keyword": "로봇청소기", "rank": 3}]},
    {"device": "PC", "position": 1, "items": ["로봇청소기", "무선청소기"]},
]

for i, payload in enumerate(payloads):
    result = _request("POST", "/npc-estimate/average-position-bid/keyword", payload=payload)
    print(f"패턴{i+1} status={result['status_code']}")
    print(json.dumps(result["data"], ensure_ascii=False, indent=2)[:400])
    print()
