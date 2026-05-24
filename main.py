import json
import os
from dotenv import load_dotenv

from modules.ai_keyword_generator import generate_ai_keyword_plan
from modules.naver_suggest import get_naver_suggestions
from modules.google_suggest import get_google_suggestions
from modules.keyword_filter import filter_ad_keywords
from modules.keyword_scorer import score_keywords
from modules.keyword_type_classifier import classify_keyword_type
from modules.recommendation_engine import build_recommended_keywords, calc_recommendation_score
from modules.summary_builder import build_summary_text
from modules.excel_writer import save_proposal_excel
from modules.naver_keyword_api import get_keyword_stats, get_related_keywords
from modules.keyword_normalizer import normalize_keyword_for_ad
from modules.bid_simulator import optimize_budget, simulate_expanded, simulate_scenarios

load_dotenv()

TOTAL_BUDGET       = 5_000_000
TOP_N_RECOMMENDED  = None   # None = 제한 없음, 전체 추천 키워드 사용
SUGGEST_SEED_LIMIT = 30
SUGGEST_PER_SOURCE_LIMIT = 6
RELATED_SEED_LIMIT = 15
RELATED_PER_SEED_LIMIT   = 20

# ── 중의적 키워드 블랙리스트 (영화/드라마/연예 관련) ─────────────
AMBIGUOUS_BLACKLIST = [
    "관람평", "영화", "출연진", "감독", "예매", "상영", "시청", "평점",
    "드라마", "ost", "티저", "예고편", "개봉", "흥행",
    "넷플릭스", "왓챠", "티빙", "웨이브",
]


def _is_ambiguous_keyword(keyword):
    """영화/드라마/연예 관련 중의적 키워드 판별"""
    kw = str(keyword).lower()
    for term in AMBIGUOUS_BLACKLIST:
        if term in kw:
            return True
    return False


def load_profile():
    with open("data/client_profile.json", "r", encoding="utf-8") as f:
        profile = json.load(f)
    profile.setdefault("client", "")
    profile.setdefault("brand_name", "")
    profile.setdefault("category", "")
    profile.setdefault("brand_urls", [])
    profile.setdefault("brand_variants", [])
    profile.setdefault("typo_variants", [])
    profile.setdefault("products", [])
    profile.setdefault("competitors", [])
    profile.setdefault("celebrities", [])
    profile.setdefault("must_keywords", [])
    return profile


def uniq_by_ad_keyword(items):
    seen = set()
    out  = []
    for x in items:
        x = str(x).strip()
        if not x:
            continue
        key = normalize_keyword_for_ad(x)
        if key not in seen:
            out.append(x)
            seen.add(key)
    return out


def chunk_list(items, size):
    return [items[i:i + size] for i in range(0, len(items), size)]


def build_rows_from_ai_plan(plan, profile):
    rows = []
    for cat, kws in plan.get("keywords_by_category", {}).items():
        kws = uniq_by_ad_keyword(kws)
        for kw in kws:
            rows.append({
                "keyword":      kw,
                "category":     cat,
                "keyword_type": classify_keyword_type(kw, profile),
                "score":        50,
                "source":       "ai_seed"
            })
    return rows


def normalize_seed_keyword(kw):
    kw    = str(kw).strip()
    parts = kw.split()
    if len(parts) > 3:
        kw = " ".join(parts[:3])
    weak_tail_words = ["후기", "리뷰", "추천", "비교", "정품", "공식몰",
                       "지속력", "매장위치", "시향", "구매"]
    parts = kw.split()
    if len(parts) >= 2 and parts[-1] in weak_tail_words:
        kw = " ".join(parts[:-1]).strip()
    return kw.strip()


def pick_strong_suggest_seeds(rows, profile):
    seeds = []
    seeds.append(profile.get("brand_name", ""))
    for v in profile.get("brand_variants", []):
        seeds.append(v)
    for v in profile.get("typo_variants", []):
        seeds.append(v)
    for p in profile.get("products", []):
        seeds.append(p)
        if profile.get("brand_name"):
            seeds.append(f"{profile.get('brand_name')} {p}")
    for c in profile.get("competitors", []):
        seeds.append(c)
        seeds.append(f"{c} 향수")
    for r in rows:
        kw = r["keyword"]
        if len(kw.split()) <= 3:
            seeds.append(kw)
    seeds = uniq_by_ad_keyword([normalize_seed_keyword(x) for x in seeds if x])
    return seeds[:SUGGEST_SEED_LIMIT]


