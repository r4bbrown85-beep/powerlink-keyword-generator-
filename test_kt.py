import os, json
from dotenv import load_dotenv
load_dotenv()
import sys; sys.path.insert(0, ".")
from modules.naver_keyword_api import get_keyword_stats

# 네이버S 데이터에 있는 키워드들
keywords = ["로봇청소기", "무선청소기", "헤어드라이기", "스팀청소기", "물걸레청소기"]
api_key = os.getenv("NAVER_API_KEY")
secret = os.getenv("NAVER_SECRET_KEY")
cid = os.getenv("NAVER_CUSTOMER_ID")

stats = get_keyword_stats(keywords, api_key, secret, cid)
print(f"{'키워드':15s} | KT_PC노출   | KT_PC클릭")
for kw, d in stats.items():
    print(f"{kw:15s} | {d.get('pc_impr',0):11,} | {d.get('pc_click',0):8.1f}")
