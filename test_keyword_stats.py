# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv
load_dotenv()

from modules.naver_keyword_api import get_keyword_stats

API_KEY     = os.getenv("NAVER_API_KEY", "").strip()
SECRET_KEY  = os.getenv("NAVER_SECRET_KEY", "").strip()
CUSTOMER_ID = os.getenv("NAVER_CUSTOMER_ID", "").strip()

keywords = [
    "강남임플란트", "실손보험비교", "헬로키티케이크", "인테리어견적",
    "강남피부과추천", "법인세신고대행", "남자헤어스타일",
    "제주도펜션추천", "파이썬학원", "드리미로봇청소기"
]

results = get_keyword_stats(keywords, API_KEY, SECRET_KEY, CUSTOMER_ID)
print(f"{'키워드':<16} {'PC검색량':>10} {'MO검색량':>10} {'PC클릭수':>10} {'MO클릭수':>10}")
print("-" * 60)
for kw, r in results.items():
    pc_qc = r.get('pc_impr', 0)
    mo_qc = r.get('mo_impr', 0)
    pc_cl = r.get('pc_click', 0)
    mo_cl = r.get('mo_click', 0)
    print(f"{kw:<16} {pc_qc:>10,} {mo_qc:>10,} {pc_cl:>10,} {mo_cl:>10,}")