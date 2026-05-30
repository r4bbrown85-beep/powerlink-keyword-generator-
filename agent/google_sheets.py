# -*- coding: utf-8 -*-
"""
google_sheets.py — Google Sheets 읽기/쓰기 모듈

인증 방식 (자동 선택):
  1. OAuth2 (권장) — config/oauth_credentials.json 있으면 사용
     r4bbrown85@gmail.com 계정으로 접근 가능한 모든 시트 편집 가능
  2. 서비스 계정 — config/google_service_account.json 폴백

사용법:
  writer = SheetsWriter("시트ID_or_URL")
  writer.update_tab("캠페인실적", rows, clear=True)
"""
import json
import os
from pathlib import Path
from typing import List, Optional

OAUTH_CREDENTIALS_PATH = Path("config/oauth_credentials.json")
SERVICE_ACCOUNT_PATH   = Path("config/google_service_account.json")
OAUTH_TOKEN_PATH       = Path("config/oauth_token.json")
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


class SheetsWriter:
    def __init__(self, spreadsheet_id_or_url: str):
        """
        spreadsheet_id_or_url: 스프레드시트 ID 또는 전체 URL
        """
        import gspread

        sid = spreadsheet_id_or_url
        if "/spreadsheets/d/" in sid:
            sid = sid.split("/spreadsheets/d/")[1].split("/")[0]
        self.spreadsheet_id = sid

        self.gc = self._authorize()
        self.sh = self.gc.open_by_key(self.spreadsheet_id)

    def _authorize(self):
        import gspread
        # OAuth2 우선 (r4bbrown85@gmail.com 계정)
        if OAUTH_CREDENTIALS_PATH.exists():
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request

            creds = None
            if OAUTH_TOKEN_PATH.exists():
                creds = Credentials.from_authorized_user_file(str(OAUTH_TOKEN_PATH), SCOPES)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(OAUTH_CREDENTIALS_PATH), SCOPES)
                    creds = flow.run_local_server(port=0)
                OAUTH_TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
                with open(OAUTH_TOKEN_PATH, "w") as f:
                    f.write(creds.to_json())

            return gspread.authorize(creds)

        # 서비스 계정 폴백
        if SERVICE_ACCOUNT_PATH.exists():
            from google.oauth2.service_account import Credentials
            creds = Credentials.from_service_account_file(str(SERVICE_ACCOUNT_PATH), scopes=SCOPES)
            return gspread.authorize(creds)

        raise FileNotFoundError(
            "인증 파일 없음. config/oauth_credentials.json 을 저장하세요."
        )

    def update_tab(self, tab_name: str, rows: List[dict],
                   clear: bool = True, start_cell: str = "A1") -> int:
        """
        탭에 데이터 쓰기. rows는 dict 목록.
        첫 행은 자동으로 헤더(키 이름)로 삽입.
        반환: 쓴 행 수
        """
        if not rows:
            print(f"  [{tab_name}] 데이터 없음 — 스킵")
            return 0

        try:
            ws = self.sh.worksheet(tab_name)
        except Exception:
            ws = self.sh.add_worksheet(title=tab_name, rows=500, cols=20)
            print(f"  [{tab_name}] 새 탭 생성")

        headers = list(rows[0].keys())
        values  = [headers] + [[r.get(h, "") for h in headers] for r in rows]

        if clear:
            ws.clear()

        ws.update(start_cell, values, value_input_option="USER_ENTERED")
        print(f"  [{tab_name}] {len(rows)}행 업데이트 완료")
        return len(rows)

    def read_tab(self, tab_name: str) -> List[dict]:
        """탭 전체 읽기 → List[dict]"""
        try:
            ws = self.sh.worksheet(tab_name)
            return ws.get_all_records()
        except Exception as e:
            print(f"  [{tab_name}] 읽기 실패: {e}")
            return []

    def append_rows(self, tab_name: str, rows: List[dict]) -> int:
        """기존 데이터 아래에 행 추가"""
        if not rows:
            return 0
        try:
            ws = self.sh.worksheet(tab_name)
        except Exception:
            ws = self.sh.add_worksheet(title=tab_name, rows=1000, cols=20)

        values = [[r.get(h, "") for h in rows[0].keys()] for r in rows]
        ws.append_rows(values, value_input_option="USER_ENTERED")
        print(f"  [{tab_name}] {len(rows)}행 추가")
        return len(rows)
