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

BASE_URL       = "https://api.searchad.naver.com"
CACHE_DIR      = Path("data/cache/keyword_stats")
CACHE_DAYS     = 7


def _get_cache_path(keyword: str) -> Path:
    safe_kw = re.sub(r'[\\/:*?"<>|]', "_", keyword)
    return CACHE_DIR / f"{safe_kw}.json"


def _load_cache(keyword: str):
    path = _get_cache_path(keyword)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            cached = json.load(f)
        cached_at = datetime.fromisoformat(cached["cached_at"])
        if datetime.now() - cached_at > timedelta(days=CACHE_DAYS):
            return None
        return cached["data"]
    except Exception:
        return None


def _save_cache(keyword: str, data: dict):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _get_cache_path(keyword)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "keyword":   keyword,
                "cached_at": datetime.now().isoformat(),
                "data":      data,
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"  캐시 저장 실패: {e}")


def generate_signature(timestamp, method, uri, secret_key):
    message   = f"{timestamp}.{method}.{uri}"
    signature = base64.b64encode(
        hmac.new(
            secret_key.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256
        ).digest()
    )
    return signature.decode("utf-8")


def normalize_keyword_for_api(keyword: str) -> str:
    k = str(keyword).strip()
    k = re.sub(r"\s+", " ", k)
    compact = k.replace(" ", "")
    return compact


def parse_int_like(value):
    if value is None:
        return 0
    s = str(value).strip().replace(",", "")
    if s in ["", "null", "None"]:
        return 0
    if "<" in s:
        return 10
    try:
        return int(float(s))
    except:
        return 0


def parse_float_like(value):
    if value is None:
        return 0.0
    s = str(value).strip().replace("%", "").replace(",", "")
    if s in ["", "null", "None"]:
        return 0.0
    try:
        return float(s)
    except:
        return 0.0


def normalize_competition(value):
    v = str(value or "").strip().upper()
    if v in ["높음", "HIGH"]:
        return "HIGH"
    if v in ["중간", "보통", "MID", "MEDIUM"]:
        return "MID"
    if v in ["낮음", "LOW"]:
        return "LOW"
    return "MID"


def _fetch_keyword_stat(original_kw, api_key, secret_key, customer_id):
    """API 호출해서 키워드 통계 가져오기"""
    normalized_kw = normalize_keyword_for_api(original_kw)
    if not normalized_kw:
        return None

    uri       = "/keywordstool"
    method    = "GET"
    timestamp = str(int(time.time() * 1000))
    signature = generate_signature(timestamp, method, uri, secret_key)

    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Timestamp":  timestamp,
        "X-API-KEY":    api_key,
        "X-Customer":   str(customer_id),
        "X-Signature":  signature,
    }
    params = {"hintKeywords": normalized_kw, "showDetail": 1}

    try:
        r = requests.get(BASE_URL + uri, headers=headers, params=params, timeout=10)
        if r.status_code != 200:
            return None

        data    = r.json()
        kw_list = data.get("keywordList", [])
        if not kw_list:
            return None

        # relKeyword가 조회한 키워드와 정확히 일치하는 항목 우선 사용
        # (API는 hintKeyword + 연관어를 묶어 반환하므로 첫 번째가 정확한 키워드가 아닐 수 있음)
        item = next(
            (i for i in kw_list
             if normalize_keyword_for_api(i.get("relKeyword", "")) == normalized_kw),
            kw_list[0],
        )
        pc_impr  = parse_int_like(item.get("monthlyPcQcCnt", 0))
        mo_impr  = parse_int_like(item.get("monthlyMobileQcCnt", 0))
        pc_click = parse_float_like(item.get("monthlyAvePcClkCnt", 0))
        mo_click = parse_float_like(item.get("monthlyAveMobileClkCnt", 0))

        # 실제 CTR (%) → 소수로 변환해서 저장
        pc_ctr_raw = parse_float_like(item.get("monthlyAvePcCtr", 0))
        mo_ctr_raw = parse_float_like(item.get("monthlyAveMobileCtr", 0))
        pc_ctr_pct = round(pc_ctr_raw / 100, 6) if pc_ctr_raw > 0 else 0.0
        mo_ctr_pct = round(mo_ctr_raw / 100, 6) if mo_ctr_raw > 0 else 0.0

        # plAvgDepth: 파워링크 평균 게재 순위 (1~10+, 없으면 None)
        pl_avg_depth_raw = item.get("plAvgDepth")
        pl_avg_depth = int(pl_avg_depth_raw) if pl_avg_depth_raw is not None else None

        total_impr  = pc_impr + mo_impr
        total_click = pc_click + mo_click
        ctr = round((total_click / total_impr) * 100, 4) if total_impr > 0 else 0.0

        time.sleep(0.15)

        return {
            "pc_impr":       pc_impr,
            "mo_impr":       mo_impr,
            "pc_click":      pc_click,
            "mo_click":      mo_click,
            "pc_ctr":        pc_ctr_pct,   # 신규: 실제 PC CTR (소수, ex: 0.007)
            "mo_ctr":        mo_ctr_pct,   # 신규: 실제 MO CTR (소수, ex: 0.0113)
            "pl_avg_depth":  pl_avg_depth, # 신규: 파워링크 평균 게재 순위
            "ctr":           ctr,
            "competition":   normalize_competition(item.get("compIdx", "")),
        }
    except Exception:
        return None


