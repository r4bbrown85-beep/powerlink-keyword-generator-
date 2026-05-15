# -*- coding: utf-8 -*-
"""
bid_simulator.py
카테고리 설정을 client_profile.json에서 동적으로 읽어옴.
예산 배정은 강제 비율이 아닌 효율 기반:
  1. brand 타입 키워드 → min_keywords 수만큼 무조건 상위 확보
  2. 나머지 카테고리 min_keywords 보장
  3. 남은 예산은 전체 효율(weighted_score) 순으로 배정
  4. 업그레이드로 잔여 예산 소진
"""
import json
import os
from modules.naver_estimate import (
    get_estimate_performance, get_rank_based_estimates,
    get_rank_based_estimates_cached,
    get_median_bid_batch, get_exposure_min_bid_batch,
)

# ── 기본값 (profile에 keyword_categories 없을 때 fallback) ────────
_DEFAULT_CATEGORIES = [
    {"name": "브랜드 키워드", "type": "brand",      "priority": 1.30,
     "min_keywords": 10, "target_rank": 2, "max_rank": 3,
     "max_single_ratio": 0.20, "cpc_factor": 1.10, "color": "BDD7EE"},
    {"name": "상품 키워드",   "type": "product",    "priority": 1.22,
     "min_keywords": 5,  "target_rank": 3, "max_rank": 5,
     "max_single_ratio": 0.15, "cpc_factor": 1.05, "color": "C6EFCE"},
    {"name": "일반 키워드",   "type": "general",    "priority": 1.00,
     "min_keywords": 5,  "target_rank": 4, "max_rank": 5,
     "max_single_ratio": 0.15, "cpc_factor": 1.00, "color": "FFF2CC"},
    {"name": "경쟁사 키워드", "type": "competitor", "priority": 0.88,
     "min_keywords": 0,  "target_rank": 5, "max_rank": 5,
     "max_single_ratio": 0.04, "cpc_factor": 0.90, "color": "FCE4D6"},
]

TYPE_WEIGHT = {
    "BRAND":      1.25,
    "SERVICE":    1.18,
    "INTENT":     1.10,
    "GENERIC":    1.00,
    "COMPETITOR": 0.88,
}

FALLBACK_CPC_BY_COMPETITION = {
    "HIGH": 600,
    "MID":  350,
    "LOW":  150,
}

PC_CTR_TABLE = {
    1: 0.0409, 2: 0.0366, 3: 0.0331, 4: 0.0304, 5: 0.0277,
    6: 0.0220, 7: 0.0170, 8: 0.0130, 9: 0.0090, 10: 0.0060,
}
MO_CTR_TABLE = {
    1: 0.0326, 2: 0.0247, 3: 0.0198, 4: 0.0175, 5: 0.0140,
    6: 0.0105, 7: 0.0080, 8: 0.0060, 9: 0.0045, 10: 0.0030,
}


def _load_category_config():
    try:
        with open("data/client_profile.json", "r", encoding="utf-8") as f:
            profile = json.load(f)
        cats = profile.get("keyword_categories", [])
        if cats:
            return cats
    except Exception:
        pass
    return _DEFAULT_CATEGORIES


def _get_cat_map():
    return {c["name"]: c for c in _load_category_config()}


def _norm_category(category, cat_map=None):
    category = str(category or "").strip()
    if cat_map is None:
        cat_map = _get_cat_map()
    if category in cat_map:
        return category
    for name, cfg in cat_map.items():
        if cfg.get("type") == "general":
            return name
    return list(cat_map.keys())[0] if cat_map else "일반 키워드"


def _norm_keyword_type(keyword_type):
    keyword_type = str(keyword_type or "GENERIC").strip().upper()
    return keyword_type if keyword_type in TYPE_WEIGHT else "GENERIC"


def _norm_competition(comp):
    comp = str(comp or "MID").upper().strip()
    return comp if comp in ["HIGH", "MID", "LOW"] else "MID"


def _to_float(v, default=0.0):
    try:
        if v is None or v == "":
            return float(default)
        return float(v)
    except Exception:
        return float(default)


def _clamp(v, min_v, max_v):
    return max(min_v, min(v, max_v))


def _safe_ratio(num, den, default=0.0):
    if den <= 0:
        return default
    return num / den


def _get_api_keys():
    return (
        os.getenv("NAVER_API_KEY", ""),
        os.getenv("NAVER_SECRET_KEY", ""),
        os.getenv("NAVER_CUSTOMER_ID", ""),
    )


def _build_bid_candidates(keyword_row, cat_map=None):
    """
    로그스케일 98개 bid (70~100,000원) 반환.
    API 1회로 전체 커브를 받을 수 있으므로 고경쟁 키워드도 정확하게 커버.
    (2026-04-10: 새 estimate API 적용으로 전면 교체)
    """
    from modules.naver_estimate import SCAN_BIDS
    return SCAN_BIDS


def get_priority_weight(keyword_row, cat_map=None):
    if cat_map is None:
        cat_map = _get_cat_map()
    category     = _norm_category(keyword_row.get("category", ""), cat_map)
    keyword_type = _norm_keyword_type(keyword_row.get("keyword_type", "GENERIC"))
    rec_score    = _to_float(keyword_row.get("recommendation_score", 50), 50.0)
    volume       = _to_float(keyword_row.get("monthlySearchVolume", 0), 0.0)
    cat_cfg      = cat_map.get(category, {})
    cat_type     = cat_cfg.get("type", "general")

    weight  = float(cat_cfg.get("priority", 1.0))
    weight *= TYPE_WEIGHT.get(keyword_type, 1.0)

    if cat_type == "brand":
        weight *= 1.15

    if rec_score >= 130:
        weight *= 1.18
    elif rec_score >= 110:
        weight *= 1.12
    elif rec_score >= 90:
        weight *= 1.07
    elif rec_score <= 40:
        weight *= 0.90

    if volume >= 30000:
        weight *= 1.10
    elif volume >= 10000:
        weight *= 1.06
    elif volume >= 3000:
        weight *= 1.03
    elif volume <= 100:
        weight *= 0.92

    return weight


def _estimate_rank_from_estimate_results(estimate_results):
    """
    입찰가별 PC/MO 순위를 각각 독립적으로 계산.
    PC 순위: PC 클릭수 기준으로만 계산
    MO 순위: MO 클릭수 기준으로만 계산
    → 같은 입찰가라도 PC 1위 / MO 4위 이런 결과가 정확히 반영됨
    """
    if not estimate_results:
        return {}

    valid = [(e["bid"], e["pc_clicks"], e["mo_clicks"])
             for e in estimate_results if e["clicks"] > 0]
    if not valid:
        return {}

    max_pc = max(v[1] for v in valid) if valid else 1
    max_mo = max(v[2] for v in valid) if valid else 1

    rank_map = {}
    for bid, pc_clk, mo_clk in valid:
        # PC 순위: PC 클릭 비율로만 계산 (MO 영향 없음)
        pc_ratio = _safe_ratio(pc_clk, max(max_pc, 1), 0.0)
        pc_rank  = max(1, min(10, int(10 - pc_ratio * 9)))

        # MO 순위: MO 클릭 비율로만 계산 (PC 영향 없음)
        mo_ratio = _safe_ratio(mo_clk, max(max_mo, 1), 0.0)
        mo_rank  = max(1, min(10, int(10 - mo_ratio * 9)))

        # 통합 순위는 참고용 (예산 배분 시 가중 평균)
        # MO 검색량이 압도적으로 많으므로 MO 순위에 가중치
        total_rank = max(1, min(10, round(pc_rank * 0.3 + mo_rank * 0.7)))

        rank_map[bid] = (total_rank, pc_rank, mo_rank)
    return rank_map


