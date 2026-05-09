import re


def normalize_keyword_for_ad(keyword: str) -> str:
    """
    네이버 파워링크 키워드 비교용 정규화
    - 소문자
    - 모든 공백 제거
    - 좌우 공백 제거

    예:
    '프레데릭말' == '프레데릭 말'
    """
    k = str(keyword).strip().lower()
    k = re.sub(r"\s+", "", k)
    return k


def normalize_keyword_for_proposal(keyword: str) -> str:
    """
    네이버 파워링크 제안서용 키워드 정규화.
    네이버 SA는 키워드 공백을 무시하고 붙여쓰기로 처리하므로
    제안서에도 붙여쓰기로 통일.

    예) '외장 SSD' → '외장SSD'
        '삼성 SSD' → '삼성SSD'
        '외장 하드 추천' → '외장하드추천'
    """
    k = str(keyword).strip()
    k = re.sub(r"\s+", "", k)
    return k


def uniq_by_ad_keyword(items):
    """
    띄어쓰기 차이는 같은 키워드로 보고 중복 제거
    """
    seen = set()
    out = []

    for x in items:
        x = str(x).strip()
        if not x:
            continue

        key = normalize_keyword_for_ad(x)

        if key not in seen:
            out.append(x)
            seen.add(key)

    return out