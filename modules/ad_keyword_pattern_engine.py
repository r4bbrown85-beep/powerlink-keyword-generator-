def build_ad_keywords(profile):

    brand = profile.get("brand_name", "")
    products = profile.get("products", [])
    regions = profile.get("regions", [])
    competitors = profile.get("competitors", [])

    # 핵심 키워드
    core_keywords = []

    for p in products:
        core_keywords.append(p)

    # 기본 확장
    core_keywords += [
        "골프레슨",
        "골프 개인레슨",
        "골프연습장",
        "스크린골프",
        "골프 아카데미"
    ]

    core_keywords = list(set(core_keywords))

    # modifier
    modifiers = [
        "가격",
        "비용",
        "추천",
        "후기",
        "예약"
    ]

    keywords = set()

    # core
    for c in core_keywords:
        keywords.add(c)

    # core + modifier
    for c in core_keywords:
        for m in modifiers:
            keywords.add(f"{c} {m}")

    # 지역 + core
    for r in regions:
        for c in core_keywords:
            keywords.add(f"{r} {c}")

    # 지역 + core + modifier
    for r in regions:
        for c in core_keywords:
            for m in modifiers:
                keywords.add(f"{r} {c} {m}")

    # 브랜드
    if brand:
        keywords.add(brand)

        for c in core_keywords:
            keywords.add(f"{brand} {c}")

    # 경쟁사
    for comp in competitors:
        keywords.add(comp)

    return list(keywords)