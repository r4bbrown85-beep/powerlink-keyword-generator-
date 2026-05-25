# -*- coding: utf-8 -*-
"""
naver_reporter.py — Naver SA 실적 리포트 API 모듈

지원 리포트:
  1. 캠페인별 실적    : get_campaign_stats(days=7)
  2. 광고그룹별 실적  : get_adgroup_stats(campaign_id, days=7)
  3. 키워드별 실적    : get_keyword_stats(days=7)

반환 형식: List[dict] — 구글 시트에 바로 쓸 수 있는 행 목록
"""
import base64
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timedelta

import requests

BASE_URL = "https://api.searchad.naver.com"


# ── 인증 ────────────────────────────────────────────────────────────────────

def _headers(api_key, secret, customer_id, method, uri):
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


def _get(uri, params, creds):
    api_key, secret, customer_id = creds
    try:
        resp = requests.get(
            f"{BASE_URL}{uri}",
            headers=_headers(api_key, secret, customer_id, "GET", uri),
            params=params,
            timeout=30,
        )
        if resp.ok:
            return resp.json()
        print(f"  API 오류 {resp.status_code}: {resp.text[:200]}")
        return None
    except Exception as e:
        print(f"  요청 실패: {e}")
        return None


def _date_range(days: int):
    end   = datetime.now()
    start = end - timedelta(days=days - 1)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


# ── 캠페인 목록 ──────────────────────────────────────────────────────────────

def _get_campaigns(creds) -> list:
    result = _get("/ncc/campaigns", {"searchType": "ALL"}, creds)
    if not result or not isinstance(result, list):
        return []
    return result


def _get_adgroups(campaign_id: str, creds) -> list:
    result = _get("/ncc/adgroups", {"nccCampaignId": campaign_id}, creds)
    if not result or not isinstance(result, list):
        return []
    return result


def _get_keywords_for_adgroup(adgroup_id: str, creds) -> list:
    result = _get("/ncc/keywords", {"nccAdgroupId": adgroup_id}, creds)
    if not result or not isinstance(result, list):
        return []
    return result


# ── 실적 조회 공통 ───────────────────────────────────────────────────────────

def _fetch_stats(ids: list, fields: list, breakdown: str,
                 since: str, until: str, creds) -> list:
    all_rows = []
    chunk_size = 50
    for i in range(0, len(ids), chunk_size):
        batch = ids[i:i+chunk_size]
        params = {
            "ids":       ",".join(batch),
            "fields":    json.dumps(fields),      # API requires JSON array
            "timeRange": json.dumps({"since": since, "until": until}),
            "breakdown": breakdown,
        }
        result = _get("/stats", params, creds)
        if not result:
            continue
        rows = result if isinstance(result, list) else result.get("data", [])
        all_rows.extend(rows)
    return all_rows


# ── Public: 캠페인별 실적 ────────────────────────────────────────────────────

def get_campaign_stats(creds, days: int = 7) -> list:
    """
    캠페인별 실적 요약 (adgroup → campaign 집계).
    반환: [{"캠페인명": ..., "노출수": ..., "클릭수": ..., "광고비": ...,
            "CTR(%)": ..., "CPC(원)": ..., "기간": ...}, ...]
    """
    since, until = _date_range(days)
    campaigns    = _get_campaigns(creds)
    if not campaigns:
        print("  캠페인 없음")
        return []

    # adgroup ID → campaign name 맵
    agid_to_camp = {}
    all_agids    = []
    for camp in campaigns:
        cid   = camp["nccCampaignId"]
        cname = camp.get("campaignName", cid)
        for ag in _get_adgroups(cid, creds):
            agid = ag.get("nccAdgroupId")
            if agid:
                agid_to_camp[agid] = cname
                all_agids.append(agid)

    if not all_agids:
        print("  광고그룹 없음")
        return []

    rows = _fetch_stats(
        all_agids,
        ["impCnt", "clkCnt", "salesAmt", "ctr", "avgCpc"],
        "adGroup", since, until, creds
    )

    # campaign 기준으로 집계
    agg: dict = {}
    for r in rows:
        agid  = r.get("id") or r.get("nccAdgroupId") or ""
        cname = agid_to_camp.get(agid, agid)
        if cname not in agg:
            agg[cname] = {"노출수": 0, "클릭수": 0, "광고비": 0}
        agg[cname]["노출수"] += int(r.get("impCnt", 0) or 0)
        agg[cname]["클릭수"] += int(r.get("clkCnt", 0) or 0)
        agg[cname]["광고비"] += int(r.get("salesAmt", 0) or 0)

    result = []
    for cname, d in agg.items():
        ctr = round(d["클릭수"] / d["노출수"] * 100, 2) if d["노출수"] > 0 else 0
        cpc = round(d["광고비"] / d["클릭수"]) if d["클릭수"] > 0 else 0
        result.append({
            "기간":    f"{since}~{until}",
            "캠페인명": cname,
            "노출수":  d["노출수"],
            "클릭수":  d["클릭수"],
            "광고비":  d["광고비"],
            "CTR(%)":  ctr,
            "CPC(원)": cpc,
        })
    result.sort(key=lambda x: x["광고비"], reverse=True)
    print(f"  캠페인별 실적: {len(result)}개")
    return result


# ── Public: 키워드별 실적 ────────────────────────────────────────────────────

