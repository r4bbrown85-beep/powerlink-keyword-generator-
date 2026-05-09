def generate_keywords(base_keyword):

    suffix_list = [
        "추천",
        "가격",
        "비용",
        "후기",
        "상담",
        "잘하는곳",
        "전문",
        "비교"
    ]

    keywords = []

    # 기본 키워드
    keywords.append(base_keyword)

    # 띄어쓰기 버전
    if len(base_keyword) > 2:
        keywords.append(base_keyword[:2] + " " + base_keyword[2:])

    # 확장 키워드
    for suffix in suffix_list:
        keywords.append(base_keyword + " " + suffix)

    return keywords