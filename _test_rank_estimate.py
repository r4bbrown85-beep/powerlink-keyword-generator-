import sys, os
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv()

from modules.naver_estimate import get_rank_based_estimates, _get_curve, _get_avg_position_bids, SCAN_BIDS

ak  = os.environ.get('NAVER_API_KEY')
sk  = os.environ.get('NAVER_SECRET_KEY', os.environ.get('NAVER_SECRET_KEY',''))
cid = os.environ.get('NAVER_CUSTOMER_ID')

kw = '강남피부과'

print("=== 1. MO 커브 전체 (keywordplus=False) ===")
curve = _get_curve(kw, 'MOBILE', ak, sk, cid, keywordplus=False)
active = [e for e in curve if e['impressions'] > 0]
max_clicks = max((e['clicks'] for e in active), default=0)
sat = next((e for e in active if e['clicks'] == max_clicks), None)
print(f"  커브 포인트 수: {len(curve)} / 유효: {len(active)}")
print(f"  포화점(sat_bid): bid={sat['bid']:,}  clicks={sat['clicks']:,}  impressions={sat['impressions']:,}")
print(f"  20000~22000원 범위:")
for e in curve:
    if 18000 <= e['bid'] <= 25000:
        print(f"    bid={e['bid']:,}  clicks={e['clicks']:,}  impr={e['impressions']:,}")

print()
print("=== 2. API2 평균위치 입찰가 (MO rank1) ===")
api2 = _get_avg_position_bids(kw, 'MOBILE', [1,2,3,4,5], ak, sk, cid)
print("  API2 결과:", api2)

print()
print("=== 3. get_rank_based_estimates 전체 실행 ===")
result = get_rank_based_estimates(kw, ak, sk, cid, target_ranks=[1,2,3,4,5])
for device in ['PC', 'MO']:
    print(f"  {device}:")
    for rank, d in sorted(result.get(device, {}).items()):
        print(f"    순위{rank}: bid={d.get('bid',0):,}  clicks={d.get('clicks',0):,}  impr={d.get('impressions',0):,}")
