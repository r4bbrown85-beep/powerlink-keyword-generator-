import os, json
from dotenv import load_dotenv
load_dotenv()
import sys; sys.path.insert(0, ".")
from modules.naver_estimate_api import _request

# 로봇청소기 2위 200원으로 performance-bulk 호출했을때
# 실제로 어느 정도 입찰가부터 노출이 시작되는지 확인
kw = "로봇청소기"
bids = [70, 100, 150, 200, 250, 300, 400, 500, 700, 1000, 1500, 2000, 2670, 3000]
print(f"{'입찰가':8s} | {'PC노출':8s} | {'PC클릭':6s}")
print("-" * 30)
for bid in bids:
    res = _request("POST", "/estimate/performance-bulk", payload={
        "items": [{"keyword": kw, "bid": bid, "device": "PC"}]
    })
    pc = next((x for x in res["data"].get("items",[]) if x.get("device")=="PC"), {})
    print(f"{bid:8,} | {pc.get('impressions',0):8,} | {pc.get('clicks',0):6,}")
