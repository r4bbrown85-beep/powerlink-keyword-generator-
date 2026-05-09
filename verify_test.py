import os, sys, time, json
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, '.')
from modules.naver_estimate_api import get_performance_bulk

NAVERS_DATA = [
    ('로봇청소기', 1, 7230, 626, 7680, 3380),
    ('로봇청소기', 2, 6030, 603, 6340, 2740),
    ('무선청소기', 1, 2950, 494, 5320, 1408),
    ('헤어드라이기', 1, 12280, 110, 6790, 402),
    ('스팀청소기', 1, 2780, 339, 3970, 460),
]

for kw, rank, pc_bid, ns_pc_clk, mo_bid, ns_mo_clk in NAVERS_DATA:
    res_pc = get_performance_bulk(items=[{'keyword': kw, 'bid': pc_bid}], device='PC')
    res_mo = get_performance_bulk(items=[{'keyword': kw, 'bid': mo_bid}], device='MOBILE')
    print(f'[{kw} {rank}위] PC bid={pc_bid} NS={ns_pc_clk} API={res_pc["data"]}')
    print(f'[{kw} {rank}위] MO bid={mo_bid} NS={ns_mo_clk} API={res_mo["data"]}')
    time.sleep(0.3)