def get_keyword_stats(creds, days: int = 7, top_n: int = 100) -> list:
    """
    키워드별 실적. 광고비 순 top_n 반환.
    반환: [{"키워드": ..., "캠페인명": ..., "노출수": ..., "클릭수": ...,
            "광고비": ..., "CTR": ..., "CPC": ..., "평균순위": ...}, ...]
    """
    since, until = _date_range(days)
    campaigns    = _get_campaigns(creds)
    if not campaigns:
        return []

    camp_map = {c["nccCampaignId"]: c.get("campaignName", c["nccCampaignId"])
                for c in campaigns}

    # 전체 캠페인 → adgroup → 키워드 수집
    kw_map   = {}   # nccKeywordId → {text, campaign_name}
    all_kids = []
    for camp in campaigns:
        cid   = camp["nccCampaignId"]
        cname = camp_map.get(cid, cid)
        for ag in _get_adgroups(cid, creds):
            agid = ag.get("nccAdgroupId")
            if not agid:
                continue
            for kw in _get_keywords_for_adgroup(agid, creds):
                kid = kw.get("nccKeywordId")
                txt = kw.get("keyword", "").strip()
                if kid and txt:
                    kw_map[kid]  = {"text": txt, "campaign": cname}
                    all_kids.append(kid)

    if not all_kids:
        print("  등록 키워드 없음")
        return []

    rows = _fetch_stats(
        all_kids,
        ["impCnt", "clkCnt", "salesAmt", "ctr", "avgCpc", "avgRnk"],
        "keyword", since, until, creds
    )

    result = []
    for r in rows:
        kid  = r.get("id") or r.get("nccKeywordId") or ""
        info = kw_map.get(kid, {})
        imps = int(r.get("impCnt", 0) or 0)
        clks = int(r.get("clkCnt", 0) or 0)
        cost = int(r.get("salesAmt", 0) or 0)
        ctr  = round(float(r.get("ctr", 0) or 0) * 100, 2)
        cpc  = round(float(r.get("avgCpc", 0) or 0), 0)
        rank = round(float(r.get("avgRnk", 0) or 0), 1)
        if imps == 0 and clks == 0 and cost == 0:
            continue
        result.append({
            "기간":    f"{since}~{until}",
            "캠페인명": info.get("campaign", ""),
            "키워드":  info.get("text", kid),
            "노출수":  imps,
            "클릭수":  clks,
            "광고비":  cost,
            "CTR(%)":  ctr,
            "CPC(원)": int(cpc),
            "평균순위": rank if rank > 0 else "",
        })

    result.sort(key=lambda x: x["광고비"], reverse=True)
    result = result[:top_n]
    print(f"  키워드별 실적: {len(result)}개 (top {top_n})")
    return result


# ── Public: 일별 트렌드 ──────────────────────────────────────────────────────

def get_daily_trend(creds, days: int = 30) -> list:
    """
    전체 계정 일별 실적 트렌드.
    반환: [{"날짜": ..., "노출수": ..., "클릭수": ..., "광고비": ...,
            "CTR(%)": ..., "CPC(원)": ...}, ...]
    """
    since, until = _date_range(days)
    campaigns    = _get_campaigns(creds)
    if not campaigns:
        return []

    camp_ids = [c["nccCampaignId"] for c in campaigns]

    daily: dict = {}
    # adgroup IDs 수집
    all_agids = []
    for cid in camp_ids:
        for ag in _get_adgroups(cid, creds):
            agid = ag.get("nccAdgroupId")
            if agid:
                all_agids.append(agid)

    for agid in all_agids[:30]:   # 과도한 API 호출 방지
        params = {
            "ids":       agid,
            "fields":    json.dumps(["impCnt", "clkCnt", "salesAmt"]),
            "timeRange": json.dumps({"since": since, "until": until}),
            "breakdown": "day",
        }
        result = _get("/stats", params, creds)
        if not result:
            continue
        rows = result if isinstance(result, list) else result.get("data", [])
        for r in rows:
            dt   = r.get("date") or r.get("dt", "")
            if not dt:
                continue
            if dt not in daily:
                daily[dt] = {"노출수": 0, "클릭수": 0, "광고비": 0}
            daily[dt]["노출수"] += int(r.get("impCnt", 0) or 0)
            daily[dt]["클릭수"] += int(r.get("clkCnt", 0) or 0)
            daily[dt]["광고비"] += int(r.get("salesAmt", 0) or 0)

    result = []
    for dt in sorted(daily.keys()):
        d   = daily[dt]
        ctr = round(d["클릭수"] / d["노출수"] * 100, 2) if d["노출수"] > 0 else 0
        cpc = round(d["광고비"] / d["클릭수"]) if d["클릭수"] > 0 else 0
        result.append({
            "날짜":    dt,
            "노출수":  d["노출수"],
            "클릭수":  d["클릭수"],
            "광고비":  d["광고비"],
            "CTR(%)":  ctr,
            "CPC(원)": cpc,
        })

    print(f"  일별 트렌드: {len(result)}일")
    return result


# ── 편의 함수 ────────────────────────────────────────────────────────────────

def get_creds_from_env() -> tuple:
    """환경변수에서 Naver SA 인증 정보 읽기"""
    from dotenv import load_dotenv
    load_dotenv()
    return (
        os.getenv("NAVER_API_KEY", ""),
        os.getenv("NAVER_SECRET_KEY", ""),
        os.getenv("NAVER_CUSTOMER_ID", ""),
    )
