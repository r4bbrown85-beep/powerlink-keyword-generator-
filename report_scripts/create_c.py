import sys
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import gspread

TOKEN_PATH = Path('config/oauth_token.json')
SCOPES = ['https://www.googleapis.com/auth/spreadsheets','https://www.googleapis.com/auth/drive']
creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())

service = build('sheets', 'v4', credentials=creds)
gc = gspread.authorize(creds)

DST_ID = '1jwynjel06dgzjE-X6tAMJbWuGSKGmZ_kPodMt6cfj2E'
SRC_ID = '1F3jWEB8235zfL8dQlgjDIlHVpIhFCWi7s8z--PKoT6U'
SRC_REVIEW_SID = 1609983932
SRC_PLAN_SID   = 150274068

sh = gc.open_by_key(DST_ID)

# 기존 [C] 탭 있으면 삭제
for ws in sh.worksheets():
    if ws.title.startswith('[C]'):
        sh.del_worksheet(ws)
        print(f'삭제: {ws.title}')

def copy_sheet(src_sid, new_title):
    result = service.spreadsheets().sheets().copyTo(
        spreadsheetId=SRC_ID, sheetId=src_sid,
        body={'destinationSpreadsheetId': DST_ID}
    ).execute()
    new_sid = result['sheetId']
    service.spreadsheets().batchUpdate(
        spreadsheetId=DST_ID,
        body={'requests': [{'updateSheetProperties': {
            'properties': {'sheetId': new_sid, 'title': new_title},
            'fields': 'title'
        }}]}
    ).execute()
    print(f'복사: {new_title} (sheetId={new_sid})')
    return new_sid

SID_C_R = copy_sheet(SRC_REVIEW_SID, '[C] 채널2팀-상반기리뷰')
SID_C_H = copy_sheet(SRC_PLAN_SID,   '[C] 채널2팀-하반기플랜')

sh = gc.open_by_key(DST_ID)
ws_cr = sh.worksheet('[C] 채널2팀-상반기리뷰')
ws_ch = sh.worksheet('[C] 채널2팀-하반기플랜')

