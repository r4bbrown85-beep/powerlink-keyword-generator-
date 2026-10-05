# 미디어채널팀 업무 자동화 프로젝트

## 담당자
- 유승환 (미디어채널팀 팀장, 나스미디어) — 2026-08-10 채널1팀·채널2팀 통합으로 팀명 변경

---

## 📌 작업 로그 — 이어받을 때 먼저 읽을 곳

진행 중인 작업의 상세 기록(현재 구조·검증결과·이어서 할 일)은 **`docs\작업로그\`** 에 있다.
**"지난번에 하던 것 이어서" / "그때 논의한 방식대로" 류 요청이 오면 `docs\작업로그\README.md`부터 읽는다.**

| 문서 | 작업 |
|---|---|
| `네이버_일단위매출_목표시뮬레이션.md` | 4213_실적상세 처리, 월 목표 → 일별 시나리오 (`agent/naver_target_simulator.py`) |
| `카카오_NOTE_벤치마크.md` | 카카오 로우데이터 → NOTE 업로드 CSV 변환 |
| `X_일단위매출_트래킹.md` | X Ads API 일단위 스캔 (`agent/scan_x_ads_daily.py`, 매일 04:00) |
| `경영KPI_3Q.md` | 분기 KPI PPTX 작성 규격·함정 |
| `기타_인보이스_환경이슈.md` | 애플/구글 인보이스, 탐색기 크래시 |

README에 **공통 전제**(DRM win32com, OAuth 토큰 scopes 생략, 장시간 작업은 PowerShell Start-Process, 한글 인코딩, raw string)가 정리돼 있으니 환경 함정을 재발견하지 말 것.

---

## 핵심 작업: 주간 회의록 정리

매주 금요일 오전 "회의록 정리해줘" 요청 시 실행.

### 소스 (반드시 이 시트를 직접 읽어야 함)
- **팀 주간 회의록 Google Sheet**
  - URL: https://docs.google.com/spreadsheets/d/1ZXkhrtGGFMCVzEP-PEBqra7mAcY0ob8FL_jWXL5KWIs/edit?gid=2011819062#gid=2011819062
  - 시트명: `26년 주간회의록`
  - API 인증: `config/briefing_token.json`
  - ⚠️ 2026-08-10 채널1·2팀 통합(미디어채널팀)으로 매체 섹션 순서 갱신: 구글 → 네이버 → 메타 → 카카오 → 토스 → 오픈AI → 크리테오 → (X·쿠팡 등 그 주 있으면) → 미팅&설명회. 상세는 `회의록_변환_가이드.md` 참고

### 출력 파일 (2026-08-23 개편: 실장_회의록 시트 폐지)
- 저장 위치: `C:\Users\Administrator\Desktop\0.팀 운영 관련 업무\주간 회의록 관련\`
- 파일명 예시: `회의록정리_0626.xlsx` (날짜는 해당 주차 날짜)
- **2개 시트만: 본부_회의록 / 전체_원본정리** (실장_회의록 시트는 더 이상 만들지 않음)

### 붙여넣기 대상
| 시트 | 대상 Google Sheet | 탭 |
|------|-----------------|-----|
| 본부_회의록 | 미디어본부 Worksheet | 주간회의 탭 → 미디어채널팀 섹션 |

**실장_회의록(실장 주간회의록 미디어채널실)은 더 이상 팀장이 직접 작성하지 않는다.** 실장님이 상단 취급고 표는 직접 채우고, 하단 Media Issues/Issue Report는 본부_회의록을 참고해 실장님이 직접 작성하는 구조로 바뀜(2026-08-23 확인). 팀장/Claude 작업 범위에서 제외.

### 작업 원칙
1. **반드시 팀 주간 회의록 시트를 Sheets API로 직접 읽어 실제 데이터 기반으로 작성** (추정/창작 금지)
2. 팀장(유승환)이 선택적으로 복붙만 하면 되도록 **최대한 많은 내용** 포함
3. **전 매체 빠짐없이** 포함 — 이번주 이슈가 없어 보이는 매체도 시트에 있으면 포함
4. 기존에 썼던 톤·형태에 맞춰 정리

---

## 서식 기준 (0621 파일 실측값)

### 공통
- 폰트 크기: **11pt**
- 색상 코드:
  - 헤더 배경: `4F81BD` (진파랑)
  - 팀/채널 셀: `BDD7EE` (연파랑)
  - 항목/매체 셀: `DEEAF1` (연하늘)
  - 이번주 계획: `FFFF99` (노란)
- 행 높이: 단일행 16.5 / 2줄행 33.0 / 헤더행 18.0

### 본부_회의록 열 넓이
| A(날짜) | B(팀) | C(구분) | D(항목) | E(내용) | F(추가논의) |
|---------|-------|---------|---------|---------|------------|
| 7 | 10 | 10 | 15 | 62 | 32 |

### 전체_원본정리 열 넓이
| A(매체) | B(구분) | C(내용) |
|---------|---------|---------|
| 12 | 10 | 95 |

---

## 실행 스크립트
- ⚠️ `C:\Users\Administrator\AppData\Local\Temp\make_minutes_v5.py`는 **재사용 템플릿이 아니다** — 2026-06-27에 06/29 주차 전용으로 하드코딩해서 만든 1회성 산출물(팀명 "미디어채널2팀", 3시트 구조 포함해 그 주 데이터가 그대로 박혀 있음). 그대로 재실행하거나 복사해서 쓰지 말 것. 매주 새로 스크립트를 짜거나 win32com/openpyxl로 직접 작성하되, **가이드(`회의록_변환_가이드.md`)의 최신 서식·구조 규칙을 그때그때 반영**해서 만든다(2026-08-23부터 2시트: 본부_회의록/전체_원본정리).
- DRM 파일 읽기: `win32com.client.Dispatch("Excel.Application")` 사용 (사내 DRM 투명 복호화)
- Google Sheets 읽기: `google-auth`, `google-api-python-client` 라이브러리 사용

---

## 아침 브리핑 자동화
- 스크립트: `briefing/morning_briefing.py`
- 발송 시간: 매일 오전 07:05
- 인증 토큰: `config/briefing_token.json`

---

## 매체 매출 예측 / 목표 달성률 (`agent/revenue_forecast.py`)

매체별 "이번 달 얼마 나올까", "목표 달성되나" 질문에 쓰는 공용 모듈.
2026-09-27에 네이버 GFA 54개월(1,640일) 실측으로 설계·검증했다.

```python
from agent.revenue_forecast import RevenueForecaster, load_holidays, load_naver_series, format_report
fc = RevenueForecaster(load_naver_series("GFA"), load_holidays())
print(format_report(fc.forecast_month_end("2026-09", target=3_237_000_000)))
print(RevenueForecaster.summarize_backtest(fc.backtest()))   # 새 매체엔 이 검증 먼저
```

- 데이터 캐시: `data/cache/forecast/`(gitignore 대상). 없으면 시트에서 자동 재수집.
- 새 매체는 `pd.Series(index=날짜, value=일매출)`만 만들어 넘기면 된다.
- **검증 없이 결과만 보고하지 말 것** — `backtest()`로 그 매체에서도 방법 선택이 맞는지 먼저 확인.
- 상세 근거·함정은 메모리 `project_media_revenue_forecasting.md` 참고.

## 파워링크 키워드 제안서 앱 배포 규칙

이 프로젝트의 앱은 **Streamlit Cloud**에 배포되어 있음.
- URL: `https://km5huupfnn4tfrurc8fnxy.streamlit.app/`
- 팀원들이 이 링크로 접속해서 사용 중

**코드 수정 후 반드시 GitHub push** — push해야 Streamlit Cloud에 자동 반영됨.
로컬 파일 수정만으로는 앱에 반영되지 않음.

작업 완료 시 항상:
```
git add <수정된 파일들>
git commit -m "..."
git push origin main
```

---

## 주의사항
- 회의록 내용은 **절대 추정/창작하지 말 것** — 반드시 팀 시트 원본 데이터 사용
- DRM 보호 엑셀 파일은 openpyxl로 직접 열기 불가 → win32com 사용
- 기존 파일 열린 상태에서 저장 시 PermissionError 발생 → 파일명 변경하여 저장
