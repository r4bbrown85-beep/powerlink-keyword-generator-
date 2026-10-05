# 작업 로그 색인

미디어채널팀(유승환 팀장) 업무 자동화 작업의 상세 기록. **새 터미널/새 세션에서 "지난번에 하던 것 이어서" 류 요청이 오면 이 폴더부터 읽는다.**

| 문서 | 다루는 작업 | 최종 갱신 |
|---|---|---|
| [네이버_일단위매출_목표시뮬레이션.md](네이버_일단위매출_목표시뮬레이션.md) | 4213_실적상세 CSV 처리, 시트 업데이트, 월 목표 → 일별 시나리오 시뮬레이터 | 2026-10-06 |
| [카카오_NOTE_벤치마크.md](카카오_NOTE_벤치마크.md) | 카카오 월별 로우데이터 → NOTE 플랫폼 업로드 CSV 변환 | 2026-10-06 |
| [X_일단위매출_트래킹.md](X_일단위매출_트래킹.md) | X Ads API 일단위 스캔 자동화, 월별 탭 구조 | 2026-10-06 |
| [경영KPI_3Q.md](경영KPI_3Q.md) | 분기 KPI 실적/추진계획 PPTX 작성 | 2026-10-06 |
| [기타_인보이스_환경이슈.md](기타_인보이스_환경이슈.md) | 애플 인보이스, 구글 세금계산서, 탐색기 크래시 | 2026-10-06 |

## 공통 전제 (어느 작업이든 먼저 알아야 하는 것)

1. **사내 파일은 대부분 DRM(SCDSA004)으로 감싸져 있다.** openpyxl / csv / pandas로 직접 못 연다 → `win32com.client.DispatchEx("Excel.Application")`로 값만 읽는다. 팀장이 열어둔 파일·폴더는 절대 닫지 않는다.
2. **Google Sheets 인증은 `config/briefing_token.json`.** `Credentials.from_authorized_user_file(TOKEN_PATH)` — **scopes 인자를 절대 넘기지 않는다**(여러 스크립트가 공유하는 토큰이라 하드코딩하면 아침 브리핑이 크래시난 전례가 있음). 스코프 확장은 `briefing/auth_setup.py`만 수정 후 재인증.
3. **몇 분 넘게 걸리는 스크립트는 PowerShell `Start-Process`로 독립 프로세스로 띄운다.** Bash 툴이 관리하는 프로세스(foreground/background 무관)는 예측 불가하게 강제종료된다.
   ```powershell
   Start-Process -FilePath "python" -ArgumentList "-u","<스크립트>" -WorkingDirectory "<repo>" `
     -RedirectStandardOutput "<로그>" -RedirectStandardError "<로그>.err" -WindowStyle Hidden
   ```
4. **콘솔 한글 깨짐**: Bash 툴로 `python -c`에 한글을 인라인으로 넣으면 깨진다 → 스크립트 파일(UTF-8)로 써서 실행.
5. **Windows 경로를 docstring/문자열에 쓸 때는 raw string**(`r"""..."""`) — `\N`, `\x` 등이 escape로 먹힌다.
6. 새 산출물 폴더가 필요한데 전용 폴더가 없으면 **임의로 만들지 말고 팀장에게 물어본다.**

## 현재 돌고 있는 무인 자동화

| 작업명 | 시각 | 내용 |
|---|---|---|
| `MorningBriefing` | 매일 07:05 | `briefing/morning_briefing.py` |
| `XAdsDailyScan` | 매일 04:00 | `agent/run_x_ads_daily.bat` → `agent/scan_x_ads_daily.py` |
| 회의록 비교 | 매주 화 23:00 | `minutes_review/` (안 써도 계속 돌리기로 결정됨 — 끄자고 먼저 제안하지 말 것) |
| 컨택리포트 | 매일 01:00 | 별도 폴더(업무자동화), 로그인 필요 |
