def score_keywords(keywords):

    high_intent = ["가격","예약","상담","비용","추천","후기","비교"]
    location_words = ["강남","잠실","송파","분당","판교"]

    scored = []

    for k in keywords:

        score = 50

        for w in high_intent:
            if w in k:
                score += 20

        for w in location_words:
            if w in k:
                score += 15

        if len(k) > 10:
            score += 5

        scored.append((k,score))

    return scored