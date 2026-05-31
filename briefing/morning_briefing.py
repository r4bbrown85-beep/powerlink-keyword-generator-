"""
아침 스케쥴 브리핑 — Gmail 발송
매일 아침 Task Scheduler 로 자동 실행
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import base64
import datetime
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# ── 설정 ──────────────────────────────────────────────
TOKEN_PATH   = Path('config/briefing_token.json')
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/gmail.send',
]
RECIPIENT    = 'r4bbrown85@gmail.com'
SHEET_ID     = '1ZXkhrtGGFMCVzEP-PEBqra7mAcY0ob8FL_jWXL5KWIs'
# ──────────────────────────────────────────────────────


def get_creds():
    if not TOKEN_PATH.exists():
        print('[오류] briefing_token.json 없음. auth_setup.py 먼저 실행하세요.')
        sys.exit(1)
    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_PATH.write_text(creds.to_json(), encoding='utf-8')
    return creds


def get_calendar_events(creds, today: datetime.date) -> list[dict]:
    svc = build('calendar', 'v3', credentials=creds)
    tz_offset = '+09:00'
    time_min = f'{today.isoformat()}T00:00:00{tz_offset}'
    time_max = f'{today.isoformat()}T23:59:59{tz_offset}'

    calendars_resp = svc.calendarList().list().execute()
    all_events = []

    for cal in calendars_resp.get('items', []):
        cal_id    = cal['id']
        cal_title = cal.get('summary', '')
        try:
            resp = svc.events().list(
                calendarId=cal_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime',
            ).execute()
            for ev in resp.get('items', []):
                start_raw = ev.get('start', {})
                start_str = start_raw.get('dateTime', start_raw.get('date', ''))
                all_events.append({
                    'calendar': cal_title,
                    'title':    ev.get('summary', '(제목없음)'),
                    'start':    start_str,
                    'location': ev.get('location', ''),
                    'desc':     ev.get('description', ''),
                })
        except Exception:
            pass

    all_events.sort(key=lambda x: x['start'])
    return all_events


def fmt_time(dt_str: str) -> str:
    if not dt_str:
        return ''
    try:
        if 'T' in dt_str:
            dt = datetime.datetime.fromisoformat(dt_str)
            return dt.strftime('%H:%M')
        return '종일'
    except Exception:
        return dt_str


def get_sheet_schedule(creds, today: datetime.date) -> list[str]:
    svc   = build('sheets', 'v4', credentials=creds)
    today_strs = [
        today.strftime('%Y-%m-%d'),
        today.strftime('%Y.%m.%d'),
        today.strftime('%m/%d'),
        today.strftime('%-m/%-d') if sys.platform != 'win32' else today.strftime('%#m/%#d'),
        f'{today.month}/{today.day}',
        f'{today.month}월 {today.day}일',
        f'{today.month}월{today.day}일',
    ]
    today_strs = list(dict.fromkeys(today_strs))  # 중복 제거

    result = svc.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range='A1:Z500',
    ).execute()
    rows = result.get('values', [])

    matched_rows = []
    for row in rows:
        row_text = ' '.join(str(c) for c in row)
        for ts in today_strs:
            if ts in row_text:
                clean = [c.strip() for c in row if str(c).strip()]
                line  = '  |  '.join(clean)
                if line not in matched_rows:
                    matched_rows.append(line)
                break
    return matched_rows


def weekday_kr(d: datetime.date) -> str:
    return ['월', '화', '수', '목', '금', '토', '일'][d.weekday()]


def build_html(today: datetime.date,
               cal_events: list[dict],
               sheet_rows: list[str]) -> str:
    weekday = weekday_kr(today)
    date_str = today.strftime(f'%Y년 %m월 %d일 ({weekday})')

    # 캘린더 이벤트 HTML
    if cal_events:
        rows_html = ''
        for ev in cal_events:
            t = fmt_time(ev['start'])
            label = f'<span style="color:#888;font-size:12px;">[{ev["calendar"]}]</span>'
            loc   = f'<br><span style="color:#555;font-size:12px;">📍 {ev["location"]}</span>' if ev['location'] else ''
            rows_html += f'''
            <tr>
              <td style="padding:6px 12px;color:#1a73e8;font-weight:bold;white-space:nowrap;">{t}</td>
              <td style="padding:6px 12px;">{ev["title"]} {label}{loc}</td>
            </tr>'''
        cal_block = f'''
        <h3 style="color:#1a73e8;margin:20px 0 8px;">📅 Google Calendar</h3>
        <table style="border-collapse:collapse;width:100%;">{rows_html}</table>'''
    else:
        cal_block = '<h3 style="color:#1a73e8;margin:20px 0 8px;">📅 Google Calendar</h3><p style="color:#888;">오늘 캘린더 일정 없음</p>'

    # 시트 스케쥴 HTML
    if sheet_rows:
        items_html = ''.join(
            f'<li style="padding:4px 0;">{re.sub(r"<", "&lt;", r)}</li>'
            for r in sheet_rows
        )
        sheet_block = f'''
        <h3 style="color:#0f9d58;margin:20px 0 8px;">📋 팀 업무 시트</h3>
        <ul style="margin:0;padding-left:20px;">{items_html}</ul>'''
    else:
        sheet_block = '<h3 style="color:#0f9d58;margin:20px 0 8px;">📋 팀 업무 시트</h3><p style="color:#888;">오늘 해당 항목 없음</p>'

    return f'''<!DOCTYPE html>
<html><body style="font-family:'Noto Sans KR',sans-serif;max-width:680px;margin:0 auto;padding:20px;color:#333;">
  <div style="background:#1a73e8;color:white;padding:16px 20px;border-radius:8px;margin-bottom:20px;">
    <h2 style="margin:0;font-size:18px;">☀️ 오늘의 스케쥴 브리핑</h2>
    <p style="margin:4px 0 0;font-size:14px;opacity:0.9;">{date_str}</p>
  </div>
  {cal_block}
  {sheet_block}
  <hr style="margin:24px 0;border:none;border-top:1px solid #eee;">
  <p style="font-size:11px;color:#aaa;text-align:center;">자동 발송 · powerlink_keyword_generator</p>
</body></html>'''


def send_gmail(creds, subject: str, html_body: str):
    svc = build('gmail', 'v1', credentials=creds)

    msg = MIMEMultipart('alternative')
    msg['To']      = RECIPIENT
    msg['From']    = RECIPIENT
    msg['Subject'] = subject
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    svc.users().messages().send(userId='me', body={'raw': raw}).execute()


def main():
    today = datetime.date.today()
    print(f'[브리핑] {today}')

    creds = get_creds()

    print('  캘린더 조회 중...')
    cal_events = get_calendar_events(creds, today)
    print(f'  → {len(cal_events)}건')

    print('  시트 스케쥴 조회 중...')
    sheet_rows = get_sheet_schedule(creds, today)
    print(f'  → {len(sheet_rows)}행')

    html  = build_html(today, cal_events, sheet_rows)
    weekday = weekday_kr(today)
    subj  = f'[브리핑] {today.strftime("%m/%d")}({weekday}) 오늘의 스케쥴'

    print('  Gmail 발송 중...')
    send_gmail(creds, subj, html)
    print(f'  ✅ 발송 완료 → {RECIPIENT}')


if __name__ == '__main__':
    main()
