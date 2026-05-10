import json
import os
import re
import hashlib
from pathlib import Path
from datetime import datetime, timedelta

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _call_llm(system: str, user: str, temperature: float = 0.2, max_tokens: int = 4096) -> str:
    """
    Claude 우선, ANTHROPIC_API_KEY 없으면 OpenAI(gpt-4o) 폴백.
    호출 코드는 모델에 무관하게 동일하게 작성 가능.
    """
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        import anthropic as _anthropic
        c = _anthropic.Anthropic(api_key=anthropic_key)
        resp = c.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return resp.content[0].text
    else:
        resp = _openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
        )
        return resp.choices[0].message.content

# SNS/소셜미디어 플랫폼 — 해당 브랜드가 SNS 툴이 아닌 경우 키워드로 부적절
_SNS_PLATFORMS = frozenset([
    "인스타그램", "instagram", "페이스북", "facebook", "유튜브", "youtube",
    "트위터", "twitter", "틱톡", "tiktok", "카카오스토리", "핀터레스트", "pinterest",
    "링크드인", "linkedin", "스냅챗", "snapchat", "레딧", "reddit",
])

_SNS_CATEGORY_HINTS = frozenset(["소셜미디어", "sns", "인플루언서", "social", "마케팅툴"])

# 구매 의도 없는 범용 부정 패턴
_NEGATIVE_INTENT_PATTERNS = [
    "폐기", "버리는법", "처분방법", "재활용방법", "공짜", "무료로 받",
    "주가", "주식", "채용", "취업", "공채", "입사지원", "합병",
    "as of", "investor",
]

# AI 키워드 캐시 설정
_AI_CACHE_DIR  = Path("data/cache/ai_keywords")
_AI_CACHE_DAYS = 7


def _get_ai_cache_key(profile: dict) -> str:
    key_fields = {
        "brand_name": profile.get("brand_name", ""),
        "category":   profile.get("category", ""),
        "products":   sorted(profile.get("products", [])),
        "competitors": sorted(profile.get("competitors", [])),
    }
    key_str  = json.dumps(key_fields, ensure_ascii=False, sort_keys=True)
    key_hash = hashlib.md5(key_str.encode()).hexdigest()[:12]
    safe_brand = re.sub(r'[\\/:*?"<>| ]', "_", profile.get("brand_name", "unknown"))
    return f"{safe_brand}_{key_hash}"


def _load_ai_cache(cache_key: str):
    _AI_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _AI_CACHE_DIR / f"{cache_key}.json"
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            cached = json.load(f)
        cached_at = datetime.fromisoformat(cached["cached_at"])
        if datetime.now() - cached_at > timedelta(days=_AI_CACHE_DAYS):
            return None
        print(f"    AI 키워드 캐시 사용: {cached['brand_name']} ({cached_at.strftime('%m/%d %H:%M')})")
        return cached["data"]
    except Exception:
        return None


def _save_ai_cache(cache_key: str, brand_name: str, data: dict):
    _AI_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _AI_CACHE_DIR / f"{cache_key}.json"
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "brand_name": brand_name,
                "cached_at":  datetime.now().isoformat(),
                "data":       data,
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"    AI 캐시 저장 실패: {e}")


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9_]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()


def _safe_json_loads(text: str):
    text = _strip_code_fence(text)
    return json.loads(text)


def _dedupe_keywords_by_category(keywords_by_category):
    cleaned = {}
    for cat, kws in keywords_by_category.items():
        seen = set()
        temp = []
        for kw in kws:
            kw = str(kw).strip()
            if not kw:
                continue
            if kw not in seen:
                temp.append(kw)
                seen.add(kw)
        cleaned[cat] = temp
    return cleaned


