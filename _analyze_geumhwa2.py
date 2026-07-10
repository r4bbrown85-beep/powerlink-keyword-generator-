import openpyxl, sys, io
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
path = r'c:\Users\Administrator\Downloads\(주)금화_proposal_20260709.xlsx'
wb = openpyxl.load_workbook(path, data_only=True)
ws = wb['톰맥캔_제안서']

valid_cats = {'톰맥캔 브랜드', '경쟁사 브랜드', '샌들·플랫슈즈·여성구두 제품', '여성 신발·구두 카테고리'}
kws = []
for i, row in enumerate(ws.iter_rows(values_only=True), 1):
    kw, cat = row[1], row[2]
    if kw and cat in valid_cats:
        kws.append({
            'row': i, 'kw': kw, 'cat': cat,
            'pc_bid': row[3], 'pc_impr': row[4], 'pc_click': row[5], 'pc_cost': row[6], 'pc_rank': row[7],
            'mo_bid': row[8], 'mo_impr': row[9], 'mo_click': row[10], 'mo_cost': row[11], 'mo_rank': row[12],
            'note': row[13],
        })

print(f'총 키워드: {len(kws)}개')
for cat, cnt in Counter(k['cat'] for k in kws).items():
    print(f'  [{cat}] {cnt}개')

# 비용 합계 검증
pc_cost_sum = sum((k['pc_cost'] or 0) for k in kws)
mo_cost_sum = sum((k['mo_cost'] or 0) for k in kws)
print(f'\nPC 비용합계(재계산): {pc_cost_sum:,}원 / 시트요약: 120,505원')
print(f'MO 비용합계(재계산): {mo_cost_sum:,}원 / 시트요약: 379,487원')
print(f'합계(재계산): {pc_cost_sum+mo_cost_sum:,}원 / Overview: 499,992원')

# fallback(추정) vs 실측(estimate 성공)
fallback = [k for k in kws if k['note'] and '추정' in str(k['note'])]
real = [k for k in kws if not (k['note'] and '추정' in str(k['note']))]
print(f'\n추정(fallback) 키워드: {len(fallback)}개 / 실측(API성공): {len(real)}개')
print(f'Overview 명시값 - 성과 예측: 9개, 입찰가 추정: 203개')

# 노출은 있는데 클릭/비용 0인 이상 키워드
odd = [k for k in kws if ((k['pc_impr'] or 0) > 0 and not (k['pc_cost'] or 0)) or ((k['mo_impr'] or 0) > 0 and not (k['mo_cost'] or 0))]
print(f'\n노출은 있는데 비용 0인 이상 키워드: {len(odd)}개')
for k in odd:
    print(f'  [{k["cat"]}] {k["kw"]}  PC(impr={k["pc_impr"]},cost={k["pc_cost"]})  MO(impr={k["mo_impr"]},cost={k["mo_cost"]})')

# 예산 500,000원인데 실측 클릭수 대비 비용 이상치 체크 - 입찰가 0 or 이상값
weird_bid = [k for k in kws if (k['pc_bid'] and k['pc_bid'] < 0) or (k['mo_bid'] and k['mo_bid'] < 0)]
print(f'\n음수 입찰가: {len(weird_bid)}개')

# 브랜드 제외 패턴(AI 인사이트에서 명시) 위반 체크
exclude_terms = ['남성구두', '남성 구두', '키즈슈즈', '키즈 슈즈', '명품샌들', '명품 샌들', '수제화']
print('\n=== AI 인사이트 "제외 패턴" 위반 의심 키워드 ===')
found_any = False
for k in kws:
    kwtxt = str(k['kw'])
    for pat in exclude_terms:
        if pat in kwtxt:
            print(f'  [{k["cat"]}] {kwtxt}  (패턴: {pat})')
            found_any = True
if not found_any:
    print('  없음')

# 경쟁사 브랜드 키워드 전체 나열 (AI인사이트에 언급된 5개 브랜드와 일치하는지)
print('\n=== 경쟁사 브랜드 키워드 전체 ===')
for k in kws:
    if k['cat'] == '경쟁사 브랜드':
        print(f'  {k["kw"]}  PC입찰={k["pc_bid"]} MO입찰={k["mo_bid"]} note={k["note"]}')

# 톰맥캔 브랜드 키워드 전체
print('\n=== 톰맥캔 브랜드 키워드 전체 ===')
for k in kws:
    if k['cat'] == '톰맥캔 브랜드':
        print(f'  {k["kw"]}  PC입찰={k["pc_bid"]} impr={k["pc_impr"]} click={k["pc_click"]} cost={k["pc_cost"]} rank={k["pc_rank"]}  note={k["note"]}')

# 중복 키워드 체크
kw_counts = Counter(k['kw'] for k in kws)
dups = {k:v for k,v in kw_counts.items() if v > 1}
print(f'\n=== 중복 키워드: {len(dups)}개 ===')
for k,v in dups.items():
    print(f'  {k}: {v}회')

# 비고(note) 값 종류
print('\n=== 비고(note) 값 종류 ===')
print(Counter(str(k['note']) for k in kws))

# 일반 카테고리 상위비용 키워드
print('\n=== 카테고리별 비용 상위 5개 ===')
for cat in valid_cats:
    cat_kws = [k for k in kws if k['cat']==cat]
    cat_kws.sort(key=lambda x: -((x['pc_cost'] or 0)+(x['mo_cost'] or 0)))
    print(f'--- {cat} ---')
    for k in cat_kws[:5]:
        print(f'  {k["kw"]}  PC비용={k["pc_cost"]} MO비용={k["mo_cost"]}')