def pick_related_seeds(rows, profile):
    seeds = []
    seeds.append(profile.get("brand_name", ""))
    for v in profile.get("brand_variants", [])[:2]:
        seeds.append(v)
    for p in profile.get("products", [])[:3]:
        seeds.append(p)
    for c in profile.get("competitors", [])[:3]:
        seeds.append(c)
    high_score = sorted(rows, key=lambda x: x.get("score", 0), reverse=True)
    for r in high_score[:8]:
        kw = r["keyword"]
        if len(kw.split()) <= 2:
            seeds.append(kw)
    seeds = uniq_by_ad_keyword([x for x in seeds if x])
    return seeds[:RELATED_SEED_LIMIT]


def expand_with_suggest(rows, profile):
    seeds    = pick_strong_suggest_seeds(rows, profile)
    expanded = []
    for kw in seeds:
        print("===== SUGGEST TEST =====")
        print("seed:", kw)
        try:
            naver = get_naver_suggestions(kw)
            print("[NAVER] suggestions=", len(naver))
        except Exception:
            naver = []
        try:
            google = get_google_suggestions(kw)
            print("[GOOGLE] suggestions=", len(google))
        except Exception:
            google = []
        for s in naver[:SUGGEST_PER_SOURCE_LIMIT]:
            expanded.append((s, "naver_suggest"))
        for s in google[:SUGGEST_PER_SOURCE_LIMIT]:
            expanded.append((s, "google_suggest"))
    print("expanded total:", len(expanded))
    return expanded


def expand_with_related_keywords(rows, profile):
    api_key = os.getenv("NAVER_API_KEY")
    secret  = os.getenv("NAVER_SECRET_KEY")
    cid     = os.getenv("NAVER_CUSTOMER_ID")
    if not api_key or not secret or not cid:
        print("네이버 API 키 없음 - 연관키워드 스킵")
        return []
    seeds     = pick_related_seeds(rows, profile)
    expanded  = []
    seen_norm = set()
    print(f"연관키워드 조회 시드: {len(seeds)}개")
    for seed in seeds:
        print(f"  [연관키워드] seed: {seed}")
        related = get_related_keywords(seed, api_key, secret, cid, query_type="RELATED")
        print(f"    → {len(related)}개")
        for item in related[:RELATED_PER_SEED_LIMIT]:
            kw   = item["keyword"]
            norm = normalize_keyword_for_ad(kw)
            if norm in seen_norm:
                continue
            seen_norm.add(norm)
            expanded.append(item)
    print(f"연관키워드 확장 총: {len(expanded)}개")
    return expanded


def guess_category_for_suggestion(keyword, selected_categories, profile):
    k  = str(keyword).strip()
    nk = normalize_keyword_for_ad(k)
    brand_all = (
        [profile.get("brand_name", "")]
        + profile.get("brand_variants", [])
        + profile.get("typo_variants", [])
    )
    for b in brand_all:
        if b and normalize_keyword_for_ad(b) in nk:
            for c in selected_categories:
                if "브랜드" in c:
                    return c
    for comp in profile.get("competitors", []):
        if comp and normalize_keyword_for_ad(comp) in nk:
            for c in selected_categories:
                if "경쟁사" in c:
                    return c
    for p in profile.get("products", []):
        if p and normalize_keyword_for_ad(p) in nk:
            for c in selected_categories:
                if "상품" in c or "제품" in c:
                    return c
    for celeb in profile.get("celebrities", []):
        if celeb and normalize_keyword_for_ad(celeb) in nk:
            for c in selected_categories:
                if "일반" in c:
                    return c
    for c in selected_categories:
        if "일반" in c or "카테고리" in c or "구매의도" in c or "연관" in c:
            return c
    return selected_categories[0] if selected_categories else "일반 키워드"


