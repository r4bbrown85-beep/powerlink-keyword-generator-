"""
1회 실행 스크립트 — briefing_token.json 생성
실행: python briefing/auth_setup.py
브라우저 열리면 r4bbrown85@gmail.com 계정으로 로그인 후 권한 허용
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/gmail.send',
]

CREDS_PATH = Path('config/oauth_credentials.json')
TOKEN_PATH = Path('config/briefing_token.json')

if not CREDS_PATH.exists():
    print(f'[오류] {CREDS_PATH} 파일이 없습니다.')
    sys.exit(1)

print('브라우저가 열립니다. r4bbrown85@gmail.com 계정으로 로그인하세요.')
flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_PATH), SCOPES)
creds = flow.run_local_server(port=0)

TOKEN_PATH.write_text(creds.to_json(), encoding='utf-8')
print(f'✅ 토큰 저장 완료: {TOKEN_PATH}')
print('이제 morning_briefing.py 를 실행할 수 있습니다.')
