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

# ── 설정 ─────────────────────────────────────────────────
TOKEN_PATH = Path('config/briefing_token.json')
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/gmail.send',
]
RECIPIENT  = 'r4bbrown85@gmail.com'
SHEET_ID   = '1ZXkhrtGGFMCVzEP-PEBqra7mAcY0ob8FL_jWXL5KWIs'
SHEET_TAB  = '26년 근무 일정'
MY_NAME    = '유승환'   # 본인 이름 (시트 B열 부분 매칭)
MEMBERS    = ['유승환', '이선애', '김나은', '박현', '남경희', '매체설명회']

HIGH_KW  = ['QBR', '보고', '면접', '계약', '발표', '대표', '본부장', '실장', 'PT', '프레젠']
MED_KW   = ['미팅', '웨비나', '설명회', '점약', '충전', '킥오프', '리뷰', '회의']
# ─────────────────────────────────────────────────────────


def get_creds():
    if not TOKEN_PATH.exists():
        print('[오류] briefing_token.json 없음. auth_setup.py 먼저 실행하세요.')
        sys.exit(1)
    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_PATH.write_text(creds.to_json(), encoding='utf-8')
    return creds


# ── 중요도 판정 ──────────────────────────────────────────
def priority(text: str) -> int:
    """0=일반 1=중간 2=높음"""
    t = text.upper()
    if any(k.upper() in t for k in HIGH_KW):
        return 2
    if any(k.upper() in t for k in MED_KW):
        return 1
    return 0

PRIORITY_ICON = {2: '🔴', 1: '🟡', 0: ''}
PRIORITY_COLOR = {2: '#c0392b', 1: '#e67e22', 0: '#333'}


# ── Google Calendar ──────────────────────────────────────
def get_calendar_events(creds, today: datetime.date) -> list[dict]:
    svc = build('calendar', 'v3', credentials=creds)
    tz  = '+09:00'
    time_min = f'{today.isoformat()}T00:00:00{tz}'
    time_max = f'{today.isoformat()}T23:59:59{tz}'

    all_events = []
    cals = svc.calendarList().list().execute().get('items', [])
    for cal in cals:
        try:
            resp = svc.events().list(
                calendarId=cal['id'],
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime',
            ).execute()
            for ev in resp.get('items', []):
                s = ev.get('start', {})
                all_events.append({
                    'calendar': cal.get('summary', ''),
                    'title':    ev.get('summary', '(제목없음)'),
                    'start':    s.get('dateTime', s.get('date', '')),
                    'location': ev.get('location', ''),
                })
        except Exception:
            pass
    all_events.sort(key=lambda x: x['start'])
    return all_events


def fmt_time(s: str) -> str:
    try:
        if 'T' in s:
            return datetime.datetime.fromisoformat(s).strftime('%H:%M')
        return '종일'
    except Exception:
        return s


# ── 시트 파싱 ────────────────────────────────────────────
def parse_korean_date(cell: str, year: int) -> datetime.date | None:
    m = re.match(r'(\d+)월\s*(\d+)일', cell.strip())
    if not m:
        return None
    try:
        return datetime.date(year, int(m.group(1)), int(m.group(2)))
    except ValueError:
        return None


def parse_schedule_sheet(creds, today: datetime.date) -> dict:
    svc = build('sheets', 'v4', credentials=creds)
    result = svc.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range=f'{SHEET_TAB}!A1:P300',
    ).execute()
    rows = result.get('values', [])

    def cell(row, idx, default=''):
        return row[idx].strip() if idx < len(row) else default

    # 주간 헤더 행 탐지 (cells[2]~[6] 에 "X월 Y일" 패턴)
    week_blocks = []  # list of (header_row_idx, {col_idx: date})
    for i, row in enumerate(rows):
        dates = {}
        for j in range(2, 7):
            d = parse_korean_date(cell(row, j), today.year)
            if d:
                dates[j] = d
        if len(dates) >= 3:
            week_blocks.append((i, dates))

    # 오늘이 속한 주 찾기
    target_block = None
    for (blk_i, date_map) in week_blocks:
        if today in date_map.values():
            target_block = (blk_i, date_map)
            break

    result_data = {
        'week_data':   {},   # {member_name: {date: schedule_text}}
        'week_notes':  [],   # 주간 메모 리스트 (중복 제거)
        'date_map':    {},   # {col_idx: date}
        'found':       target_block is not None,
    }
    if not target_block:
        return result_data

    blk_i, date_map = target_block
    result_data['date_map'] = date_map

    # 다음 주간 헤더 위치 (현재 블록 종료 기준)
    blk_indices = [b[0] for b in week_blocks]
    cur_pos = blk_indices.index(blk_i)
    end_i = blk_indices[cur_pos + 1] if cur_pos + 1 < len(blk_indices) else len(rows)

    # 사람 행 파싱 (헤더+요일 행 2개 건너뜀)
    seen_notes = set()
    for i in range(blk_i + 2, end_i):
        row = rows[i]
        name_cell = cell(row, 1)
        if not name_cell:
            continue

        schedules = {}
        for col, d in date_map.items():
            schedules[d] = cell(row, col)

        note = cell(row, 7)
        if note and note not in seen_notes:
            seen_notes.add(note)
            result_data['week_notes'].append(note)

        result_data['week_data'][name_cell] = schedules

    return result_data


