import os, json
from dotenv import load_dotenv
load_dotenv()
import sys; sys.path.insert(0, ".")
from modules.naver_estimate_api import _request

kw = "로봇청소기"
# 1단계: 로그 스케일 넓은 탐색
stage1_bids = [70, 200, 500, 1000, 2000, 5000, 10000, 30000, 100000]

print("=== 1단계: 넓은 범위 탐색 ===")
print(f"{'입찰가':10s} | {'PC노출':8s} | {'PC클릭':6s} | {'MO노출':8s} | {'MO클릭':6s}")
print("-" * 50)

items = []
for bid in stage1_bids:
    items.append({"keyword": kw, "bid": bid, "device": "PC"})
    items.append({"keyword": kw, "bid": bid, "device": "MOBILE"})

res = _request("POST", "/estimate/performance-bulk", payload={"items": items})
results = res["data"].get("items", [])

for bid in stage1_bids:
    pc = next((x for x in results if x["bid"]==bid and x["device"]=="PC"), {})
    mo = next((x for x in results if x["bid"]==bid and x["device"]=="MOBILE"), {})
    print(f"{bid:10,} | {pc.get('impressions',0):8,} | {pc.get('clicks',0):6,} | {mo.get('impressions',0):8,} | {mo.get('clicks',0):6,}")
