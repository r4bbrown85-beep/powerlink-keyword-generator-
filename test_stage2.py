import os, json
from dotenv import load_dotenv
load_dotenv()
import sys; sys.path.insert(0, ".")
from modules.naver_estimate_api import _request

kw = "로봇청소기"

# 2단계: PC는 2,000~5,000 / MO는 5,000~10,000 구간 정밀 스캔
def make_range(start, end, n=10):
    step = (end - start) // n
    return [start + step * i for i in range(n+1)]

pc_bids = make_range(2000, 5000, 10)
mo_bids = make_range(5000, 10000, 10)

print(f"PC 스캔 구간: {pc_bids}")
print(f"MO 스캔 구간: {mo_bids}")
print()

items = []
for bid in pc_bids:
    items.append({"keyword": kw, "bid": bid, "device": "PC"})
for bid in mo_bids:
    items.append({"keyword": kw, "bid": bid, "device": "MOBILE"})

res = _request("POST", "/estimate/performance-bulk", payload={"items": items})
results = res["data"].get("items", [])

print("=== 2단계: PC 정밀 스캔 ===")
print(f"{'입찰가':8s} | {'PC노출':8s} | {'PC클릭':6s} | {'CPC':8s}")
print("-" * 40)
for bid in pc_bids:
    pc = next((x for x in results if x["bid"]==bid and x["device"]=="PC"), {})
    impr = pc.get("impressions", 0)
    clk = pc.get("clicks", 0)
    cpc = round(pc.get("cost",0)/clk) if clk > 0 else 0
    print(f"{bid:8,} | {impr:8,} | {clk:6,} | {cpc:8,}")

print()
print("=== 2단계: MO 정밀 스캔 ===")
print(f"{'입찰가':8s} | {'MO노출':8s} | {'MO클릭':6s} | {'CPC':8s}")
print("-" * 40)
for bid in mo_bids:
    mo = next((x for x in results if x["bid"]==bid and x["device"]=="MOBILE"), {})
    impr = mo.get("impressions", 0)
    clk = mo.get("clicks", 0)
    cpc = round(mo.get("cost",0)/clk) if clk > 0 else 0
    print(f"{bid:8,} | {impr:8,} | {clk:6,} | {cpc:8,}")
