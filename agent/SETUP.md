# 에이전트 자동화 시스템 설정 가이드

## 1. 현재 상태

| 기능 | 상태 | 비고 |
|------|------|------|
| Naver SA 실적 API | ✅ 완료 | .env 인증 사용 |
| Google Sheets 쓰기 | ⏳ 설정 필요 | 서비스 계정 JSON 필요 |
| 브라우저 자동화 | ✅ 준비됨 | Selenium + Edge |

---

## 2. Google Sheets 설정 (필수)

### 2-1. Google Cloud Console에서 서비스 계정 만들기

1. https://console.cloud.google.com 접속
2. 새 프로젝트 생성 (또는 기존 프로젝트 사용)
3. **API 및 서비스 → 라이브러리** 에서 아래 2개 활성화:
   - Google Sheets API
   - Google Drive API
4. **API 및 서비스 → 사용자 인증 정보 → 사용자 인증 정보 만들기 → 서비스 계정**
5. 서비스 계정 이름 입력 (예: `naver-sa-reporter`) → 만들기
6. **키 탭 → 키 추가 → JSON** → 다운로드
7. 다운로드한 JSON 파일을 이 경로에 저장:
   ```
   config/google_service_account.json
   ```

### 2-2. 구글 시트 공유

1. 사용할 구글 시트 열기
2. 우상단 **공유** 클릭
3. 서비스 계정 이메일 입력 (JSON 파일 안의 `client_email` 값)
4. 역할: **편집자** 선택 → 공유

---

## 3. 실행 방법

```bash
# 캠페인별 실적 확인 (콘솔 출력)
python agent/run.py --task campaign_stats --days 7

# 키워드별 실적 확인
python agent/run.py --task keyword_stats --days 7 --top 100

# 일별 트렌드 30일
python agent/run.py --task daily_trend --days 30

# 구글 시트에 전체 리포트 업데이트
python agent/run.py --task report_to_sheets \
  --sheet_url "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID" \
  --days 7 --top 100
```

---

## 4. 구글 시트 업데이트 결과

`report_to_sheets` 실행 시 3개 탭이 자동 생성/업데이트됩니다:

| 탭 이름 | 내용 |
|---------|------|
| 캠페인실적 | 캠페인별 노출/클릭/광고비/CTR/CPC |
| 키워드실적 | 키워드별 실적 + 평균순위 |
| 일별트렌드 | 30일 일별 지표 추이 |

---

## 5. 확장 아이디어

- **매일 자동 실행**: Windows 작업 스케줄러로 `python agent/run.py --task report_to_sheets ...` 등록
- **입찰가 조회 자동화**: Selenium으로 검색광고센터 접속 후 입찰 현황 스크린샷
- **알림 발송**: 특정 KPI 이상/이하 시 이메일 또는 슬랙 알림
