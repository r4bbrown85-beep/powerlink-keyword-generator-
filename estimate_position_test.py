import os
import time
import hmac
import hashlib
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL    = "https://api.searchad.naver.com"
api_key     = os.getenv("NAVER_API_KEY")
secret      = os.getenv("NAVER_SECRET_KEY")
customer_id = os.getenv("NAVER_CUSTOMER_ID")


def make_headers(method, uri):
    timestamp = str(int(time.time() * 1000))
    message   = f"{timestamp}.{method}.{uri}"
    signature = base64.b64encode(
        hmac.new(secret.encode(), message.encode(), hashlib.sha256).digest()
    ).decode()
    return {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Timestamp":  timestamp,
        "X-API-KEY":    api_key,
        "X-Customer":   str(customer_id),
        "X-Signature":  signature,
    }


# ── 1. keywordstool API로 keyword ID 확인 ──────────────────────
print("=" * 50)
print("1. keywordstool API 응답 전체 확인 (향수직구)")
uri = "/keywordstool"
headers = make_headers("GET", uri)
resp = requests.get(
    BASE_URL + uri,
    headers=headers,
    params={"hintKeywords": "향수직구", "showDetail": 1},
    timeout=10
)
print(f"Status: {resp.status_code}")
data = resp.json()
kw_list = data.get("keywordList", [])
if kw_list:
    print("첫 번째 키워드 전체 필드:")
    for k, v in kw_list[0].items():
        print(f"  {k}: {v}")
else:
    print("결과 없음")


# ── 2. keyword ID 추출 후 average-position-bid/id 테스트 ────────
print()
print("=" * 50)
print("2. average-position-bid/id 테스트")

# keywordstool에서 ID 추출
kw_id = None
if kw_list:
    kw_id = kw_list[0].get("nccKeywordId") or kw_list[0].get("keywordId") or kw_list[0].get("id")
    print(f"추출된 keyword ID: {kw_id}")

if kw_id:
    for device in ["PC", "MOBILE"]:
        uri2 = "/npc-estimate/average-position-bid/id"
        headers2 = make_headers("POST", uri2)
        payload2 = {
            "device": device,
            "items": [
                {"key": kw_id, "position": 1},
                {"key": kw_id, "position": 2},
                {"key": kw_id, "position": 3},
            ]
        }
        resp2 = requests.post(BASE_URL + uri2, json=payload2, headers=headers2, timeout=30)
        print(f"\n[{device}] Status: {resp2.status_code}")
        print(f"[{device}] Response: {resp2.json()}")
else:
    print("keyword ID를 찾을 수 없음 - keywordstool 응답에 ID 필드 없음")


# ── 3. 혹시 다른 ID 필드명 시도 ─────────────────────────────────
print()
print("=" * 50)
print("3. 가능한 모든 ID 필드 출력")
if kw_list:
    item = kw_list[0]
    id_candidates = {k: v for k, v in item.items() if "id" in k.lower() or "key" in k.lower()}
    print("ID 관련 필드들:", id_candidates)

print("\n완료")