def build_relevance_filter(profile):
    tokens = set()

    def add_tokens(text):
        if not text:
            return
        t = str(text).strip().lower()
        tokens.add(t)
        tokens.add(t.replace(" ", ""))

    add_tokens(profile.get("brand_name", ""))
    add_tokens(profile.get("category", ""))
    for v in profile.get("brand_variants", []):
        add_tokens(v)
    for v in profile.get("typo_variants", []):
        add_tokens(v)
    for p in profile.get("products", []):
        add_tokens(p)
    for c in profile.get("competitors", []):
        add_tokens(c)
    for cel in profile.get("celebrities", []):
        add_tokens(cel)
    for kw in profile.get("must_keywords", []):
        add_tokens(kw)

    category_text = profile.get("category", "").lower()
    if "향수" in category_text or "perfume" in category_text:
        general_tokens = [
            "향수", "퍼퓸", "perfume", "니치", "명품", "브랜드",
            "오드퍼퓸", "오드뚜왈렛", "오드코롱", "핸드크림", "바디크림",
            "직구", "면세", "선물", "시향", "지속력", "남자향수", "여자향수",
            "남성향수", "여성향수", "플로럴", "우디", "머스크", "시트러스",
            "럭셔리", "데이트", "출근", "봄", "여름", "샘플", "구매처"
        ]
        for t in general_tokens:
            tokens.add(t)
    return tokens


def is_relevant_keyword(keyword, relevance_tokens, profile):
    kw_lower    = str(keyword).strip().lower()
    kw_no_space = kw_lower.replace(" ", "")
    for token in relevance_tokens:
        if not token:
            continue
        if token in kw_lower or token in kw_no_space:
            return True
    return False


def filter_unrelated_keywords(rows, profile):
    """
    무관련 키워드 제거:
    1. 중의적 블랙리스트 필터 (영화/드라마 등)
       단, 브랜드명과 함께 쓰인 키워드는 예외 허용
    2. 관련성 토큰 기반 필터
    """
    relevance_tokens = build_relevance_filter(profile)
    brand_name_norm  = normalize_keyword_for_ad(profile.get("brand_name", ""))
    brand_variants   = [normalize_keyword_for_ad(v)
                        for v in profile.get("brand_variants", [])
                        + profile.get("typo_variants", [])]
    all_brand_norms  = [b for b in [brand_name_norm] + brand_variants if b]

    filtered = []
    removed  = 0

    for row in rows:
        source  = row.get("source", "")
        kw      = row.get("keyword", "")
        kw_norm = normalize_keyword_for_ad(kw)

        # AI 시드는 무조건 통과
        if source == "ai_seed":
            filtered.append(row)
            continue

        # 필수 키워드는 무조건 통과
        must_kws = [normalize_keyword_for_ad(m) for m in profile.get("must_keywords", [])]
        if kw_norm in must_kws:
            filtered.append(row)
            continue

        # 중의적 블랙리스트 체크
        # 브랜드명과 함께 쓰인 경우만 허용 (예: 프레데릭말 프렌치 러버 → OK)
        if _is_ambiguous_keyword(kw):
            has_brand = any(b in kw_norm for b in all_brand_norms)
            if not has_brand:
                removed += 1
                continue

        # 관련성 토큰 필터
        if is_relevant_keyword(kw, relevance_tokens, profile):
            filtered.append(row)
        else:
            removed += 1

    print(f"  무관련 키워드 제거: {removed}개 / 남은 키워드: {len(filtered)}개")
    return filtered


def merge_all_rows(ai_rows, suggest_items, related_items, selected_categories, profile):
    merged    = []
    seen_norm = set()
    for row in ai_rows:
        kw   = row["keyword"]
        norm = normalize_keyword_for_ad(kw)
        if norm not in seen_norm:
            merged.append(row)
            seen_norm.add(norm)
    for kw, source in suggest_items:
        norm = normalize_keyword_for_ad(kw)
        if norm in seen_norm:
            continue
        merged.append({
            "keyword":      kw,
            "category":     guess_category_for_suggestion(kw, selected_categories, profile),
            "keyword_type": classify_keyword_type(kw, profile),
            "score":        50,
            "source":       source
        })
        seen_norm.add(norm)
    for item in related_items:
        kw   = item["keyword"]
        norm = normalize_keyword_for_ad(kw)
        if norm in seen_norm:
            continue
        merged.append({
            "keyword":      kw,
            "category":     guess_category_for_suggestion(kw, selected_categories, profile),
            "keyword_type": classify_keyword_type(kw, profile),
            "score":        50,
            "source":       item.get("source", "naver_related"),
            "pc_impr":      item.get("pc_impr", 0),
            "mo_impr":      item.get("mo_impr", 0),
            "pc_click":     item.get("pc_click", 0),
            "mo_click":     item.get("mo_click", 0),
            "competition":  item.get("competition", "MID"),
        })
        seen_norm.add(norm)
    return merged


