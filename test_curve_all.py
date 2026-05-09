# -*- coding: utf-8 -*-
"""
test_curve_all.py
10개 키워드 전체 커브 스캔 → 클릭 포화점 vs 에이스퀘어 1위 비교
"""
import base64, hashlib, hmac, os, time
import requests
from dotenv import load_dotenv
load_dotenv()

API_KEY     = os.getenv("NAVER_API_KEY", "").strip()
SECRET_KEY  = os.getenv("NAVER_SECRET_KEY", "").strip()
CUSTOMER_ID = os.getenv("NAVER_CUSTOMER_ID", "").strip()

# 로그스케일 98개 bid
lo, hi, n = 70, 100000, 100
BIDS = sorted(set(
    int(round(lo * (hi/lo) ** (i/(n-1)) / 10) * 10)
    for i in range(n)
))
BIDS[0] = 70

TEST_KEYWORDS = [
    "강남임플란트", "실손보험비교", "헬로키티케이크", "인테리어견적",
    "강남피부과추천", "법인세신고대행", "남자헤어스타일",
    "제주도펜션추천", "파이썬학원", "드리미로봇청소기"
]

# 에이스퀘어 1위 정답
ACE_1ST = {
    ("강남임플란트",   "PC"):   (514,   16),
    ("강남임플란트",   "MO"): (1430,   32),
    ("실손보험비교",   "PC"): (1511,  113),
    ("실손보험비교",   "MO"): (3863,  428),
    ("헬로키티케이크", "PC"):   (99,    0),
    ("헬로키티케이크", "MO"):  (780,   11),
    ("인테리어견적",   "PC"):  (873,   89),
    ("인테리어견적",   "MO"): (1711,  213),
    ("강남피부과추천", "PC"):  (417,    7),
    ("강남피부과추천", "MO"):  (906,   22),
    ("법인세신고대행", "PC"):  (120,    7),
    ("법인세신고대행", "MO"):  (140,    4),
    ("남자헤어스타일", "PC"): (2019,   18),
    ("남자헤어스타일", "MO"):(10217,  101),
    ("제주도펜션추천", "PC"):  (340,   31),
    ("제주도펜션추천", "MO"): (1231,  135),
    ("파이썬학원",     "PC"):  (141,    5),
    ("파이썬학원",     "MO"):  (442,   19),
    ("드리미로봇청소기","PC"): (5435,  164),
    ("드리미로봇청소기","MO"):(26808,  657),
}

def get_curve(keyword, device):
    uri = "/estimate/performance/keyword"
    ts  = str(int(time.time() * 1000))
    msg = f"{ts}.POST.{uri}"
    sig = base64.b64encode(
        hmac.new(SECRET_KEY.encode(), msg.encode(), hashlib.sha256).digest()
    ).decode()
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Timestamp": ts, "X-API-KEY": API_KEY,
        "X-Customer": CUSTOMER_ID, "X-Signature": sig,
    }
    resp = requests.post(
        f"https://api.searchad.naver.com{uri}",
        headers=headers,
        json={"device": device, "key": keyword, "bids": BIDS},
        timeout=60
    )
    if not resp.ok:
        return []
    return resp.json().get("estimate", [])

def find_saturation(estimates):
    """클릭수 최대값이 처음 나오는 포화점 반환"""
    if not estimates:
        return None
    max_clicks = max(e["clicks"] for e in estimates)
    if max_clicks == 0:
        # 클릭 없으면 노출 최대값으로
        max_impr = max(e["impressions"] for e in estimates)
        sat = next((e for e in estimates if e["impressions"] == max_impr), None)
    else:
        sat = next((e for e in estimates if e["clicks"] == max_clicks), None)
    return sat

print(f"{'키워드':<14} {'구분':<4} | {'우리_노출':>8} {'우리_클릭':>7} {'우리_bid':>8} | {'에이스_노출':>9} {'에이스_클릭':>8} | {'노출오차':>7} {'클릭일치':>6}")
print("-" * 100)

match_count = 0
total_count = 0

for kw in TEST_KEYWORDS:
    for device, dev_label in [("PC","PC"), ("MOBILE","MO")]:
        estimates = get_curve(kw, device)
        time.sleep(0.3)

        sat = find_saturation(estimates)
        ace = ACE_1ST.get((kw, dev_label))

        if not sat or not ace:
            print(f"{kw:<14} {dev_label:<4} | {'데이터없음':>8}")
            continue

        our_impr   = sat["impressions"]
        our_clicks = sat["clicks"]
        our_bid    = sat["bid"]
        ace_impr, ace_clicks = ace

        impr_diff = f"{(our_impr-ace_impr)/ace_impr*100:+.1f}%" if ace_impr > 0 else "N/A"
        click_ok  = "✅" if our_clicks == ace_clicks else f"❌({our_clicks}vs{ace_clicks})"
        impr_ok   = "✅" if ace_impr > 0 and abs(our_impr-ace_impr)/ace_impr <= 0.05 else ("N/A" if ace_impr == 0 else f"❌{impr_diff}")

        total_count += 1
        if our_clicks == ace_clicks:
            match_count += 1

        print(f"{kw:<14} {dev_label:<4} | {our_impr:>8,} {our_clicks:>7,} {our_bid:>8,} | {ace_impr:>9,} {ace_clicks:>8,} | {impr_ok:>7} {click_ok:>6}")

print(f"\n클릭 일치율: {match_count}/{total_count} ({match_count/total_count*100:.0f}%)")