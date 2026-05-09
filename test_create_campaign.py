import os, json
from dotenv import load_dotenv
load_dotenv()
import sys; sys.path.insert(0, ".")
from modules.naver_estimate_api import _request

# 1단계: 테스트 캠페인 생성
print("=== 캠페인 생성 ===")
campaign_result = _request("POST", "/ncc/campaigns", payload={
    "name": "[TEST] 키워드 조회용",
    "campaignTp": "WEB_SITE",
    "deliveryMethod": "ACCELERATED",
    "usePeriod": False,
    "dailyBudget": 0
})
print(f"status: {campaign_result['status_code']}")
print(json.dumps(campaign_result["data"], ensure_ascii=False, indent=2))