def attach_base_scores(rows):
    keywords  = [row["keyword"] for row in rows]
    scored    = score_keywords(keywords)
    score_map = {k: s for k, s in scored}
    for row in rows:
        row["score"] = score_map.get(row["keyword"], 50)
    return rows


def attach_naver_stats(rows):
    api_key = os.getenv("NAVER_API_KEY")
    secret  = os.getenv("NAVER_SECRET_KEY")
    cid     = os.getenv("NAVER_CUSTOMER_ID")
    if not api_key or not secret or not cid:
        print("네이버 API 키 없음")
        for row in rows:
            row.setdefault("pc_impr", 0)
            row.setdefault("mo_impr", 0)
            row.setdefault("pc_click", 0)
            row.setdefault("mo_click", 0)
            row.setdefault("ctr", 0)
            row.setdefault("competition", "MID")
            row.setdefault("monthlySearchVolume", 0)
            row.setdefault("topOfPageBid", 1000)
        return rows

    need_api = [row for row in rows if not row.get("pc_impr") and not row.get("mo_impr")]
    already  = [row for row in rows if row.get("pc_impr") or row.get("mo_impr")]
    print(f"  네이버 stats 조회 필요: {len(need_api)}개 / 이미 보유: {len(already)}개")

    keywords  = [row["keyword"] for row in need_api]
    stats_map = {}
    for batch in chunk_list(keywords, 5):
        try:
            res = get_keyword_stats(batch, api_key, secret, cid)
            stats_map.update(res)
        except Exception as e:
            print("네이버 API 조회 실패:", e)

    attached_count = 0
    for row in rows:
        if row.get("pc_impr") or row.get("mo_impr"):
            row.setdefault("monthlySearchVolume",
                           row.get("pc_impr", 0) + row.get("mo_impr", 0))
            row.setdefault("competition", "MID")
            comp   = str(row["competition"]).upper()
            volume = row["monthlySearchVolume"]
            est_top_bid = 1800 if comp == "HIGH" else (600 if comp == "LOW" else 1000)
            if volume >= 30000: est_top_bid += 500
            elif volume >= 10000: est_top_bid += 300
            elif volume >= 3000:  est_top_bid += 150
            row["topOfPageBid"] = est_top_bid
            attached_count += 1
            continue

        data               = stats_map.get(row["keyword"], {})
        row["pc_impr"]     = data.get("pc_impr", 0)
        row["mo_impr"]     = data.get("mo_impr", 0)
        row["pc_click"]    = data.get("pc_click", 0)
        row["mo_click"]    = data.get("mo_click", 0)
        row["ctr"]         = data.get("ctr", 0)
        row["competition"] = data.get("competition", "MID")
        row["monthlySearchVolume"] = row["pc_impr"] + row["mo_impr"]

        comp   = str(row["competition"]).upper()
        volume = row["monthlySearchVolume"]
        est_top_bid = 1800 if comp == "HIGH" else (600 if comp == "LOW" else 1000)
        if volume >= 30000: est_top_bid += 500
        elif volume >= 10000: est_top_bid += 300
        elif volume >= 3000:  est_top_bid += 150
        row["topOfPageBid"] = est_top_bid

        if row["pc_impr"] or row["mo_impr"] or row["pc_click"] or row["mo_click"]:
            attached_count += 1

    print(f"네이버 데이터 부착 성공 키워드 수: {attached_count}/{len(rows)}")
    return rows


def attach_recommendation_scores(rows):
    for row in rows:
        row["recommendation_score"] = calc_recommendation_score(row)
    return rows


