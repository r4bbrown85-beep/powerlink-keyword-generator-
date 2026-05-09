def make_seeds(profile):

    brand = profile.get("brand_name", "")
    industry = profile.get("industry", "")
    products = profile.get("products", [])
    competitors = profile.get("competitors", [])
    must_keywords = profile.get("must_keywords", [])

    brand_seeds = []
    general_seeds = []
    competitor_seeds = []

    # 브랜드 seed는 짧게
    if brand:
        brand_seeds.append(brand)

    # 일반 seed도 짧게
    if industry:
        general_seeds.append(industry)

    for p in products:
        if p:
            general_seeds.append(p)

    for m in must_keywords:
        if m:
            general_seeds.append(m)

    # 경쟁사 seed도 짧게
    for c in competitors:
        if c:
            competitor_seeds.append(c)

    # 중복 제거
    brand_seeds = list(dict.fromkeys(brand_seeds))
    general_seeds = list(dict.fromkeys(general_seeds))
    competitor_seeds = list(dict.fromkeys(competitor_seeds))

    return brand_seeds, general_seeds, competitor_seeds