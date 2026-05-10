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

    prompt = f"""
너는 10년 경력의 한국 네이버 검색광고 전문 키워드 플래너다.
아래 브랜드 정체성 문서를 완전히 이해한 뒤, 이 브랜드에 맞는 키워드만 생성하라.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【브랜드 정체성 - 반드시 숙지】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{identity_stmt}
{cat_context}

이 브랜드가 아닌 것: {not_this_brand}

브랜드명: {brand}
한글 표기: {korean_names if korean_names else "없음"}
카테고리: {category}
제품/모델: {products if products else "카테고리 기반 추정"}
경쟁사: {competitors if competitors else "카테고리 기반 추정"}
필수 포함: {must_kw_list if must_kw_list else "없음"}
키워드 테마: {general_themes if general_themes else "카테고리 기반 생성"}
광고 목표: {campaign_goal}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【카테고리별 키워드 생성 지침】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【브랜드 키워드】 15~25개
- 브랜드명({brand}) + 제품/카테고리 조합
- 한글 표기({korean_names}) + 제품/카테고리 조합
- 브랜드명 + 가격/후기/추천/구매/비교
- 위에서 정의한 이 브랜드와 관련된 키워드만 생성
- "이 브랜드가 아닌 것"에 해당하는 키워드는 절대 생성 금지

【상품 키워드】 15~25개
- 브랜드명({brand}) 또는 한글표기({korean_names}) + 실제 제품/모델 조합
- 브랜드명 + 용량 (예: ENB 1TB, ENB 2TB)
- 브랜드명 + 가격/후기/추천/비교/구매
⚠️ 절대 금지: 브랜드 정체성("이 브랜드가 아닌 것")에 해당하는 키워드
⚠️ 절대 금지: enbridge, enby, ENBD, enbd 의학용어 등 다른 의미의 영문 조합

【일반 키워드】 40~60개
- {category} 카테고리에서 실제 검색량이 많은 핵심 키워드를 반드시 포함
- ⭐ 검색량 많은 핵심 키워드 우선: {category} 단독, {category} 추천, {category} 가격 등
- 용량별 (예: 1TB, 2TB, 4TB, 500GB 등) 키워드 반드시 포함
- 용도별 (예: 게임용, 영상편집, 맥북, 백업 등) 키워드 포함
- 특성별 (예: 가성비, 대용량, 휴대용, 고속 등) 키워드 포함
- 표기 변형 쌍 포함 (같은 제품의 다른 표현)
- 브랜드명 없는 카테고리 순수 검색어 위주로 생성
- 아래 테마 반드시 반영:
{chr(10).join(f"  * {t}" for t in general_themes) if general_themes else f"  * {category} 추천, 가격, 비교, 후기"}

【경쟁사 키워드】 10~15개
- 입력된 경쟁사 브랜드명 + {category} 제품 관련 조합만
- 경쟁사당 최대 2~3개
⚠️ 절대 금지: 경쟁사 + 주가/주식/채용/합병 등 투자/금융 관련 키워드

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【절대 금지 — 반드시 준수】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ "이 브랜드가 아닌 것"에 해당하는 키워드
❌ SNS/소셜미디어 플랫폼: 인스타그램, 유튜브, 페이스북, 틱톡, 트위터 등
   (소셜미디어 마케팅 툴 브랜드가 아닌 경우 완전 금지)
❌ 브랜드명·제품명과 철자 일부가 겹치는 타 브랜드 이름
   예) 제품에 "gram"이 포함돼도 Instagram·Grammarly·gramicci·gramsnap 생성 금지
   예) 브랜드가 "ENB"라도 Enbridge·CJ ENM·ENBD 생성 금지
❌ {category}와 직접 관련 없는 타 업종·타 카테고리 키워드
❌ 구매 의도 없는 키워드: 폐기, 처분, 버리는법, 재활용, 공짜, 무료로 받기 등
❌ 정보 탐색성 키워드: 뜻, 의미, 영어로, 어원, 역사 등
❌ 문장형 키워드
❌ 주가/채용/합병/의학용어/금융 관련 키워드
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
    cleaned = _verify_keywords_by_ai(cleaned, brand, category, brand_identity)

    result = {
        "selected_categories":   ["브랜드 키워드", "상품 키워드", "일반 키워드", "경쟁사 키워드"],
        "category_descriptions": category_descriptions,
        "keywords_by_category":  cleaned
    }

    # 캐시 저장
    _save_ai_cache(cache_key, brand, result)

    return result


def _verify_keywords_by_ai(keywords_by_category: dict, brand: str, category: str,
                            brand_identity: dict = None) -> dict:
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

    # 브랜드 정체성 문서 컨텍스트
    identity_stmt  = brand_identity.get("identity_statement", f"{brand}은(는) {category} 브랜드입니다.") if brand_identity else f"{brand}은(는) {category} 브랜드입니다."
    not_this_brand = brand_identity.get("what_this_brand_is_not", "") if brand_identity else ""
    korean_names   = brand_identity.get("korean_names", []) if brand_identity else []

    verify_prompt = f"""너는 네이버 검색광고 키워드 검증 전문가다.
아래 브랜드 정체성을 완전히 이해하고, 이와 무관한 키워드를 제거하라.

━━━ 브랜드 정체성 ━━━
{identity_stmt}
이 브랜드가 아닌 것: {not_this_brand if not_this_brand else "명시되지 않음"}
브랜드 한글 표기: {korean_names if korean_names else "없음"}

━━━ 제거 기준 (의심스러우면 제거, 확실한 것만 유지) ━━━
1. 위의 "이 브랜드가 아닌 것"에 해당하는 키워드
2. {category}와 직접 관련이 없는 키워드 (간접적이거나 불분명한 경우도 제거)
3. SNS/소셜미디어 플랫폼 이름 (인스타그램, 유튜브, 페이스북, 트위터, 틱톡 등)
4. 주가/채용/합병/의학용어/금융 관련 키워드
5. 브랜드명·제품명과 철자 일부만 일치하는 타 브랜드 이름
   - 예) 브랜드가 ENB면: enbridge, enphase, CJ ENM 등 제거
   - 예) 제품에 "gram"이 포함돼도: Instagram, Grammarly, gramicci, gramsnap 등 제거
6. 브랜드 변형처럼 보이지만 실제로 다른 회사인 키워드
7. 구매 의도 없는 키워드: 폐기, 처분, 버리는법, 공짜, 무료로 받기 등
8. 이 브랜드 광고를 클릭할 가능성이 없는 검색 의도를 가진 키워드

━━━ 유지 기준 ━━━
- 브랜드명({brand}) + {category} 관련 조합
- 한글 표기({korean_names}) + 제품 관련 조합
- {category} 카테고리 순수 검색 키워드
- 입력된 경쟁사 + {category} 제품 관련 키워드

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
                "카테고리와 직접 관련이 없거나 다른 브랜드/서비스와 혼동되는 키워드를 정확하게 찾아낸다. "
                "의심스러운 키워드는 제거하는 방향으로 판단한다. "
                "반드시 JSON만 출력한다."
            ),
            user=verify_prompt,
            temperature=0.0,
            max_tokens=1024,
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