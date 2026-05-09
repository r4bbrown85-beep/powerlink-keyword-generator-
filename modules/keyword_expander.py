import re


def _norm(s: str) -> str:
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _dedupe(lst):
    seen = set()
    out = []
    for x in lst:
        x = _norm(str(x))
        if not x:
            continue
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def _filter_banned(lst, banned_words):
    if not banned_words:
        return lst
    out = []
    for k in lst:
        bad = False
        for bw in banned_words:
            if bw and bw in k:
                bad = True
                break
        if not bad:
            out.append(k)
    return out


def ensure_min_keywords(base_keywords, min_count: int, templates: list[str]) -> list[str]:
    """
    base_keywords가 min_count 미만이면 templates로 자동 확장해서 채움.
    templates에는 "{k}"가 들어가야 함.
    """
    base_keywords = _dedupe(base_keywords)
    if len(base_keywords) >= min_count:
        return base_keywords

    out = base_keywords[:]
    i = 0
    while len(out) < min_count and i < 5000:
        for k in base_keywords:
            for t in templates:
                out.append(t.replace("{k}", k))
                if len(out) >= min_count:
                    break
            if len(out) >= min_count:
                break
        out = _dedupe(out)
        i += 1
        if len(base_keywords) == 0:
            break

    return out[: max(min_count, len(out))]


def build_category_keywords(
    brand_seeds: list[str],
    general_seeds: list[str],
    competitor_seeds: list[str],
    must_keywords: list[str] | None = None,
    seasonal_issues: list[str] | None = None,
    banned_words: list[str] | None = None,
    min_per_category: int = 20,
):
    """
    카테고리별 키워드 정리 + 최소 개수 보장.
    """
    must_keywords = must_keywords or []
    seasonal_issues = seasonal_issues or []
    banned_words = banned_words or []

    # 1) 기본 정리
    brand = _dedupe(brand_seeds + must_keywords)
    general = _dedupe(general_seeds + must_keywords)
    competitor = _dedupe(competitor_seeds)

    # 2) 금칙어 제거
    brand = _filter_banned(brand, banned_words)
    general = _filter_banned(general, banned_words)
    competitor = _filter_banned(competitor, banned_words)

    # 3) 시즌 키워드 확장(일반에 합치기)
    if seasonal_issues:
        season_templates = [
            "{k} " + s for s in seasonal_issues
        ]
        general = _dedupe(general + [t.replace("{k}", k) for k in must_keywords for t in season_templates])

    # 4) 카테고리별 최소 20개 보장용 템플릿
    common_templates = [
        "{k} 가격", "{k} 비용", "{k} 후기", "{k} 추천", "{k} 비교",
        "{k} 예약", "{k} 위치", "{k} 상담", "{k} 이벤트", "{k} 할인",
        "{k} 주차", "{k} 시간", "{k} 연락처", "{k} 당일", "{k} 근처",
        "{k} 잘하는곳", "{k} 전문", "{k} 초보", "{k} 레슨", "{k} 1:1"
    ]

    # brand가 비면 채울 기준이 없으니, industry 기반으로라도 채움
    if not brand and general:
        brand = _dedupe(general[:5])

    brand = ensure_min_keywords(brand, min_per_category, common_templates)
    general = ensure_min_keywords(general, min_per_category, common_templates)
    competitor = ensure_min_keywords(competitor, min_per_category, common_templates)

    return brand, general, competitor


def merge_all(brand, general, competitor):
    """
    전체 키워드 합치기(중복 제거)
    """
    return _dedupe(brand + general + competitor)