_SNS_PLATFORMS = frozenset([
    "인스타그램", "instagram", "페이스북", "facebook", "유튜브", "youtube",
    "트위터", "twitter", "틱톡", "tiktok", "카카오스토리", "핀터레스트", "pinterest",
    "링크드인", "linkedin", "스냅챗", "snapchat", "레딧", "reddit",
])

_SNS_CATEGORY_HINTS = frozenset(["소셜미디어", "sns", "인플루언서", "social", "마케팅툴"])

_NEGATIVE_INTENT_PATTERNS = [
    "폐기", "버리는법", "처분방법", "재활용방법", "공짜", "무료로 받",
    "주가", "주식", "채용", "취업", "공채", "입사지원", "합병",
    "수리점", "수리센터", "수리업체", "수리기사",
]


def filter_rows_by_brand_context(rows: list, profile: dict) -> list:
    """
    suggest/related 확장 키워드 rows에 브랜드 컨텍스트 필터 적용.
    - SNS 플랫폼 이름 제거 (SNS 툴 브랜드가 아닌 경우)
    - 구매 의도 없는 패턴 제거
    - brand_identity.forbidden_fragments 매칭 키워드 제거
    """
    brand_identity  = profile.get("brand_identity", {})
    forbidden_raw   = brand_identity.get("forbidden_fragments", [])
    forbidden_lower = [f.lower() for f in forbidden_raw if isinstance(f, str) and len(f) >= 3]
    brand_lower     = profile.get("brand_name", "").lower()
    category_lower  = profile.get("category", "").lower()
    is_sns_brand    = any(hint in category_lower for hint in _SNS_CATEGORY_HINTS)

    removed = []
    result  = []

    for row in rows:
        kw_text  = row[0] if isinstance(row, tuple) else row.get("keyword", "")
        kw_lower = kw_text.lower()
        skip     = False

        if not is_sns_brand:
            for sns in _SNS_PLATFORMS:
                if sns in kw_lower:
                    skip = True
                    break

        if not skip:
            for pat in _NEGATIVE_INTENT_PATTERNS:
                if pat in kw_text:
                    skip = True
                    break

        if not skip and forbidden_lower:
            for frag in forbidden_lower:
                if frag in kw_lower and brand_lower not in kw_lower:
                    skip = True
                    break

        if skip:
            removed.append(kw_text)
        else:
            result.append(row)

    if removed:
        print(f"    [컨텍스트필터] 제거 {len(removed)}개: {', '.join(removed[:6])}{'...' if len(removed) > 6 else ''}")

    return result


def filter_ad_keywords(keywords):
    banned = [
        # 정보 탐색성 (구매 의도 없음)
        "뜻", "의미", "역사", "정의", "유래", "소개", "이란", "무엇",
        "영어로", "일본어로", "중국어로", "어원",
        # 폐기/처분 의도 (구매 의도 없음)
        "폐기", "버리는법", "처분방법", "재활용방법",
        # 무료 추구 (유료 광고 클릭 가능성 없음)
        "공짜", "무료로 받",
        # 비구매 의도 — 금융/채용/주가
        "주가", "주식", "채용", "취업", "공채", "입사지원", "합병",
        # 수리/서비스 업체 검색 (제품 구매 의도 없음)
        "수리점", "수리센터", "수리업체", "수리기사",
    ]

    result = []

    for k in keywords:
        k_str = str(k).strip()
        if not k_str:
            continue

        blocked = False
        for b in banned:
            if b in k_str:
                blocked = True
                break

        if not blocked:
            result.append(k_str)

    return list(dict.fromkeys(result))