# ══════════════════════════════════════════════
# [C] 상반기 리뷰 — A·B 통합 + 간결화
# ══════════════════════════════════════════════
c_review = {
    # ── 핵심 역할 (B6~B11) ────────────────────────────────
    'B6':
        ' • 메타·토스·네이버·당근·크리테오·컬리 주요 RTB 매체 공식 파트너사 창구; '
        '25년 네이버 DA 판매 1위 · 프리미어 파트너사 자격 유지 · 인센티브 4.65억 확보',

    'B7':
        ' • [파트너십 성과] 메타 2025 Agency First Game Changer 수상(W컨셉 협력광고·나스X메타 세미나) / '
        '당근 취급고 YoY +134.5% / 메타 26년 1Q 취급고 YoY +13.7%',

    'B8':
        ' • [영업지원] 메타 POC 1차 창구 / SA 운영 광고주 24→28개 / 워크서포트 주당 30~63건 / '
        'W컨셉 협력광고 49→83 브랜드 성장',

    'B9':
        ' • [신규 매출원] ADVoost 쇼핑 최대 2,000만원/월 · 파트너 부스트 2Q 달성률 50.6% / '
        '토스 LOT 족보·SA 리포트 자동화 개발 중',

    'B10':
        ' • [계정 인프라] 대대행사 14개사 등록 / 네이버 Expert 4개사 선정 / '
        '메타 NOTE 플랫폼 스레드·협력광고·RTA 벤치마크 기능 배포',

    'B11':
        ' • [팀원 구성] 유승환 팀장(13년차) / 이선애 책임(11년차) / '
        '김나은 선임(3년차) / 박현 선임(4년차) / 남경희 선임(상반기 IPP)',

    # ── 네이버 (B15~B17) ──────────────────────────────────
    'B15':
        ' • [25년 연간] 취급고 1,419억(NOSP 932+GFA 487+SA 203억) / GFA YoY +5.5% / 인센티브 4.65억 / '
        '[26년 1Q] 취급고 297억(YoY -24.7%—시장 둔화) / ADVoost 月 최대 2,000만원 · 부스트 2Q 50.6%',

    'B16':
        ' • NOSP 대형 광고주(삼성·넥슨·LG·샤넬) 의존도 집중 — 개별 이탈 시 매출 변동 민감 / '
        'GFA API 리포트 자동화 연동 대기 / SA YoY -55%는 테무 직영 전환 기저효과',

    'B17':
        ' • 영업 조직 SA 이해도 편차 → DA+SA 복합 제안 역량 교육 강화 필요 / '
        'ADVoost·SNB·네이버스 활용 방안 정기 공유 체계 마련',

    # ── 메타 (B19~B21) ──────────────────────────────────
    'B19':
        ' • [25년] 자력 매출 YoY +6.7% / Game Changer 수상 / 광고계정 288→348개(+20.8%) / '
        '[26년 1Q] 취급고 YoY +13.7% · 인보이스 +19.2% / W컨셉 협력광고 1.21억(YoY 성장)',

    'B20':
        ' • GBP 성장지원금 25년 미달성 → 26년 달성 집중 / W컨셉 협업서 9/21 만료 전 연장 결정 필요 / '
        '잦은 플랫폼 오류 보상 불가 → 광고주 만족도 리스크',

    'B21':
        ' • ELCA 이탈 시 협력광고 매출 구조 타격 우려(협력광고 비중 36.7%) / '
        '메타 직커뮤니케이션 불가 정책 → 채널2팀 POC 리소스 집중 구조 지속',

    # ── 토스 (B23~B25) ──────────────────────────────────
    'B23':
        ' • LOT 파트너사 자격 유지 / 4월 정산 7.43억 / 세일즈커넥트 참여 · LOT 족보 제작 완료 / '
        '2Q 인센티브 목표 14.3억(1구간)~16.7억(3구간)',

    'B24':
        ' • 광고주 직영업(CP 직접 접촉)으로 팀·광고주 간 불편 간헐적 발생 / '
        '3구간 폐지·18억 신구간 협의 중 → 인센티브 구조 변화 대응 필요',

    'B25':
        ' • 단독 협업 리포트 논의 중 / Buy & Play at toss 신규 상품(5월 출시) 활용 기회 / '
        '나스미디어 단독 프로모션 혜택 요청 지속',

    # ── 기타 (B27~B29) ──────────────────────────────────
    'B27':
        ' • 당근: 25년 127억(YoY +134.5%, 자력 +45.4%) / 광고계정 52→104개 / 분기 QBR 안정 운영',

    'B28':
        ' • 크리테오: 인보이스 정산 안정 / 기존 광고주(넥슨·LG전자) 유지 / '
        '컬리: 프로모션 지원금 공지 완료 · 커머스 광고주 확장 추진',

    'B29':
        ' • 공통 과제: 신규 쿠폰 집행 시 수수료 미수취 문제 / 매출 자동 대시보드 도입 시급 / '
        '쿠팡·배달의민족 신규 매체 탐색 진행 중',

    # ── 담당자 (B32~B39) ────────────────────────────────
    'B32': '[이선애]',
    'B33':
        ' • 메타 Game Changer 수상 주도(W컨셉 협력광고·세미나) / '
        '협력광고 49→83 브랜드 성장 / 26년 MAFA 어워즈 수상 목표',
    'B34':
        ' • ELCA 이탈 대비 나스미디어 메타 경쟁력 자료 기획 / 토스 원시트·협업 리포트 기획',

    'B35': '[김나은]',
    'B36':
        ' • 메타 NOTE 플랫폼 고도화(스레드·협력광고·RTA 4~5월 배포) / '
        '워크서포트 주당 30~63건 1차 창구 / 이슈 리포트 제작',
    'B37':
        ' • 토스 4월 정산 7.43억 / 세일즈커넥트 참여 · LOT 족보 완료 / 2Q 인센티브 달성률 트래킹',

    'B38': '[박현]',
    'B39':
        ' • SA 28개 광고주 운영·제안서·컨설팅 / ADVoost 월 최대 2,000만원 / '
        'SA 리포트 자동화 솔루션 개발 중(GFA API 연동 포함)',
}

