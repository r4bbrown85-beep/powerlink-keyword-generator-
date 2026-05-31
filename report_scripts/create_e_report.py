import sys
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import gspread, time

TOKEN_PATH = Path('config/oauth_token.json')
SCOPES = ['https://www.googleapis.com/auth/spreadsheets','https://www.googleapis.com/auth/drive']
creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
gc = gspread.authorize(creds)

DST_ID = '1jwynjel06dgzjE-X6tAMJbWuGSKGmZ_kPodMt6cfj2E'
wb = gc.open_by_key(DST_ID)

def rgb(r, g, b):
    return {'red': r/255, 'green': g/255, 'blue': b/255}

# ── 색상 ──────────────────────────────────────
C_NAVY    = rgb(30, 70, 120)    # 진파랑 - 대제목
C_BLUE    = rgb(70, 130, 180)   # 중간파랑 - 섹션헤더
C_LBLUE   = rgb(210, 228, 248)  # 연하늘 - 서브섹션
C_WHITE   = rgb(255, 255, 255)
C_DARK    = rgb(30, 30, 30)
C_GRAY    = rgb(245, 245, 245)  # 연회색 - 짝수행

def make_fmt(bg, fg=None, bold=False, size=10, italic=False, align='LEFT', valign='MIDDLE', wrap=True):
    return {
        'backgroundColor': bg,
        'textFormat': {
            'bold': bold,
            'italic': italic,
            'fontSize': size,
            'foregroundColor': fg or C_DARK,
        },
        'horizontalAlignment': align,
        'verticalAlignment': valign,
        'wrapStrategy': 'WRAP' if wrap else 'CLIP',
    }

def cell_req(sid, r, c, val, fmt, span_cols=None):
    req = {
        'updateCells': {
            'rows': [{'values': [{'userEnteredValue': {'stringValue': str(val)},
                                  'userEnteredFormat': fmt}]}],
            'fields': 'userEnteredValue,userEnteredFormat',
            'range': {'sheetId': sid, 'startRowIndex': r, 'endRowIndex': r+1,
                      'startColumnIndex': c, 'endColumnIndex': c+1}
        }
    }
    return req

def merge_req(sid, r, c1, c2):
    return {'mergeCells': {
        'range': {'sheetId': sid, 'startRowIndex': r, 'endRowIndex': r+1,
                  'startColumnIndex': c1, 'endColumnIndex': c2},
        'mergeType': 'MERGE_ALL'
    }}

def col_width(sid, c, px):
    return {'updateDimensionProperties': {
        'range': {'sheetId': sid, 'dimension': 'COLUMNS', 'startIndex': c, 'endIndex': c+1},
        'properties': {'pixelSize': px}, 'fields': 'pixelSize'}}

def row_height(sid, r, px):
    return {'updateDimensionProperties': {
        'range': {'sheetId': sid, 'dimension': 'ROWS', 'startIndex': r, 'endIndex': r+1},
        'properties': {'pixelSize': px}, 'fields': 'pixelSize'}}

def freeze_req(sid, rows=1):
    return {'updateSheetProperties': {
        'properties': {'sheetId': sid,
                       'gridProperties': {'frozenRowCount': rows}},
        'fields': 'gridProperties.frozenRowCount'}}

# ─────────────────────────────────────────────────────────
# 행 정의: (type, text)
# type: TITLE | TEAM | SEC | SUBSEC | BULLET | BLANK
# ─────────────────────────────────────────────────────────