def attach_budget_plan(recommended_rows, total_budget):
    keyword_rows = []
    for row in recommended_rows:
        keyword_rows.append({
            "keyword":              row["keyword"],
            "category":             row.get("category", ""),
            "keyword_type":         row.get("keyword_type", "GENERIC"),
            "competition":          row.get("competition", "MID"),
            "monthlySearchVolume":  row.get("monthlySearchVolume", 1000),
            "topOfPageBid":         row.get("topOfPageBid", 1000),
            "recommendation_score": row.get("recommendation_score", 50),
            "pc_impr":              row.get("pc_impr", 0),
            "mo_impr":              row.get("mo_impr", 0),
            "pc_click":             row.get("pc_click", 0),
            "mo_click":             row.get("mo_click", 0),
        })

    # 검색량 0 키워드 사전 확인 (디버그)
    zero_impr_count = sum(1 for r in keyword_rows if not r.get("pc_impr") and not r.get("mo_impr"))
    print(f"  [DEBUG] optimize_budget 투입 키워드 중 검색량 0: {zero_impr_count}개")

    selected, total_cost, selected_keywords, standby_rows, all_options_map = optimize_budget(keyword_rows, total_budget)
    print(f"  [DEBUG] standby_rows 수신: {len(standby_rows)}개 / all_options_map: {len(all_options_map)}개")

    selected_map = {sim["keyword"]: sim for sim in selected}

    # ── 카테고리별 Estimate 성공 입찰가 평균 계산 ──────────────────────────
    # Fallback 키워드 입찰가 제안 시 참고값으로 사용
    cat_bid_avg = {}
    for sim in selected:
        if sim.get("is_fallback", False):
            continue
        cat = sim.get("category", "일반 키워드")
        pc_bid = sim.get("pc_bid", sim.get("bid", 0)) or 0
        mo_bid = sim.get("mo_bid", sim.get("bid", 0)) or 0
        if cat not in cat_bid_avg:
            cat_bid_avg[cat] = {"pc": [], "mo": []}
        if pc_bid > 0: cat_bid_avg[cat]["pc"].append(pc_bid)
        if mo_bid > 0: cat_bid_avg[cat]["mo"].append(mo_bid)

    # 평균 계산
    cat_avg_pc = {cat: int(sum(v["pc"]) / len(v["pc"])) for cat, v in cat_bid_avg.items() if v["pc"]}
    cat_avg_mo = {cat: int(sum(v["mo"]) / len(v["mo"])) for cat, v in cat_bid_avg.items() if v["mo"]}

    for row in recommended_rows:
        sim = selected_map.get(row["keyword"])
        if sim:
            is_fb = sim.get("is_fallback", False)
            row["proposed_bid"]       = sim.get("bid", "")
            row["proposed_bid_pc"]    = sim.get("pc_bid", sim.get("bid", ""))
            row["proposed_bid_mo"]    = sim.get("mo_bid", sim.get("bid", ""))
            row["is_fallback"]        = is_fb
            row["not_selected"]       = False

            if is_fb:
                # Fallback(추정) 키워드: 입찰가만 제안, 성과값은 빈칸
                # 입찰가는 같은 카테고리 Estimate 성공 키워드 평균 기준 (리즈너블한 수준)
                cat = row.get("category", "일반 키워드")
                # topOfPageBid 기반으로 키워드별 차별화된 입찰가 계산
                # 같은 카테고리라도 경쟁도/검색량에 따라 다른 입찰가 제안
                top_bid = row.get("topOfPageBid", 0) or 0
                cat_pc_avg = cat_avg_pc.get(cat, 300)
                cat_mo_avg = cat_avg_mo.get(cat, 300)

                if top_bid > 0:
                    # topOfPageBid 대비 카테고리 평균 비율로 스케일링
                    # 예: 카테고리 평균 topOfPageBid 대비 이 키워드의 topOfPageBid 비율
                    cat_top_bids = [r.get("topOfPageBid", 0) for r in recommended_rows
                                    if r.get("category","") == cat
                                    and not r.get("is_fallback", True)
                                    and (r.get("topOfPageBid", 0) or 0) > 0]
                    cat_avg_top = sum(cat_top_bids) / len(cat_top_bids) if cat_top_bids else top_bid
                    scale = min(top_bid / cat_avg_top, 2.0) if cat_avg_top > 0 else 1.0
                    fallback_pc_bid = max(70, int(cat_pc_avg * scale))
                    fallback_mo_bid = max(70, int(cat_mo_avg * scale))
                else:
                    fallback_pc_bid = cat_pc_avg
                    fallback_mo_bid = cat_mo_avg

                row["proposed_bid"]    = fallback_pc_bid
                row["proposed_bid_pc"] = fallback_pc_bid
                row["proposed_bid_mo"] = fallback_mo_bid
                # bid_simulator가 계산한 추정 순위 사용 (브랜드=1위, 일반=카테고리 목표순위)
                _est_rank = sim.get("rank", "")
                row["proposed_rank"]    = _est_rank
                row["proposed_rank_pc"] = sim.get("rank_pc", _est_rank)
                row["proposed_rank_mo"] = sim.get("rank_mo", _est_rank)
                for field in [
                    "sim_impressions", "sim_ctr", "sim_clicks", "sim_cpc", "sim_cost", "anchor_bid",
                    "pc_sim_impressions", "pc_sim_ctr", "pc_sim_clicks", "pc_sim_cpc", "pc_sim_cost",
                    "mo_sim_impressions", "mo_sim_ctr", "mo_sim_clicks", "mo_sim_cpc", "mo_sim_cost",
                ]:
                    row[field] = ""
            else:
                # Estimate 성공 키워드: 실제 데이터로 성과 표시
                row["proposed_rank"]      = sim["rank"]
                row["proposed_rank_pc"]   = sim.get("rank_pc", "")
                row["proposed_rank_mo"]   = sim.get("rank_mo", "")
                row["sim_impressions"]    = sim["impressions"]
                row["sim_ctr"]            = sim["ctr"]
                row["sim_clicks"]         = sim["clicks"]
                row["sim_cpc"]            = sim["cpc"]
                row["sim_cost"]           = sim["cost"]
                row["anchor_bid"]         = sim.get("anchor_bid", "")
                row["pc_sim_impressions"] = sim.get("pc_impressions", 0)
                row["pc_sim_ctr"]         = sim.get("pc_ctr", 0)
                row["pc_sim_clicks"]      = sim.get("pc_clicks", 0)
                row["pc_sim_cpc"]         = sim.get("pc_cpc", 0)
                row["pc_sim_cost"]        = sim.get("pc_cost", 0)
                row["mo_sim_impressions"] = sim.get("mo_impressions", 0)
                row["mo_sim_ctr"]         = sim.get("mo_ctr", 0)
                row["mo_sim_clicks"]      = sim.get("mo_clicks", 0)
                row["mo_sim_cpc"]         = sim.get("mo_cpc", 0)
                row["mo_sim_cost"]        = sim.get("mo_cost", 0)
        else:
            # 예산 배분에서 선택 안 된 키워드:
            # topOfPageBid 기반으로 최소 입찰가 제안 (성과 예측은 불가)
            top_bid = row.get("topOfPageBid", 0) or 0
            competition = str(row.get("competition", "MID")).upper()
            pc_impr = row.get("pc_impr", 0) or 0
            mo_impr = row.get("mo_impr", 0) or 0

            # 입찰가: topOfPageBid의 50% 수준 (최소 70원)
            if top_bid > 0:
                suggest_bid = max(70, int(top_bid * 0.5))
            else:
                # topOfPageBid 없으면 경쟁도 기반 기본값
                suggest_bid = {"HIGH": 300, "LOW": 70}.get(competition, 150)

            row["proposed_bid"]       = suggest_bid
            row["proposed_bid_pc"]    = suggest_bid
            row["proposed_bid_mo"]    = suggest_bid
            row["proposed_rank"]      = ""
            row["proposed_rank_pc"]   = ""
            row["proposed_rank_mo"]   = ""
            # 성과 예측 불가 → 전부 빈칸 (억지 추정값 넣지 않음)
            for field in [
                "sim_impressions", "sim_ctr", "sim_clicks", "sim_cpc", "sim_cost", "anchor_bid",
                "pc_sim_impressions", "pc_sim_ctr", "pc_sim_clicks", "pc_sim_cpc", "pc_sim_cost",
                "mo_sim_impressions", "mo_sim_ctr", "mo_sim_clicks", "mo_sim_cpc", "mo_sim_cost",
            ]:
                row[field] = ""
            row["is_fallback"] = False
            row["not_selected"] = True  # 예산 선택 제외 플래그

    return recommended_rows, total_cost, standby_rows, all_options_map


