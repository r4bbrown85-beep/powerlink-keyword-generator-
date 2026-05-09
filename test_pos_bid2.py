import os, json
from dotenv import load_dotenv
load_dotenv()
import sys; sys.path.insert(0, ".")
from modules.naver_estimate_api import _request

# keyword 대신 다른 필드명 시도
payloads = [
    {"device": "PC", "items": [{"keywordId": "로봇청소기", "position": 1}]},
    {"device": "PC", "items": [{"relKeyword": "로봇청소기", "position": 1}]},
    {"device": "PC", "items": [{"hintKeyword": "로봇청소기", "position": 1}]},
    {"device": "PC", "items": [{"keyword": "로봇청소기", "position": 1, "matchType": "BROAD"}]},
]

for i, payload in enumerate(payloads):
    result = _request("POST", "/npc-estimate/average-position-bid/keyword", payload=payload)
    print(f"패턴{i+1} status={result['status_code']}")
    print(json.dumps(result["data"], ensure_ascii=False, indent=2)[:300])
    print()
