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


def _call_llm(system: str, user: str, temperature: float = 0.2, max_tokens: int = 4096,
              model: str = None) -> str:
    """
    Claude 우선, ANTHROPIC_API_KEY 없으면 OpenAI(gpt-4o) 폴백.
    model 인자로 특정 모델 지정 가능 (기본: claude-sonnet-4-6).
    """
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        import anthropic as _anthropic
        c = _anthropic.Anthropic(api_key=anthropic_key)
        resp = c.messages.create(
            model=model or "claude-sonnet-4-6",
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
            timeout=90,
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

# ── 매입/구매 비즈니스 감지 ─────────────────────────────────────────────────
_BUYING_KEYWORDS = frozenset([
    "매입", "구매대행", "중고매입", "매각", "회수", "처분", "수거",
    "buy", "purchase", "secondhand", "used", "refurbished",
])

def _is_buying_business(profile: dict) -> bool:
    """카테고리·제품·브랜드명에서 '매입업체' 패턴을 감지."""
    texts = " ".join([
        profile.get("category", ""),
        profile.get("brand_name", ""),
        " ".join(profile.get("products", [])),
        profile.get("brand_identity", {}).get("identity_statement", ""),
    ]).lower().replace(" ", "")
    return any(kw in texts for kw in _BUYING_KEYWORDS)


def _build_buying_business_prompt(brand, category, products, competitors,
                                   korean_str, must_str, campaign_goal,
                                   identity_stmt, not_this_brand,
                                   doc_context: str = "",
                                   campaign_notes: str = "") -> str:
    """
    매입/구매 비즈니스 전용 키워드 생성 프롬프트.
    판매자(물건을 팔고 싶은 사람)가 검색할 키워드를 생성한다.
    """
    products_str = ", ".join(products) if products else f"{category} 관련 품목"
    competitors_str = ", ".join(competitors) if competitors else "동종 매입업체"
    doc_section = f"\n━━━ 참고 문서 내용 ━━━\n{doc_context[:1500]}\n" if doc_context else ""
    notes_section = f"\n━━━ 캠페인 특이사항 ━━━\n{campaign_notes}\n" if campaign_notes else ""

    return f"""아래 광고주가 네이버 파워링크 광고를 집행한다.
이 광고주는 제품을 "판매"하는 게 아니라 특정 품목을 "매입(구매)"하는 업체다.
따라서 키워드의 타깃은 "물건을 팔고 싶어하는 사람(판매자)"이다.

━━━ 광고주 브리핑 ━━━
브랜드: {brand}  |  한글 표기: {korean_str}
매입 품목: {products_str}
카테고리: {category}
동종 경쟁 매입업체: {competitors_str}
광고 목표: {campaign_goal}
{f"브랜드 정의: {identity_stmt}" if identity_stmt else ""}
{f"이 캠페인이 아닌 것: {not_this_brand}" if not_this_brand else ""}
{f"반드시 포함할 키워드: {must_str}" if must_str != "없음" else ""}
{notes_section}{doc_section}

━━━ 핵심 원칙 ━━━
● 타깃: "{products_str}을 처분/판매하려는 한국 사람이 네이버에서 검색할 키워드"
● 검색 의도: 팔고 싶다 / 처분하고 싶다 / 매각하고 싶다 / 매입업체를 찾는다
● 절대 제외: 매입 품목을 "구매하려는" 소비자 키워드 (반대 방향)
● 절대 제외: 관련 없는 카테고리 품목 (예: 중고 매입이어도 오토바이·가전·핸드폰 등 제외)
● 매입 대상 품목({products_str})과 직접 관련된 키워드만 생성

━━━ 4개 광고 그룹 ━━━

[브랜드 키워드] 15~25개
{brand}를 이미 알고 직접 검색하는 사람 대상
→ {brand} + 매입/구매/연락처/위치/후기
→ {korean_str} + 동일 조합

[상품 키워드] 40~60개  ← 가장 중요
구체적인 품목을 판매하려는 사람 대상
→ 품목명 + 매입/팝니다/처분/판매/매각/업체
→ 품목명 + 중고/사용/실험실/연구소
→ 품목명 단독 (중고 거래 의도 포함)
→ 모델명/시리즈명 + 매입/팝니다
→ 제조사 + 품목명 + 매입/처분
→ 브랜드 + 품목명 + 팝니다/매각

[일반 키워드] 30~50개
매입업체를 찾는 잠재 고객 (어떤 브랜드인지 모르는 상태)
→ 중고 + {category} + 매입/처분/업체/전문
→ 실험실/연구소/제약사/바이오 + {category} + 처분/판매
→ {category} + 중고 + 팝니다/삽니다/업체
→ 분야별 카테고리 장비 + 처분/매각/매입
→ "중고 장비 매입업체", "실험실 장비 처분" 류

[경쟁사 키워드] 20~35개
동종 매입업체를 검색하는 사람에게 노출
→ 경쟁 매입업체명 + 매입/가격/후기/비교
→ 동종업체 + {category} + 매입

━━━ 출력 형식 (JSON만, 마크다운 없음) ━━━
{{
  "selected_categories": ["브랜드 키워드", "상품 키워드", "일반 키워드", "경쟁사 키워드"],
  "category_descriptions": {{
    "브랜드 키워드": "한 문장",
    "상품 키워드": "한 문장",
    "일반 키워드": "한 문장",
    "경쟁사 키워드": "한 문장"
  }},
  "keywords_by_category": {{
    "브랜드 키워드": ["키워드1", "키워드2"],
    "상품 키워드": ["키워드1", "키워드2"],
    "일반 키워드": ["키워드1", "키워드2"],
    "경쟁사 키워드": ["키워드1", "키워드2"]
  }}
}}"""


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
    doc_context    = profile.get("doc_context", "")       # PDF/문서 추출 텍스트
    campaign_notes = profile.get("campaign_notes", "")   # 사용자 캠페인 메모

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
    must_str        = ", ".join(must_kw_list) if must_kw_list else "없음"

    # ── 매입 비즈니스 분기 ──────────────────────────────────────────────────
    is_buying = _is_buying_business(profile)
    if is_buying:
        print(f"    [AI키워드] 매입 비즈니스 감지 → 판매자 의도 키워드 모드 적용")
        user_msg = _build_buying_business_prompt(
            brand, category, products, competitors,
            korean_str, must_str, campaign_goal,
            identity_stmt, not_this_brand, doc_context, campaign_notes
        )
        content = _call_llm(
            system=(
                "너는 10년 경력의 네이버 파워링크 검색광고 전문 컨설턴트다. "
                "이 광고주는 특정 품목을 매입하는 업체이므로, "
                "물건을 팔고 싶은 사람(판매자)이 검색할 키워드만 생성한다. "
                "절대 구매자 의도 키워드나 카테고리와 무관한 품목 키워드를 생성하지 않는다. "
                "반드시 JSON만 출력한다."
            ),
            user=user_msg,
            temperature=0.2,
            max_tokens=4096,
        )
        data = _safe_json_loads(content)
        keywords_by_category = data.get("keywords_by_category", {})
        category_descriptions = data.get("category_descriptions", {})
        selected_categories   = data.get("selected_categories", [])
        cleaned = _dedupe_keywords_by_category(keywords_by_category)
        for cat in ["브랜드 키워드", "상품 키워드", "일반 키워드", "경쟁사 키워드"]:
            cleaned.setdefault(cat, [])
            category_descriptions.setdefault(cat, f"{cat} 중심의 검색 수요를 확보하기 위한 키워드")
        cleaned = _rule_based_brand_filter(cleaned, profile)
        result = {
            "selected_categories":   ["브랜드 키워드", "상품 키워드", "일반 키워드", "경쟁사 키워드"],
            "category_descriptions": category_descriptions,
            "keywords_by_category":  cleaned
        }
        _save_ai_cache(cache_key, brand, result)
        return result

    # ── 일반 판매 비즈니스 프롬프트 ─────────────────────────────────────────
    doc_section = ""
    if doc_context:
        doc_section = f"\n━━━ 참고 문서 내용 (제품 카탈로그 / 마케팅 문서) ━━━\n{doc_context[:1500]}\n"
    notes_section = f"\n━━━ 캠페인 특이사항 ━━━\n{campaign_notes}\n" if campaign_notes else ""

    # 광고주 브리핑 → 소비자 구매 검색 시뮬레이션 방식
    user_msg = f"""아래 광고주가 네이버 파워링크 광고를 집행한다.
SEO/SEM 전문가 관점에서 이 광고주의 최적 검색광고 키워드를 제안해줘.

━━━ 광고주 브리핑 ━━━
브랜드: {brand}  |  한글 표기: {korean_str}
이 캠페인의 광고 제품: {products_str}
카테고리: {category}
경쟁사: {competitors_str}
광고 목표: {campaign_goal}
{f"브랜드 정의: {identity_stmt}" if identity_stmt else ""}
{f"이 캠페인이 아닌 것 (제외 대상): {not_this_brand}" if not_this_brand else ""}
{f"반드시 포함할 키워드: {must_str}" if must_str != "없음" else ""}
{notes_section}{doc_section}

━━━ 핵심 원칙 ━━━
● "{products_str}을 구매하려는 한국 소비자가 네이버에서 실제로 검색할 검색어"만 생성한다
● {brand}의 다른 제품군은 이 캠페인과 무관 → 완전 제외
● 구매 의도 없는 검색어 (뉴스·주가·채용·SNS·학술·뜻·폐기 등) 완전 제외
● 제품명에 포함된 짧은 영문이 다른 영어 단어의 부분이 되는 키워드 제외
  (예: 제품명 "gram" → "grammar", "instagram" 등 완전히 다른 단어 제외)
● 브랜드명·제품명이 식품·음료·과자·생활용품·타 업종 브랜드와 동일하거나 유사한 경우,
  해당 타 업종 연상 키워드 완전 제외
  (예: 게임명 "이클립스" → "이클립스포도", "이클립스캔디", "이클립스껌" 등 식품류 제외)
● 반드시 {category} 카테고리와 직접 연관된 검색 의도를 가진 키워드만 생성

━━━ 4개 광고 그룹 ━━━

[브랜드 키워드] 20~30개
{brand}를 이미 알고 직접 검색하는 구매 의향 사용자 대상
→ {brand} + {category}/추천/가격/후기/구매/할인/비교
→ {korean_str} + 동일 조합
→ 제외: 주가·채용·공채·지역매장·{brand}의 다른 제품군

[상품 키워드] 40~60개  ← 가장 중요, 반드시 충분히 생성
{products_str}을 구체적으로 찾는 구매 직전 소비자 대상
→ 브랜드 + 모델명, 모델명 단독(잘 알려진 경우)
→ 브랜드 + 스펙(인치/용량/세대/처리속도 등)
→ 브랜드 + 용도(게임용/업무용/학생용/영상편집용 등)
→ 브랜드 + 특성(가성비/경량/고성능/슬림 등)
→ 한글·영문·혼용 표기 모두 포함
→ 제외: 이 캠페인 제품 외 {brand}의 모든 다른 제품

[일반 키워드] 40~60개
{category}로 검색하는 브랜드 인지 전 잠재 구매자 대상
→ {category} 단독, 추천, 가격, 비교, 순위, 후기
→ 스펙별: 다양한 크기·용량·인치·세대 + {category}
→ 용도별: 게임용·사무용·학생용·디자인·영상편집 + {category}
→ 특성별: 가성비·경량·고성능·슬림 + {category}
→ 한글/영문/혼용 표기 쌍 포함

[경쟁사 키워드] 25~40개  ← 반드시 25개 이상
{competitors_str} 검색자에게 노출하여 전환 유도
→ 각 경쟁사 + {category}/모델/가격/추천/비교/구매
→ 경쟁사당 최소 4개 이상 (경쟁사 목록이 짧으면 {category} 시장 주요 브랜드로 보완)
→ 제외: 경쟁사 + 주가·채용·합병 등 비구매 키워드

━━━ 출력 형식 (JSON만, 마크다운 없음) ━━━
{{
  "selected_categories": ["브랜드 키워드", "상품 키워드", "일반 키워드", "경쟁사 키워드"],
  "category_descriptions": {{
    "브랜드 키워드": "한 문장",
    "상품 키워드": "한 문장",
    "일반 키워드": "한 문장",
    "경쟁사 키워드": "한 문장"
  }},
  "keywords_by_category": {{
    "브랜드 키워드": ["키워드1", "키워드2"],
    "상품 키워드": ["키워드1", "키워드2"],
    "일반 키워드": ["키워드1", "키워드2"],
    "경쟁사 키워드": ["키워드1", "키워드2"]
  }}
}}"""

    content = _call_llm(
        system=(
            "너는 10년 경력의 네이버 파워링크 검색광고 전문 컨설턴트다. "
            "광고주의 제품을 구매하려는 한국 소비자가 네이버에서 실제로 검색할 키워드만 추천한다. "
            "구매 의도가 없는 키워드, 광고 제품과 무관한 키워드는 절대 생성하지 않는다. "
            "반드시 JSON만 출력한다."
        ),
        user=user_msg,
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

    # 1차: 규칙 기반 필터 (SNS, 부정의도, forbidden_fragments)
    cleaned = _rule_based_brand_filter(cleaned, profile)
    # 2차: AI 검증 — 동음이의어·무관 카테고리 키워드 제거 (Haiku로 빠르게)
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
                "브랜드명이 동음이의어로 사용되는 타 업종(식품·음료·과자·생활용품 등) 연상 키워드, "
                "다른 브랜드/서비스와 혼동되는 키워드를 정확하게 찾아낸다. "
                "의심스러운 키워드는 제거하는 방향으로 판단한다. "
                "반드시 JSON만 출력한다."
            ),
            user=verify_prompt,
            temperature=0.0,
            max_tokens=2048,
            model="claude-haiku-4-5-20251001",
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