_HIGH_INTENT = [
    "가격", "예약", "상담", "비용", "추천", "후기", "비교",
    "구매", "신청", "견적", "할인", "이벤트", "무료체험", "데모",
    "문의", "신청하기", "체험", "도입", "구독",
]

# 전환 의도가 특히 강한 단어 — 위 목록의 부분집합
_STRONG_INTENT = frozenset([
    "견적", "신청", "도입", "상담", "무료체험", "데모", "구매",
])


def score_keywords(keywords):
    """
    키워드별 절대 의도 점수 부여.
    배치 크기나 구성에 무관하게 동일 키워드는 항상 동일 점수.
    반환: [(keyword, score), ...] — score 범위 40~90
    """
    if not keywords:
        return []

    scored = []
    for k in keywords:
        intent_count = sum(1 for w in _HIGH_INTENT if w in k)

        if intent_count == 0:
            s = 40
        elif intent_count == 1:
            s = 60
        else:
            s = 75

        # 강한 전환 의도 단어 포함 시 보너스
        if any(w in k for w in _STRONG_INTENT):
            s = min(90, s + 10)

        # 구체적인 키워드(6자 이상)는 전환율 경향 높음
        if len(k) >= 6:
            s = min(90, s + 5)

        scored.append((k, s))

    return scored
