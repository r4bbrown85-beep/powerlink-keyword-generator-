def filter_ad_keywords(keywords):
    banned = [
        "뜻",
        "의미",
        "역사",
        "정의",
        "유래",
        "소개",
        "이란",
        "무엇"
    ]

    result = []

    for k in keywords:
        blocked = False

        for b in banned:
            if b in k:
                blocked = True
                break

        if not blocked:
            result.append(k)

    return list(dict.fromkeys(result))