import os, json
from dotenv import load_dotenv
load_dotenv()
import sys; sys.path.insert(0, ".")
from modules.naver_estimate_api import _request

kw_text = "마케팅회사"

# 입찰가를 촘촘하게 스캔해서 실제 커브 확인
bids = [500, 1000, 2000, 3000, 4000, 5000, 7000, 7370, 10000, 14150, 15000]
print(f"입찰가별 실제 성과:")
print(f"{'bid':8s} | {'PC노출':8s} | {'PC클릭':6s} | {'PC비용':10s}")
print("-" * 45)
for bid in bids:
    res = _request("POST", "/estimate/performance-bulk", payload={
        "items": [
            {"keyword": kw_text, "bid": bid, "device": "PC"},
            {"keyword": kw_text, "bid": bid, "device": "MOBILE"},
        ]
    })
    items = res["data"].get("items", [])
    pc = next((x for x in items if x.get("device") == "PC"), {})
    print(f"{bid:8,} | {pc.get('impressions',0):8,} | {pc.get('clicks',0):6,} | {pc.get('cost',0):10,}")
