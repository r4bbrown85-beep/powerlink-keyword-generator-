def filter_ad_keywords(keywords):
    banned = [
        # 정보 탐색성 (구매 의도 없음)
        "뜻", "의미", "역사", "정의", "유래", "소개", "이란", "무엇",
        "영어로", "일본어로", "중국어로", "어원",
        # 폐기/처분 의도 (구매 의도 없음)
        "폐기", "버리는법", "처분방법", "재활용방법",
        # 무료 추구 (유료 광고 클릭 가능성 없음)
        "공짜", "무료로 받",
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