ROWS_H1 = [
# ── 타이틀 ──
('TITLE',  '■ 미디어본부 - 미디어 채널실 리뷰 / 채널2팀 (유승환)'),
('TEAM',   '팀원(5명): 유승환 팀장(13년차) · 이선애 책임(11년차) · 김나은 선임(3년차) · 박현 선임(4년차) · 남경희 선임(상반기 IPP)'),
('BLANK',  ''),

# ── SECTION 1 ──
('SEC',    '# 현재 팀의 핵심 역할'),
('BULLET', '• [매체 파트너십 단일 창구]  메타·토스·네이버·당근·크리테오·컬리 등 주요 RTB 매체 공식 파트너 창구 운영. 25년 네이버 DA 판매 1위(파트너사 기준) · GFA YoY +5.5% · 프리미어 파트너사 자격 유지'),
('BULLET', '• [인센티브 실적]  25년 네이버 4.65억(매출목표 9·11월 달성 + ADVoost쇼핑 5,571만 + 스크린 416만) / 26년 ADVoost 최대 2,000만원/월 · 파트너 부스트 2Q 달성률 50.6%(가이던스 48.4% 상회) / 토스 25년 연 인센티브 1.21억'),
('BULLET', '• [파트너십 성과]  메타 2025 Agency First Game Changer 수상(W컨셉 협력광고·세미나 공동 기획 주도) / 당근 YoY +134.5%(자력 +45.4%, 127억) / 메타 26년 1Q 취급고 YoY +13.7%(인보이스 +19.2%)'),
('BULLET', '• [영업지원]  메타 POC 1차 창구(플래너 직커뮤 불가) · SA 운영 26년 24→28개 (+17%) · 제안서·컨설팅·온보딩 지속 / 워크서포트 주당 30~63건 처리'),
('BULLET', '• [신규 매출원]  W컨셉 협력광고 49→83 브랜드 +69% 성장(25년 1.17억→26년 1Q 1.21억) / 토스 세일즈커넥트 참여·LOT 족보 제작 / NOTE 플랫폼(스레드·협력광고·RTA 벤치마크) 고도화 배포 예정'),
('BULLET', '• [운영 인프라]  대대행사 14개사 등록 완료 / PA퀵윈 5월 11건 확정 / SA 리포트 자동화 솔루션 개발 중(데이터킷·GFA API) / 네이버 Expert 프로그램 4개사 선정(금성침대·토리든·클라렌·KGM)'),
('BLANK',  ''),

# ── SECTION 2 ──
('SEC',    '# 주요 매체 관리/운영 및 이슈 사항 (상반기)'),
('SUBSEC', '[네이버]'),
('BULLET', '• [25년 연간]  취급고 1,419억(NOSP 932억 + GFA 487억 + SA 203억) / GFA YoY +5.5% / 인센티브 4.65억 확보'),
('BULLET', '• [26년 현황]  1Q 취급고 297억(YoY -24.7% — 시장 전반 둔화) / SA 25억(YoY -55% — 테무 직영 이관 기저효과) / 4월 취급고 107.5억(NOSP 52.4 + GFA 47.2 + SA 8.0) / ADVoost 최대 2,000만원/월 달성 · 파트너 부스트 2Q 50.6%'),
('BULLET', '• [SA 운영]  26년 3월 기준 19개사 → 4월 28개사 / PA퀵윈 25년 평균 2~3개 → 26년 8~9개로 확대 / Expert 프로그램 4개사 킥오프(4/21~22) / SA 리포트 자동화 3Q 내 배포 목표'),
('BULLET', '• [이슈]  NOSP 대형광고주(삼성·넥슨·LG·샤넬) 의존도 집중 / 영업조직 SA 이해도 편차 → DA+SA 복합 제안 역량 강화 교육 체계 필요 / GFA API 전체 호출 네이버 측 확인 중(리포트 자동화 연동 대기)'),
('BLANK',  ''),
('SUBSEC', '[메타]'),
('BULLET', '• [25년]  취급고(대행사월) 70,982백만원(YoY -8.8% / 자력 +6.7%) / 광고계정 288→348개(+20.8%) / Agency First Game Changer 수상 / 협력광고 취급고 56.4억(YoY +173%, W컨셉 기여) / 성장지원금(GBP) 미달성'),
('BULLET', '• [26년 1Q]  취급고 YoY +13.7% / 인보이스 +19.2% / 광고계정 평균 287개 / 4월 인보이스 46.6억(YoY +4.1%) / W컨셉 협력광고 1Q 1.21억(YoY +56%) / Top광고주: 샤넬·문화체육관광부·월드비전'),
('BULLET', '• [이슈]  GBP 성장지원금 25년 미달성(22·23년 각 31억·28억 수령) → 26년 회복 시급 / W컨셉 협업서 2026.9.21 만료 → 연장 의사결정 필요 / ELCA 협력광고 비중 36.7% 집중 — 이탈 시 구조 타격 / 메타 직커뮤니케이션 불가 정책 → POC 리소스 집중 지속'),
('BLANK',  ''),
('SUBSEC', '[토스]'),
('BULLET', '• [25년]  취급고 4,866백만원(YoY +28%) / 연 인센티브 1.21억(상반기 6,011만 + 3Q 3,570만 + 4Q 2,500만) / Top광고주: KT(8.6%)·BHC(6.5%)·LG전자(4.7%)'),
('BULLET', '• [26년 1Q]  1.21억(YoY +31.5%) — 2구간(5%) 달성·추가 6,049만 확보 / 4월 정산 7.43억(수기정산 1.02억 포함) / 2Q 인센티브 구간: 14.3억(1구간·2%) ~ 16.7억(3구간·10%)'),
('BULLET', '• [이슈]  광고주 직영업(CP 직접 접촉)으로 광고팀·광고주 간 불편 간헐 발생 / 3구간 정액 폐지·18억 신구간 신설 협의 중 → 인센티브 구조 변화 예상 / 단독 협업 리포트·Buy & Play 신규 상품 기획 진행 중'),
('BLANK',  ''),
('SUBSEC', '[기타 매체]'),
('BULLET', '• [당근]  25년 취급고 127.2억(YoY +134.5% / TEMU 포함, 자력 78.8억 +45.4%) / 광고계정 52→104개(+100%) / 네이티브 광고 94%(이미지 71%+세로영상 23%) / 26년 R.U.N 프로젝트 추진(Reach·Upsell·Navigation)'),
('BULLET', '• [크리테오·컬리]  크리테오 인보이스 정산 안정화 · 기존 광고주 안정 운영 / 컬리 26년 프로모션 영업 활성화 지원금 공지 완료 · 커머스 광고주 확장 추진'),
('BULLET', '• [넷플릭스·티빙]  25년 넷플릭스 취급고 165억·인센티브 약 14억 / 2월 디지털방송팀으로 이관 완료'),
('BULLET', '• [신규 탐색]  틱톡 Deal Agency 계약·3월 취급고 4.7억(YoY +46.5%) / 쿠팡 Brand AD 설명회·배달의민족 미팅·더현대하이 탐색 진행 중'),
('BULLET', '• [공통 이슈]  신규 광고주 쿠폰 집행 시 수수료 미수취 → 세일즈 유인 부족 / 매출 수동 트래킹 → 자동 대시보드 도입 시급'),
('BLANK',  ''),

# ── SECTION 3 ──
('SEC',    '# 팀 내 담당자별 핵심 목표 및 진행 사항'),
('SUBSEC', '[이선애]'),
('BULLET', '• ✔ 메타 Agency First Game Changer 수상 주도 (W컨셉 협력광고 파트너십·세미나 기획)'),
('BULLET', '• ✔ W컨셉 협력광고 49→83 브랜드 성장 달성'),
('BULLET', '• 진행 중: 26년 MAFA 어워즈 수상 목표 (W컨셉 온사이트+협력광고 시너지 사례 기획)'),
('BULLET', '• 진행 중: ELCA 이탈 대비 나스미디어 메타 경쟁력 자료 기획 / 토스 원시트 제작'),
('SUBSEC', '[김나은]'),
('BULLET', '• 진행 중: NOTE 플랫폼 고도화(스레드·협력광고·RTA 벤치마크 기능 4~5월 배포 예정)'),
('BULLET', '• 진행 중: 워크서포트 1차 창구 운영(주당 30~63건) / 미디어 애드 이슈 리포트 월별 제작·배포'),
('BULLET', '• ✔ 토스 세일즈커넥트 참여·LOT 족보 제작 완료'),
('BULLET', '• 진행 중: 2Q 인센티브(14.3억~16.7억) 달성률 주단위 트래킹'),
('SUBSEC', '[박현]'),
('BULLET', '• ✔ Expert 프로그램 4개사 선정 완료(금성침대·토리든·클라렌·KGM / 4/21~22 킥오프)'),
('BULLET', '• 진행 중: SA 28개 광고주 운영·컨설팅·제안서 지원 (목표 35개)'),
('BULLET', '• 진행 중: ADVoost 쇼핑 월 최대 2,000만원 추가 수수료 달성 유지'),
('BULLET', '• 진행 중: SA 리포트 자동화 솔루션 개발(데이터킷·GFA API 연동 / 3Q 배포 목표)'),
('BULLET', '• 진행 중: SA 5월 예상 추가 수수료 약 950만원'),
]

