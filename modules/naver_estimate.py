# -*- coding: utf-8 -*-
"""
naver_estimate.py  (2026-04-10 최종)

로직 확정:
  1. performance/keyword (98개 bid 커브) → 클릭 포화점 = 1위
  2. average-position-bid/keyword → 2~5위 순위별 bid 획득
  3. 커브에서 해당 bid의 노출/클릭/비용 lookup → 순위별 성과

에이스퀘어와 동일한 값 산출 (검증 완료 2026-04-10)
"""
import base64
import hashlib
import hmac
import json
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

BASE_URL   = "https://api.searchad.naver.com"
CACHE_DIR  = Path("data/cache/estimate")
CACHE_DAYS = 7

# 로그스케일 98개 bid (70원 ~ 100,000원, 10원 단위)
_lo, _hi, _n = 70, 100000, 100
SCAN_BIDS = sorted(set(
    int(round(_lo * (_hi / _lo) ** (i / (_n - 1)) / 10) * 10)
    for i in range(_n)
))
SCAN_BIDS[0] = 70


# ── 캐시 ──────────────────────────────────────────────────────────────────────

def _cache_path(keyword: str, suffix: str) -> Path:
    safe = re.sub(r'[\\/:*?"<>|]', "_", keyword)
    return CACHE_DIR / f"{safe}_{suffix}.json"

def _load_cache(path: Path, days: int = CACHE_DAYS):
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            c = json.load(f)
        if datetime.now() - datetime.fromisoformat(c["cached_at"]) > timedelta(days=days):
            return None
        return c["data"]
    except Exception:
        return None

def _save_cache(path: Path, data):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"cached_at": datetime.now().isoformat(), "data": data},
                      f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ── 공통 API 호출 ─────────────────────────────────────────────────────────────

def _normalize(keyword: str) -> str:
    return re.sub(r"\s+", "", str(keyword).strip())

def _headers(api_key: str, secret: str, customer_id: str, uri: str) -> dict:
    ts  = str(int(time.time() * 1000))
    sig = base64.b64encode(
        hmac.new(secret.encode(), f"{ts}.POST.{uri}".encode(), hashlib.sha256).digest()
    ).decode()
    return {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Timestamp": ts, "X-API-KEY": api_key,
        "X-Customer": str(customer_id), "X-Signature": sig,
    }

