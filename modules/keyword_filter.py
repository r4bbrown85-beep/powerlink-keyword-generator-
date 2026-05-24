_SNS_PLATFORMS = frozenset([
    "인스타그램", "instagram", "페이스북", "facebook", "유튜브", "youtube",
    "트위터", "twitter", "틱톡", "tiktok", "카카오스토리", "핀터레스트", "pinterest",
    "링크드인", "linkedin", "스냅챗", "snapchat", "레딧", "reddit",
])

_SNS_CATEGORY_HINTS = frozenset(["소셜미디어", "sns", "인플루언서", "social", "마케팅툴"])

def filter_rows_by_brand_context(rows: list, profile: dict) -> list:
    """
    suggest/related 확장 키워드 rows에 브랜드 컨텍스트 필터 적용.
    - SNS 플랫폼 이름 제거 (SNS 툴 브랜드가 아닌 경우)
    - 구매 의도 없는 패턴 제거 (_NON_PURCHASE_INTENT 공유)
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
            for pat in _NON_PURCHASE_INTENT:
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


# ── 범용 비구매 의도 시그널 ──────────────────────────────────────────────────
# 어떤 광고주든 관계없이 구매/전환 의도가 없는 검색 패턴.
# 업종·도메인 의존성이 없으므로 여기서 전역 차단.
# (교육과정, 정부지원 등 업종별 도메인 키워드는 main_multi._DOMAIN_MISMATCH_RULES에서 처리)
_NON_PURCHASE_INTENT = [
    # 정의·정보 탐색 (구매 아닌 학습 의도)
    "뜻", "의미", "역사", "정의", "유래", "소개", "이란", "무엇",
    "영어로", "일본어로", "중국어로", "어원",
    # 폐기·처분 (제품 구매 의도 없음)
    "폐기", "버리는법", "처분방법", "재활용방법",
    # 무료 획득 의도 (유료 광고 클릭 전환 불가)
    "공짜", "무료로 받",
    # 채용·주가 (상품/서비스 구매 의도 없음)
    "주가", "주식", "채용", "취업", "공채", "입사지원", "합병",
    # 수리업체 검색 (신규 구매 의도 없음)
    "수리점", "수리센터", "수리업체", "수리기사",
    # 행정/서식 — 문서 다운로드 의도, 구매 전환 없음
    "업무분장", "민간군사기업",
    # 초광범위 기업 비교 탐색 — 특정 브랜드 구매 의도 없음
    "기업비교", "기업추천", "기업가격",
    # 서식/양식 검색 — 무료 문서 탐색 의도
    "양식", "서식", "일지양식", "일지서식",
    # 기업 분석/평가 정보 검색 — 소프트웨어 구매와 무관
    "기업분析보고서", "기업분석보고서", "기업분析사이트", "기업분석사이트",
    # 기업 검색 디렉토리 — 소프트웨어/서비스 구매 의도 없음
    "기업검색", "중소기업검색",
    # 금융/투자 관련
    "as of", "investor",
]

# ── 단독으로 광고 키워드가 될 수 없는 1개념 명사 ────────────────────────────
# 어떤 수식어도 없는 최상위 비즈니스 개념 명사.
# 검색 의도가 특정되지 않아 전환율이 사실상 0 — 업종 무관하게 전역 차단.
# ex) "기업" 단독 검색 → 의도 불명. "기업용 그룹웨어" 검색 → 유효.
_STANDALONE_GENERIC_NOUNS = frozenset([
    "업무", "기업", "회사", "영업", "관리", "운영", "기관",
    "단체", "조직", "업체", "사업", "사무", "사무실",
])


def filter_ad_keywords(keywords):
    result = []

    for k in keywords:
        k_str = str(k).strip()
        if not k_str:
            continue

        # 완전 일치: 단독 개념 명사 (수식어 없는 최상위 명사는 광고 타겟팅 불가)
        if k_str in _STANDALONE_GENERIC_NOUNS:
            continue

        # 부분 포함: 범용 비구매 의도 시그널
        if any(pat in k_str for pat in _NON_PURCHASE_INTENT):
            continue

        result.append(k_str)

    return list(dict.fromkeys(result))