def _estimate_rank_from_ctr_fallback(pc_clicks, pc_impr, mo_clicks, mo_impr):
    pc_ctr  = _safe_ratio(pc_clicks, pc_impr, 0.0)
    mo_ctr  = _safe_ratio(mo_clicks, mo_impr, 0.0)
    pc_rank = 10
    for rank in range(1, 11):
        if pc_ctr >= PC_CTR_TABLE.get(rank, 0.005):
            pc_rank = rank
            break
    mo_rank = 10
    for rank in range(1, 11):
        if mo_ctr >= MO_CTR_TABLE.get(rank, 0.003):
            mo_rank = rank
            break
    return max(1, min(10, round((pc_rank + mo_rank) / 2))), pc_rank, mo_rank


def _cap_options_by_budget(options, category, total_budget, cat_map=None):
    if cat_map is None:
        cat_map = _get_cat_map()
    cat_cfg     = cat_map.get(category, {})
    max_ratio   = float(cat_cfg.get("max_single_ratio", 0.15))
    max_cost    = total_budget * max_ratio
    target_rank = cat_cfg.get("target_rank")
    max_rank    = cat_cfg.get("max_rank")

    # 1. 예산 상한 필터
    capped = [opt for opt in options if opt["cost"] <= max_cost]
    if not capped and options:
        capped = [min(options, key=lambda x: x["cost"])]

    if not capped:
        return []

    # 2. max_rank 필터: PC/MO 중 하나라도 달성 가능하면 유지
    if max_rank:
        is_fallback = capped[0].get("is_fallback", True)
        if not is_fallback:
            # Estimate 성공: PC 또는 MO 중 하나가 max_rank 이내면 유지
            rank_filtered = [opt for opt in capped
                             if opt["rank_pc"] <= max_rank or opt["rank_mo"] <= max_rank]
            if rank_filtered:
                capped = rank_filtered
            else:
                return []  # PC/MO 모두 달성 불가 → 제외
        else:
            # Fallback: 느슨하게 적용
            rank_filtered = [opt for opt in capped
                             if opt["rank_pc"] <= max_rank or opt["rank_mo"] <= max_rank]
            if rank_filtered:
                capped = rank_filtered

    # 3. target_rank에 가장 가까운 옵션 우선 정렬
    #    MO 검색량이 많으므로 MO 순위 기준 우선, PC는 보조
    if target_rank and capped:
        capped.sort(key=lambda x: (
            abs(x["rank_mo"] - target_rank) * 0.7 + abs(x["rank_pc"] - target_rank) * 0.3,
            -x["weighted_score"],
            x["cost"]
        ))

    return capped


def _build_fallback_options(keyword_row, total_budget=5_000_000, cat_map=None,
                             median_bid_pc=0, median_bid_mo=0,
                             exposure_min_bid_pc=0, exposure_min_bid_mo=0):
    """
    Estimate API 데이터 없는 키워드 처리.
    노출/클릭/비용은 0으로 처리하고 입찰가만 제안.
    예산 계산에서 제외되지만 제안서에는 포함됨.

    입찰가 결정 우선순위:
      브랜드: 70원 고정
      일반/상품/경쟁사:
        1. median_bid (실제 시장 중간값) ← 가장 정확
        2. max(median_bid, exposure_min_bid) ← 노출 최소 입찰가 이상 보장
        3. 위 데이터 없으면 competition 기반 fallback
    """
    if cat_map is None:
        cat_map = _get_cat_map()
    keyword      = keyword_row.get("keyword", "")
    category     = _norm_category(keyword_row.get("category", ""), cat_map)
    keyword_type = _norm_keyword_type(keyword_row.get("keyword_type", "GENERIC"))
    competition  = _norm_competition(keyword_row.get("competition", "MID"))
    cat_cfg      = cat_map.get(category, {})

    pc_impr = _to_float(keyword_row.get("pc_impr", 0))
    mo_impr = _to_float(keyword_row.get("mo_impr", 0))

    if pc_impr <= 0 and mo_impr <= 0:
        return []

    priority_weight = get_priority_weight(keyword_row, cat_map)
    cat_type        = cat_cfg.get("type", "general")

    if cat_type == "brand":
        pc_bid = mo_bid = bid = 70
        target_rank = 1
    else:
        base_cpc    = FALLBACK_CPC_BY_COMPETITION.get(competition, 350)
        base_cpc   *= float(cat_cfg.get("cpc_factor", 1.0))
        base_bid    = int(round(base_cpc / 10) * 10)
        target_rank = int(cat_cfg.get("target_rank", 5))

        # PC 입찰가: median → max(median, exposure_min) → base
        if median_bid_pc > 0:
            pc_bid = int(round(median_bid_pc / 10) * 10)
        else:
            pc_bid = base_bid
        if exposure_min_bid_pc > 0:
            pc_bid = max(pc_bid, exposure_min_bid_pc)
        pc_bid = max(70, pc_bid)

        # MO 입찰가: median → max(median, exposure_min) → base
        if median_bid_mo > 0:
            mo_bid = int(round(median_bid_mo / 10) * 10)
        else:
            mo_bid = base_bid
        if exposure_min_bid_mo > 0:
            mo_bid = max(mo_bid, exposure_min_bid_mo)
        mo_bid = max(70, mo_bid)

        bid = max(pc_bid, mo_bid)

    options = [{
        "keyword":         keyword,
        "category":        category,
        "keyword_type":    keyword_type,
        "bid":             bid,
        "pc_bid":          pc_bid,
        "mo_bid":          mo_bid,
        "rank":            target_rank,
        "rank_pc":         target_rank,
        "rank_mo":         target_rank,
        "impressions":     0,
        "clicks":          0,
        "ctr":             0.0,
        "cpc":             0,
        "cost":            0,
        "pc_impressions":  int(pc_impr),
        "pc_clicks":       0,
        "pc_ctr":          0.0,
        "pc_cpc":          0,
        "pc_cost":         0,
        "mo_impressions":  int(mo_impr),
        "mo_clicks":       0,
        "mo_ctr":          0.0,
        "mo_cpc":          0,
        "mo_cost":         0,
        "anchor_bid":      bid,
        "priority_weight": round(priority_weight, 4),
        "efficiency":      0.0,
        "weighted_score":  0.0,
        "is_fallback":     True,
    }]
    return options


