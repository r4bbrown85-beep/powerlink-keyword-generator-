from modules.keyword_normalizer import normalize_keyword_for_ad


def classify_keyword_type(keyword, profile):

    brand = profile.get("brand_name", "")
    brand_variants = profile.get("brand_variants", [])
    typo_variants = profile.get("typo_variants", [])
    competitors = profile.get("competitors", [])
    celebrities = profile.get("celebrities", [])
    products = profile.get("products", [])

    k = str(keyword).strip()

    if not k:
        return "GENERIC"

    nk = normalize_keyword_for_ad(k)

    # 브랜드 + 변형
    brand_all = [brand] + brand_variants + typo_variants

    for b in brand_all:
        if b and normalize_keyword_for_ad(b) in nk:
            return "BRAND"

    # 상품 — INTENT보다 먼저 검사 (e.g. "그룹웨어 가격" → SERVICE, not INTENT)
    for p in products:
        if p and normalize_keyword_for_ad(p) in nk:
            return "SERVICE"

    # 경쟁사
    for c in competitors:
        if c and normalize_keyword_for_ad(c) in nk:
            return "COMPETITOR"

    # 구매 의도
    intent_words = [
        "가격",
        "비용",
        "후기",
        "리뷰",
        "추천",
        "비교",
        "예약",
        "문의",
        "상담",
        "구매",
        "매장",
        "정품",
        "시향",
        "공식몰"
    ]

    for w in intent_words:
        if w in k:
            return "INTENT"

    # 연관인물
    for celeb in celebrities:
        if celeb and normalize_keyword_for_ad(celeb) in nk:
            return "GENERIC"

    return "GENERIC"