import os, sys, time
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, ".")
from modules.naver_estimate_api import _request

tests = [
    ("PC+MO 쌍 device inside", "/estimate/performance-bulk", {
        "items": [
            {"keyword": "로봇청소기", "bid": 7230, "device": "PC"},
            {"keyword": "로봇청소기", "bid": 7680, "device": "MOBILE"},
        ]
    }),
    ("PC만 device inside", "/estimate/performance-bulk", {
        "items": [{"keyword": "로봇청소기", "bid": 7230, "device": "PC"}]
    }),
    ("PC+MO device outside", "/estimate/performance-bulk", {
        "device": "PC",
        "items": [
            {"keyword": "로봇청소기", "bid": 7230},
            {"keyword": "로봇청소기", "bid": 7230},
        ]
    }),
]

for name, uri, payload in tests:
    res = _request("POST", uri, payload=payload)
    print(f"[{name}] status={res['status_code']}")
    print(f"  {res['data']}")
    print()
    time.sleep(0.3)
