import sys, os
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv()
os.environ['NAVER_SECRET_KEY'] = os.environ.get('NAVER_SECRET_KEY','')
os.environ.setdefault('NAVER_API_KEY', os.environ.get('NAVER_API_KEY',''))

from modules.naver_estimate import _post

ak  = os.environ.get('NAVER_API_KEY')
sk  = os.environ.get('NAVER_SECRET_KEY')
cid = os.environ.get('NAVER_CUSTOMER_ID')

kw     = '강남피부과'
device = 'MOBILE'
test_bids = [18490, 19900, 20160, 21420]

def show(label, result):
    print(f"=== {label} ===")
    if result:
        for e in sorted(result.get('estimate', []), key=lambda x: int(x['bid'])):
            print(f"  bid={int(e['bid']):,}  impressions={int(e.get('impressions',0)):,}  clicks={int(e.get('clicks',0)):,}")
    else:
        print("  결과 없음")
    print()

r1 = _post('/estimate/performance/keyword',
    {'device': device, 'key': kw, 'bids': test_bids},
    ak, sk, cid)
show("keywordplus 없음 (기본값)", r1)

import time; time.sleep(0.5)

r2 = _post('/estimate/performance/keyword',
    {'device': device, 'key': kw, 'bids': test_bids, 'keywordplus': True},
    ak, sk, cid)
show("keywordplus=True", r2)
