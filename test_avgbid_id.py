import os, json
from dotenv import load_dotenv
load_dotenv()
import sys; sys.path.insert(0, ".")
from modules.naver_estimate_api import _request

# 첫번째 캠페인의 광고그룹 조회
campaign_id = "cmp-a001-01-000000004224653"
result = _request("GET", "/ncc/adgroups", params={"nccCampaignId": campaign_id})
data = result["data"]
print("adgroups status:", result["status_code"])
if isinstance(data, list) and data:
    adgroup_id = data[0].get("nccAdgroupId")
    print("첫번째 adgroup_id:", adgroup_id)
    
    # 광고그룹의 키워드 조회
    result2 = _request("GET", "/ncc/keywords", params={"nccAdgroupId": adgroup_id})
    kws = result2["data"]
    print("keywords status:", result2["status_code"])
    if isinstance(kws, list) and kws:
        print(f"키워드 수: {len(kws)}")
        # 첫번째 키워드 ID와 텍스트 출력
        for kw in kws[:5]:
            print(f"  id={kw.get('nccKeywordId')} keyword={kw.get('keyword')}")
        
        # average-position-bid/id 테스트
        kw_id = kws[0].get("nccKeywordId")
        kw_text = kws[0].get("keyword")
        print(f"\n[{kw_text}] 순위별 입찰가 조회...")
        for device in ["PC", "MOBILE"]:
            res = _request("POST", "/npc-estimate/average-position-bid/id", payload={
                "device": device,
                "items": [{"key": kw_id, "position": p} for p in [1,2,3,4,5]]
            })
            print(f"  {device} status={res['status_code']}")
            print(f"  {json.dumps(res['data'], ensure_ascii=False, indent=2)}")