batch = [{'range': c, 'values': [[v]]} for c, v in c_review.items()]
ws_cr.batch_update(batch, value_input_option='RAW')
print('[C] 상반기 리뷰 입력 완료')

# 담당자 이름 볼드
fmt_cr = []
for r in [32, 35, 38]:
    fmt_cr.append({'repeatCell': {
        'range': {'sheetId': SID_C_R, 'startRowIndex': r-1, 'endRowIndex': r, 'startColumnIndex': 1, 'endColumnIndex': 12},
        'cell': {'userEnteredFormat': {'textFormat': {'bold': True, 'fontSize': 10}}},
        'fields': 'userEnteredFormat.textFormat'
    }})
for r in range(6, 40):
    fmt_cr.append({'updateDimensionProperties': {
        'range': {'sheetId': SID_C_R, 'dimension': 'ROWS', 'startIndex': r-1, 'endIndex': r},
        'properties': {'pixelSize': 36}, 'fields': 'pixelSize'
    }})
service.spreadsheets().batchUpdate(spreadsheetId=DST_ID, body={'requests': fmt_cr}).execute()
print('[C] 상반기 리뷰 서식 완료')


# ══════════════════════════════════════════════
# [C] 하반기 플랜 — A·B 통합 + 간결화
# ══════════════════════════════════════════════
c_plan = {
    # ── 우선 추진 과제 (B6~B20) ──────────────────────────
    'B6':  '[네이버] ① 프리미어 파트너사 지위 강화 + GFA/SA 성장',
    'B7':
        ' • 파트너 부스트 3Q 타겟 달성 / ADVoost 쇼핑 연 2억+ 목표(25년 5,571만원 기준) / '
        'PA 퀵윈 월별 신청 관리',
    'B8':
        ' • GFA 월 50억 목표 / 커머스 빅광고주(패션·화장품·가전) 신규 수주 / '
        'SA 28개→35개 확대 목표',
    'B9':
        ' • DA+SA 통합 리포트 자동화 3Q 배포 / DA+SA 복합 제안 Kit 배포 → 영업본부 역량 강화',

    'B10': '[메타] ② Agency First Awards 수상 + 성장 모멘텀 유지',
    'B11':
        ' • W컨셉 온사이트+협력광고 시너지 사례 → 4Q Agency First Awards 도전 / '
        '협업서 9/21 만료 전 연장 결정(상위 레벨 필요)',
    'B12':
        ' • 26년 1Q YoY +13.7% 기조 유지 / GBP 성장지원금 26년 Target 달성 집중 / '
        'ELCA 이탈 대비 신규 엔터프라이즈 광고주 확보',
    'B13':
        ' • AI Advantage+ 캠페인 적용 확대 / 글로벌 협업 확대(젠틀몬스터·넥슨 스레드)',

    'B14': '[토스] ③ LOT 인센티브 최대화 + 단독 협업 확대',
    'B15':
        ' • 2Q 인센티브 목표(14.3억~16.7억) 달성 / 3구간 폐지·18억 신구간 협의 결과 대응 / '
        '3Q 프로모션 참여 → 연 수수료 최대화',
    'B16':
        ' • 단독 협업 리포트 발행 → 영업본부 토스 가이드라인 공식화 / '
        'Buy & Play at toss 신규 상품 집행 확대',
    'B17':
        ' • 세일즈커넥트 수료 후 내부 역량 강화 교육 실시 / TEP 파트너사 자격 유지',

    'B18': '[기타] 버티컬 매체 성장 기회 포착',
    'B19':
        ' • 당근: 광고계정 104개+ 유지·성장 / 자력 성장 +45% 기조 유지 / QBR 파이프라인 강화',
    'B20':
        ' • 크리테오: 신규 광고주 발굴 / 컬리: 커머스 광고주 확장 / '
        '쿠팡·배달의민족·더현대하이 신규 매체 파트너십 기반 마련',

    # ── 담당자별 핵심 과제 (B22~B36) ────────────────────
    'B22': '[이선애]',
    'B23':
        ' • Agency First Awards 수상 도전 (W컨셉 협력광고 시너지 사례 완성)',
    'B24':
        ' • 26년 나스X메타 단독 세미나 기획·운영 / ELCA 이탈 대비 메타 경쟁력 자료 제작',
    'B25':
        ' • 토스 단독 협업 리포트 발행 기여 / 원시트 제안 자료 제작·배포',

    'B27': '[김나은]',
    'B28':
        ' • 메타 NOTE 플랫폼 하반기 추가 기능 기획·배포 / 이슈 리포트 품질 강화',
    'B29':
        ' • 토스 LOT 인센티브 달성 / 세일즈커넥트 수료 후 내부 교육 실시',
    'B30':
        ' • GBP 성장지원금 Target 달성 기여 / 메타 광고계정 350개+ 유지',

    'B33': '[박현]',
    'B34':
        ' • SA 리포트 자동화 3Q 배포(GFA API 연동 포함) / SA 운영 35개 목표',
    'B35':
        ' • DA+SA 통합 분석 서비스 차별화 → 영업본부 공유',
    'B36':
        ' • 매출 트래킹 자동 대시보드 구축(매체별·시간대별 전일 소진 집계)',

    # ── 지원 요청 (B38~B48) ─────────────────────────────
    'B38': '[매체사 상위 레벨 협의]',
    'B39':
        ' • 메타 코리아 — 허진영 이사 부재 후 컨택 감소, 정기 관계 재개 선제 요청 (GBP 목표 달성 지원)',
    'B40':
        ' • W컨셉 협력광고 협업서 9/21 만료 → 상위 레벨 연장 결정 필요 (Agency First 전략 자산)',
    'B41':
        ' • 토스 CPT 등 신규 상품 나스미디어 우선 제공 협의 / '
        '네이버 프리미어 파트너 써밋 실장·임원급 참여 확대',

    'B43': '[영업본부 협업 구조]',
    'B44':
        ' • 채널2팀 파트너십 성과(인센티브 4.65억 · Game Changer · 프리미어 파트너사)를 '
        '영업 경쟁력 근거로 영업본부 전체 공식 어필 필요',
    'B45':
        ' • DA+SA 통합 제안 Kit 배포 + 정기 교육 → 영업본부 복합 수주 역량 강화',

    'B46': '[인력·운영체계]',
    'B47':
        ' • 신규 인원 충원 요청 — 1인당 5개+ 매체 담당으로 전략 업무 집중도 저하 우려',
    'B48':
        ' • 매출 자동 대시보드 도입 / 워크서포트 가이드 체계화 지원',
}