def _rule_based_brand_filter(keywords_by_category: dict, profile: dict) -> dict:
    """
    AI 생성 후 1차 규칙 기반 필터.
    - SNS 플랫폼 이름 제거 (SNS 툴 브랜드 제외)
    - 구매 의도 없는 폐기/공짜 패턴 제거
    - brand_identity.forbidden_fragments에 명시된 단어 포함 키워드 제거
    """
    brand_identity     = profile.get("brand_identity", {})
    forbidden_raw      = brand_identity.get("forbidden_fragments", [])
    forbidden_lower    = [f.lower() for f in forbidden_raw if isinstance(f, str) and len(f) >= 3]
    brand_lower        = profile.get("brand_name", "").lower()
    category_lower     = profile.get("category", "").lower()
    is_sns_brand       = any(hint in category_lower for hint in _SNS_CATEGORY_HINTS)

    removed = []
    result  = {}

    for cat, kw_list in keywords_by_category.items():
        filtered = []
        for kw in kw_list:
            kw_text  = kw.get("keyword", "") if isinstance(kw, dict) else str(kw)
            kw_lower = kw_text.lower()
            skip     = False

            # SNS 플랫폼 필터
            if not is_sns_brand:
                for sns in _SNS_PLATFORMS:
                    if sns in kw_lower:
                        skip = True
                        break

            # 부정 의도 패턴
            if not skip:
                for pat in _NEGATIVE_INTENT_PATTERNS:
                    if pat in kw_text:
                        skip = True
                        break

            # forbidden_fragments (brand_identity에서 명시된 혼동 단어)
            if not skip and forbidden_lower:
                for frag in forbidden_lower:
                    if frag in kw_lower and brand_lower not in kw_lower:
                        skip = True
                        break

            if skip:
                removed.append(kw_text)
            else:
                filtered.append(kw)

        result[cat] = filtered

    if removed:
        print(f"    [규칙필터] 제거 {len(removed)}개: {', '.join(removed[:8])}{'...' if len(removed) > 8 else ''}")

    return result