def _fetch_keyword_stats_batch(original_kws, api_key, secret_key, customer_id):
    """최대 5개 키워드를 /keywordstool 한 번 호출로 통계 조회."""
    if not original_kws:
        return {}

    norm_map  = {normalize_keyword_for_api(kw): kw for kw in original_kws}
    hint_str  = ",".join(norm_map.keys())
    uri       = "/keywordstool"
    method    = "GET"
    timestamp = str(int(time.time() * 1000))
    signature = generate_signature(timestamp, method, uri, secret_key)
    headers   = {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Timestamp":  timestamp,
        "X-API-KEY":    api_key,
        "X-Customer":   str(customer_id),
        "X-Signature":  signature,
    }
    params = {"hintKeywords": hint_str, "showDetail": 1}

    try:
        r = requests.get(BASE_URL + uri, headers=headers, params=params, timeout=10)
        if r.status_code != 200:
            return {}

        kw_list = r.json().get("keywordList", [])
        result  = {}

        for kw_norm, original_kw in norm_map.items():
            item = next(
                (i for i in kw_list
                 if normalize_keyword_for_api(i.get("relKeyword", "")) == kw_norm),
                None,
            )
            if not item:
                continue

            pc_impr      = parse_int_like(item.get("monthlyPcQcCnt", 0))
            mo_impr      = parse_int_like(item.get("monthlyMobileQcCnt", 0))
            pc_click     = parse_float_like(item.get("monthlyAvePcClkCnt", 0))
            mo_click     = parse_float_like(item.get("monthlyAveMobileClkCnt", 0))
            pc_ctr_raw   = parse_float_like(item.get("monthlyAvePcCtr", 0))
            mo_ctr_raw   = parse_float_like(item.get("monthlyAveMobileCtr", 0))
            total_impr   = pc_impr + mo_impr
            total_click  = pc_click + mo_click
            pl_raw       = item.get("plAvgDepth")

            data = {
                "pc_impr":      pc_impr,
                "mo_impr":      mo_impr,
                "pc_click":     pc_click,
                "mo_click":     mo_click,
                "pc_ctr":       round(pc_ctr_raw / 100, 6) if pc_ctr_raw > 0 else 0.0,
                "mo_ctr":       round(mo_ctr_raw / 100, 6) if mo_ctr_raw > 0 else 0.0,
                "pl_avg_depth": int(pl_raw) if pl_raw is not None else None,
                "ctr":          round((total_click / total_impr) * 100, 4) if total_impr > 0 else 0.0,
                "competition":  normalize_competition(item.get("compIdx", "")),
            }
            result[original_kw] = data

        time.sleep(0.15)
        return result
    except Exception:
        return {}


