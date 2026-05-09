import os, json
from dotenv import load_dotenv
load_dotenv()
import sys; sys.path.insert(0, ".")
from modules.naver_estimate_api import _request

# keyword 타입에서 다양한 파라미터 구조 시도
payloads = [
    {"device": "PC", "items": [{"keyword": "로봇청소기", "position": 1}]},
    {"device": "PC", "items": [{"keyword": "로봇청소기", "position": 1}, {"keyword": "로봇청소기", "position": 3}, {"keyword": "로봇청소기", "position": 5}]},
    {"device": "PC", "items": [{"keyword": "헤어드라이기", "position": 1}, {"keyword": "헤어드라이기", "position": 3}]},
]

for i, payload in enumerate(payloads):
    result = _request("POST", "/npc-estimate/average-position-bid/keyword", payload=payload)
    print(f"패턴{i+1} status={result['status_code']}")
    print(json.dumps(result["data"], ensure_ascii=False, indent=2))
    print()