def generate_ai_keyword_plan(profile):
    # 캐시 확인
    cache_key = _get_ai_cache_key(profile)
    cached    = _load_ai_cache(cache_key)
    if cached is not None:
        return cached

    brand          = profile.get("brand_name", "")
    category       = profile.get("category", "")
    brand_variants = profile.get("brand_variants", [])
    typo_variants  = profile.get("typo_variants", [])
    products       = profile.get("products", [])
    competitors    = profile.get("competitors", [])
    celebrities    = profile.get("celebrities", [])
    must_keywords  = profile.get("must_keywords", [])
    product_lines  = profile.get("product_lines", [])
    general_themes = profile.get("general_keyword_themes", [])
    sales_channels = profile.get("sales_channels", [])
    campaign_goal  = profile.get("campaign_goal", "구매전환")

    # 브랜드 정체성 문서 (setup_profile에서 생성)
    brand_identity = profile.get("brand_identity", {})
    identity_stmt  = brand_identity.get("identity_statement", f"{brand}은(는) {category} 브랜드입니다.")
    cat_context    = brand_identity.get("category_context", "")
    not_this_brand = brand_identity.get("what_this_brand_is_not", "")
    korean_names   = brand_identity.get("korean_names", brand_variants)

    # must_keywords에서 키워드 텍스트만 추출
    must_kw_list = []
    for m in must_keywords:
        if isinstance(m, dict):
            must_kw_list.append(m.get("keyword", ""))
        else:
            must_kw_list.append(str(m))
    must_kw_list = [k for k in must_kw_list if k]

    products_str    = ", ".join(products) if products else f"{category} 관련 제품"
    competitors_str = ", ".join(competitors) if competitors else "카테고리 내 주요 경쟁 브랜드"
    korean_str      = ", ".join(korean_names) if korean_names else "없음"
    themes_str      = chr(10).join(f"  * {t}" for t in general_themes) if general_themes else f"  * {category} 추천, {category} 가격, {category} 비교, {category} 후기"

    prompt = f"""
너는 10년 경력의 한국 네이버 검색광고 전문 키워드 플래너다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【캠페인 광고 대상 — 이 원칙이 모든 것보다 우선한다】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
광고주 브랜드: {brand}
이 캠페인이 홍보하는 제품: {products_str}
카테고리: {category}

⚠️ 이 캠페인은 오직 위의 제품({products_str})만 홍보한다.
⚠️ {brand}가 다른 제품군도 보유하더라도, 위 제품과 무관한 모든 키워드는 절대 생성 금지.
⚠️ 예) LG전자 노트북 캠페인 → 정수기·퓨리케어·냉장고·세탁기·TV·에어컨 등 일절 금지

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【브랜드 정체성 — 반드시 숙지】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{identity_stmt}
{cat_context}

이 브랜드·캠페인이 아닌 것: {not_this_brand}

브랜드명: {brand} | 한글 표기: {korean_str}
제품/모델: {products_str}
경쟁사: {competitors_str}
필수 포함: {", ".join(must_kw_list) if must_kw_list else "없음"}
광고 목표: {campaign_goal}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【카테고리별 키워드 생성 지침】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【브랜드 키워드】 20~30개
목적: 브랜드명을 알고 검색하는 사용자 포착
- {brand} + {category} 조합 (예: {brand} {category}, {brand} {category} 추천)
- {brand} + 가격/후기/추천/구매/비교/할인 조합
- 한글 표기({korean_str}) + {category} 조합
- 한글 표기 + 가격/후기/추천/구매/비교
- {brand} + 공식사이트/쇼핑몰
⚠️ 절대 금지: 주가, 주식, 채용, 취업, 공채, 입사, 지역명, 매장, 대리점
⚠️ 절대 금지: 이 캠페인 제품({products_str})과 무관한 {brand}의 모든 다른 제품

【상품 키워드】 40~60개  ← 반드시 40개 이상 생성할 것
목적: 특정 제품/모델을 찾는 구매 의향 높은 사용자 포착
생성 기준:
1. 브랜드명 + 제품명/모델명 조합: {products_str}의 각 모델을 활용
2. 모델명 단독 키워드 (브랜드명 없이, 모델명이 잘 알려진 경우)
3. 브랜드명 + 스펙 조합: 용량·크기·해상도·처리속도·인치·세대 등
4. 브랜드명 + 용도 조합: 게임용·업무용·학생용·디자인용·영상편집용 등
5. 브랜드명 + 가격/후기/추천/비교/구매/할인/이벤트 조합
6. 브랜드명 + 특성 조합: 가성비·경량·고성능·방수·슬림·고속 등
7. 제품명 표기 변형: 한글·영문·혼용 표기 모두 포함
⚠️ 절대 금지: 이 캠페인 제품({products_str})과 무관한 {brand}의 다른 제품 일절 금지

【일반 키워드】 40~60개
목적: 브랜드 인지 전 카테고리로 검색하는 잠재 고객 포착
- ⭐ 가장 중요: {category} 단독, {category} 추천, {category} 가격, {category} 비교, {category} 순위
- 스펙별 조합: 다양한 용량·크기·인치·세대 + {category}
- 용도별 조합: 게임용·사무용·학생용·디자인·영상편집 + {category}
- 특성별 조합: 가성비·경량·고성능·방수·슬림 + {category}
- 구매 상황별: 선물용·최신형·신제품 + {category}
- 표기 변형: 한글/영문/혼용 표기 쌍 모두 포함
- 테마 반드시 반영:
{themes_str}

【경쟁사 키워드】 25~40개  ← 반드시 25개 이상 생성할 것
목적: 경쟁 브랜드 검색자에게 노출하여 전환 유도
경쟁사 목록: {competitors_str}
- 각 경쟁사 + {category} 조합 (예: 삼성 노트북, 삼성 노트북 추천)
- 각 경쟁사 + 모델명/라인업 조합
- 각 경쟁사 + 가격/후기/추천/비교/구매/할인 조합
- 각 경쟁사 + 스펙 조합
- 경쟁사당 최소 4개 이상 생성 (경쟁사가 5개면 총 20개 이상)
- 경쟁사가 부족하면 {category} 시장의 실제 주요 브랜드로 보완
⚠️ 절대 금지: 경쟁사 + 주가/주식/채용/합병/투자/금융 관련 키워드
⚠️ 절대 금지: 경쟁사 + {category}와 무관한 다른 제품군 키워드

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【절대 금지 — 위반 시 해당 키워드 전부 무효】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ 이 캠페인 제품({products_str})과 무관한 키워드 (최우선)
❌ 주가·주식·채용·취업·공채·입사지원·합병 관련 키워드
❌ 지역명 + 브랜드 조합 (지역 매장/대리점/센터 류)
❌ "이 브랜드·캠페인이 아닌 것"에 해당하는 키워드
❌ SNS/소셜미디어: 인스타그램·유튜브·페이스북·틱톡·트위터 등 (SNS 툴 브랜드 제외)
❌ 브랜드명·제품명 철자 일부만 겹치는 타 브랜드 이름
❌ {category}와 직접 관련 없는 타 업종·타 카테고리 키워드
❌ 구매 의도 없는 키워드: 폐기·처분·버리는법·재활용·공짜·무료 등
❌ 정보 탐색성 키워드: 뜻·의미·영어로·어원·역사 등
❌ 문장 어미형 키워드 (~은, ~는, ~이다, ~있는, ~하는 등)
❌ 경쟁사 키워드를 브랜드/상품 카테고리에 포함

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
출력 형식 (JSON만, 마크다운 없음)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{{
  "selected_categories": ["브랜드 키워드", "상품 키워드", "일반 키워드", "경쟁사 키워드"],
  "category_descriptions": {{
    "브랜드 키워드": "실무적인 1~2문장",
    "상품 키워드": "실무적인 1~2문장",
    "일반 키워드": "실무적인 1~2문장",
    "경쟁사 키워드": "실무적인 1~2문장"
  }},
  "keywords_by_category": {{
    "브랜드 키워드": [],
    "상품 키워드": [],
    "일반 키워드": [],
    "경쟁사 키워드": []
  }}
}}
"""

    content = _call_llm(
        system=(
            "너는 한국 네이버 검색광고 키워드 전문가다. "
            "주어진 브랜드/카테고리에 맞는 실제 검색 키워드만 생성한다. "
            "다른 업종의 키워드를 절대 포함하지 않는다. "
            "반드시 JSON만 출력한다. 마크다운 코드블록 없이 순수 JSON만."
        ),
        user=prompt,
        temperature=0.2,
        max_tokens=4096,
    )
    data    = _safe_json_loads(content)

    selected_categories   = data.get("selected_categories", [])
    category_descriptions = data.get("category_descriptions", {})
    keywords_by_category  = data.get("keywords_by_category", {})

    cleaned = _dedupe_keywords_by_category(keywords_by_category)

    for cat in ["브랜드 키워드", "상품 키워드", "일반 키워드", "경쟁사 키워드"]:
        cleaned.setdefault(cat, [])
        category_descriptions.setdefault(cat, f"{cat} 중심의 검색 수요를 확보하기 위한 키워드")

    # ── 1단계: 규칙 기반 필터 (SNS, 부정의도, forbidden_fragments) ──
    cleaned = _rule_based_brand_filter(cleaned, profile)

    # ── 2단계: AI 기반 관련성 검증 ──
    brand_identity = profile.get("brand_identity", {})
    cleaned = _verify_keywords_by_ai(cleaned, brand, category, brand_identity, products)

    result = {
        "selected_categories":   ["브랜드 키워드", "상품 키워드", "일반 키워드", "경쟁사 키워드"],
        "category_descriptions": category_descriptions,
        "keywords_by_category":  cleaned
    }

    # 캐시 저장
    _save_ai_cache(cache_key, brand, result)

    return result