def build_keyword_options(keyword_row, total_budget=5_000_000, cat_map=None,
                           median_bid_pc=0, median_bid_mo=0,
                           exposure_min_bid_pc=0, exposure_min_bid_mo=0):
    if cat_map is None:
        cat_map = _get_cat_map()
    keyword         = keyword_row.get("keyword", "")
    category        = _norm_category(keyword_row.get("category", ""), cat_map)
    keyword_type    = _norm_keyword_type(keyword_row.get("keyword_type", "GENERIC"))
    priority_weight = get_priority_weight(keyword_row, cat_map)

    api_key, secret, customer_id = _get_api_keys()

    # ── API 2: 순위별 정확한 입찰가 데이터 (PC/MO 독립 최적화) ──────────────
    rank_data = get_rank_based_estimates_cached(keyword, api_key, secret, customer_id,
                                                 target_ranks=[1, 2, 3, 4, 5])
    if rank_data:
        # JSON 캐시: int 키가 string으로 직렬화되므로 복원
        pc_ranks = {int(k): v for k, v in rank_data.get("PC", {}).items()}
        mo_ranks = {int(k): v for k, v in rank_data.get("MO", {}).items()}

        options = []
        for rank in [1, 2, 3, 4, 5]:
            pc_data = pc_ranks.get(rank, {})
            mo_data = mo_ranks.get(rank, {})

            pc_bid    = int(pc_data.get("bid", 0) or 0)
            mo_bid    = int(mo_data.get("bid", 0) or 0)
            pc_impr   = int(pc_data.get("impressions", 0) or 0)
            pc_clicks = int(pc_data.get("clicks", 0) or 0)
            pc_cost   = int(pc_data.get("cost", 0) or 0)
            mo_impr   = int(mo_data.get("impressions", 0) or 0)
            mo_clicks = int(mo_data.get("clicks", 0) or 0)
            mo_cost   = int(mo_data.get("cost", 0) or 0)

            total_impr   = pc_impr + mo_impr
            total_clicks = pc_clicks + mo_clicks
            total_cost   = pc_cost + mo_cost

            if total_clicks == 0:
                continue

            efficiency     = _safe_ratio(total_clicks, total_cost, 0.0)
            traffic_bonus  = _safe_ratio(total_clicks, max(total_impr, 1), 0.0)
            weighted_score = (efficiency * 0.82 + traffic_bonus * 0.18) * priority_weight

            options.append({
                "keyword":         keyword,
                "category":        category,
                "keyword_type":    keyword_type,
                "bid":             pc_bid or mo_bid,
                "pc_bid":          pc_bid,
                "mo_bid":          mo_bid,
                "rank":            rank,
                "rank_pc":         rank if pc_bid > 0 else 0,
                "rank_mo":         rank if mo_bid > 0 else 0,
                "impressions":     total_impr,
                "clicks":          total_clicks,
                "ctr":             round(_safe_ratio(total_clicks, total_impr), 4),
                "cpc":             int(round(_safe_ratio(total_cost, total_clicks))),
                "cost":            total_cost,
                "pc_impressions":  pc_impr,
                "pc_clicks":       pc_clicks,
                "pc_ctr":          round(_safe_ratio(pc_clicks, pc_impr), 4),
                "pc_cpc":          int(round(_safe_ratio(pc_cost, pc_clicks))),
                "pc_cost":         pc_cost,
                "mo_impressions":  mo_impr,
                "mo_clicks":       mo_clicks,
                "mo_ctr":          round(_safe_ratio(mo_clicks, mo_impr), 4),
                "mo_cpc":          int(round(_safe_ratio(mo_cost, mo_clicks))),
                "mo_cost":         mo_cost,
                "anchor_bid":      0,
                "priority_weight": round(priority_weight, 4),
                "efficiency":      efficiency,
                "weighted_score":  weighted_score,
                "is_fallback":     False,
            })

        if options:
            options.sort(key=lambda x: (-x["weighted_score"], x["rank"], x["cost"]))
            return _cap_options_by_budget(options, category, total_budget, cat_map)

    # ── Fallback: API 1 커브 기반 추정 ───────────────────────────────────────
    bid_candidates   = _build_bid_candidates(keyword_row, cat_map)
    estimate_results = get_estimate_performance(keyword, bid_candidates, api_key, secret, customer_id)

    if not estimate_results or all(est["clicks"] == 0 for est in estimate_results):
        return _build_fallback_options(keyword_row, total_budget, cat_map,
                                       median_bid_pc, median_bid_mo,
                                       exposure_min_bid_pc, exposure_min_bid_mo)

    rank_map = _estimate_rank_from_estimate_results(estimate_results)
    options  = []

    for est in estimate_results:
        bid          = est["bid"]
        pc_impr      = est["pc_impressions"]
        pc_clicks    = est["pc_clicks"]
        pc_cost      = est["pc_cost"]
        mo_impr      = est["mo_impressions"]
        mo_clicks    = est["mo_clicks"]
        mo_cost      = est["mo_cost"]
        total_impr   = est["impressions"]
        total_clicks = est["clicks"]
        total_cost   = est["cost"]
        if total_clicks == 0:
            continue

        rank_info      = rank_map.get(bid, (5, 5, 5))
        efficiency     = _safe_ratio(total_clicks, total_cost, 0.0)
        traffic_bonus  = _safe_ratio(total_clicks, max(total_impr, 1), 0.0)
        weighted_score = (efficiency * 0.82 + traffic_bonus * 0.18) * priority_weight

        options.append({
            "keyword":         keyword,
            "category":        category,
            "keyword_type":    keyword_type,
            "bid":             bid,
            "pc_bid":          bid,
            "mo_bid":          bid,
            "rank":            rank_info[0],
            "rank_pc":         rank_info[1],
            "rank_mo":         rank_info[2],
            "impressions":     total_impr,
            "clicks":          total_clicks,
            "ctr":             round(_safe_ratio(total_clicks, total_impr), 4),
            "cpc":             int(round(_safe_ratio(total_cost, total_clicks))),
            "cost":            total_cost,
            "pc_impressions":  pc_impr,
            "pc_clicks":       pc_clicks,
            "pc_ctr":          round(_safe_ratio(pc_clicks, pc_impr), 4),
            "pc_cpc":          int(round(_safe_ratio(pc_cost, pc_clicks))),
            "pc_cost":         pc_cost,
            "mo_impressions":  mo_impr,
            "mo_clicks":       mo_clicks,
            "mo_ctr":          round(_safe_ratio(mo_clicks, mo_impr), 4),
            "mo_cpc":          int(round(_safe_ratio(mo_cost, mo_clicks))),
            "mo_cost":         mo_cost,
            "anchor_bid":      0,
            "priority_weight": round(priority_weight, 4),
            "efficiency":      efficiency,
            "weighted_score":  weighted_score,
            "is_fallback":     False,
        })

    if not options:
        return _build_fallback_options(keyword_row, total_budget, cat_map)

    options.sort(key=lambda x: (-x["weighted_score"], x["rank"], x["cost"]))
    return _cap_options_by_budget(options, category, total_budget, cat_map)



def _real_cost(opt):
    """PC캠페인 + MO캠페인 분리 운영 기준 실제 비용."""
    pc = opt.get("pc_cost", 0) or 0
    mo = opt.get("mo_cost", 0) or 0
    return (pc + mo) if (pc + mo) > 0 else (opt.get("cost", 0) or 0)

def _pick_initial_option(options, budget_left):
    for option in options:
        if _real_cost(option) <= budget_left:
            return option
    return None


def _select_records_with_budget(records, budget, selected_map):
    spent = 0
    for item in sorted(records, key=lambda x: (
        -x["best_option"]["weighted_score"], x["best_option"]["cost"], x["keyword"]
    )):
        if item["keyword"] in selected_map:
            continue
        budget_left = budget - spent
        if budget_left <= 0:
            break
        best = _pick_initial_option(item["options"], budget_left)
        if best is None:
            continue
        selected_map[item["keyword"]] = best
        real_cost = best.get("pc_cost", 0) + best.get("mo_cost", 0)
        spent += _real_cost(best)
    return spent


def _upgrade_selected_with_budget(records, budget_left, selected_map):
    if budget_left <= 0:
        return 0
    spent = 0
    while True:
        candidates = []
        for item in records:
            current = selected_map.get(item["keyword"])
            if not current:
                continue
            cur_cost = _real_cost(current)
            for better in sorted(
                [o for o in item["options"] if _real_cost(o) > cur_cost],
                key=lambda x: _real_cost(x)
            ):
                diff_cost  = _real_cost(better) - cur_cost
                diff_score = better["weighted_score"] - current["weighted_score"]
                # diff_cost만 양수면 업그레이드 허용 (클릭 늘리기 위해 비용 증가 감수)
                if diff_cost <= 0:
                    continue
                candidates.append({
                    "keyword":        item["keyword"],
                    "better":         better,
                    "diff_cost":      diff_cost,
                    "value_per_cost": diff_score / diff_cost,
                })
        if not candidates:
            break
        candidates.sort(key=lambda x: (-x["value_per_cost"], x["diff_cost"]))
        upgraded = False
        for cand in candidates:
            if cand["diff_cost"] <= (budget_left - spent):
                selected_map[cand["keyword"]] = cand["better"]
                spent += cand["diff_cost"]
                upgraded = True
                break
        if not upgraded:
            break
    return spent


