# X(트위터) Ads 일단위 매출 트래킹

최종 갱신 2026-10-06

## 현재 운영 구조 (2026-10 전환)

**스크립트**: `agent/scan_x_ads_daily.py`
**스케줄러**: `XAdsDailyScan` — 매일 04:00, `agent/run_x_ads_daily.bat`
**로그**: `agent/x_ads_daily_log.txt`

### 대상 시트가 10월부터 바뀌었다

```python
SHEET_ID = "1V-gAyGok-H29rzXtvpE5UTFjhh-DYNbL6SW74dBrwNs"   # 신규 전용 스프레드시트
def x_tab_name(d):
    return f"{d.month}월_X일단위 매출 트래킹(화이트리스트 적용)"
```

- **9월까지**는 "26년 주간회의록" 스프레드시트의 `X일단위 매출 트래킹` / `...(화이트리스트 적용)` 두 탭. 과거 조회할 때만 본다.
- **10월부터**는 위 신규 파일의 **월별 탭(1개월 = 1탭)**. 원본/화이트리스트 2탭 병행 운영은 종료, **화이트리스트 적용 탭 하나만** 쓴다.
- 날짜 열이 **1~31일 고정 그리드로 미리 깔려 있다**(6행 헤더). 열을 추가하는 게 아니라 `first_date_col_idx1 + d.day - 1`로 해당 칸을 직접 계산해 쓴다(`update_fixed_grid_tab()`).
- **수식은 코드가 쓰지 않는다** — 템플릿 탭에 이미 있다.

### 다음 달 탭 자동 생성 — `ensure_month_tab()`

팀장 지시: *"11월 탭은 미리 만들지 말고 11월 시작할 때, 10월 탭 바로 왼쪽에."*

1. 전월 탭을 `duplicateSheet` + `insertSheetIndex = 전월탭_index` → 새 달이 **왼쪽**에 붙는다(최신 월이 맨 앞)
2. `_reset_month_tab_contents()`로 B:E 계정 데이터 + 날짜 값 범위 클리어, 6행 날짜 헤더와 B4 제목을 새 달 기준으로 재작성
3. **`appendDimension`을 먼저 호출해 그리드를 `first_date + 30`까지 넓힌다** — 안 하면 `Range AM6 exceeds grid limits`(2026-10-04 실제 발생: 38열 시트에 35개 날짜열을 쓰려다 반쪽 생성된 탭을 지우고 재시도). 날짜 루프는 **그 달 실일수(최대 31일)로 캡**.

→ 11월 탭은 **11/2 새벽 실행 때 자동 생성**된다. 미리 만들지 말 것(한 번 미리 만들었다가 팀장이 지웠음).

### 월 경계 버그 수정 (가장 중요)

```python
today = date.today()
yesterday = today - timedelta(days=1)
month_start = yesterday.replace(day=1)   # "어제" 기준 월
recheck_start = max(month_start, yesterday - timedelta(days=RECHECK_DAYS - 1))
```

기존 코드는 `month_start = today.replace(day=1)` + **매월 1일엔 실행을 스킵하는 가드**였다. 새벽 4시 작업이 전날(=전월 마지막 날) 데이터를 쓰는 구조이므로 이 조합은 **매월 마지막 날 매출을 영구 유실**시킨다(9/30이 그래서 비어 있었고 팀장이 직접 채웠다).

**이 라인은 절대 `today` 기준으로 되돌리지 말 것.**

### 계정 목록 자동 갱신 — `refresh_accounts_list()`

`x_ads_accounts.json`은 2026-09-08 스냅샷(547개)으로 **고정돼 있었다** → 그 뒤 새로 접근권한이 생긴 계정은 영구히 스캔 대상에서 빠지는 구조(팀장 질문 *"계정이 더 늘어나지는 않는 건가?"*로 발견).

수정: 매 실행 시 `https://ads-api.x.com/12/accounts`를 페이지네이션 전수 조회해 파일을 갱신하고, 이전 목록과 diff해서 `[신규 접근권한]` 라인을 로그에 남긴다. → **신규 집행 계정도 다음날 자동 반영.**

### 수동 편집 보존 원칙 (여전히 유효)

여러 명이 같은 시트를 수동 편집한다(참조명, 계정명 뒤 대행사 표기, 계정명 색, O/X 수동 조정, 예약형 집계박스).

- **클리어 금지** — 과거에 `A4:AZ1000`을 매일 clear하고 재작성해서 수동 편집이 반복 소실된 사고가 있었다
- **총액순 재정렬 금지** — 기존 순서 그대로 누적
- 신규 계정은 각 블록 **맨 밑에 추가**
- 헤더·숫자값은 `RAW`, 수식만 `USER_ENTERED`로 **분리 호출** — 같이 쓰면 날짜 문자열("09/03")이 날짜 시리얼로 자동 파싱된다

