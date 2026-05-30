import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import gspread

TOKEN_PATH = r'C:\Users\Administrator\Desktop\powerlink_keyword_generator\config\oauth_token.json'
CREDS_PATH = r'C:\Users\Administrator\Desktop\powerlink_keyword_generator\config\oauth_credentials.json'

with open(TOKEN_PATH) as f:
    token_data = json.load(f)
with open(CREDS_PATH) as f:
    creds_data = json.load(f)['installed']

creds = Credentials(
    token=token_data.get('token'),
    refresh_token=token_data.get('refresh_token'),
    token_uri=creds_data['token_uri'],
    client_id=creds_data['client_id'],
    client_secret=creds_data['client_secret'],
)
if creds.expired:
    creds.refresh(Request())

gc = gspread.authorize(creds)
service = build('sheets', 'v4', credentials=creds)

SHEET_ID = '1TnMGBLtunxykI6AOn3TDBJbkblUmNznbyR_yXo-Ns_c'

# 시트 목록 확인 (숨긴 것 포함)
meta = service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
sheets = meta.get('sheets', [])
print(f'[시트 목록] 총 {len(sheets)}개\n')
for s in sheets:
    p = s['properties']
    hidden = ' [숨김]' if p.get('hidden') else ''
    print(f'  sheetId={p["sheetId"]:>12}  {p["title"]}{hidden}')

print('\n' + '='*60)

# 전체 시트 내용 읽기
wb = gc.open_by_key(SHEET_ID)
for ws in wb.worksheets():
    rows = ws.get_all_values()
    print(f'\n[시트: {ws.title}]  ({len(rows)}행)')
    print('='*60)
    for i, row in enumerate(rows):
        if any(c.strip() for c in row):
            cells = [c for c in row if c.strip()]
            line = ' | '.join(cells)
            if len(line) > 250:
                line = line[:247] + '...'
            print(f'R{i+1}: {line}')
