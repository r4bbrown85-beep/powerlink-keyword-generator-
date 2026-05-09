from modules.keyword_normalizer import normalize_keyword_for_ad


def _to_int(v):
    if v is None:
        return 0

    if isinstance(v, (int, float)):
        return int(v)

    s = str(v).strip().replace(",", "")

    if s in ["", "null", "None"]:
        return 0

    if "<" in s:
        return 10

    try:
        return int(float(s))
    except:
        return 0


def _to_float(v):
    if v is None:
        return 0.0

    if isinstance(v, (int, float)):
        return float(v)

    s = str(v).strip().replace("%", "").replace(",", "")

    if s in ["", "null", "None"]:
        return 0.0

    try:
        return float(s)
    except:
        return 0.0


def calc_recommendation_score(row):
    base_score = int(row.get("score", 50))

    pc_impr = _to_int(row.get("pc_impr", 0))
    mo_impr = _to_int(row.get("mo_impr", 0))
    pc_click = _to_float(row.get("pc_click", 0))
    mo_click = _to_float(row.get("mo_click", 0))
    ctr = _to_float(row.get("ctr", 0))

    total_impr = pc_impr + mo_impr
    total_click = pc_click + mo_click

    rec_score = base_score

    # 검색량 가중치
    if total_impr >= 10000:
        rec_score += 40
    elif total_impr >= 3000:
        rec_score += 30
    elif total_impr >= 1000:
        rec_score += 22
    elif total_impr >= 300:
        rec_score += 15
    elif total_impr >= 100:
        rec_score += 10
    elif total_impr >= 30:
        rec_score += 5

    # 클릭 가중치
    if total_click >= 100:
        rec_score += 20
    elif total_click >= 30:
        rec_score += 12
    elif total_click >= 10:
        rec_score += 7
    elif total_click >= 3:
        rec_score += 3

    # CTR 가중치
    if ctr >= 10:
        rec_score += 15
    elif ctr >= 5:
        rec_score += 10
    elif ctr >= 2:
        rec_score += 5

    keyword_type = row.get("keyword_type", "GENERIC")
    category = row.get("category", "")

    # 광고주 중심 가중치
    if keyword_type == "BRAND":
        rec_score += 20
    elif keyword_type == "SERVICE":
        rec_score += 25
    elif keyword_type == "INTENT":
        rec_score += 15
    elif keyword_type == "COMPETITOR":
        rec_score -= 5

    # 카테고리 가중치
    if category == "상품 키워드":
        rec_score += 20
    elif category == "브랜드 키워드":
        rec_score += 15
    elif category == "일반 키워드":
        rec_score += 5
    elif category == "경쟁사 키워드":
        rec_score -= 5

    return rec_score


def _passes_minimum_filter(row):
    keyword_type = row.get("keyword_type", "GENERIC")
    category = row.get("category", "")

    pc_impr = _to_int(row.get("pc_impr", 0))
    mo_impr = _to_int(row.get("mo_impr", 0))
    pc_click = _to_float(row.get("pc_click", 0))
    mo_click = _to_float(row.get("mo_click", 0))

    total_impr = pc_impr + mo_impr
    total_click = pc_click + mo_click

    if keyword_type == "BRAND":
        return True

    if category in ["상품 키워드", "일반 키워드"] and total_impr >= 20:
        return True

    if total_impr >= 30:
        return True

    if total_click >= 1:
        return True

    return False


def build_recommended_keywords(rows, top_n=160):
    enriched = []

    for row in rows:
        copied = dict(row)
        copied["recommendation_score"] = calc_recommendation_score(copied)
        enriched.append(copied)

    filtered = [r for r in enriched if _passes_minimum_filter(r)]

    if len(filtered) < 50:
        filtered = enriched

    filtered = sorted(
        filtered,
        key=lambda x: (
            -x["recommendation_score"],
            -(_to_int(x.get("pc_impr", 0)) + _to_int(x.get("mo_impr", 0))),
            x["keyword"]
        )
    )

    category_quota = {
        "브랜드 키워드": 35,
        "상품 키워드": 50,
        "일반 키워드": 45,
        "경쟁사 키워드": 30
    }

    picked = []
    seen_norm = set()
    category_count = {k: 0 for k in category_quota.keys()}

    for row in filtered:
        kw = row["keyword"]
        norm = normalize_keyword_for_ad(kw)
        cat = row.get("category", "")

        # 띄어쓰기만 다른 키워드는 같은 키워드로 취급
        if norm in seen_norm:
            continue

        if cat in category_quota and category_count[cat] >= category_quota[cat]:
            continue

        picked.append(row)
        seen_norm.add(norm)

        if cat in category_count:
            category_count[cat] += 1

        if len(picked) >= top_n:
            break

    if len(picked) < top_n:
        for row in filtered:
            kw = row["keyword"]
            norm = normalize_keyword_for_ad(kw)

            if norm in seen_norm:
                continue

            picked.append(row)
            seen_norm.add(norm)

            if len(picked) >= top_n:
                break

    return picked