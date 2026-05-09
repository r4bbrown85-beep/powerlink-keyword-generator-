# -*- coding: utf-8 -*-
"""
/npc-estimate/average-position-bid/keyword 엔드포인트 테스트
순위(position)를 넣으면 해당 순위 달성 입찰가 + 클릭 반환 여부 확인
"""
import os, time, hmac, hashlib, base64, requests
from dotenv import load_dotenv
load_dotenv()

BASE_URL    = "https://api.searchad.naver.com"
api_key     = os.getenv("NAVER_API_KEY")
secret      = os.getenv("NAVER_SECRET_KEY")
customer_id = os.getenv("NAVER_CUSTOMER_ID")

def make_headers(method, uri):
    ts  = str(int(time.time() * 1000))
    sig = base64.b64encode(
        hmac.new(secret.encode(), f"{ts}.{method}.{uri}".encode(), hashlib.sha256).digest()
    ).decode()
    return {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Timestamp": ts, "X-API-KEY": api_key,
        "X-Customer": str(customer_id), "X-Signature": sig,
    }

TEST_KW = "딥디크"

# 테스트 1: /npc-estimate/average-position-bid/keyword (키워드 텍스트 기반)
print("=" * 60)
print("테스트 1: /npc-estimate/average-position-bid/keyword")
for device in ["PC", "MOBILE"]:
    uri = "/npc-estimate/average-position-bid/keyword"
    payload = {
        "device": device,
        "items": [
            {"key": TEST_KW, "position": 1},
            {"key": TEST_KW, "position": 2},
            {"key": TEST_KW, "position": 3},
            {"key": TEST_KW, "position": 4},
            {"key": TEST_KW, "position": 5},
        ]
    }
    resp = requests.post(BASE_URL + uri, json=payload,
                         headers=make_headers("POST", uri), timeout=30)
    print(f"\n[{device}] status={resp.status_code}")
    print(f"응답: {resp.text[:500]}")

# 테스트 2: /estimate/performance-bulk에 position 파라미터 추가
print("\n" + "=" * 60)
print("테스트 2: /estimate/performance-bulk + position 파라미터")
uri = "/estimate/performance-bulk"
payload = {
    "items": [
        {"keyword": TEST_KW, "bid": 900, "device": "PC", "position": 1},
        {"keyword": TEST_KW, "bid": 900, "device": "PC", "position": 2},
        {"keyword": TEST_KW, "bid": 900, "device": "MOBILE", "position": 1},
    ]
}
resp = requests.post(BASE_URL + uri, json=payload,
                     headers=make_headers("POST", uri), timeout=30)
print(f"status={resp.status_code}")
print(f"응답: {resp.text[:500]}")

# 테스트 3: /npc-estimate/performance-bulk (다른 경로)
print("\n" + "=" * 60)
print("테스트 3: /npc-estimate/performance-bulk")
uri = "/npc-estimate/performance-bulk"
payload = {
    "items": [
        {"keyword": TEST_KW, "bid": 900, "device": "PC"},
        {"keyword": TEST_KW, "bid": 900, "device": "MOBILE"},
    ]
}
resp = requests.post(BASE_URL + uri, json=payload,
                     headers=make_headers("POST", uri), timeout=30)
print(f"status={resp.status_code}")
print(f"응답: {resp.text[:300]}")