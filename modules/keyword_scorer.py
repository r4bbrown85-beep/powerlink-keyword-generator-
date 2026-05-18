_HIGH_INTENT = [
    "가격", "예약", "상담", "비용", "추천", "후기", "비교",
    "구매", "신청", "견적", "할인", "이벤트", "무료체험", "데모",
    "문의", "신청하기", "체험", "도입", "구독",
]


def score_keywords(keywords):
    """
    키워드 리스트에 원시 점수를 부여한 뒤 배치 내 백분위로 정규화.
    반환: [(keyword, score), ...] — score 범위 40~100
    """
    if not keywords:
        return []

    raw = []
    for k in keywords:
        s = 0
        for w in _HIGH_INTENT:
            if w in k:
                s += 1
        if len(k) >= 6:
            s += 0.5
        raw.append(s)

    mn, mx = min(raw), max(raw)
    scored = []
    for k, s in zip(keywords, raw):
        if mx > mn:
            normalized = 40 + int((s - mn) / (mx - mn) * 60)
        else:
            normalized = 50
        scored.append((k, normalized))

    return scored
