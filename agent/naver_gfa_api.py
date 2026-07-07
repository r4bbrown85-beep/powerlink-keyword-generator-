# -*- coding: utf-8 -*-
"""
네이버 GFA(성과형 디스플레이 광고) API 헬퍼.

OAuth 인증은 naver_gfa_auth_setup.py로 1회 실행해 config/gfa_token.json을 만들어둔 뒤 사용.
access_token 만료 시 refresh_token으로 자동 갱신.

인증 헤더 형식(Authorization: Bearer {액세스 토큰})은 공식 가이드
(https://naver-ad-api.github.io/openapi-guide/docs/prepare/api-call-with-access-token)로 확인됨.

주의(FAQ 기준, 위 가이드 /docs/faq): GFA Client ID가 "활성" 상태가 되기 전에 먼저 로그인 동의를
해버리면 이후 인증이 실패할 수 있고, 이 경우 네이버 로그인 서비스 동의를 철회 후 재동의해야 함.
따라서 naver_gfa_auth_setup.py는 GFA 관리시스템(대표 관리 계정 > 설정 > API 관리)에서
해당 Client ID 상태가 "활성"으로 바뀐 뒤에 실행할 것.

관리계정 멤버가 아니어도 관리계정 권한 레벨에 따라 하위 캠페인/광고그룹/소재 관리가 가능하며,
이 경우 요청 헤더에 AccessManagerAccountNo(관리계정 ID)를 함께 전달해야 함.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import os
import json
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

CLIENT_ID     = os.getenv("NAVER_GFA_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("NAVER_GFA_CLIENT_SECRET", "")
TOKEN_PATH    = Path("config/gfa_token.json")
BASE_URL      = "https://openapi.naver.com/v1/ad-api"


def _load_token() -> dict:
    if not TOKEN_PATH.exists():
        raise RuntimeError(
            f"{TOKEN_PATH} 없음 — 먼저 python agent/naver_gfa_auth_setup.py 를 실행하세요."
        )
    return json.loads(TOKEN_PATH.read_text(encoding="utf-8"))


def _save_token(token: dict):
    TOKEN_PATH.write_text(json.dumps(token, ensure_ascii=False, indent=2), encoding="utf-8")


def _refresh_token(refresh_token: str) -> dict:
    url = "https://nid.naver.com/oauth2.0/token?" + urllib.parse.urlencode({
        "grant_type":    "refresh_token",
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": refresh_token,
    })
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_access_token() -> str:
    """저장된 토큰을 반환. 액세스 토큰이 만료됐을 가능성에 대비해 항상 갱신 시도."""
    token = _load_token()
    refreshed = _refresh_token(token["refresh_token"])
    if "access_token" in refreshed:
        token.update(refreshed)
        _save_token(token)
        return token["access_token"]
    # 갱신 실패 시 기존 access_token으로 시도 (아직 안 만료됐을 수 있음)
    print(f"[경고] 토큰 갱신 실패, 기존 access_token 사용 시도: {refreshed}")
    return token["access_token"]


def call_api(method: str, path: str, params: dict = None, body: dict = None) -> dict:
    """
    GFA API 호출. path는 '/adAccounts' 같은 버전 이후 경로.
    실제 인증 헤더 형식이 다를 경우 이 함수의 headers 부분만 수정하면 됨.
    """
    access_token = get_access_token()
    url = f"{BASE_URL}/1{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type":  "application/json; charset=UTF-8",
    }
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return {"status": resp.status, "body": json.loads(resp.read().decode("utf-8"))}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", "ignore")
        return {"status": e.code, "error": err_body}


def explore():
    """연결 확인용 — 광고 계정 목록 조회를 시도하고 원본 응답을 그대로 출력."""
    print("GFA API 연결 테스트: GET /adAccounts")
    result = call_api("GET", "/adAccounts", params={"page": 0, "size": 10})
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    explore()