def _post(uri: str, payload: dict, api_key: str, secret: str, customer_id: str,
          max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            resp = requests.post(
                f"{BASE_URL}{uri}",
                headers=_headers(api_key, secret, customer_id, uri),
                json=payload, timeout=60
            )
            if resp.status_code == 429:
                wait = 2 ** attempt
                print(f"    [API] 429 Rate limit — {wait}초 대기 후 재시도 ({attempt+1}/{max_retries})")
                time.sleep(wait)
                continue
            return resp.json() if resp.ok else None
        except Exception:
            return None
    print(f"    [API] {uri} 재시도 {max_retries}회 초과 — 스킵")
    return None


# ── API 1: performance/keyword 커브 ───────────────────────────────────────────

def _get_curve(keyword: str, device: str,
               api_key: str, secret: str, customer_id: str,
               keywordplus: bool = True) -> list:
    """
    커브 반환 [{bid, impressions, clicks, cost}, ...] (캐시 포함)
    device: "PC" or "MOBILE"
    keywordplus=True: 확장검색 포함 / keywordplus=False: 정확검색 (네이버 키워드 도구 기준)
    keywordplus 명시 전달 필수 — 생략 시 API 기본값은 broad-match(과대추정)
    """
    api_kw = _normalize(keyword)
    # v2: keywordplus=False 시에도 명시적으로 false 전달 — API no-field 기본값이 broad-match임을 확인
    suffix = f"{device}_curve" + ("_kp" if keywordplus else "_v2")
    path = _cache_path(api_kw, suffix)
    cached = _load_cache(path)
    if cached is not None:
        return cached  # 캐시 히트: sleep 불필요

    payload = {"device": device, "key": api_kw, "bids": SCAN_BIDS, "keywordplus": keywordplus}

    result = _post(
        "/estimate/performance/keyword",
        payload,
        api_key, secret, customer_id
    )
    time.sleep(0.15)  # 실제 API 호출 후에만 rate-limit 대기

    if not result:
        return []

    curve = sorted(
        [{"bid": int(e["bid"]), "impressions": int(e.get("impressions", 0)),
          "clicks": int(e.get("clicks", 0)), "cost": int(e.get("cost", 0))}
         for e in result.get("estimate", [])],
        key=lambda x: x["bid"]
    )
    _save_cache(path, curve)
    return curve


# ── API 2: average-position-bid/keyword ───────────────────────────────────────

def _get_avg_position_bids(keyword: str, device: str, ranks: list,
                            api_key: str, secret: str, customer_id: str) -> dict:
    """
    순위별 평균 입찰가 반환 {rank: bid} (캐시 포함)
    캐시가 요청 ranks를 모두 포함하지 않으면 재호출 (rank 1 추가 등 대응).
    """
    api_kw = _normalize(keyword)
    path = _cache_path(api_kw, f"{device}_avgbid")
    cached = _load_cache(path)
    if cached is not None:
        cached_bids = {int(k): v for k, v in cached.items()}
        if all(r in cached_bids for r in ranks):
            return cached_bids  # 캐시 히트: sleep 불필요

    result = _post(
        "/estimate/average-position-bid/keyword",
        {"device": device, "items": [{"key": api_kw, "position": r} for r in ranks]},
        api_key, secret, customer_id
    )
    time.sleep(0.15)  # 실제 API 호출 후에만 rate-limit 대기

    if not result:
        return {}

    rank_bids = {int(e["position"]): int(e["bid"])
                 for e in result.get("estimate", []) if e.get("bid")}
    _save_cache(path, rank_bids)
    return rank_bids


# ── 커브에서 bid lookup ────────────────────────────────────────────────────────

def _lookup_curve(curve: list, bid: int) -> dict:
    """커브에서 bid에 가장 가까운 entry 반환"""
    if not curve:
        return {}
    return min(curve, key=lambda x: abs(x["bid"] - bid))


# ── 핵심: 순위별 성과 추출 ────────────────────────────────────────────────────

def _validate_monotonicity(rank_results: dict) -> dict:
    """
    rank별 bid/clicks 단조성 검증.
    rank 1 → 5 방향으로 bid는 감소, clicks도 감소해야 정상.
    위반 rank는 제거.
    """
    valid      = {}
    prev_bid    = float("inf")
    prev_clicks = float("inf")
    for rank in sorted(rank_results.keys()):
        d      = rank_results[rank]
        bid    = d.get("bid", 0)
        clicks = d.get("clicks", 0)
        if bid > prev_bid:
            print(f"      [단조성 위반] rank {rank} bid={bid:,} > rank {rank-1} bid={int(prev_bid):,} → 제거")
            continue
        if rank > 1 and clicks > prev_clicks:
            print(f"      [단조성 위반] rank {rank} clicks={clicks} > rank {rank-1} clicks={int(prev_clicks)} → 제거")
            continue
        valid[rank]  = d
        prev_bid     = bid
        prev_clicks  = clicks
    return valid


def get_rank_based_estimates(keyword: str, api_key: str, secret: str, customer_id: str,
                              target_ranks: list = None,
                              kt_pc_impr: int = None, kt_mo_impr: int = None) -> dict:
    """
    순위별 예상 노출/클릭/입찰가/비용 반환.

    1위: API 2(average-position-bid) rank=1 bid와 커브 포화점 중 큰 값 사용
    2~5위: API 2 bid를 커브에서 lookup
    missing bid: 정확한 값 별도 호출 후 커브 캐시에도 저장
    단조성 검증: bid/clicks 역전 rank는 자동 제거

    반환: {"PC": {1: {bid,impressions,clicks,cost,cpc,ctr}, ...}, "MO": {...}}
    """
    if target_ranks is None:
        target_ranks = [1, 2, 3, 4, 5]

    api_kw  = _normalize(keyword)
    results = {"PC": {}, "MO": {}}

    for device, api_device in [("PC", "PC"), ("MO", "MOBILE")]:
        # keywordplus=False: 네이버 키워드 도구와 동일한 기준 (정확검색 기준)
        # keywordplus=True는 확장검색 포함으로 MO 클릭을 2배 과대추정하는 문제 확인
        curve = _get_curve(keyword, api_device, api_key, secret, customer_id, keywordplus=False)
        if not curve:
            print(f"    [{keyword}][{device}] 커브 데이터 없음")
            continue

        active = [e for e in curve if e["impressions"] > 0]
        if not active:
            continue

        # 커브 포화점 (1위 후보 #1)
        max_clicks = max(e["clicks"] for e in active)
        sat        = next((e for e in active if e["clicks"] == max_clicks), None)
        sat_bid    = sat["bid"] if sat else 0

        # API 2: rank 1 포함 전체 target_ranks 한번에 조회
        api2_bids = _get_avg_position_bids(keyword, api_device, target_ranks,
                                            api_key, secret, customer_id)

        # 1위 bid: API 2 우선, 없을 때만 포화점 사용
        # max(sat_bid, api2) 방식은 keywordplus 커브의 포화점이 실제 rank1 bid보다
        # 높은 경우 성과를 과대추정하는 문제 발생 (MO 클릭 2배 과대계산 사례 확인)
        api2_rank1 = api2_bids.get(1, 0)
        rank1_bid  = api2_rank1 if api2_rank1 > 0 else sat_bid

        # rank별 확정 bid
        rank_bids: dict[int, int] = {}
        for rank in target_ranks:
            if rank == 1:
                if rank1_bid > 0:
                    rank_bids[1] = rank1_bid
            else:
                b = api2_bids.get(rank, 0)
                if b > 0:
                    rank_bids[rank] = b

        # missing bid 보완 + 커브 캐시 갱신
        curve_bid_set = {e["bid"] for e in curve}
        missing_bids  = [b for b in rank_bids.values() if b not in curve_bid_set]
        if missing_bids:
            extra = _post(
                "/estimate/performance/keyword",
                {"device": api_device, "key": api_kw, "bids": missing_bids, "keywordplus": False},
                api_key, secret, customer_id
            )
            if extra:
                for e in extra.get("estimate", []):
                    curve.append({
                        "bid":         int(e["bid"]),
                        "impressions": int(e.get("impressions", 0)),
                        "clicks":      int(e.get("clicks", 0)),
                        "cost":        int(e.get("cost", 0)),
                    })
                curve.sort(key=lambda x: x["bid"])
                # 보강된 커브를 캐시에 저장 (다음 실행 시 재호출 방지) — _v2 suffix 유지
                _save_cache(_cache_path(api_kw, f"{api_device}_curve_v2"), curve)

        curve_map = {e["bid"]: e for e in curve}

        # rank별 성과 추출
        rank_results: dict[int, dict] = {}
        for rank in sorted(rank_bids.keys()):
            bid   = rank_bids[rank]
            entry = curve_map.get(bid) or _lookup_curve(curve, bid)
            if not entry:
                continue
            clicks = entry["clicks"]
            impr   = entry["impressions"]
            cost   = entry["cost"]
            rank_results[rank] = {
                "bid":         bid,
                "impressions": impr,
                "clicks":      clicks,
                "cost":        cost,
                "cpc":         round(cost / clicks) if clicks > 0 else bid,
                "ctr":         round(clicks / impr, 4) if impr > 0 else 0,
                "click_ratio": round(clicks / impr, 4) if impr > 0 else 0,
            }

        # 단조성 검증
        results[device] = _validate_monotonicity(rank_results)

        r1 = results[device].get(1, {})
        print(f"    [{keyword}][{device}] 1위: bid={r1.get('bid',0):,}원 / 클릭={r1.get('clicks',0):,}"
              f" | API2={api2_rank1:,}원 / 포화점={sat_bid:,}원")

    return results


def get_rank_based_estimates_cached(keyword: str, api_key: str, secret: str, customer_id: str,
                                     target_ranks: list = None,
                                     kt_pc_impr: int = None, kt_mo_impr: int = None,
                                     cache_days: int = CACHE_DAYS) -> dict:
    """순위별 Estimate 결과 (결과 캐시 포함).
    cache key suffix _v4: target_rank 성과 데이터 일관성 수정 반영.
    """
    path = _cache_path(_normalize(keyword), "rank_estimates_v5")
    cached = _load_cache(path, cache_days)
    if cached is not None:
        return cached
    data = get_rank_based_estimates(keyword, api_key, secret, customer_id,
                                     target_ranks, kt_pc_impr, kt_mo_impr)
    if data:
        _save_cache(path, data)
    return data


def get_estimate_performance(keyword: str, bids: list,
                              api_key: str, secret: str, customer_id: str,
                              keywordplus: bool = True) -> list:
    """기존 호환용: bid별 PC+MO 통합 성과 반환."""
    api_kw = _normalize(keyword)
    pc = {e["bid"]: e for e in _get_curve(api_kw, "PC",     api_key, secret, customer_id, keywordplus)}
    mo = {e["bid"]: e for e in _get_curve(api_kw, "MOBILE", api_key, secret, customer_id, keywordplus)}
    results = []
    for bid in sorted(set(bids)):
        p = pc.get(bid, {"impressions":0,"clicks":0,"cost":0})
        m = mo.get(bid, {"impressions":0,"clicks":0,"cost":0})
        results.append({
            "bid": bid,
            "pc_impressions": p["impressions"], "pc_clicks": p["clicks"], "pc_cost": p["cost"],
            "mo_impressions": m["impressions"], "mo_clicks": m["clicks"], "mo_cost": m["cost"],
            "impressions": p["impressions"]+m["impressions"],
            "clicks":      p["clicks"]+m["clicks"],
            "cost":        p["cost"]+m["cost"],
        })
    return results


# ── 배치 조회: 중간값 입찰가 / 노출 최소 입찰가 ─────────────────────────────

def _batch_estimate_query(uri: str, keywords: list, device: str,
                           cache_suffix: str,
                           api_key: str, secret: str, customer_id: str,
                           chunk_size: int = 100) -> dict:
    """
    중간값/노출최소 입찰가 공통 배치 조회 헬퍼.
    반환: {keyword: bid}
    """
    result   = {}
    uncached = []
    for kw in keywords:
        path   = _cache_path(_normalize(kw), f"{device}_{cache_suffix}")
        cached = _load_cache(path)
        if cached is not None:
            result[kw] = cached
        else:
            uncached.append(kw)

    for i in range(0, len(uncached), chunk_size):
        batch     = uncached[i : i + chunk_size]
        norm_map  = {_normalize(kw): kw for kw in batch}   # 정규화키 → 원본
        resp = _post(
            uri,
            {"device": device, "period": "MONTH",
             "items": list(norm_map.keys())},
            api_key, secret, customer_id
        )
        if not resp:
            continue
        for e in resp.get("estimate", []):
            kw_norm = str(e.get("keyword", ""))
            bid     = int(e.get("bid", 0))
            if bid <= 0:
                continue
            orig = norm_map.get(kw_norm, kw_norm)
            result[orig] = bid
            _save_cache(_cache_path(kw_norm, f"{device}_{cache_suffix}"), bid)

    return result


def get_median_bid_batch(keywords: list, device: str,
                          api_key: str, secret: str, customer_id: str) -> dict:
    """
    키워드 리스트의 중간값 입찰가 배치 조회.
    device: "PC" or "MOBILE"
    반환: {keyword: median_bid}
    """
    if not keywords:
        return {}
    return _batch_estimate_query(
        "/estimate/median-bid/keyword", keywords, device,
        "medianbid", api_key, secret, customer_id
    )


def get_exposure_min_bid_batch(keywords: list, device: str,
                                api_key: str, secret: str, customer_id: str) -> dict:
    """
    키워드 리스트의 노출 최소 입찰가 배치 조회.
    device: "PC" or "MOBILE"
    반환: {keyword: exposure_min_bid}
    """
    if not keywords:
        return {}
    return _batch_estimate_query(
        "/estimate/exposure-minimum-bid/keyword", keywords, device,
        "expminbid", api_key, secret, customer_id
    )