import os, json
from dotenv import load_dotenv
load_dotenv()
import sys; sys.path.insert(0, ".")
from modules.naver_estimate_api import _request

keywords = ["로봇청소기", "헤어드라이기", "드리미 포켓", "마케팅회사"]

def stage1_scan(kw):
    bids = [70, 200, 500, 1000, 2000, 5000, 10000, 30000, 100000]
    items = []
    for bid in bids:
        items.append({"keyword": kw, "bid": bid, "device": "PC"})
        items.append({"keyword": kw, "bid": bid, "device": "MOBILE"})
    res = _request("POST", "/estimate/performance-bulk", payload={"items": items})
    results = res["data"].get("items", [])
    
    pc = [(bid, next((x for x in results if x["bid"]==bid and x["device"]=="PC"), {})) for bid in bids]
    mo = [(bid, next((x for x in results if x["bid"]==bid and x["device"]=="MOBILE"), {})) for bid in bids]
    return pc, mo

def find_saturation(scan_results):
    """노출수가 처음 포화되는 구간 찾기"""
    max_impr = max(x[1].get("impressions",0) for x in scan_results)
    if max_impr == 0:
        return None, None
    
    # 포화 시작 지점 (max의 95% 이상)
    sat_threshold = max_impr * 0.95
    prev_bid = None
    sat_bid = None
    for bid, data in scan_results:
        impr = data.get("impressions", 0)
        if impr >= sat_threshold and sat_bid is None:
            sat_bid = bid
            break
        prev_bid = bid
    
    return prev_bid, sat_bid

def stage2_scan(kw, pc_start, pc_end, mo_start, mo_end, n=10):
    def make_range(start, end, n):
        if start is None or end is None:
            return []
        step = max((end - start) // n, 10)
        return list(range(start, end + step, step))[:n+1]
    
    pc_bids = make_range(pc_start, pc_end, n)
    mo_bids = make_range(mo_start, mo_end, n)
    
    items = []
    for bid in pc_bids:
        items.append({"keyword": kw, "bid": bid, "device": "PC"})
    for bid in mo_bids:
        items.append({"keyword": kw, "bid": bid, "device": "MOBILE"})
    
    if not items:
        return [], [], pc_bids, mo_bids
    
    res = _request("POST", "/estimate/performance-bulk", payload={"items": items})
    results = res["data"].get("items", [])
    
    pc = [(bid, next((x for x in results if x["bid"]==bid and x["device"]=="PC"), {})) for bid in pc_bids]
    mo = [(bid, next((x for x in results if x["bid"]==bid and x["device"]=="MOBILE"), {})) for bid in mo_bids]
    return pc, mo

print("=" * 70)
for kw in keywords:
    print(f"\n{'='*70}")
    print(f"[{kw}]")
    
    # 1단계
    pc1, mo1 = stage1_scan(kw)
    print(f"\n1단계 스캔:")
    print(f"{'입찰가':10s} | {'PC노출':8s} | {'PC클릭':6s} | {'MO노출':8s} | {'MO클릭':6s}")
    print("-" * 55)
    for bid, pc in pc1:
        mo_data = next((x[1] for x in mo1 if x[0]==bid), {})
        print(f"{bid:10,} | {pc.get('impressions',0):8,} | {pc.get('clicks',0):6,} | {mo_data.get('impressions',0):8,} | {mo_data.get('clicks',0):6,}")
    
    # 포화 구간 찾기
    pc_prev, pc_sat = find_saturation(pc1)
    mo_prev, mo_sat = find_saturation(mo1)
    print(f"\nPC 포화 구간: {pc_prev}원 ~ {pc_sat}원")
    print(f"MO 포화 구간: {mo_prev}원 ~ {mo_sat}원")
    
    # 2단계
    if pc_prev and pc_sat:
        pc2, mo2 = stage2_scan(kw, pc_prev, pc_sat, mo_prev, mo_sat)
        
        print(f"\n2단계 정밀 스캔:")
        print(f"PC:")
        print(f"{'입찰가':8s} | {'노출':8s} | {'클릭':6s} | {'CPC':8s}")
        print("-" * 38)
        for bid, data in pc2:
            clk = data.get("clicks", 0)
            cpc = round(data.get("cost",0)/clk) if clk > 0 else 0
            print(f"{bid:8,} | {data.get('impressions',0):8,} | {clk:6,} | {cpc:8,}")
        
        print(f"MO:")
        print(f"{'입찰가':8s} | {'노출':8s} | {'클릭':6s} | {'CPC':8s}")
        print("-" * 38)
        for bid, data in mo2:
            clk = data.get("clicks", 0)
            cpc = round(data.get("cost",0)/clk) if clk > 0 else 0
            print(f"{bid:8,} | {data.get('impressions',0):8,} | {clk:6,} | {cpc:8,}")