def main():
    print("================================")
    print("1 광고주 프로파일")
    print("================================")
    profile    = load_profile()
    advertiser = profile.get("brand_name", "")
    print("광고주:", advertiser)

    print("================================")
    print("2 AI 키워드 생성")
    print("================================")
    plan                = generate_ai_keyword_plan(profile)
    selected_categories = plan.get("selected_categories", [])
    category_desc       = plan.get("category_descriptions", {})
    ai_rows             = build_rows_from_ai_plan(plan, profile)
    print("AI 키워드:", len(ai_rows))

    print("================================")
    print("3 자동완성 확장")
    print("================================")
    suggest_items = expand_with_suggest(ai_rows, profile)

    print("================================")
    print("3-2 네이버 연관키워드 확장")
    print("================================")
    related_items = expand_with_related_keywords(ai_rows, profile)

    print("================================")
    print("4 키워드 병합 및 무관련 필터링")
    print("================================")
    rows = merge_all_rows(ai_rows, suggest_items, related_items,
                          selected_categories, profile)
    rows = filter_unrelated_keywords(rows, profile)
    filtered_keywords = filter_ad_keywords([row["keyword"] for row in rows])
    filtered_set      = {normalize_keyword_for_ad(x) for x in filtered_keywords}
    rows              = [row for row in rows
                         if normalize_keyword_for_ad(row["keyword"]) in filtered_set]
    rows = attach_base_scores(rows)
    print("전체 키워드:", len(rows))

    print("================================")
    print("5 네이버 데이터 조회")
    print("================================")
    rows = attach_naver_stats(rows)

    print("================================")
    print("6 추천 키워드 선정")
    print("================================")
    rows        = attach_recommendation_scores(rows)
    if TOP_N_RECOMMENDED is None:
        # 제한 없음 - 점수 순으로 전체 정렬
        recommended = sorted(rows, key=lambda x: -x.get("recommendation_score", 0))
    else:
        recommended = build_recommended_keywords(rows, top_n=TOP_N_RECOMMENDED)
    print(f"추천 키워드: {len(recommended)}개{'  (전체 키워드 사용)' if TOP_N_RECOMMENDED is None else ''}")

    print("================================")
    print("7 예산 기반 시뮬레이션")
    print("================================")
    recommended, total_cost, standby_rows, all_options_map = attach_budget_plan(recommended, TOTAL_BUDGET)
    print(f"월 예산: {TOTAL_BUDGET:,}원")
    print(f"예상 총 비용: {total_cost:,}원")

    print("================================")
    print("8 summary 생성")
    print("================================")
    summary = build_summary_text(profile, rows, recommended)

    print("================================")
    print("8-2 확장 제안 시뮬레이션")
    print("================================")
    # 현재 제안 키워드 & 예산외 키워드 분리
    current_rows    = [r for r in recommended if not r.get("not_selected", False)]
    not_sel_rows    = [r for r in recommended if r.get("not_selected", False)]

    # 예산외 키워드를 시뮬레이션용 포맷으로 변환
    not_sel_kw_rows = []
    for row in not_sel_rows:
        not_sel_kw_rows.append({
            "keyword":             row["keyword"],
            "category":            row.get("category", ""),
            "keyword_type":        row.get("keyword_type", "GENERIC"),
            "competition":         row.get("competition", "MID"),
            "monthlySearchVolume": row.get("monthlySearchVolume", 0),
            "topOfPageBid":        row.get("topOfPageBid", 1000),
            "pc_impr":             row.get("pc_impr", 0),
            "mo_impr":             row.get("mo_impr", 0),
        })

    scenario_data = simulate_scenarios(current_rows, not_sel_kw_rows, TOTAL_BUDGET, all_options_map)
    print(f"시나리오 계산 완료: {len(scenario_data['scenarios'])}개 시나리오")

    print("================================")
    print("9 엑셀 저장")
    print("================================")
    save_proposal_excel(rows, recommended, category_desc, summary, advertiser, standby_rows, scenario_data)
    print("완료")


if __name__ == "__main__":
    main()