ROWS_H2 = [
# ── 타이틀 ──
('TITLE',  '■ 미디어본부 - 미디어 채널실 하반기 플랜 / 채널2팀 (유승환)'),
('TEAM',   '팀원(5명): 유승환 팀장(13년차) · 이선애 책임(11년차) · 김나은 선임(3년차) · 박현 선임(4년차) · 남경희 선임(상반기 IPP)'),
('BLANK',  ''),

# ── SECTION 1 ──
('SEC',    '# 우선 추진 과제 (하반기)'),
('SUBSEC', '[네이버] ① DA 1위·프리미어 파트너사 지위 강화 + GFA/SA 성장'),
('BULLET', '• 프리미어 파트너사 유지: 파트너 부스트 3Q 타겟 달성 · PA퀵윈 월별 신청 확대 / ADVoost 쇼핑 2,000만원/월 유지 (25년 연 5,571만 → 26년 연 2억+ 목표)'),
('BULLET', '• GFA 월 47억→50억 목표 / 커머스 빅광고주(패션·화장품·가전) 신규 수주 — 26년 1Q 취급고 YoY -24.7% 시장 둔화 국면에서 점유율 방어 우선'),
('BULLET', '• SA 운영 28개→35개 목표 / DA+SA 통합 분석 서비스 차별화 / 리포트 자동화 솔루션 3Q 내 배포 · 플래너 직접 활용 체계 완성'),
('BLANK',  ''),
('SUBSEC', '[메타] ② 어워즈(MAFA) 수상 + 성장 모멘텀 유지'),
('BULLET', '• W컨셉 온사이트+협력광고 시너지 사례로 4Q Agency First Awards 도전 / 협업서 9/21 만료 전 연장 결정 (상위 레벨 의사결정 필요)'),
('BULLET', '• 26년 1Q YoY +13.7% 성장 기조 유지 / ELCA 이탈 대비 신규 협력광고 핵심 광고주 발굴 / GBP 성장지원금 25년 미달성 → 26년 Target 달성 집중'),
('BULLET', '• 글로벌 캠페인 협업 확대(젠틀몬스터·넥슨·스레드) / AI Advantage+ 적용 확대로 광고주 성과 개선'),
('BLANK',  ''),
('SUBSEC', '[토스] ③ LOT 인센티브 최대화 + 단독 협업 확대'),
('BULLET', '• 2Q 인센티브 목표(14.3억~16.7억) 달성 추진 / 3구간 폐지·18억 신구간 협의 결과 최적 대응 / 3Q 목표 프로모션 참여'),
('BULLET', '• 단독 협업 리포트 발행 확정 → 영업본부 대상 토스 활용 가이드라인 공식화 / Buy & Play at Toss 신규 상품 집행 확대 지원'),
('BULLET', '• 세일즈커넥트 수료 후 내부 세일즈팀 대상 역량강화 교육 / TEP 파트너사 상위 등급 목표'),
('BLANK',  ''),
('SUBSEC', '[크리테오·당근·컬리] 버티컬 매체 성장 기회 포착'),
('BULLET', '• 당근: QBR 기반 파이프라인 강화 / 자력 성장 +45.4% 기조 유지 / 광고계정 104개→120개+ 목표'),
('BULLET', '• 컬리: 커머스 광고주 확장 / 쿠팡·배달의민족·더현대하이 신규 파트너십 기반 마련'),
('BULLET', '• 크리테오: 인센티브 프로모션 참여 · ChatGPT 광고 검토 · 신규 광고주 발굴'),
('BLANK',  ''),

# ── SECTION 2 ──
('SEC',    '# 팀 내 담당자별 핵심 과제 (하반기)'),
('SUBSEC', '[이선애]'),
('BULLET', '• Agency First Awards 수상 도전 — W컨셉 온사이트+협력광고 시너지 사례 완성·출품'),
('BULLET', '• 26년 나스X메타 단독 세미나 기획·운영 (25년 Game Changer 수상 후속)'),
('BULLET', '• ELCA 이탈 대비 나스미디어 메타 경쟁력 자료 기획·제작 (영업본부 활용)'),
('BULLET', '• 토스 단독 협업 리포트 발행 기여 / 원시트 제안 자료 제작·배포'),
('SUBSEC', '[김나은]'),
('BULLET', '• 메타 NOTE 플랫폼 하반기 추가 기능 기획·배포 / 이슈 리포트 품질 강화'),
('BULLET', '• 토스 LOT 인센티브 달성 / 세일즈커넥트 수료 후 내부 교육 실시'),
('BULLET', '• GBP 성장지원금 Target 달성 기여 / 메타 광고계정 350개+ 유지'),
('BULLET', '• 당근·크리테오 정산 안정화 / 신규 매체 온보딩 지원 / SA 리포트 자동화 협업(박현)'),
('SUBSEC', '[박현]'),
('BULLET', '• SA 리포트 자동화 솔루션 3Q 내 배포 완료 (GFA API 연동 포함) / SA 운영 35개 목표'),
('BULLET', '• DA+SA 통합 분석 서비스 차별화 자료 기획 → 영업본부 공유'),
('BULLET', '• 매출 트래킹 자동 대시보드 구축 (매체별·시간대별 전일 소진 자동 집계)'),
('BLANK',  ''),

# ── SECTION 3 ──
('SEC',    '# 실장 또는 본부장 지원이 필요한 사항'),
('SUBSEC', '[매체사 상위 레벨 협의]'),
('BULLET', '• 메타 코리아 — 허진영 이사 부재 이후 컨택 빈도 감소 → 정기 관계 재개 선제 요청 (GBP 달성 지원 포함)'),
('BULLET', '• W컨셉 협력광고 협업서 2026.9.21 만료 → 상위 레벨 연장 의사결정 필요 (Agency First 전략 자산으로 관리)'),
('BULLET', '• 토스 CPT 등 신규 상품 나스미디어 우선 제공 기회 협의 / 네이버 프리미어 파트너 써밋 실장·임원급 참여 확대(라운딩·만찬)'),
('BLANK',  ''),
('SUBSEC', '[영업본부 협업 구조]'),
('BULLET', '• 채널2팀 파트너십 업무(프리미어 파트너 지위·인센티브 4.65억·Game Changer 수상)가 나스미디어 영업 경쟁력 근거임을 영업본부 전체에 공식 어필 필요'),
('BULLET', '• DA+SA 통합 제안 표준화: 영업본부 전체가 네이버 SA+DA 복합 수주 가능하도록 제안 Kit 배포·정기 교육'),
('BLANK',  ''),
('SUBSEC', '[인력·운영체계]'),
('BULLET', '• 신규 인원 충원 요청 (1인당 5개+ 매체 담당 → 전략 집중도 저하 우려)'),
('BULLET', '• 매출 트래킹 자동 대시보드 도입 / 반복 문의 처리 워크서포트 가이드 체계화 지원 필요'),
]