def _select_additional_keywords_globally(all_records, budget_left, selected_map, soft_cap=None, current_spent=0):
    """
    효율 순으로 키워드 선택.
    soft_cap: 전체 선택 비용 상한 (None이면 budget_left만 적용)
    current_spent: 이미 선택된 키워드들의 총 비용
    """
    if budget_left <= 0:
        return 0
    spent = 0
    for item in sorted(
        [r for r in all_records if r["keyword"] not in selected_map],
        key=lambda x: (-x["best_option"]["weighted_score"], x["best_option"]["cost"], x["keyword"])
    ):
        local_left = budget_left - spent
        if local_left <= 0:
            break
        # 소프트 상한 체크: 원 예산의 120% 초과 시 중단
        if soft_cap is not None and (current_spent + spent) >= soft_cap:
            break
        option = _pick_initial_option(item["options"], local_left)
        if option is None:
            continue
        selected_map[item["keyword"]] = option
        spent += option["cost"]
    return spent


def _apply_budget_cap(selected_map, all_records, total_budget):
    total_cost = sum(_real_cost(v) for v in selected_map.values())
    if total_cost <= total_budget:
        return
    record_map = {item["keyword"]: item for item in all_records}
    while total_cost > total_budget:
        candidates = []
        for keyword, current in selected_map.items():
            item = record_map.get(keyword)
            if not item:
                continue
            cur_cost = _real_cost(current)
            for lower in sorted(
                [o for o in item["options"] if _real_cost(o) < cur_cost],
                key=lambda x: _real_cost(x), reverse=True
            ):
                save_cost = cur_cost - _real_cost(lower)
                if save_cost <= 0:
                    continue
                lose_score = current["weighted_score"] - lower["weighted_score"]
                candidates.append({
                    "keyword":   keyword,
                    "lower":     lower,
                    "save_cost": save_cost,
                    "penalty":   lose_score / save_cost,
                })
        if not candidates:
            break
        candidates.sort(key=lambda x: (x["penalty"], -x["save_cost"]))
        selected_map[candidates[0]["keyword"]] = candidates[0]["lower"]
        total_cost = sum(_real_cost(v) for v in selected_map.values())
    if total_cost > total_budget:
        for keyword, _ in sorted(
            selected_map.items(),
            key=lambda kv: (kv[1].get("weighted_score", 0), -kv[1]["cost"])
        ):
            if total_cost <= total_budget:
                break
            total_cost -= selected_map.pop(keyword)["cost"]


