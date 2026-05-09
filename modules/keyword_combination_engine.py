def uniq(items):
    return list(dict.fromkeys([str(x).strip() for x in items if str(x).strip()]))


def expand_service_variants(services):
    """
    원형 서비스 키워드를 실제 검색 표현으로 확장
    예:
    골프레슨 -> 골프 레슨, 골프 강습, 골프 수업
    골프연습장 -> 골프 연습장, 실내 골프연습장
    """
    variants = []

    synonym_map = {
        "골프레슨": [
            "골프레슨",
            "골프 레슨",
            "골프 강습",
            "골프 수업"
        ],
        "골프연습장": [
            "골프연습장",
            "골프 연습장",
            "실내 골프연습장"
        ],
        "스크린골프": [
            "스크린골프",
            "스크린 골프",
            "실내 스크린골프"
        ],
        "골프 개인레슨": [
            "골프 개인레슨",
            "골프 1:1 레슨",
            "개인 골프레슨",
            "1:1 골프레슨"
        ],
        "골프 그룹레슨": [
            "골프 그룹레슨",
            "골프 단체레슨",
            "그룹 골프레슨"
        ]
    }

    for s in services:
        s = str(s).strip()

        # 사전에 있는 대표 표현
        if s in synonym_map:
            variants.extend(synonym_map[s])
        else:
            variants.append(s)

            # 띄어쓰기 변형 자동 생성
            if "레슨" in s and " " not in s:
                variants.append(s.replace("레슨", " 레슨").strip())

            if "연습장" in s and " " not in s:
                variants.append(s.replace("연습장", " 연습장").strip())

            if "스크린골프" in s:
                variants.append(s.replace("스크린골프", "스크린 골프"))

    return uniq(variants)


def remove_bad_combinations(keywords):
    """
    품질 떨어지는 조합 제거
    """
    bad_patterns = [
        "가격 가격",
        "비용 비용",
        "후기 후기",
        "예약 예약",
        "문의 문의",
        "추천 추천",
        "가격 비용",
        "비용 가격",
        "후기 추천 후기",
        "예약 문의 예약"
    ]

    out = []

    for k in keywords:
        blocked = False

        for bad in bad_patterns:
            if bad in k:
                blocked = True
                break

        # 너무 짧거나 맥락 없는 키워드 제거
        if k in ["예약", "문의", "상담", "후기", "추천", "가격", "비용"]:
            blocked = True

        if not blocked:
            out.append(k)

    return uniq(out)


def build_combination_keywords(profile):
    services = profile.get("products", []) or []
    regions = profile.get("regions", []) or []
    brand = profile.get("brand_name", "") or ""
    competitors = profile.get("competitors", []) or []
    must_keywords = profile.get("must_keywords", []) or []
    seasonal_issues = profile.get("seasonal_issues", []) or []

    intents = [
        "가격",
        "비용",
        "추천",
        "후기",
        "체험",
        "예약",
        "문의",
        "잘하는곳",
        "유명한곳"
    ]

    services = expand_service_variants(services)

    keywords = []

    # 0) 필수 키워드 우선 포함
    keywords += must_keywords

    # 1) 서비스 원형
    for s in services:
        keywords.append(s)

    # 2) 서비스 + 의도
    for s in services:
        for i in intents:
            keywords.append(f"{s} {i}")

    # 3) 지역 + 서비스
    for r in regions:
        for s in services:
            keywords.append(f"{r} {s}")

    # 4) 지역 + 서비스 + 의도
    for r in regions:
        for s in services:
            for i in intents:
                keywords.append(f"{r} {s} {i}")

    # 5) 브랜드 + 서비스
    if brand:
        for s in services:
            keywords.append(f"{brand} {s}")
            keywords.append(f"{brand} {s} 가격")
            keywords.append(f"{brand} {s} 후기")
            keywords.append(f"{brand} {s} 예약")

    # 6) 경쟁사 + 서비스
    for c in competitors:
        for s in services:
            keywords.append(f"{c} {s}")
            keywords.append(f"{c} {s} 가격")
            keywords.append(f"{c} {s} 후기")
            keywords.append(f"{c} {s} 비교")

    # 7) 시즌 이슈 + 서비스
    for season in seasonal_issues:
        for s in services:
            keywords.append(f"{season} {s}")
            keywords.append(f"{season} {s} 추천")

    keywords = uniq(keywords)
    keywords = remove_bad_combinations(keywords)

    return keywords