def build_report_sheet(title, rows_data):
    for ws in wb.worksheets():
        if ws.title == title:
            wb.del_worksheet(ws)
            time.sleep(1)

    ws = wb.add_worksheet(title=title, rows=len(rows_data)+5, cols=2)
    sid = ws.id
    reqs = []

    # 컬럼 너비: A=900px, B=1px(보조)
    reqs.append(col_width(sid, 0, 900))
    reqs.append(col_width(sid, 1, 1))

    FMT = {
        'TITLE':  make_fmt(C_NAVY,  fg=C_WHITE, bold=True,  size=12, valign='MIDDLE'),
        'TEAM':   make_fmt(C_LBLUE, fg=C_DARK,  bold=False, size=10, valign='MIDDLE'),
        'SEC':    make_fmt(C_BLUE,  fg=C_WHITE, bold=True,  size=11, valign='MIDDLE'),
        'SUBSEC': make_fmt(C_LBLUE, fg=C_NAVY,  bold=True,  size=10, valign='MIDDLE'),
        'BULLET': make_fmt(C_WHITE, fg=C_DARK,  bold=False, size=10, valign='TOP'),
        'BLANK':  make_fmt(C_WHITE, fg=C_WHITE, bold=False, size=6,  valign='TOP'),
    }
    HEIGHT = {
        'TITLE': 36, 'TEAM': 26, 'SEC': 30, 'SUBSEC': 26,
        'BULLET': 0,  # 0 = auto (행 높이 지정 안 함 → 내용에 맞게)
        'BLANK': 8,
    }

    for ri, (rtype, text) in enumerate(rows_data, start=0):
        fmt = FMT[rtype]
        h = HEIGHT[rtype]
        if h > 0:
            reqs.append(row_height(sid, ri, h))
        reqs.append(cell_req(sid, ri, 0, text, fmt))

    batch_size = 200
    for i in range(0, len(reqs), batch_size):
        wb.batch_update({'requests': reqs[i:i+batch_size]})
        time.sleep(0.5)
    print(f"  ✓ [{title}] 완료 ({len(rows_data)}행)")
    return sid


print("[E] 상반기 보고서 초안 생성 중...")
build_report_sheet('[E] 채널2팀-상반기리뷰(초안)', ROWS_H1)

print("[E] 하반기 보고서 초안 생성 중...")
build_report_sheet('[E] 채널2팀-하반기플랜(초안)', ROWS_H2)

print("\n완료!")
print(f"  https://docs.google.com/spreadsheets/d/{DST_ID}")