## API 함정 (전부 실측 확인)

1. **`entity=ACCOUNT`는 stats에서 지원 안 됨** — 에러 없이 `"metrics": {}`만 반환. **반드시 `entity=FUNDING_INSTRUMENT`**. 계정별로 `GET /12/accounts/{id}/funding_instruments`에서 `entity_status=ACTIVE and able_to_fund=true`인 것만 걸러 그 id로 조회.
2. **DAY granularity는 계정 로컬 타임존 자정에 정확히 맞춰야 함** — UTC 자정 그대로 넣으면 `INVALID_TIME_WINDOW`. 계정 `timezone` 필드로 로컬 자정 → UTC 변환(`zoneinfo`).
3. **한 번 호출에 최대 7일+1시간**(granularity 무관).
4. **Rate limit 250회/15분** (`x-rate-limit-remaining` 헤더).
5. **한 계정에 통화가 다른 결제수단이 여러 개 있을 수 있다** — 다른 통화의 micro 값을 그냥 더하면 틀린다. 처음부터 `by_currency: {통화: {날짜: micro}}` 구조로 분리 저장.
6. **`updated_at`이 최근이어도 실제 집행과 무관** — 활성 여부는 `able_to_fund`로만 판단.
7. **일반 X API(v2)와 Ads API는 완전 별개.** 이 앱은 v2는 Project 미등록(403 client-not-enrolled), Ads API는 정상. 추가 구독료 없음.

## 화이트리스트 (인보이스 기준 95개)

API 접근 가능 계정 547개는 **"우리가 청구하는 계정"과 다르다.** X Ads 데이터 모델에 인보이스 책임을 나타내는 필드가 없다(funding instrument description에 "Nasmedia"가 있어도 신뢰 불가 — 반례 확인됨).

→ 실제 인보이스 마스터 파일(`\\121.134.243.150\...\10. X 코리아\1. 매출관리.인보이스\#Invoice\2026\`)을 win32com으로 읽어 IO Name 토큰 매칭으로 **92개 확정**, 이후 X가 직접 준 Parent별 실매출표와 대조해 SHOWBOX·PALDO 추가해 **95개**.

저장: `C:\Users\Administrator\Desktop\00. 클로드코드 생성물\X API관련\x_invoiced_whitelist_2026_1to8.json` (+ 사람용 `.xlsx` 2시트)

**접근권한 자체가 없는 사각지대 3개**(API로 원천적으로 못 잡음, 기록만): Goodai Global Inc.(Jul~Sep 11,309,226원), LG Corporation(Aug 14,000,000원), NAVER WEBTOON Ltd.(Aug 420,000원). LOTTE Corp.(598,892원)는 계열 계정이 여럿이라 특정 불가.

**토큰 매칭의 함정**: 광고주명이 범용적이면(예: "Hyundai Motor Company") 여러 계정에 점수가 오염돼 틀린 계정이 최고점을 받는다 — 2건 실제 오류 발견·수정.

## 검증 기록

- **2026-08 정확도**: KRW 361,428,370원 + USD 62,991.81 → 환율 1,300~1,400 가정 시 443.3M~449.6M원. 팀장 시트 8월 취급고 451,104,680원과 **98~99.7% 일치**.
- **2026-10-01 실측**: 매출 발생 계정 **16개, 전부 KRW**(USD 0개). 10월은 새 출발이라 계정 수가 적은 게 정상.

## 미해결

- **포트폴리오 CSV vs 시트 차이**(2026-09-21): 7일 합계 CSV 51,394,968원 vs 시트 44,912,089원(+14.4%). **일별로 방향이 뒤바뀜**(9/14~18은 CSV가 크고, 9/19~20은 시트가 큼) → 계정 누락이 아니라 **날짜 집계 타임존/경계 차이**로 추정하나 확정 못 함. 판단 기준: *방향이 한쪽으로 일관되면 계정 누락, 날짜마다 뒤바뀌면 타임존 문제.*
- **예약형(Takeover) 비교 박스 리스크**: 팀장이 만든 수식이 하드코딩 절대 행범위(`F45:F56` 등)를 쓴다. USD 계정이 늘어 상한을 넘으면 조용히 누락된다. 손대지 않기로 했으니, USD 계정 증가 얘기가 나오면 이 리스크를 먼저 상기시킬 것.
- 9월 이후 인보이스가 나오면 화이트리스트를 1~9월로 확장해야 한다(미갱신 시 신규 계약 계정이 계속 X로 표시됨).
