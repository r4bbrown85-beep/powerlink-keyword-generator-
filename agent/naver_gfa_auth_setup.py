# -*- coding: utf-8 -*-
"""
1회 실행 스크립트 — 네이버 GFA(성과형 디스플레이 광고) API OAuth 인증 후 gfa_token.json 생성
실행: python agent/naver_gfa_auth_setup.py

사전 준비 (네이버 개발자센터 https://developers.naver.com):
  1. Application > 애플리케이션 등록
     - 사용 API: "네이버 로그인" 선택 (필수)
     - 서비스 URL: http://localhost:8899
     - Callback URL: http://localhost:8899/callback   ← 반드시 이 값 그대로 등록
  2. 발급된 Client ID / Client Secret을 .env에 추가:
     NAVER_GFA_CLIENT_ID=...
     NAVER_GFA_CLIENT_SECRET=...
  3. 네이버 성과형 디스플레이 광고 관리시스템 > 대표 관리 계정 > 설정 > API 관리에서
     위 Client ID를 등록해 API 사용 권한 신청 (승인 필요)
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import os
import json
import secrets
import webbrowser
import urllib.parse
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

CLIENT_ID     = os.getenv("NAVER_GFA_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("NAVER_GFA_CLIENT_SECRET", "")
REDIRECT_URI  = "http://localhost:8899/callback"
TOKEN_PATH    = Path("config/gfa_token.json")

STATE  = secrets.token_urlsafe(16)
_result: dict = {}


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return
        qs = urllib.parse.parse_qs(parsed.query)
        _result["code"]  = qs.get("code", [None])[0]
        _result["state"] = qs.get("state", [None])[0]
        _result["error"] = qs.get("error_description", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        msg = "인증 완료. 이 창은 닫고 터미널로 돌아가세요." if _result.get("code") else "인증 실패. 터미널을 확인하세요."
        self.wfile.write(f"<html><body><h2>{msg}</h2></body></html>".encode("utf-8"))

    def log_message(self, format, *args):
        pass


def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        print("[오류] .env에 NAVER_GFA_CLIENT_ID / NAVER_GFA_CLIENT_SECRET을 먼저 설정하세요.")
        sys.exit(1)

    auth_url = "https://nid.naver.com/oauth2.0/authorize?" + urllib.parse.urlencode({
        "response_type": "code",
        "client_id":     CLIENT_ID,
        "redirect_uri":  REDIRECT_URI,
        "state":         STATE,
    })
    print("브라우저가 열립니다. 네이버 계정으로 로그인 후 권한을 허용하세요.")
    print(f"(자동으로 안 열리면 이 URL을 직접 여세요: {auth_url})\n")
    webbrowser.open(auth_url)

    server = HTTPServer(("localhost", 8899), _CallbackHandler)
    server.handle_request()  # 콜백 1건만 받고 종료

    if _result.get("error"):
        print(f"[오류] 네이버 인증 거부/실패: {_result['error']}")
        sys.exit(1)
    if _result.get("state") != STATE:
        print("[오류] state 값 불일치 — 요청이 위변조됐을 수 있어 중단합니다.")
        sys.exit(1)
    code = _result.get("code")
    if not code:
        print("[오류] 인증 코드 수신 실패.")
        sys.exit(1)

    token_url = "https://nid.naver.com/oauth2.0/token?" + urllib.parse.urlencode({
        "grant_type":    "authorization_code",
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code":          code,
        "state":         STATE,
    })
    try:
        with urllib.request.urlopen(token_url) as resp:
            token_data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"[오류] 토큰 발급 요청 실패: {e.code} {e.read().decode('utf-8', 'ignore')}")
        sys.exit(1)

    if "access_token" not in token_data:
        print(f"[오류] 토큰 발급 실패: {token_data}")
        sys.exit(1)

    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(json.dumps(token_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 토큰 저장 완료: {TOKEN_PATH}")
    print("이제 python agent/naver_gfa_api.py 로 연결을 테스트할 수 있습니다.")


if __name__ == "__main__":
    main()