def _verify_keywords_by_ai(keywords_by_category: dict, brand: str, category: str,
                            brand_identity: dict = None, products: list = None) -> dict:
    """
    브랜드 정체성 문서 기반으로 무관 키워드 제거.
    생성 단계와 동일한 컨텍스트를 사용해 일관성 확보.
    """
    all_kws = []
    for cat, kw_list in keywords_by_category.items():
        for kw in kw_list:
            kw_text = kw.get("keyword", "") if isinstance(kw, dict) else str(kw)
            if kw_text:
                all_kws.append(kw_text)

    if not all_kws:
        return keywords_by_category

    print(f"    [검증] 총 {len(all_kws)}개 키워드 검증 중...")

    identity_stmt  = brand_identity.get("identity_statement", f"{brand}은(는) {category} 브랜드입니다.") if brand_identity else f"{brand}은(는) {category} 브랜드입니다."
    not_this_brand = brand_identity.get("what_this_brand_is_not", "") if brand_identity else ""
    korean_names   = brand_identity.get("korean_names", []) if brand_identity else []
    products_str   = ", ".join(products) if products else f"{category} 관련 제품"

    verify_prompt = f"""너는 네이버 검색광고 키워드 검증 전문가다.
아래 캠페인 범위와 브랜드 정체성을 완전히 이해하고, 이와 무관한 키워드를 제거하라.

━━━ 캠페인 광고 대상 (최우선) ━━━
광고주: {brand}
이 캠페인이 홍보하는 제품: {products_str}
카테고리: {category}
⚠️ 이 제품과 무관한 키워드는 무조건 제거

━━━ 브랜드 정체성 ━━━
{identity_stmt}
이 브랜드·캠페인이 아닌 것: {not_this_brand if not_this_brand else "명시되지 않음"}
브랜드 한글 표기: {korean_names if korean_names else "없음"}

━━━ 제거 기준 (의심스러우면 제거, 확실한 것만 유지) ━━━
1. 이 캠페인 제품({products_str})과 무관한 키워드 — 최우선 제거 기준
2. "이 브랜드·캠페인이 아닌 것"에 해당하는 키워드
3. {category}와 직접 관련이 없는 키워드
4. SNS/소셜미디어 플랫폼 이름 (인스타그램, 유튜브, 페이스북, 트위터, 틱톡 등)
5. 주가·주식·채용·취업·합병·금융 관련 키워드
6. 지역명 + 브랜드 조합 (지역 매장/대리점/센터 류)
7. 브랜드명·제품명과 철자 일부만 일치하는 타 브랜드 이름
8. 구매 의도 없는 키워드: 폐기·처분·버리는법·공짜·무료로 받기 등

━━━ 유지 기준 ━━━
- 브랜드명({brand}) + {category}/{products_str} 관련 조합
- 한글 표기({korean_names}) + 제품 관련 조합
- {category} 카테고리 순수 검색 키워드
- 경쟁사 + {category} 제품 관련 키워드

키워드 목록:
{chr(10).join(f"- {kw}" for kw in all_kws)}

반드시 아래 JSON 형식으로만 응답하라:
{{
  "remove": ["제거할키워드1", "제거할키워드2", ...]
}}
"""

    try:
        content = _call_llm(
            system=(
                "너는 네이버 검색광고 키워드 관련성 검증 전문가다. "
                "캠페인 광고 제품 범위 밖의 키워드, 카테고리와 직접 관련 없는 키워드, "
                "다른 브랜드/서비스와 혼동되는 키워드를 정확하게 찾아낸다. "
                "의심스러운 키워드는 제거하는 방향으로 판단한다. "
                "반드시 JSON만 출력한다."
            ),
            user=verify_prompt,
            temperature=0.0,
            max_tokens=2048,
        )
        data = _safe_json_loads(content)
        remove_set = set(data.get("remove", []))

        if remove_set:
            print(f"    [AI검증] 제거된 키워드 {len(remove_set)}개: {', '.join(list(remove_set)[:5])}{'...' if len(remove_set)>5 else ''}")

        # 제거 적용
        verified = {}
        for cat, kw_list in keywords_by_category.items():
            filtered = []
            for kw in kw_list:
                kw_text = kw.get("keyword", "") if isinstance(kw, dict) else str(kw)
                if kw_text not in remove_set:
                    filtered.append(kw)
            verified[cat] = filtered

        return verified

    except Exception as e:
        print(f"    [AI검증] 검증 실패 (원본 사용): {e}")
        return keywords_by_category