def optimize_budget(keyword_rows, total_budget, competitors=None, cat_config=None):
    if cat_config:
        cat_map = {c["name"]: c for c in cat_config}
    else:
        cat_map = _get_cat_map()
    all_records = []
    cat_groups  = {}
    estimate_ok = 0
    fallback_ok = 0
    skip_count  = 0

    print(f"  네이버 Estimate API 호출 중... (키워드 {len(keyword_rows)}개)")

    # ── 사전 배치 조회: 중간값 입찰가 + 노출 최소 입찰가 ────────────────────
    # 검색량 있는 키워드에 한해 배치로 미리 조회 (API 왕복 절감 + Fallback 입찰가 정확도 향상)
    api_key_pre, secret_pre, customer_id_pre = _get_api_keys()
    kws_with_vol = [
        row.get("keyword", "") for row in keyword_rows
        if _to_float(row.get("pc_impr", 0)) > 0 or _to_float(row.get("mo_impr", 0)) > 0
    ]
    if kws_with_vol:
        print(f"  [사전조회] 중간값·노출최소 입찰가 배치 조회 ({len(kws_with_vol)}개)")
        _median_pc   = get_median_bid_batch(kws_with_vol, "PC",     api_key_pre, secret_pre, customer_id_pre)
        _median_mo   = get_median_bid_batch(kws_with_vol, "MOBILE", api_key_pre, secret_pre, customer_id_pre)
        _expmin_pc   = get_exposure_min_bid_batch(kws_with_vol, "PC",     api_key_pre, secret_pre, customer_id_pre)
        _expmin_mo   = get_exposure_min_bid_batch(kws_with_vol, "MOBILE", api_key_pre, secret_pre, customer_id_pre)
        print(f"  [사전조회] 중간값 PC:{len(_median_pc)}개 / MO:{len(_median_mo)}개 | "
              f"노출최소 PC:{len(_expmin_pc)}개 / MO:{len(_expmin_mo)}개")
    else:
        _median_pc = _median_mo = _expmin_pc = _expmin_mo = {}

    standby_rows = []  # 검색량 0 → 등록 대기 키워드

    for row in keyword_rows:
        pc = _to_float(row.get("pc_impr", 0))
        mo = _to_float(row.get("mo_impr", 0))

        # 검색량 0 처리
        if pc <= 0 and mo <= 0:
            skip_count += 1
            kw_type = row.get("keyword_type", "GENERIC")
            category_name = _norm_category(row.get("category", ""), cat_map)
            cat_type = cat_map.get(category_name, {}).get("type", "general")
            # 브랜드 키워드는 검색량 없어도 최소입찰가(70원)로 1위 배정해 제안서에 포함
            if cat_type == "brand":
                options = [{
                    "keyword":         row.get("keyword", ""),
                    "category":        category_name,
                    "keyword_type":    kw_type,
                    "bid":             70,
                    "rank":            1, "rank_pc": 1, "rank_mo": 1,
                    "impressions": 0, "clicks": 0, "ctr": 0.0,
                    "cpc": 0, "cost": 0,
                    "pc_impressions": 0, "pc_clicks": 0, "pc_ctr": 0.0,
                    "pc_cpc": 0, "pc_cost": 0,
                    "mo_impressions": 0, "mo_clicks": 0, "mo_ctr": 0.0,
                    "mo_cpc": 0, "mo_cost": 0,
                    "anchor_bid": 70, "priority_weight": 0.5,
                    "efficiency": 0.0, "weighted_score": 0.0,
                    "is_fallback": True,
                }]
                item = {
                    "keyword":     row.get("keyword", ""),
                    "category":    category_name,
                    "cat_type":    "brand",
                    "row":         row,
                    "options":     options,
                    "best_option": options[0],
                }
                all_records.append(item)
                cat_groups.setdefault(category_name, []).append(item)
                fallback_ok += 1
            else:
                standby_rows.append({
                    "keyword":      row.get("keyword", ""),
                    "category":     category_name,
                    "keyword_type": kw_type,
                })
            continue

        kw = row.get("keyword", "")
        options = build_keyword_options(
            row, total_budget, cat_map,
            median_bid_pc=_median_pc.get(kw, 0),
            median_bid_mo=_median_mo.get(kw, 0),
            exposure_min_bid_pc=_expmin_pc.get(kw, 0),
            exposure_min_bid_mo=_expmin_mo.get(kw, 0),
        )
        if not options:
            skip_count += 1
            continue
        if options[0].get("is_fallback", False):
            fallback_ok += 1
        else:
            estimate_ok += 1

        category = _norm_category(row.get("category", ""), cat_map)
        item = {
            "keyword":     row.get("keyword", ""),
            "category":    category,
            "cat_type":    cat_map.get(category, {}).get("type", "general"),
            "row":         row,
            "options":     options,
            "best_option": options[0],
        }
        all_records.append(item)
        cat_groups.setdefault(category, []).append(item)

    print(f"  Estimate 성공: {estimate_ok}개 | Fallback: {fallback_ok}개 | 스킵(검색량0): {len(standby_rows)}개 | 스킵(옵션없음): {skip_count - len(standby_rows)}개")

    if not all_records:
        return [], 0

    # 검색량 있는 키워드 vs Fallback 분리
    active_records   = [r for r in all_records if not r["best_option"].get("is_fallback", False)]
    fallback_records = [r for r in all_records if r["best_option"].get("is_fallback", False)]

    # ── 경쟁사 브랜드 포함 키워드 자동 재분류 ──────────────────────
    comp_cat_name = next(
        (n for n, c in cat_map.items() if c.get("type") == "competitor"),
        "경쟁사 키워드"
    )
    _comp_brands = []
    if competitors:
        for _c in competitors:
            raw = _c.lower().replace(" ", "")
            _comp_brands.append(raw)
            first = _c.split()[0].lower() if _c.split() else ""
            if first and len(first) >= 2 and first not in _comp_brands:
                _comp_brands.append(first)
    if _comp_brands:
        reclassified = 0
        for item in all_records:
            if item["cat_type"] == "brand":
                continue
            kw_norm = item["keyword"].lower().replace(" ", "")
            if any(cb and cb in kw_norm for cb in _comp_brands):
                if item["category"] != comp_cat_name:
                    item["category"] = comp_cat_name
                    item["cat_type"] = "competitor"
                    item["best_option"]["category"] = comp_cat_name
                    reclassified += 1
        if reclassified > 0:
            cat_groups.clear()
            for item in all_records:
                cat_groups.setdefault(item["category"], []).append(item)
            print(f"  경쟁사 키워드 재분류: {reclassified}개")

    # max_keywords 제한 적용: 카테고리별 최대 키워드 수 초과 시 상위 키워드만 남김
    for cat_name in list(cat_groups.keys()):
        cfg    = cat_map.get(cat_name, {})
        max_kw = cfg.get("max_keywords")
        if max_kw is None:
            continue
        records = cat_groups[cat_name]
        original_count = len(records)
        if original_count <= max_kw:
            continue
        # Estimate 성공 키워드 우선, 그 다음 weighted_score 순으로 상위 max_kw개만
        records_sorted = sorted(records, key=lambda x: (
            1 if x["best_option"].get("is_fallback", False) else 0,
            -x["best_option"]["weighted_score"]
        ))
        kept_records = records_sorted[:max_kw]
        kept_kws     = {r["keyword"] for r in kept_records}
        cat_groups[cat_name] = kept_records
        all_records[:] = [r for r in all_records
                          if r["category"] != cat_name or r["keyword"] in kept_kws]
        print(f"  [{cat_name}] max_keywords 적용: {original_count}개 → {max_kw}개")

    selected_map = {}
    remaining    = total_budget

    # 1단계: brand 타입 min_keywords 우선 확보
    for cat_name, cfg in cat_map.items():
        if cfg.get("type") != "brand":
            continue
        min_n   = int(cfg.get("min_keywords", 0))
        records = cat_groups.get(cat_name, [])
        if not records or min_n <= 0:
            continue
        count = 0
        for item in sorted(records, key=lambda x: -x["best_option"]["weighted_score"]):
            if count >= min_n:
                break
            if item["keyword"] in selected_map:
                continue
            opt = _pick_initial_option(item["options"], remaining)
            if opt is None:
                continue
            selected_map[item["keyword"]] = opt
            remaining -= _real_cost(opt)
            count += 1

    # 2단계: 나머지 카테고리 min_keywords 보장
    for cat_name, cfg in cat_map.items():
        if cfg.get("type") == "brand":
            continue
        min_n   = int(cfg.get("min_keywords", 0))
        records = cat_groups.get(cat_name, [])
        if not records or min_n <= 0:
            continue
        count = 0
        for item in sorted(records, key=lambda x: -x["best_option"]["weighted_score"]):
            if count >= min_n:
                break
            if item["keyword"] in selected_map:
                continue
            opt = _pick_initial_option(item["options"], remaining)
            if opt is None:
                continue
            selected_map[item["keyword"]] = opt
            remaining -= _real_cost(opt)
            count += 1

    # 3단계: 효율 순으로 전체 키워드 배정
    # 핵심: 예산 상한(120%)을 _real_cost 기준으로 일관되게 추적
    SOFT_CAP = total_budget * 1.20  # 원 예산 120% 소프트 상한

    # 3-1: 일반/상품 카테고리 (상한 없음) - 효율 순, SOFT_CAP까지
    no_cap_records = sorted(
        [r for r in all_records
         if r["keyword"] not in selected_map
         and cat_map.get(r["category"], {}).get("max_budget_ratio") is None],
        key=lambda x: -x["best_option"]["weighted_score"]
    )
    accumulated = sum(_real_cost(v) for v in selected_map.values())
    for item in no_cap_records:
        if accumulated >= SOFT_CAP:
            break
        opt = _pick_initial_option(item["options"], SOFT_CAP - accumulated)
        if opt is None:
            continue
        cost = _real_cost(opt)
        if accumulated + cost > SOFT_CAP:
            continue  # 이 키워드 추가하면 상한 초과 → 건너뜀
        selected_map[item["keyword"]] = opt
        accumulated += cost

    # 3-2: 업그레이드 (예산이 남으면 적극적으로 순위 올리기)
    accumulated = sum(_real_cost(v) for v in selected_map.values())
    budget_remaining = total_budget - accumulated
    if budget_remaining > 0:
        no_cap_selected = [r for r in all_records
                           if r["keyword"] in selected_map
                           and cat_map.get(r["category"], {}).get("max_budget_ratio") is None]
        # 예산 100%까지 적극적으로 순위 업그레이드
        upgrade_target = min(total_budget * 1.00 - accumulated, budget_remaining)
        if upgrade_target > 0:
            _upgrade_selected_with_budget(no_cap_selected, upgrade_target, selected_map)
        accumulated = sum(_real_cost(v) for v in selected_map.values())

    # 3-3: 여전히 예산이 많이 남으면 추가 키워드 선택 (Fallback 제외)
    accumulated = sum(_real_cost(v) for v in selected_map.values())
    if accumulated < total_budget * 0.50:
        # 예산 50% 미만 소진이면 active 키워드를 더 적극 배정
        remaining_active = [r for r in active_records
                            if r["keyword"] not in selected_map]
        for item in sorted(remaining_active,
                           key=lambda x: -x["best_option"]["weighted_score"]):
            left = total_budget - sum(_real_cost(v) for v in selected_map.values())
            if left <= 0:
                break
            opt = _pick_initial_option(item["options"], left)
            if opt is None:
                continue
            selected_map[item["keyword"]] = opt
        accumulated = sum(_real_cost(v) for v in selected_map.values())

    # 4단계: 경쟁사 카테고리 배정 (max_budget_ratio 상한 내에서)
    if accumulated >= SOFT_CAP:
        budget_left = 0
    else:
        budget_left = max(total_budget - accumulated, 0)
    if budget_left > 0:
        for cat_name, cfg in cat_map.items():
            max_ratio = cfg.get("max_budget_ratio")
            if max_ratio is None:
                continue
            cat_budget_cap = int(total_budget * max_ratio)
            records = cat_groups.get(cat_name, [])
            if not records:
                continue
            already_spent = sum(
                _real_cost(selected_map[item["keyword"]])
                for item in records if item["keyword"] in selected_map
            )
            cat_remaining = max(cat_budget_cap - already_spent, 0)
            for item in sorted(
                [r for r in records if r["keyword"] not in selected_map],
                key=lambda x: (-x["best_option"]["weighted_score"], x["best_option"]["cost"])
            ):
                if cat_remaining <= 0:
                    break
                global_left = total_budget - sum(_real_cost(v) for v in selected_map.values())
                if global_left <= 0:
                    break
                avail = min(cat_remaining, global_left)
                opt = _pick_initial_option(item["options"], avail)
                if opt is None:
                    continue
                selected_map[item["keyword"]] = opt
                _rc = _real_cost(opt)
                cat_remaining -= _rc
                remaining     -= _rc

        # 4-2단계: 경쟁사 업그레이드도 상한 내에서
        for cat_name, cfg in cat_map.items():
            max_ratio = cfg.get("max_budget_ratio")
            if max_ratio is None:
                continue
            cat_budget_cap = int(total_budget * max_ratio)
            cat_records = [r for r in all_records
                           if r["keyword"] in selected_map and r["category"] == cat_name]
            cat_spent  = sum(_real_cost(selected_map[r["keyword"]]) for r in cat_records)
            cat_left   = max(cat_budget_cap - cat_spent, 0)
            global_left = total_budget - sum(_real_cost(v) for v in selected_map.values())
            upgrade_budget = min(cat_left, global_left)
            if upgrade_budget > 0:
                _upgrade_selected_with_budget(cat_records, upgrade_budget, selected_map)

    # 5단계: 예산 초과 캡
    _apply_budget_cap(selected_map, all_records, total_budget)

    # ── PC/MO 각각 최적 입찰가 계산 ─────────────────────────────────────
    # selected_map의 옵션은 통합 weighted_score 기준으로 선택됐지만
    # 실제 제안서에는 PC/MO 캠페인이 분리 운영되므로
    # 각 디바이스에서 target_rank 달성하는 최적 입찰가를 따로 제안해야 함
    def _find_best_bid_for_device(all_options, target_rank, device="pc"):
        """
        입찰가 후보들 중 target_rank에 가장 가까운 입찰가 반환.
        device: "pc" 또는 "mo"
        """
        rank_key = "rank_pc" if device == "pc" else "rank_mo"
        cost_key = "pc_cost" if device == "pc" else "mo_cost"
        clk_key  = "pc_clicks" if device == "pc" else "mo_clicks"

        # 클릭수 있는 옵션만
        valid = [o for o in all_options if o.get(clk_key, 0) > 0]
        if not valid:
            return None

        # target_rank 이내 달성 가능한 옵션 중 가장 저렴한 입찰가
        achievable = [o for o in valid if o[rank_key] <= target_rank]
        if achievable:
            return min(achievable, key=lambda x: x["bid"])

        # target_rank 달성 불가면 가장 좋은 순위 옵션
        return min(valid, key=lambda x: (x[rank_key], x["bid"]))

    # all_options_map: keyword → 전체 입찰가 후보 옵션 리스트
    all_options_map = {item["keyword"]: item["options"] for item in all_records}

    output_rows = []
    for row in sorted(
        selected_map.values(),
        key=lambda x: (x["rank"], -x["weighted_score"], x["keyword"])
    ):
        keyword  = row["keyword"]
        category = row["category"]
        cat_cfg  = cat_map.get(category, {})
        target_rank = cat_cfg.get("target_rank", 3)

        # 선택된 옵션의 비용을 그대로 사용 (SOFT_CAP 추적과 일관성 유지)
        # pc_bid/mo_bid는 target_rank 기준 최적화하되, 성과 데이터는 row 기준
        all_opts = all_options_map.get(keyword, [row])
        pc_best  = _find_best_bid_for_device(all_opts, target_rank, "pc")
        mo_best  = _find_best_bid_for_device(all_opts, target_rank, "mo")

        # Fallback 키워드는 pc_best/mo_best가 None → 옵션에 저장된 pc_bid/mo_bid 사용
        pc_bid = pc_best["bid"] if pc_best else row.get("pc_bid", row["bid"])
        mo_bid = mo_best["bid"] if mo_best else row.get("mo_bid", row["bid"])

        # 성과 데이터: selected_map에서 선택된 row 기준 (비용 일관성)
        # pc_cost/mo_cost는 row에서 가져와야 SOFT_CAP 추적값과 일치
        pc_opt = row   # selected_map의 opt를 그대로 사용
        mo_opt = row

        output_rows.append({
            "keyword":        keyword,
            "category":       category,
            "keyword_type":   row["keyword_type"],
            "bid":            row["bid"],       # 통합 입찰가 (참고용)
            "pc_bid":         pc_bid,           # PC 전용 최적 입찰가
            "mo_bid":         mo_bid,           # MO 전용 최적 입찰가
            "rank":           row["rank"],
            "rank_pc":        pc_opt.get("rank_pc", row["rank_pc"]),
            "rank_mo":        mo_opt.get("rank_mo", row["rank_mo"]),
            "impressions":    row["impressions"],
            "ctr":            row["ctr"],
            "clicks":         row["clicks"],
            "cpc":            row["cpc"],
            "cost":           row["cost"],
            "pc_impressions": pc_opt.get("pc_impressions", row["pc_impressions"]),
            "pc_ctr":         pc_opt.get("pc_ctr", row["pc_ctr"]),
            "pc_clicks":      pc_opt.get("pc_clicks", row["pc_clicks"]),
            "pc_cpc":         pc_opt.get("pc_cpc", row["pc_cpc"]),
            "pc_cost":        pc_opt.get("pc_cost", row["pc_cost"]),
            "mo_impressions": mo_opt.get("mo_impressions", row["mo_impressions"]),
            "mo_ctr":         mo_opt.get("mo_ctr", row["mo_ctr"]),
            "mo_clicks":      mo_opt.get("mo_clicks", row["mo_clicks"]),
            "mo_cpc":         mo_opt.get("mo_cpc", row["mo_cpc"]),
            "mo_cost":        mo_opt.get("mo_cost", row["mo_cost"]),
            "anchor_bid":     row.get("anchor_bid", 0),
            "is_fallback":    row.get("is_fallback", False),
        })

    final_total_cost = sum(r["cost"] for r in output_rows)
    selected_keywords = {r["keyword"] for r in output_rows}

    # 순위 통계 출력
    rank_stats = {}
    for r in output_rows:
        cat = r["category"]
        if cat not in rank_stats:
            rank_stats[cat] = []
        rank_stats[cat].append(r["rank"])
    print("  [순위 현황]")
    for cat, ranks in rank_stats.items():
        avg = sum(ranks)/len(ranks) if ranks else 0
        over5 = sum(1 for r in ranks if r > 5)
        print(f"    {cat}: 평균 {avg:.1f}위 | 5위이내 {len(ranks)-over5}개 / 5위초과 {over5}개")

    print(f"  등록 대기 키워드: {len(standby_rows)}개 (검색량 없음)")
    all_options_map_export = {item["keyword"]: item["options"] for item in all_records}

    # 효율 우선 원칙: 예산 초과해도 강제 제거 안 함
    # 실제 SA 운영에서 예산을 딱 맞추는 건 불가능하고,
    # 효율 좋은 키워드를 포함하는 게 더 중요함
    # 단, Overview에 실제 예상 비용을 정확히 표시
    def _row_actual_cost(r):
        pc = r.get("pc_cost", 0) or 0
        mo = r.get("mo_cost", 0) or 0
        return pc + mo if (pc + mo) > 0 else (r.get("cost", 0) or 0)

    final_total_cost  = sum(_row_actual_cost(r) for r in output_rows)
    selected_keywords = {r["keyword"] for r in output_rows}
    over_budget = final_total_cost - total_budget
    if over_budget > 0:
        print(f"  [예산초과] 예상 비용 {int(final_total_cost):,}원 (예산 대비 +{int(over_budget):,}원) - 효율 우선 유지")

    return output_rows, final_total_cost, selected_keywords, standby_rows, all_options_map_export