def get_keyword_stats(keywords, api_key, secret_key, customer_id):
    result     = {}
    cache_hits = 0
    uncached   = []

    for original_kw in keywords:
        cached = _load_cache(original_kw)
        if cached is not None:
            result[original_kw] = cached
            cache_hits += 1
        else:
            uncached.append(original_kw)

    # 미캐시 키워드: 5개씩 배치로 묶어 한 번에 조회 (1/5 API 호출)
    api_calls = 0
    _empty = {
        "pc_impr": 0, "mo_impr": 0,
        "pc_click": 0.0, "mo_click": 0.0,
        "pc_ctr": 0.0, "mo_ctr": 0.0,
        "pl_avg_depth": None,
        "ctr": 0.0, "competition": "MID",
    }
    for i in range(0, len(uncached), 5):
        batch      = uncached[i : i + 5]
        batch_data = _fetch_keyword_stats_batch(batch, api_key, secret_key, customer_id)
        api_calls += 1
        for kw in batch:
            if kw in batch_data:
                _save_cache(kw, batch_data[kw])
                result[kw] = batch_data[kw]
            else:
                result[kw] = dict(_empty)

    if cache_hits > 0 or api_calls > 0:
        print(f"    keywordstool 캐시: {cache_hits}개 / API 배치: {api_calls}회 ({len(uncached)}개)")

    return result


def _call_keywordtool(hint_keywords_str, api_key, secret_key, customer_id, query_type="RELATED"):
    """
    /keywordstool 실제 호출.
    hint_keywords_str: 콤마 구분 키워드 문자열 (최대 5개 권장)
    """
    uri       = "/keywordstool"
    method    = "GET"
    timestamp = str(int(time.time() * 1000))
    signature = generate_signature(timestamp, method, uri, secret_key)
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Timestamp":  timestamp,
        "X-API-KEY":    api_key,
        "X-Customer":   str(customer_id),
        "X-Signature":  signature,
    }
    params = {"hintKeywords": hint_keywords_str, "showDetail": 1, "queryType": query_type}
    try:
        r = requests.get(BASE_URL + uri, headers=headers, params=params, timeout=15)
        if r.status_code != 200:
            return []
        results = []
        for item in r.json().get("keywordList", []):
            kw = item.get("relKeyword", "")
            if not kw:
                continue
            stat_data = {
                "pc_impr":      parse_int_like(item.get("monthlyPcQcCnt", 0)),
                "mo_impr":      parse_int_like(item.get("monthlyMobileQcCnt", 0)),
                "pc_click":     parse_float_like(item.get("monthlyAvePcClkCnt", 0)),
                "mo_click":     parse_float_like(item.get("monthlyAveMobileClkCnt", 0)),
                "pc_ctr":       round(parse_float_like(item.get("monthlyAvePcCtr", 0)) / 100, 6),
                "mo_ctr":       round(parse_float_like(item.get("monthlyAveMobileCtr", 0)) / 100, 6),
                "pl_avg_depth": int(item["plAvgDepth"]) if item.get("plAvgDepth") is not None else None,
                "competition":  normalize_competition(item.get("compIdx", "")),
            }
            _save_cache(kw, stat_data)
            results.append({"keyword": kw, "source": f"naver_{query_type.lower()}", **stat_data})
        time.sleep(0.2)
        return results
    except Exception as e:
        print(f"keywordtool 조회 실패: {e}")
        return []


def get_related_keywords_multi(seed_keywords, api_key, secret_key, customer_id,
                                query_type="RELATED", batch_size=5):
    """
    여러 씨드 키워드를 배치로 묶어서 연관 키워드 조회.
    네이버 키워드도구처럼 최대 5개씩 묶어서 한 번에 조회.
    """
    if not seed_keywords:
        return []
    all_results, seen = [], set()
    for i in range(0, len(seed_keywords), batch_size):
        batch    = [k for k in seed_keywords[i:i+batch_size] if k]
        hint_str = ",".join(normalize_keyword_for_api(k) for k in batch)
        if not hint_str:
            continue
        print(f"    [연관KW] 씨드 묶음: {batch}")
        for r in _call_keywordtool(hint_str, api_key, secret_key, customer_id, query_type):
            if r["keyword"] not in seen:
                seen.add(r["keyword"])
                all_results.append(r)
    return all_results


def get_related_keywords(seed_keyword, api_key, secret_key, customer_id, query_type="RELATED"):
    """기존 단일 씨드 호환 함수."""
    return get_related_keywords_multi(
        [seed_keyword], api_key, secret_key, customer_id, query_type
    )