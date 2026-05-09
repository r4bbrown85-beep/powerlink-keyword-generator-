import os, json
from dotenv import load_dotenv
load_dotenv()
import sys; sys.path.insert(0, ".")
from modules.naver_estimate_api import _request

for rank in [1, 3, 5]:
    result = _request("POST", "/npc-estimate/exposure-minimum-bid/keyword", payload={
        "device": "PC",
        "rank": rank,
        "items": ["로봇청소기", "무선청소기"]
    })
    print(f"rank={rank} status={result['status_code']}")
    print(json.dumps(result["data"], ensure_ascii=False, indent=2)[:400])
    print()