batch_h = [{'range': c, 'values': [[v]]} for c, v in c_plan.items()]
ws_ch.batch_update(batch_h, value_input_option='RAW')
print('[C] 하반기 플랜 입력 완료')

fmt_ch = []
bold_rows = [6, 10, 14, 18, 22, 27, 33, 38, 43, 46]
for r in bold_rows:
    fmt_ch.append({'repeatCell': {
        'range': {'sheetId': SID_C_H, 'startRowIndex': r-1, 'endRowIndex': r, 'startColumnIndex': 1, 'endColumnIndex': 12},
        'cell': {'userEnteredFormat': {'textFormat': {'bold': True, 'fontSize': 10}}},
        'fields': 'userEnteredFormat.textFormat'
    }})
for r in range(6, 49):
    fmt_ch.append({'updateDimensionProperties': {
        'range': {'sheetId': SID_C_H, 'dimension': 'ROWS', 'startIndex': r-1, 'endIndex': r},
        'properties': {'pixelSize': 36}, 'fields': 'pixelSize'
    }})
service.spreadsheets().batchUpdate(spreadsheetId=DST_ID, body={'requests': fmt_ch}).execute()
print('[C] 하반기 플랜 서식 완료')

print(f'\n✓ 완료!')
print(f'테스트 시트: https://docs.google.com/spreadsheets/d/{DST_ID}')
print('\n현재 시트 목록:')
for ws in gc.open_by_key(DST_ID).worksheets():
    print(f'  - {ws.title}')
