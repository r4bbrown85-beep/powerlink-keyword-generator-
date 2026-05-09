import os, json
from dotenv import load_dotenv
load_dotenv()
import sys; sys.path.insert(0, ".")
from modules.naver_estimate_api import _request

# 005.일반 그룹 키워드 조회
ag_id = "grp-a001-01-000000057394354"
result = _request("GET", "/ncc/keywords", params={"nccAdgroupId": ag_id})
kws = result["data"]
print(f"키워드 수: {len(kws)}")
for kw in kws[:10]:
    print(f"  id={kw.get('nccKeywordId')} keyword={kw.get('keyword')}")

# 첫번째 키워드로 순위별 입찰가 테스트
if kws:
    kw_id = kws[0].get("nccKeywordId")
    kw_text = kws[0].get("keyword")
    print(f"\n[{kw_text}] PC 순위별 입찰가:")
    res = _request("POST", "/npc-estimate/average-position-bid/id", payload={
        "device": "PC",
        "items": [{"key": kw_id, "position": p} for p in [1,2,3,4,5]]
    })
    print(json.dumps(res["data"], ensure_ascii=False, indent=2))
