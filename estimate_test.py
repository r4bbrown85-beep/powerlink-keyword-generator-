import os
from dotenv import load_dotenv
from modules.naver_estimate import get_estimate_performance

load_dotenv()

api_key     = os.getenv("NAVER_API_KEY")
secret      = os.getenv("NAVER_SECRET_KEY")
customer_id = os.getenv("NAVER_CUSTOMER_ID")

keyword = "프레데릭말"
bids    = [200, 300, 400, 500, 700, 1000]

results = get_estimate_performance(keyword, bids, api_key, secret, customer_id)

print("===== ESTIMATE RESULT =====")
for r in results:
    print(
        f"bid={r['bid']:5d} | "
        f"PC 노출={r['pc_impressions']:6,} 클릭={r['pc_clicks']:4,} 비용={r['pc_cost']:7,} | "
        f"MO 노출={r['mo_impressions']:6,} 클릭={r['mo_clicks']:4,} 비용={r['mo_cost']:7,} | "
        f"합계 클릭={r['clicks']:4,} 비용={r['cost']:8,}"
    )