# ── HTML 빌더 ────────────────────────────────────────────
WEEKDAY_KR = ['월', '화', '수', '목', '금', '토', '일']

def weekday_kr(d: datetime.date) -> str:
    return WEEKDAY_KR[d.weekday()]


def html_badge(p: int, text: str) -> str:
    icon = PRIORITY_ICON[p]
    color = PRIORITY_COLOR[p]
    return f'<span style="color:{color};">{icon} {text}</span>' if icon else text


def build_html(today: datetime.date, cal_events: list[dict], sheet: dict) -> str:
    date_str = today.strftime(f'%Y년 %m월 %d일 ({weekday_kr(today)})')
    date_map  = sheet.get('date_map', {})
    week_data = sheet.get('week_data', {})
    notes     = sheet.get('week_notes', [])

    # ── SECTION 1: 나의 오늘 ────────────────────────────
    # Calendar
    if cal_events:
        ev_rows = ''
        for ev in cal_events:
            t   = fmt_time(ev['start'])
            p   = priority(ev['title'])
            loc = f'<br><small style="color:#777;">📍 {ev["location"]}</small>' if ev['location'] else ''
            cal_label = f'<small style="color:#999;">[{ev["calendar"]}]</small>'
            ev_rows += f'''
            <tr>
              <td style="padding:5px 10px;color:#1a73e8;font-weight:bold;white-space:nowrap;vertical-align:top;">{t}</td>
              <td style="padding:5px 10px;vertical-align:top;">{html_badge(p, ev["title"])} {cal_label}{loc}</td>
            </tr>'''
        cal_section = f'<table style="border-collapse:collapse;width:100%;margin-bottom:4px;">{ev_rows}</table>'
    else:
        cal_section = '<p style="color:#aaa;margin:4px 0;">캘린더 일정 없음</p>'

    # Sheet — my schedule today
    my_sched_today = ''
    today_col = None
    for col, d in date_map.items():
        if d == today:
            today_col = col
            break

    for name, schedules in week_data.items():
        if MY_NAME in name:
            sched = schedules.get(today, '')
            if sched:
                items = [s.strip() for s in sched.split('/') if s.strip()]
                bullets = ''.join(
                    f'<li style="padding:2px 0;">{html_badge(priority(it), it)}</li>'
                    for it in items
                )
                my_sched_today = f'<ul style="margin:4px 0;padding-left:18px;">{bullets}</ul>'
            break
    if not my_sched_today:
        my_sched_today = '<p style="color:#aaa;margin:4px 0;">시트 일정 없음</p>'

    # ── SECTION 2: 팀원 오늘 현황 ──────────────────────
    team_today_rows = ''
    for name, schedules in week_data.items():
        if '매체설명회' in name:
            continue
        sched = schedules.get(today, '')
        bg = '#fff'
        if MY_NAME in name:
            bg = '#e8f0fe'
        p_val = priority(sched)
        icon  = PRIORITY_ICON[p_val]
        color = PRIORITY_COLOR[p_val]
        sched_html = f'<span style="color:{color};">{icon} {sched}</span>' if sched else '<span style="color:#ccc;">—</span>'
        team_today_rows += f'''
        <tr style="background:{bg};">
          <td style="padding:5px 10px;font-weight:{"bold" if MY_NAME in name else "normal"};white-space:nowrap;">{name}</td>
          <td style="padding:5px 10px;">{sched_html}</td>
        </tr>'''

    # 매체 행사
    for name, schedules in week_data.items():
        if '매체설명회' in name:
            sched = schedules.get(today, '')
            if sched:
                team_today_rows += f'''
        <tr style="background:#f9f9e8;">
          <td style="padding:5px 10px;color:#888;white-space:nowrap;">매체/행사</td>
          <td style="padding:5px 10px;color:#888;">{sched}</td>
        </tr>'''

    # ── SECTION 3: 주간 테이블 ──────────────────────────
    if date_map:
        sorted_cols = sorted(date_map.items())
        week_header = '<th style="padding:6px 8px;background:#f5f5f5;">이름</th>'
        for col, d in sorted_cols:
            wd  = weekday_kr(d)
            is_today = (d == today)
            bg  = '#1a73e8' if is_today else '#f5f5f5'
            clr = 'white' if is_today else '#333'
            week_header += f'<th style="padding:6px 8px;background:{bg};color:{clr};font-size:12px;">{wd}<br>{d.month}/{d.day}</th>'

        week_body = ''
        for name, schedules in week_data.items():
            if '매체설명회' in name:
                continue
            is_me = MY_NAME in name
            row_bg = '#e8f0fe' if is_me else 'white'
            week_body += f'<tr style="background:{row_bg};">'
            week_body += f'<td style="padding:5px 8px;font-size:12px;white-space:nowrap;font-weight:{"bold" if is_me else "normal"};">{name}</td>'
            for col, d in sorted_cols:
                sched = schedules.get(d, '')
                is_today_col = (d == today)
                cell_bg = '#dbeafe' if (is_today_col and is_me) else ('#eff3ff' if is_today_col else 'transparent')
                p_val   = priority(sched)
                color   = PRIORITY_COLOR[p_val]
                icon    = PRIORITY_ICON[p_val]
                text    = f'{icon} {sched}' if icon and sched else sched
                week_body += f'<td style="padding:5px 8px;font-size:11px;color:{color};background:{cell_bg};max-width:120px;">{text or "—"}</td>'
            week_body += '</tr>'

        # 매체 행사 행
        for name, schedules in week_data.items():
            if '매체설명회' in name:
                week_body += '<tr style="background:#fafaf0;">'
                week_body += '<td style="padding:5px 8px;font-size:12px;color:#888;white-space:nowrap;">매체/행사</td>'
                for col, d in sorted_cols:
                    sched = schedules.get(d, '')
                    is_today_col = (d == today)
                    cell_bg = '#fffff0' if is_today_col else 'transparent'
                    week_body += f'<td style="padding:5px 8px;font-size:11px;color:#888;background:{cell_bg};">{sched or "—"}</td>'
                week_body += '</tr>'

        week_table = f'''
        <div style="overflow-x:auto;">
          <table style="border-collapse:collapse;width:100%;min-width:500px;">
            <thead><tr>{week_header}</tr></thead>
            <tbody>{week_body}</tbody>
          </table>
        </div>'''
    else:
        week_table = '<p style="color:#aaa;">시트에서 이번 주 데이터를 찾지 못했습니다.</p>'

    # ── SECTION 4: 주요 메모 ────────────────────────────
    if notes:
        note_items = ''.join(
            f'<li style="padding:3px 0;font-size:12px;">{html_badge(priority(n), n)}</li>'
            for n in notes
        )
        notes_section = f'<ul style="margin:4px 0;padding-left:18px;">{note_items}</ul>'
    else:
        notes_section = '<p style="color:#aaa;font-size:12px;">메모 없음</p>'

    def section(title: str, color: str, body: str) -> str:
        return f'''
    <div style="margin-bottom:20px;">
      <h3 style="color:{color};margin:0 0 8px;font-size:15px;border-bottom:2px solid {color};padding-bottom:4px;">{title}</h3>
      {body}
    </div>'''

    return f'''<!DOCTYPE html>
<html><body style="font-family:'Noto Sans KR',Arial,sans-serif;max-width:720px;margin:0 auto;padding:20px;color:#333;font-size:13px;">

  <div style="background:linear-gradient(135deg,#1a73e8,#0d47a1);color:white;padding:18px 22px;border-radius:10px;margin-bottom:22px;">
    <h2 style="margin:0;font-size:20px;">☀️ 아침 스케쥴 브리핑</h2>
    <p style="margin:4px 0 0;opacity:0.88;">{date_str}</p>
  </div>

  {section("📅 나의 오늘 — Google Calendar", "#1a73e8",
    cal_section)}

  {section(f"📋 나의 오늘 — {SHEET_TAB}", "#0f9d58",
    my_sched_today)}

  {section("👥 팀원 오늘 현황", "#7b1fa2",
    f'<table style="border-collapse:collapse;width:100%;">{team_today_rows}</table>'
    if team_today_rows else '<p style="color:#aaa;">데이터 없음</p>')}

  {section("📆 이번 주 팀 일정", "#e65100", week_table)}

  {section("📌 이번 주 주요 메모", "#37474f", notes_section)}

  <hr style="border:none;border-top:1px solid #eee;margin:20px 0;">
  <p style="font-size:10px;color:#bbb;text-align:center;">자동 발송 · powerlink_keyword_generator</p>
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

    print('  시트 파싱 중...')
    sheet = parse_schedule_sheet(creds, today)
    members_found = len(sheet['week_data'])
    print(f'  → 팀원 {members_found}명 / 메모 {len(sheet["week_notes"])}건')

    html  = build_html(today, cal_events, sheet)
    wd    = weekday_kr(today)
    subj  = f'[브리핑] {today.strftime("%m/%d")}({wd}) 오늘의 스케쥴'

    print('  Gmail 발송 중...')
    send_gmail(creds, subj, html)
    print(f'  ✅ 발송 완료 → {RECIPIENT}')


if __name__ == '__main__':
    main()
