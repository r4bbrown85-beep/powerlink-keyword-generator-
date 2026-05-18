# -*- coding: utf-8 -*-
"""
naver_stats.py — 계정 실집행 실적 조회

용도:
  1. 계정 내 등록 키워드 목록 조회 → 제안서에 "기등록" 표기
  2. 키워드별 실적(평균순위·CTR) 조회 → estimate 순위 보정 참고

API 흐름:
  GET /ncc/campaigns → campaign ID 목록
  GET /ncc/adgroups  → adgroup ID 목록
  GET /ncc/keywords  → 등록 키워드 (텍스트 + ID)
  GET /stats         → 키워드별 30일 실적 (avgRnk, ctr, clkCnt)

캐시: 1일 (실집행 데이터는 매일 갱신)
실패 시 빈 결과 반환 — 메인 플로우에 영향 없음
"""
import base64
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

BASE_URL   = "https://api.searchad.naver.com"
CACHE_DIR  = Path("data/cache/stats")
CACHE_DAYS = 1
_MAX_CAMPAIGNS  = 20
_MAX_KW_PER_REQ = 100


# ── 인증 헬퍼 ──────────────────────────────────────────────────────────────────

def _headers(api_key: str, secret: str, customer_id: str,
             method: str, uri: str) -> dict:
    ts  = str(int(time.time() * 1000))
    sig = base64.b64encode(
        hmac.new(secret.encode(), f"{ts}.{method}.{uri}".encode(), hashlib.sha256).digest()
    ).decode()
    return {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Timestamp":  ts,
        "X-API-KEY":    api_key,
        "X-Customer":   str(customer_id),
        "X-Signature":  sig,
    }


def _get(uri: str, params: dict, api_key: str, secret: str, customer_id: str):
    try:
        resp = requests.get(
            f"{BASE_URL}{uri}",
            headers=_headers(api_key, secret, customer_id, "GET", uri),
            params=params,
            timeout=30,
        )
        return resp.json() if resp.ok else None
    except Exception:
        return None


# ── 캐시 ──────────────────────────────────────────────────────────────────────

def _cache_path(key: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{key}.json"


def _load_cache(path: Path):
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            c = json.load(f)
        if datetime.now() - datetime.fromisoformat(c["cached_at"]) > timedelta(days=CACHE_DAYS):
            return None
        return c["data"]
    except Exception:
        return None


def _save_cache(path: Path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"cached_at": datetime.now().isoformat(), "data": data},
                      f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ── 공통: 캠페인 + 키워드 목록 조회 ──────────────────────────────────────────

def _fetch_campaign_ids(api_key: str, secret: str, customer_id: str) -> list:
    result = _get("/ncc/campaigns", {"searchType": "ALL"}, api_key, secret, customer_id)
    if not result or not isinstance(result, list):
        return []
    return [c["nccCampaignId"] for c in result if c.get("nccCampaignId")]


def _fetch_keyword_map(campaign_ids: list,
                       api_key: str, secret: str, customer_id: str) -> dict:
    """반환: {nccKeywordId: keyword_text}"""
    kw_map = {}
    for cid in campaign_ids[:_MAX_CAMPAIGNS]:
        result = _get("/ncc/keywords", {"nccCampaignId": cid}, api_key, secret, customer_id)
        if not result or not isinstance(result, list):
            continue
        for kw in result:
            kid = kw.get("nccKeywordId")
            txt = kw.get("keyword", "").strip()
            if kid and txt:
                kw_map[kid] = txt
    return kw_map


# ── Public API 1: 등록 키워드 목록 (중복 체크용) ─────────────────────────────

def get_registered_keywords(api_key: str, secret: str, customer_id: str) -> set:
    """
    계정 내 등록된 모든 키워드 텍스트 반환.
    제안서에서 "기등록" 여부 표기에 사용.
    반환: set[str]
    """
    path   = _cache_path(f"registered_kws_{customer_id}")
    cached = _load_cache(path)
    if cached is not None:
        return set(cached)

    camp_ids = _fetch_campaign_ids(api_key, secret, customer_id)
    if not camp_ids:
        return set()

    kw_map = _fetch_keyword_map(camp_ids, api_key, secret, customer_id)
    registered = set(kw_map.values())

    _save_cache(path, list(registered))
    print(f"  [계정] 등록 키워드 조회: {len(registered)}개")
    return registered


# ── Public API 2: 실집행 실적 조회 (순위 보정 참고용) ────────────────────────

def get_keyword_actual_stats(api_key: str, secret: str, customer_id: str) -> dict:
    """
    계정 내 등록 키워드의 최근 30일 실적 조회.
    반환: {keyword_text: {"avg_rank": float, "ctr": float, "clicks": int}}

    활용:
      - estimate 순위와 실제 avg_rank 비교해 신뢰도 판단
      - 제안서 비고란에 "실측 N위" 표기 가능
    """
    path   = _cache_path(f"actual_stats_{customer_id}")
    cached = _load_cache(path)
    if cached is not None:
        print(f"  [실적] 캐시 사용: {len(cached)}개 키워드")
        return cached

    camp_ids = _fetch_campaign_ids(api_key, secret, customer_id)
    if not camp_ids:
        return {}

    kw_map = _fetch_keyword_map(camp_ids, api_key, secret, customer_id)
    if not kw_map:
        return {}

    end_dt   = datetime.now()
    start_dt = end_dt - timedelta(days=30)
    kid_list = list(kw_map.keys())

    result = {}
    for i in range(0, len(kid_list), _MAX_KW_PER_REQ):
        batch = kid_list[i : i + _MAX_KW_PER_REQ]
        params = {
            "ids":       ",".join(batch),
            "fields":    "clkCnt,impCnt,ctr,avgRnk",
            "timeRange": json.dumps({
                "since": start_dt.strftime("%Y-%m-%d"),
                "until": end_dt.strftime("%Y-%m-%d"),
            }),
            "breakdown": "keyword",
        }
        stats = _get("/stats", params, api_key, secret, customer_id)
        if not stats:
            continue
        rows = stats if isinstance(stats, list) else stats.get("data", [])
        for item in rows:
            kid    = item.get("id") or item.get("nccKeywordId")
            kw_txt = kw_map.get(kid)
            if not kw_txt:
                continue
            avg_rank = float(item.get("avgRnk", 0) or 0)
            ctr      = float(item.get("ctr", 0) or 0)
            clicks   = int(item.get("clkCnt", 0) or 0)
            if avg_rank > 0 or clicks > 0:
                result[kw_txt] = {
                    "avg_rank": round(avg_rank, 1),
                    "ctr":      round(ctr, 4),
                    "clicks":   clicks,
                }

    _save_cache(path, result)
    print(f"  [실적] 키워드별 실집행 실적 조회 완료: {len(result)}개")
    return result
