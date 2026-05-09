def build_summary_text(profile, all_rows, recommended_rows):
    advertiser = profile.get("brand_name", "") or profile.get("brand", "")
    industry = profile.get("industry", "")

    total_count = len(all_rows)
    recommended_count = len(recommended_rows)

    type_count = {}
    for row in all_rows:
        t = row.get("keyword_type", "GENERIC")
        type_count[t] = type_count.get(t, 0) + 1

    brand_n = type_count.get("BRAND", 0)
    generic_n = type_count.get("GENERIC", 0)
    service_n = type_count.get("SERVICE", 0)
    local_n = type_count.get("LOCAL", 0)
    intent_n = type_count.get("INTENT", 0)
    competitor_n = type_count.get("COMPETITOR", 0)

    summary = f"""
본 제안서는 {advertiser} 광고주의 네이버 파워링크 운영을 위한 키워드 전략을 기반으로 작성되었습니다.

광고주 업종은 {industry}이며, 브랜드/서비스/지역/의도/경쟁사 키워드 구조를 반영하여 전체 {total_count}개의 키워드 후보군을 도출하였습니다.
이 중 실제 광고 집행 적합도가 높은 {recommended_count}개의 키워드를 우선 운영 추천 키워드로 선별하였습니다.

전체 후보군은 다음과 같이 구성됩니다.
- 브랜드 키워드: {brand_n}개
- 일반 키워드: {generic_n}개
- 서비스 키워드: {service_n}개
- 지역 키워드: {local_n}개
- 의도형 키워드: {intent_n}개
- 경쟁사 키워드: {competitor_n}개

추천 키워드는 브랜드 방어, 일반 탐색 수요, 지역 기반 유입, 가격/후기/예약 의도, 경쟁사 비교 수요까지 폭넓게 반영하여 선별하였습니다.
""".strip()

    return summary