# ── 확장 제안 시뮬레이션 ────────────────────────────────────────────────────
def _get_best_options_for_kw(row, cat_map):
    """키워드 하나의 모든 입찰가 후보별 PC/MO 최적 옵션 반환."""
    keyword   = row.get("keyword", "")
    category  = _norm_category(row.get("category", ""), cat_map)
    cat_cfg   = cat_map.get(category, {})
    target_rank = cat_cfg.get("target_rank", 3)

    pc_impr = _to_float(row.get("pc_impr", 0))
    mo_impr = _to_float(row.get("mo_impr", 0))
    if pc_impr <= 0 and mo_impr <= 0:
        return None

    api_key, secret, customer_id = _get_api_keys()
    bid_candidates   = _build_bid_candidates(row, cat_map)
    estimate_results = get_estimate_performance(keyword, bid_candidates, api_key, secret, customer_id)

    if not estimate_results or all(e["clicks"] == 0 for e in estimate_results):
        return None

    rank_map   = _estimate_rank_from_estimate_results(estimate_results)
    valid_opts = []
    for est in estimate_results:
        bid = est["bid"]
        if est["clicks"] == 0:
            continue
        ri = rank_map.get(bid, (5, 5, 5))
        valid_opts.append({
            "bid":            bid,
            "rank_pc":        ri[1],
            "rank_mo":        ri[2],
            "pc_clicks":      est["pc_clicks"],
            "mo_clicks":      est["mo_clicks"],
            "pc_impressions": est["pc_impressions"],
            "mo_impressions": est["mo_impressions"],
            "pc_cost":        est["pc_cost"],
            "mo_cost":        est["mo_cost"],
        })

    if not valid_opts:
        return None

    # target_rank 달성 최소 입찰가
    pc_achiev = [o for o in valid_opts if o["rank_pc"] <= target_rank and o["pc_clicks"] > 0]
    mo_achiev = [o for o in valid_opts if o["rank_mo"] <= target_rank and o["mo_clicks"] > 0]
    pc_best   = min(pc_achiev, key=lambda x: x["bid"]) if pc_achiev else min(valid_opts, key=lambda x: x["rank_pc"])
    mo_best   = min(mo_achiev, key=lambda x: x["bid"]) if mo_achiev else min(valid_opts, key=lambda x: x["rank_mo"])

    return {
        "keyword":   keyword,
        "category":  category,
        "pc_bid":    pc_best["bid"],
        "mo_bid":    mo_best["bid"],
        "pc_impressions": pc_best["pc_impressions"],
        "mo_impressions": mo_best["mo_impressions"],
        "pc_clicks":      pc_best["pc_clicks"],
        "mo_clicks":      mo_best["mo_clicks"],
        "pc_cost":        pc_best["pc_cost"],
        "mo_cost":        mo_best["mo_cost"],
        "rank_pc":        pc_best["rank_pc"],
        "rank_mo":        mo_best["rank_mo"],
        "is_fallback":    False,
    }


