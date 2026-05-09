def uniq(items):
    seen = set()
    out = []
    for x in items:
        x = str(x).strip()
        if not x:
            continue
        if x not in seen:
            out.append(x)
            seen.add(x)
    return out


def build_perfume_keyword_categories(profile):
    brand = profile.get("brand_name", "")
    brand_variants = profile.get("brand_variants", []) or [brand]
    products = profile.get("products", []) or []
    category_keywords = profile.get("category_keywords", []) or []
    intent_keywords = profile.get("intent_keywords", []) or []
    must_keywords = profile.get("must_keywords", []) or []

    category_map = {
        "브랜드 키워드": [],
        "브랜드+카테고리 키워드": [],
        "제품 키워드": [],
        "구매의도 키워드": []
    }

    # 1. 브랜드 키워드
    for b in brand_variants:
        category_map["브랜드 키워드"].append(b)
        category_map["브랜드 키워드"].append(f"{b} 향수")

    # 2. 브랜드 + 카테고리
    for b in brand_variants:
        for ck in category_keywords:
            category_map["브랜드+카테고리 키워드"].append(f"{b} {ck}")

    # 3. 제품 키워드
    for p in products:
        category_map["제품 키워드"].append(p)
        category_map["제품 키워드"].append(f"{p} 향수")
        # 브랜드 + 제품은 현실적으로 자주 쓰이는 패턴만 추가
        category_map["제품 키워드"].append(f"{brand} {p}")

    # 4. 구매 의도 키워드
    # 브랜드 중심 구매 의도
    for b in brand_variants:
        for i in intent_keywords:
            category_map["구매의도 키워드"].append(f"{b} 향수 {i}")
            if i in ["가격", "추천", "후기"]:
                category_map["구매의도 키워드"].append(f"{b} {i}")

    # 제품 중심 구매 의도
    for p in products:
        for i in intent_keywords:
            # 너무 긴 문장을 막기 위해 제품 키워드는 핵심 의도만 붙임
            if i in ["가격", "후기", "추천"]:
                category_map["구매의도 키워드"].append(f"{p} {i}")
                category_map["구매의도 키워드"].append(f"{p} 향수 {i}")

    # must_keywords 우선 포함
    category_map["브랜드 키워드"].extend(must_keywords)

    # 정리
    for cat in category_map:
        category_map[cat] = uniq(category_map[cat])

    return category_map


def build_perfume_category_descriptions():
    return {
        "브랜드 키워드": "브랜드명 및 브랜드 직접 탐색 수요를 확보하기 위한 키워드",
        "브랜드+카테고리 키워드": "브랜드와 향수 카테고리를 결합한 핵심 탐색 키워드",
        "제품 키워드": "대표 향수명 및 제품명 중심의 세부 키워드",
        "구매의도 키워드": "가격, 추천, 후기, 구매, 매장 등 전환 직전 의도가 강한 키워드"
    }