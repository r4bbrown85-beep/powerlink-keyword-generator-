import os, json
from dotenv import load_dotenv
load_dotenv()
import sys; sys.path.insert(0, ".")
from modules.naver_estimate_api import _request

# 전체 캠페인 목록
result = _request("GET", "/ncc/campaigns", params={})
campaigns = result["data"]
print(f"전체 캠페인 수: {len(campaigns)}")
for c in campaigns:
    print(f"  {c.get('nccCampaignId')} | {c.get('name')}")