def simulate_expanded(keyword_rows):
    """
    예산 무제한으로 모든 키워드의 최적 입찰가/성과 계산.
    (하위 호환용 - simulate_scenarios에서 내부 사용)
    """
    cat_map = _get_cat_map()
    results = []
    for row in keyword_rows:
        opt = _get_best_options_for_kw(row, cat_map)
        if opt:
            results.append(opt)
    total = sum(r["pc_cost"] + r["mo_cost"] for r in results)
    print(f"  확장 시뮬레이션: {len(results)}개 키워드 / 예상 총 비용: {total:,}원")
    return results, total


def simulate_scenarios(current_rows, not_selected_rows, base_budget, all_options_map=None):
    """
    확장 제안 시트용 시나리오 데이터 생성.

    반환:
      {
        "bid_up_rows":      현재 제안 키워드 중 입찰가 올리면 효과 있는 것들,
        "new_kw_rows":      예산 추가 시 진입 가능한 신규 키워드,
        "scenarios": [
            {"label": "현재 제안(500만)", "budget": 5000000, "kw_count": N, "clicks": N, "cost": N},
            {"label": "+200만 (700만)", ...},
            {"label": "+500만 (1000만)", ...},
        ]
      }
    """
    cat_map = _get_cat_map()

    # 1. 현재 제안 키워드 최적화 옵션 (입찰가 올리면 개선되는 것)
    # 예산 상한 없이 전체 커브 재조회 — _cap_options_by_budget으로 잘린 상위 bid 영역 복원
    # 기준: 현재보다 높은 입찰가로 올렸을 때 클릭증가율 20% 이상이고 효율이 가장 좋은 것
    from modules.naver_estimate import SCAN_BIDS
    _sim_api_key, _sim_secret, _sim_cid = _get_api_keys()

    bid_up_rows = []
    for row in current_rows:
        if row.get("is_fallback", False):
            continue

        keyword  = row.get("keyword", "")
        category = _norm_category(row.get("category", ""), cat_map)
        cur_pc_bid = row.get("proposed_bid_pc", 0) or row.get("proposed_bid", 0) or 0
        cur_mo_bid = row.get("proposed_bid_mo", 0) or row.get("proposed_bid", 0) or 0

        # 예산 상한 없이 전체 입찰 커브 조회 (캐시 활용, 추가 API 호출 없음)
        full_estimates = get_estimate_performance(keyword, SCAN_BIDS,
                                                  _sim_api_key, _sim_secret, _sim_cid)
        if not full_estimates:
            continue
        rank_map_full = _estimate_rank_from_estimate_results(full_estimates)
        full_opts = []
        for est in full_estimates:
            if est["clicks"] == 0:
                continue
            _bid = est["bid"]
            _ri  = rank_map_full.get(_bid, (5, 5, 5))
            full_opts.append({
                "bid":       _bid,
                "pc_clicks": est["pc_clicks"],
                "mo_clicks": est["mo_clicks"],
                "pc_cost":   est["pc_cost"],
                "mo_cost":   est["mo_cost"],
                "rank_pc":   _ri[1],
                "rank_mo":   _ri[2],
            })
        if not full_opts:
            continue

        # 현재 입찰가와 가장 가까운 옵션 찾기
        cur_pc_opt = (next((o for o in full_opts if o["bid"] == cur_pc_bid), None)
                      or min(full_opts, key=lambda x: abs(x["bid"] - cur_pc_bid)))
        cur_mo_opt = (next((o for o in full_opts if o["bid"] == cur_mo_bid), None)
                      or min(full_opts, key=lambda x: abs(x["bid"] - cur_mo_bid)))

        cur_pc_clicks = cur_pc_opt.get("pc_clicks", 0) or 0
        cur_mo_clicks = cur_mo_opt.get("mo_clicks", 0) or 0
        cur_total_clicks = cur_pc_clicks + cur_mo_clicks
        if cur_total_clicks <= 0:
            continue

        # 내부 순위 기준으로 현재 순위 설정 (추천 순위와 동일한 기준으로 일관성 유지)
        cur_pc_rank = cur_pc_opt.get("rank_pc", row.get("proposed_rank_pc", "-"))
        cur_mo_rank = cur_mo_opt.get("rank_mo", row.get("proposed_rank_mo", "-"))

        # 현재보다 높은 입찰가 옵션들 중 클릭 증가 효율이 좋은 것 탐색
        better_pc_opts = sorted(
            [o for o in full_opts if o["bid"] > cur_pc_bid and o.get("pc_clicks", 0) > cur_pc_clicks],
            key=lambda x: x["bid"]
        )
        better_mo_opts = sorted(
            [o for o in full_opts if o["bid"] > cur_mo_bid and o.get("mo_clicks", 0) > cur_mo_clicks],
            key=lambda x: x["bid"]
        )

        if not better_pc_opts and not better_mo_opts:
            continue

        # PC 최적 업그레이드: 클릭 증가율 대비 비용 증가율이 가장 좋은 것
        best_pc_up = None
        best_pc_efficiency = 0
        for opt in better_pc_opts:
            click_gain = opt["pc_clicks"] - cur_pc_clicks
            cost_gain  = opt.get("pc_cost", 0) - (cur_pc_opt or {}).get("pc_cost", 0)
            if cost_gain <= 0:
                continue
            click_rate = click_gain / max(cur_pc_clicks, 1)   # 클릭 증가율
            efficiency = click_gain / cost_gain                 # 클릭당 추가비용 효율
            # 클릭 증가율 20% 이상이고 효율이 좋은 것
            if click_rate >= 0.20 and efficiency > best_pc_efficiency:
                best_pc_efficiency = efficiency
                best_pc_up = opt

        # MO 최적 업그레이드
        best_mo_up = None
        best_mo_efficiency = 0
        for opt in better_mo_opts:
            click_gain = opt["mo_clicks"] - cur_mo_clicks
            cost_gain  = opt.get("mo_cost", 0) - (cur_mo_opt or {}).get("mo_cost", 0)
            if cost_gain <= 0:
                continue
            click_rate = click_gain / max(cur_mo_clicks, 1)
            efficiency = click_gain / cost_gain
            if click_rate >= 0.20 and efficiency > best_mo_efficiency:
                best_mo_efficiency = efficiency
                best_mo_up = opt

        if not best_pc_up and not best_mo_up:
            continue

        # 추천 입찰가: PC/MO 각각 최적 업그레이드 옵션
        rec_pc_bid  = best_pc_up["bid"]  if best_pc_up  else cur_pc_bid
        rec_mo_bid  = best_mo_up["bid"]  if best_mo_up  else cur_mo_bid
        rec_pc_rank = best_pc_up.get("rank_pc", cur_pc_rank) if best_pc_up else cur_pc_rank
        rec_mo_rank = best_mo_up.get("rank_mo", cur_mo_rank) if best_mo_up else cur_mo_rank

        # 추가 클릭 / 추가 비용
        add_pc_clicks = (best_pc_up["pc_clicks"] - cur_pc_clicks) if best_pc_up else 0
        add_mo_clicks = (best_mo_up["mo_clicks"] - cur_mo_clicks) if best_mo_up else 0
        add_pc_cost   = (best_pc_up.get("pc_cost",0) - (cur_pc_opt or {}).get("pc_cost",0)) if best_pc_up else 0
        add_mo_cost   = (best_mo_up.get("mo_cost",0) - (cur_mo_opt or {}).get("mo_cost",0)) if best_mo_up else 0

        bid_up_rows.append({
            "keyword":        keyword,
            "category":       category,
            "pc_bid":         rec_pc_bid,
            "mo_bid":         rec_mo_bid,
            "rank_pc":        rec_pc_rank,
            "rank_mo":        rec_mo_rank,
            "add_pc_clicks":  add_pc_clicks,
            "add_mo_clicks":  add_mo_clicks,
            "add_pc_cost":    add_pc_cost,
            "add_mo_cost":    add_mo_cost,
            "pc_efficiency":  round(best_pc_efficiency * 1000, 1),  # 1000원당 추가 클릭
            "mo_efficiency":  round(best_mo_efficiency * 1000, 1),
            "cur_pc_bid":     cur_pc_bid,
            "cur_mo_bid":     cur_mo_bid,
            "cur_pc_rank":    cur_pc_rank,
            "cur_mo_rank":    cur_mo_rank,
        })

    # 효율 높은 순 정렬 (PC+MO 추가 클릭 합산)
    bid_up_rows.sort(key=lambda x: -(x.get("add_pc_clicks",0) + x.get("add_mo_clicks",0)))

    # 2. 예산외 키워드 중 신규 진입 가능한 것들
    new_kw_rows = []
    for row in not_selected_rows:
        opt = _get_best_options_for_kw(row, cat_map)
        if opt:
            new_kw_rows.append(opt)
    # 비용 낮은 순으로 정렬 (진입 장벽 낮은 것부터)
    new_kw_rows.sort(key=lambda x: x["pc_cost"] + x["mo_cost"])

    # 3. 시나리오별 예산 계산
    # 현재 제안 기준 비용 (fallback 포함, not_selected 제외)
    cur_cost   = sum((r.get("pc_sim_cost") or 0) + (r.get("mo_sim_cost") or 0)
                     for r in current_rows if not r.get("not_selected"))
    cur_clicks = sum((r.get("pc_sim_clicks") or 0) + (r.get("mo_sim_clicks") or 0)
                     for r in current_rows if not r.get("not_selected"))
    # pc_sim_cost가 없으면 pc_cost로 fallback
    if cur_cost == 0:
        cur_cost   = sum((r.get("pc_cost") or 0) + (r.get("mo_cost") or 0)
                         for r in current_rows if not r.get("not_selected"))
        cur_clicks = sum((r.get("pc_clicks") or 0) + (r.get("mo_clicks") or 0)
                         for r in current_rows if not r.get("not_selected"))

    # 확장 시나리오 기준:
    # - 현재 제안 비용(cur_cost) 기준으로 표시
    # - 확장 예산은 원 예산(base_budget) × 비율로 설정
    #   1단계: 원 예산 × 1.5 (50% 증액)
    #   2단계: 원 예산 × 2.0 (100% 증액)
    scenario_budgets = [
        int(base_budget * 1.5),  # 1단계: 원 예산 50% 증액
        int(base_budget * 2.0),  # 2단계: 원 예산 100% 증액
    ]

    scenarios = []
    # 현재 제안을 첫 번째 시나리오로 추가
    scenarios.append({
        "label":      f"현재 제안 ({int(cur_cost)//10000:,}만원)",
        "budget":     int(cur_cost),
        "kw_count":   len([r for r in current_rows if not r.get("not_selected")]),
        "clicks":     cur_clicks,
        "cost":       cur_cost,
        "add_kws":    0,
        "add_clicks": 0,
        "add_cost":   0,
    })

    # bid_up_rows는 이미 추가 클릭 합산 기준으로 정렬됨 (효율 높은 순)
    for budget in scenario_budgets:
        add_budget = budget - cur_cost
        add_cost   = 0
        add_clicks = 0
        add_kws    = 0

        # 1순위: 기존 키워드 입찰가 업그레이드 (클릭 증가 효율 높은 순)
        for bur in bid_up_rows:
            extra_cost   = (bur.get("add_pc_cost", 0) or 0) + (bur.get("add_mo_cost", 0) or 0)
            extra_clicks = (bur.get("add_pc_clicks", 0) or 0) + (bur.get("add_mo_clicks", 0) or 0)
            if extra_cost <= 0:
                continue
            if add_cost + extra_cost <= add_budget:
                add_cost   += extra_cost
                add_clicks += extra_clicks

        # 2순위: 신규 키워드 추가 (진입 비용 낮은 순)
        for nkw in new_kw_rows:
            kw_cost   = nkw["pc_cost"] + nkw["mo_cost"]
            kw_clicks = nkw["pc_clicks"] + nkw["mo_clicks"]
            if add_cost + kw_cost <= add_budget:
                add_cost   += kw_cost
                add_clicks += kw_clicks
                add_kws    += 1

        pct = int((budget / base_budget - 1) * 100)
        label = f"확장 {pct}% ({budget//10000:,}만원)"
        scenarios.append({
            "label":      label,
            "budget":     budget,
            "kw_count":   len([r for r in current_rows if not r.get("not_selected")]) + add_kws,
            "clicks":     cur_clicks + add_clicks,
            "cost":       cur_cost + add_cost,
            "add_kws":    add_kws,
            "add_clicks": add_clicks,
            "add_cost":   add_cost,
        })

    print(f"  확장 시나리오: 신규진입가능 {len(new_kw_rows)}개 / 입찰가개선 {len(bid_up_rows)}개")
    return {
        "bid_up_rows": bid_up_rows,
        "new_kw_rows": new_kw_rows,
        "scenarios":   scenarios,
    }