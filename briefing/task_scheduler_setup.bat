@echo off
:: 매일 오전 8:00 아침 브리핑 Task Scheduler 등록
:: 관리자 권한으로 실행 필요

schtasks /create ^
  /tn "MorningBriefing" ^
  /tr "\"C:\Users\Administrator\Desktop\powerlink_keyword_generator\briefing\run_briefing.bat\"" ^
  /sc daily ^
  /st 08:00 ^
  /ru "%USERNAME%" ^
  /f

if %errorlevel% == 0 (
    echo [완료] Task Scheduler 등록 성공 - 매일 08:00 실행
) else (
    echo [오류] 등록 실패. 관리자 권한으로 다시 실행하세요.
)
pause
