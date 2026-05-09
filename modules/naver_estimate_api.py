import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, List, Optional

import requests


BASE_URL = "https://api.searchad.naver.com"


def _get_env(name: str) -> str:
    v = os.getenv(name, "").strip()
    if not v:
        raise RuntimeError(f"환경변수 누락: {name}")
    return v


def _make_signature(timestamp: str, method: str, uri: str, secret_key: str) -> str:
    message = f"{timestamp}.{method}.{uri}"
    digest = hmac.new(
        secret_key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    ).digest()
    return base64.b64encode(digest).decode("utf-8")


def _make_headers(method: str, uri: str) -> Dict[str, str]:
    api_key = _get_env("NAVER_API_KEY")
    secret_key = _get_env("NAVER_SECRET_KEY")
    customer_id = _get_env("NAVER_CUSTOMER_ID")

    timestamp = str(int(time.time() * 1000))
    signature = _make_signature(timestamp, method, uri, secret_key)

    return {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Timestamp": timestamp,
        "X-API-KEY": api_key,
        "X-Customer": customer_id,
        "X-Signature": signature,
    }


def _request(method: str, uri: str, payload: Optional[dict] = None, params: Optional[dict] = None) -> Dict[str, Any]:
    headers = _make_headers(method, uri)
    url = f"{BASE_URL}{uri}"

    resp = requests.request(
        method=method,
        url=url,
        headers=headers,
        json=payload,
        params=params,
        timeout=30,
    )

    text = resp.text
    try:
        data = resp.json()
    except Exception:
        data = {"raw_text": text}

    return {
        "status_code": resp.status_code,
        "ok": resp.ok,
        "data": data,
        "raw_text": text,
        "url": url,
        "uri": uri,
        "payload": payload,
        "params": params,
    }


def get_exposure_minimum_bid_keyword(keywords: List[str], device: str = "PC") -> Dict[str, Any]:
    """
    최소 노출 입찰가 조회 (정상 동작 확인됨)
    POST /npc-estimate/exposure-minimum-bid/keyword
    """
    uri = "/npc-estimate/exposure-minimum-bid/keyword"
    payload = {
        "device": device.upper(),
        "items": keywords,
    }
    return _request("POST", uri, payload=payload)


def get_average_position_bid_by_id(items: List[Dict[str, Any]], device: str = "PC") -> Dict[str, Any]:
    """
    순위 기반 입찰가 조회
    POST /npc-estimate/average-position-bid/id
    """
    uri = "/npc-estimate/average-position-bid/id"
    payload = {
        "device": device.upper(),
        "items": items,
    }
    return _request("POST", uri, payload=payload)


def get_performance_bulk(items: List[Dict[str, Any]], device: str = "PC") -> Dict[str, Any]:
    """
    bulk 호출 - device를 각 item 안에 넣어야 정상 동작 (검증 완료 2026-04-06)
    네이버 공식 플랫폼 월간예상실적과 동일한 값 반환 확인됨
    """
    uri = "/estimate/performance-bulk"
    device_upper = device.upper()
    # device를 각 item 안에 주입
    items_with_device = [
        {**item, "device": device_upper} for item in items
    ]
    payload = {"items": items_with_device}
    return _request("POST", uri, payload=payload)


def try_estimate_patterns(keyword: str, bid: int, device: str = "PC") -> Dict[str, Any]:
    """
    performance-bulk 패턴 테스트.

    에러 분석 결과:
    - device=null  → device를 items 안에 각각 넣어야 함
    - invalid collections size → PC + MOBILE 두 개를 동시에 넣어야 할 가능성

    아래 패턴들을 순차 테스트.
    """
    candidates = [
        # ── 기존 패턴 (실패 확인됨) ──────────────────────────────
        {
            "name": "pattern_1_old_device_outside",
            "uri": "/estimate/performance-bulk",
            "payload": {
                "device": device.upper(),
                "items": [{"keyword": keyword, "bid": bid}],
            },
        },
        # ── 신규 패턴: device를 items 안에 넣기 ─────────────────
        {
            "name": "pattern_2_device_inside_single",
            "uri": "/estimate/performance-bulk",
            "payload": {
                "items": [{"keyword": keyword, "bid": bid, "device": device.upper()}],
            },
        },
        # ── 신규 패턴: PC + MOBILE 두 개 동시 (size 조건 만족) ──
        {
            "name": "pattern_3_pc_and_mobile_pair",
            "uri": "/estimate/performance-bulk",
            "payload": {
                "items": [
                    {"keyword": keyword, "bid": bid, "device": "PC"},
                    {"keyword": keyword, "bid": bid, "device": "MOBILE"},
                ],
            },
        },
        # ── 신규 패턴: device 없이 PC+MOBILE 쌍 ─────────────────
        {
            "name": "pattern_4_pair_no_device_field",
            "uri": "/estimate/performance-bulk",
            "payload": {
                "device": device.upper(),
                "items": [
                    {"keyword": keyword, "bid": bid},
                    {"keyword": keyword, "bid": bid},
                ],
            },
        },
        # ── 신규 패턴: npc-estimate 경로로 시도 ─────────────────
        {
            "name": "pattern_5_npc_path_device_inside",
            "uri": "/npc-estimate/performance-bulk",
            "payload": {
                "items": [
                    {"keyword": keyword, "bid": bid, "device": "PC"},
                    {"keyword": keyword, "bid": bid, "device": "MOBILE"},
                ],
            },
        },
        # ── 신규 패턴: npc-estimate 경로 + device 바깥 ──────────
        {
            "name": "pattern_6_npc_path_device_outside",
            "uri": "/npc-estimate/performance-bulk",
            "payload": {
                "device": device.upper(),
                "items": [{"keyword": keyword, "bid": bid}],
            },
        },
    ]

    results = []
    for c in candidates:
        res = _request("POST", c["uri"], payload=c["payload"])
        result = {
            "name": c["name"],
            "status_code": res["status_code"],
            "ok": res["ok"],
            "data": res["data"],
            "payload": c["payload"],
        }
        results.append(result)

        # 성공하면 바로 출력해서 알 수 있게
        if res["ok"]:
            print(f"  ✅ 성공 패턴 발견: {c['name']}")

    return {
        "keyword": keyword,
        "bid": bid,
        "device": device,
        "results": results,
    }