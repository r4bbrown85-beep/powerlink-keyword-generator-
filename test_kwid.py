import os, json
from dotenv import load_dotenv
load_dotenv()
import sys; sys.path.insert(0, ".")
from modules.naver_estimate_api import _request

# /npc-estimate/average-position-bid/id 엔드포인트 - 숫자 ID 방식
# 먼저 키워드 ID 조회
result = _request("GET", "/keywordstool", params={"hintKeywords": "로봇청소기", "showDetail": 1})
data = result["data"]
kw_list = data.get("keywordList", [])
if kw_list:
    item = kw_list[0]
    print("키워드 item 전체 필드:", json.dumps(item, ensure_ascii=False, indent=2)[:600])
