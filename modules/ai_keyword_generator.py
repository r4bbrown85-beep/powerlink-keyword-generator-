import json
import os
import re
import time
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
    429 rate_limit_error 발생 시 최대 2회 재시도 (65초 간격).
    model 인자로 특정 모델 지정 가능 (기본: claude-sonnet-4-6).
    """
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        import anthropic as _anthropic
        c = _anthropic.Anthropic(api_key=anthropic_key, max_retries=0)
        for attempt in range(3):
            try:
                resp = c.messages.create(
                    model=model or "claude-sonnet-4-6",
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                    timeout=90,
                )
                return resp.content[0].text
            except _anthropic.RateLimitError:
                if attempt < 2:
                    wait_sec = 65
                    print(f"    [API] 토큰 한도 초과 — {wait_sec}초 후 재시도 ({attempt+1}/2)...")
                    time.sleep(wait_sec)
                else:
                    raise
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


def _call_llm_with_web_search(system: str, user: str, max_tokens: int = 2000) -> str:
    """Claude API + web_search_20250305 도구로 실시간 웹 검색 후 응답 생성.
    ANTHROPIC_API_KEY 없거나 웹검색 도구 미지원 시 일반 _call_llm으로 폴백."""
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        return _call_llm(system, user, max_tokens=max_tokens)

    import anthropic as _anthropic
    c = _anthropic.Anthropic(api_key=anthropic_key, max_retries=0)
    messages = [{"role": "user", "content": user}]
    last_resp = None

    try:
        for _ in range(10):
            last_resp = c.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=max_tokens,
                system=system,
                messages=messages,
                tools=[{"type": "web_search_20250305", "name": "web_search"}],
                timeout=120,
            )

            if last_resp.stop_reason == "end_turn":
                return "".join(b.text for b in last_resp.content if hasattr(b, "text"))

            if last_resp.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": last_resp.content})
                tool_results = [
                    {"type": "tool_result", "tool_use_id": b.id, "content": ""}
                    for b in last_resp.content if b.type == "tool_use"
                ]
                messages.append({"role": "user", "content": tool_results})
            else:
                break

        if last_resp:
            return "".join(b.text for b in last_resp.content if hasattr(b, "text"))
    except Exception as web_err:
        print(f"    [웹검색] 도구 사용 불가 ({type(web_err).__name__}): {web_err}")
        print(f"    [웹검색] 일반 LLM 호출로 폴백 (웹검색 없이 생성)...")
        return _call_llm(system, user, max_tokens=max_tokens)

    return ""


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


# ── 캠페인 목표별 키워드 생성 가이드라인 ─────────────────────────────────────

_GOAL_GUIDES = {
    "사전예약/사전등록": (
        "● 이 캠페인은 출시 전 사전예약·사전등록 유도가 핵심이다\n"
        "● 브랜드/상품 키워드에 '사전예약, 사전등록, 얼리버드, 출시일, 베타신청, 사전체험, 출시예정' 등을 적극 결합\n"
        "● 일반 키워드는 출시 전 기대감을 가진 잠재 이용자가 검색할 키워드 위주로 구성"
    ),
    "런칭/서비스 오픈": (
        "● 이 캠페인은 서비스·게임·브랜드의 신규 론칭을 알리는 것이 핵심이다\n"
        "● '출시, 오픈, 런칭, 정식서비스, 신규오픈, 시작하기, 첫달무료' 등 개시 관련 키워드 강조\n"
        "● 기존 유사 서비스 이용자가 갈아타도록 유도하는 비교·전환 키워드도 포함"
    ),
    "신작/개봉 홍보": (
        "● 이 캠페인은 신작 콘텐츠(영화·OTT·웹툰·공연)의 관심 유도 및 관람/시청 전환이 핵심이다\n"
        "● '개봉, 신작, 상영, 스트리밍, 첫방영, 예매, 줄거리, 출연진, 감독, 리뷰, 후기' 계열 키워드 적극 포함\n"
        "● 브랜드 키워드는 작품명·시리즈명 중심, 상품 키워드는 등장인물·OST·에피소드 등 콘텐츠 요소 포함\n"
        "● 경쟁사는 같은 장르 경쟁 콘텐츠/플랫폼으로 구성"
    ),
    "문의/상담 유도": (
        "● 이 캠페인은 직접 구매보다 문의·상담·견적 요청을 통한 리드 전환이 핵심이다\n"
        "● '무료상담, 상담신청, 전문가상담, 견적문의, 전화상담, 온라인상담, 무료견적, 상담예약' 계열 키워드 적극 결합\n"
        "● 일반 키워드는 구매 고려 단계(비교·추천·선택방법)에 있는 잠재고객 위주로 구성"
    ),
    "가입자수 확대": (
        "● 이 캠페인은 신규 회원 가입·구독·등록 유도가 핵심이다\n"
        "● '회원가입, 무료가입, 구독신청, 무료등록, 계정만들기, 서비스가입, 무료회원' 계열 키워드 강조\n"
        "● 일반 키워드는 서비스를 처음 알게 된 신규 이용자가 검색할 키워드 위주로 구성"
    ),
    "무료체험 신청": (
        "● 이 캠페인은 제품·서비스의 무료 체험 신청 유도가 핵심이다\n"
        "● '무료체험, 체험판, 무료이용, 30일무료, 트라이얼, 무료신청, 체험신청, 데모신청' 계열 키워드 강조\n"
        "● 진입 장벽을 낮추는 키워드(무료·체험·부담없이) 우선 구성"
    ),
    "방문/예약 유도": (
        "● 이 캠페인은 오프라인 매장 방문 또는 온라인 예약 전환이 핵심이다\n"
        "● '방문예약, 온라인예약, 예약신청, 매장위치, 예약가능, 당일예약, 사전예약' 계열 키워드 강조\n"
        "● 지역명 + 브랜드/서비스 조합 키워드 적극 포함 (매장 방문 의도 캡처)"
    ),
}


def _build_goal_guidance(campaign_goal: str) -> str:
    """선택된 캠페인 목표에 해당하는 프롬프트 가이드라인 반환."""
    lines = [guide for key, guide in _GOAL_GUIDES.items() if key in campaign_goal]
    if not lines:
        return ""
    return "\n━━━ 캠페인 목표별 키워드 가이드라인 ━━━\n" + "\n".join(lines)


def _build_buying_business_prompt(brand, category, products, competitors,
                                   korean_str, must_str, campaign_goal,
                                   identity_stmt, not_this_brand,
                                   doc_context: str = "",
                                   campaign_notes: str = "",
                                   sa_strategy_memo: str = "") -> str:
    """
    매입/구매 비즈니스 전용 키워드 생성 프롬프트.
    판매자(물건을 팔고 싶은 사람)가 검색할 키워드를 생성한다.
    """
    products_str     = ", ".join(products) if products else f"{category} 관련 품목"
    competitors_str  = ", ".join(competitors) if competitors else "동종 매입업체"
    doc_section      = f"\n━━━ 참고 문서 내용 ━━━\n{doc_context[:1500]}\n" if doc_context else ""
    notes_section    = f"\n━━━ 캠페인 특이사항 ━━━\n{campaign_notes}\n" if campaign_notes else ""
    strategy_section = f"\n━━━ SA 전략 인사이트 (자동 분석) ━━━\n{sa_strategy_memo}\n" if sa_strategy_memo else ""
    goal_section     = _build_goal_guidance(campaign_goal)

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
{notes_section}{strategy_section}{goal_section}{doc_section}

━━━ 핵심 원칙 ━━━
● 타깃: "{products_str}을 처분/판매하려는 한국 사람이 네이버에서 검색할 키워드"
● 검색 의도: 팔고 싶다 / 처분하고 싶다 / 매각하고 싶다 / 매입업체를 찾는다
● 절대 제외: 매입 품목을 "구매하려는" 소비자 키워드 (반대 방향)
● 절대 제외: 관련 없는 카테고리 품목 (예: 중고 매입이어도 오토바이·가전·핸드폰 등 제외)
● 매입 대상 품목({products_str})과 직접 관련된 키워드만 생성

━━━ 광고 그룹 설계 ━━━
이 매입 광고주에 맞는 3~4개 광고 그룹을 직접 설계한다. 타입은 4종만 허용된다.

[brand 타입] 필수 1개 — {brand}를 직접 검색하는 사람, 15~25개
→ {brand} + 매입/구매/연락처/위치/후기
→ {korean_str} + 동일 조합

[product 타입] 권장 1개 — 구체적 품목 판매 의도, 40~60개
→ 품목명({products_str}) + 매입/팝니다/처분/판매/매각/업체
→ 품목명 + 중고/사용/실험실/연구소
→ 모델명/시리즈명 + 매입/팝니다, 제조사+품목+처분

[general 타입] 권장 1개 — 브랜드 모르고 매입업체 찾는 검색, 30~50개
→ 중고 + {category} + 매입/처분/업체/전문
→ {category} + 팝니다/삽니다/업체/처분
→ "중고 장비 매입업체", "실험실 장비 처분" 류

[competitor 타입] 선택 1개 — 동종 매입업체 검색자 전환 유도, 20~35개
→ 경쟁 매입업체명 + 매입/가격/후기/비교

그룹명은 한국어, 광고주 매입 업종에 맞게 구체적으로 명명한다.
예: "{brand} 브랜드", "{products_str} 매입", "{category} 매입업체", "경쟁사"
target_rank: brand=1, product=1~2, general=3~4, competitor=4~5

━━━ 출력 형식 (JSON만, 마크다운 없음) ━━━
{{
  "category_configs": [
    {{"name": "그룹명", "type": "brand|product|general|competitor", "target_rank": 1, "description": "한 문장"}}
  ],
  "keywords_by_category": {{
    "그룹명": ["키워드1", "키워드2"]
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
    # 행정/서식 — 문서 다운로드 의도, 구매 전환 없음
    "업무분장", "민간군사기업",
    # 초광범위 기업 비교 패턴 — 특정 브랜드 구매 의도 없음
    "기업비교", "기업추천", "기업가격",
    # 서식/양식 검색 — 무료 문서 탐색 의도, 소프트웨어 구매 전환 없음
    "양식", "서식", "일지양식", "일지서식",
    # 기업 분석/평가 정보 검색 — 비즈메카류 서비스와 무관
    "기업분析보고서", "기업분석보고서", "기업분析사이트", "기업분석사이트",
    # 기업 검색 디렉토리 — 소프트웨어/서비스 구매 의도 없음
    "기업검색", "중소기업검색",
]

# AI 키워드 캐시 설정
_AI_CACHE_DIR  = Path("data/cache/ai_keywords")
_AI_CACHE_DAYS = 7
# 프롬프트·필터 로직 변경 시 이 값을 올리면 기존 캐시가 자동 무효화됨
_AI_CACHE_VERSION = "v6"

# ── 카테고리 타입별 bid_simulator 필드 기본값 ─────────────────────────────
_CAT_TYPE_DEFAULTS = {
    "brand":      {"priority": 1.30, "min_keywords": 5,  "target_rank": 1, "max_rank": 3,
                   "max_single_ratio": 0.20, "cpc_factor": 1.10, "color": "BDD7EE"},
    "product":    {"priority": 1.22, "min_keywords": 3,  "target_rank": 2, "max_rank": 5,
                   "max_single_ratio": 0.15, "cpc_factor": 1.05, "color": "C6EFCE"},
    "general":    {"priority": 1.00, "min_keywords": 3,  "target_rank": 3, "max_rank": 5,
                   "max_single_ratio": 0.15, "cpc_factor": 1.00, "color": "FFF2CC"},
    "competitor": {"priority": 0.88, "min_keywords": 0,  "target_rank": 4, "max_rank": 5,
                   "max_single_ratio": 0.04, "cpc_factor": 0.90, "color": "FCE4D6",
                   "max_budget_ratio": 0.15},
}

# AI 미반환 시 fallback 4개 카테고리
_DEFAULT_CAT_CONFIGS_RAW = [
    {"name": "브랜드 키워드", "type": "brand",      "target_rank": 1, "description": "브랜드 직접 검색 사용자"},
    {"name": "상품 키워드",   "type": "product",    "target_rank": 2, "description": "구체적 제품 탐색 사용자"},
    {"name": "일반 키워드",   "type": "general",    "target_rank": 3, "description": "카테고리 탐색 잠재 구매자"},
    {"name": "경쟁사 키워드", "type": "competitor", "target_rank": 4, "description": "경쟁사 검색자 전환 유도"},
]


def _enrich_cat_configs(cat_cfgs_raw: list) -> list:
    """AI 생성 category_configs에 bid_simulator 필요 필드 채우기."""
    result = []
    for i, cat in enumerate(cat_cfgs_raw):
        t = str(cat.get("type", "general")).lower()
        if t not in _CAT_TYPE_DEFAULTS:
            t = "general"
        enriched = _CAT_TYPE_DEFAULTS[t].copy()
        enriched["name"]        = cat.get("name", f"카테고리{i+1}")
        enriched["type"]        = t
        enriched["target_rank"] = int(cat.get("target_rank", enriched["target_rank"]))
        if "description" in cat:
            enriched["description"] = cat["description"]
        result.append(enriched)
    return result


def _get_ai_cache_key(profile: dict) -> str:
    key_fields = {
        "brand_name": profile.get("brand_name", ""),
        "category":   profile.get("category", ""),
        "products":   sorted(profile.get("products", [])),
        "competitors": sorted(profile.get("competitors", [])),
        "_v":          _AI_CACHE_VERSION,
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
                "cache_ver":  _AI_CACHE_VERSION,
                "data":       data,
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"    AI 캐시 저장 실패: {e}")


def clear_ai_cache_for_brand(brand_name: str) -> int:
    """특정 브랜드의 AI 키워드 캐시(키워드 + 전략메모) 삭제. 삭제된 파일 수 반환."""
    _AI_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe_brand = re.sub(r'[\\/:*?"<>| ]', "_", brand_name)
    deleted = 0
    for f in _AI_CACHE_DIR.glob(f"{safe_brand}_*.json"):
        try:
            f.unlink()
            deleted += 1
        except Exception:
            pass
    return deleted


def clear_all_ai_cache() -> int:
    """전체 AI 키워드 캐시 삭제. 삭제된 파일 수 반환."""
    _AI_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    deleted = 0
    for f in _AI_CACHE_DIR.glob("*.json"):
        try:
            f.unlink()
            deleted += 1
        except Exception:
            pass
    return deleted


def list_ai_cached_brands() -> list[dict]:
    """캐시된 브랜드 목록 반환 [{brand_name, cached_at, files, cache_ver, is_stale}]."""
    _AI_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    brands: dict[str, dict] = {}
    for f in sorted(_AI_CACHE_DIR.glob("*.json")):
        try:
            import json as _json
            data = _json.loads(f.read_text(encoding="utf-8"))
            bname = data.get("brand_name", "?")
            ver   = data.get("cache_ver", "v1")
            if bname not in brands:
                brands[bname] = {
                    "brand_name": bname,
                    "cached_at":  data.get("cached_at", "")[:16],
                    "files":      0,
                    "cache_ver":  ver,
                    "is_stale":   ver != _AI_CACHE_VERSION,
                }
            brands[bname]["files"] += 1
        except Exception:
            pass
    return list(brands.values())


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
    # 경쟁사명 목록 (3자 이상만, 소문자 정규화)
    competitors_lower  = [
        c.lower().strip() for c in profile.get("competitors", [])
        if isinstance(c, str) and len(c.strip()) >= 3
    ]

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

            # 경쟁사 단독 키워드 차단: 경쟁사명 포함 + 우리 브랜드명 없음
            # 단, 경쟁사 키워드 카테고리는 경쟁사명이 포함되는 것이 의도적이므로 제외
            if not skip and competitors_lower and brand_lower and cat != "경쟁사 키워드":
                for comp in competitors_lower:
                    if comp in kw_lower and brand_lower not in kw_lower:
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


def generate_sa_strategy_memo(profile: dict) -> str:
    """
    네이버 SA 전략 브리핑 자동 생성.
    브랜드 정보를 분석해 키워드 생성에 참고할 전략 인사이트를 반환.
    결과는 7일 캐시 — 같은 브랜드 반복 생성 시 재호출 없음.
    """
    cache_key = _get_ai_cache_key(profile) + "_strategy"
    cached    = _load_ai_cache(cache_key)
    if cached is not None:
        return cached.get("memo", "")

    brand          = profile.get("brand_name", "")
    category       = profile.get("category", "")
    products       = profile.get("products", [])
    competitors    = profile.get("competitors", [])
    campaign_goal  = profile.get("campaign_goal", "구매전환")
    campaign_notes = profile.get("campaign_notes", "")
    brand_identity = profile.get("brand_identity", {})
    identity_stmt  = brand_identity.get("identity_statement", "")

    products_str    = ", ".join(products) if products else f"{category} 관련 제품"
    competitors_str = ", ".join(competitors) if competitors else "카테고리 내 주요 경쟁 브랜드"
    notes_line      = f"\n캠페인 메모: {campaign_notes}" if campaign_notes else ""
    identity_line   = f"\n브랜드 정의: {identity_stmt}" if identity_stmt else ""

    prompt = f"""네이버 파워링크 캠페인 제안서를 위한 키워드 전략 인사이트를 도출해주세요.

광고주: {brand} / 카테고리: {category} / 제품: {products_str}
경쟁사: {competitors_str} / 목표: {campaign_goal}{identity_line}{notes_line}

웹 검색으로 {brand}의 서비스 특징, 경쟁사와의 차별점, 타깃 고객 검색 패턴을 파악하세요.

아래 항목을 각 2~3줄로 간결하게 작성 (총 400자 이내):
1. 브랜드 현황: {brand} 핵심 서비스/포지셔닝
2. 검색 패턴: 잠재 고객이 실제 검색할 키워드 유형
3. 차별화 기회: 경쟁사 대비 강점 키워드 영역
4. 제외 패턴: 전환율 낮은 키워드 유형"""

    try:
        memo = _call_llm_with_web_search(
            system=(
                "당신은 10년 경력의 네이버 파워링크 검색광고 전략 컨설턴트입니다. "
                "웹 검색 도구를 활용해 브랜드의 최신 정보를 수집하고 키워드 전략 인사이트를 제공합니다. "
                "마크다운 없이 일반 텍스트로만 응답합니다."
            ),
            user=prompt,
            max_tokens=1200,
        )
        memo = memo.strip()
        if memo:
            _save_ai_cache(cache_key, brand, {"memo": memo})
            print(f"    [SA전략메모] 생성 완료 ({len(memo)}자)")
        else:
            print(f"    [SA전략메모] 빈 결과 반환 — 캐시 미저장 (다음 실행 시 재시도)")
        return memo
    except Exception as e:
        print(f"    [SA전략메모] 생성 실패: {type(e).__name__}: {e}")
        return ""


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
    doc_context      = profile.get("doc_context", "")        # PDF/문서 추출 텍스트
    campaign_notes   = profile.get("campaign_notes", "")    # 사용자 캠페인 메모
    sa_strategy_memo = profile.get("sa_strategy_memo", "")  # 자동 생성 SA 전략 브리핑

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
            identity_stmt, not_this_brand, doc_context, campaign_notes, sa_strategy_memo
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
        cat_cfgs_raw         = data.get("category_configs", [])
        cleaned = _dedupe_keywords_by_category(keywords_by_category)
        if not cat_cfgs_raw:
            cat_cfgs_raw = _DEFAULT_CAT_CONFIGS_RAW[:]
        category_config = _enrich_cat_configs(cat_cfgs_raw)
        for cat in category_config:
            cleaned.setdefault(cat["name"], [])
        cleaned = _rule_based_brand_filter(cleaned, profile)
        selected_categories   = [c["name"] for c in category_config]
        category_descriptions = {c["name"]: c.get("description", "") for c in category_config}
        result = {
            "selected_categories":   selected_categories,
            "category_descriptions": category_descriptions,
            "category_config":       category_config,
            "keywords_by_category":  cleaned,
        }
        _save_ai_cache(cache_key, brand, result)
        return result

    # ── 일반 판매 비즈니스 프롬프트 ─────────────────────────────────────────
    doc_section      = f"\n━━━ 참고 문서 내용 (제품 카탈로그 / 마케팅 문서) ━━━\n{doc_context[:1500]}\n" if doc_context else ""
    notes_section    = f"\n━━━ 캠페인 특이사항 ━━━\n{campaign_notes}\n" if campaign_notes else ""
    strategy_section = f"\n━━━ SA 전략 인사이트 (자동 분석) ━━━\n{sa_strategy_memo}\n" if sa_strategy_memo else ""
    goal_section     = _build_goal_guidance(campaign_goal)

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
{notes_section}{strategy_section}{goal_section}{doc_section}

━━━ 핵심 원칙 ━━━
● "{products_str}을 구매하려는 한국 소비자가 네이버에서 실제로 검색할 검색어"만 생성한다
● {brand}의 다른 제품군은 이 캠페인과 무관 → 완전 제외
● 구매 의도 없는 검색어 (뉴스·주가·채용·SNS·학술·뜻·폐기 등) 완전 제외
● 제품명에 포함된 짧은 영문이 다른 영어 단어의 부분이 되는 키워드 제외
  (예: 제품명 "gram" → "grammar", "instagram" 등 완전히 다른 단어 제외)
● 브랜드명·제품명이 식품·음료·과자·생활용품·타 업종 브랜드와 동일하거나 유사한 경우,
  해당 타 업종 연상 키워드 완전 제외
  (예: 게임명 "이클립스" → "이클립스포도", "이클립스캔디", "이클립스껌" 등 식품류 제외)
● 브랜드명이 일반 명사·고유명사와 우연히 동일/유사한 경우, 그 일반 명사 본래 의미에서
  연상되는 키워드는 절대 생성하지 않는다
  (예: 브랜드 "성경" → 종교 서적 "성경(Bible)"과 무관 → "성경말씀", "성경공부", "성경구절",
   "종교", "통일교", "교회" 등 종교 연상 키워드 완전 금지. 브랜드 "미소"→"미소짓다" 등
   일반 감정·동사 표현 금지)
● 반드시 {category} 카테고리와 직접 연관된 검색 의도를 가진 키워드만 생성
● 개수는 목표치일 뿐 강제 할당량이 아니다 — 실제로 검색될 법한 키워드가 소진되면
  그 이하 개수로 멈춘다. 개수를 채우려고 단어를 억지로 이어붙이거나(예: "브랜드명+무관 단어",
  "브랜드명+숫자·용량 임의조합"), 실존 여부가 불확실한 초장꼬리 표현을 만들지 않는다.
  브랜드 규모가 작을수록(신생·니치 브랜드) 실제 검색 가능한 키워드 자체가 적으므로,
  목표 개수보다 적게 내더라도 품질을 우선한다.

━━━ 광고 그룹 설계 ━━━
이 광고주에 맞는 3~5개 광고 그룹을 직접 설계한다. 타입은 4종만 허용된다.

[brand 타입] 필수 1개 — {brand} 직접 검색 사용자, 10~20개 (품질 우선)
→ {brand} + {category}/추천/가격/후기/구매/할인/비교 (실제 검색되는 조합만)
→ {korean_str} + 동일 조합
→ 절대 금지: 브랜드명+무관 단어 임의 조합, 실존하지 않는 변형어, 브랜드명과 무관한
  단어(종교·인명·타업종 용어 등)를 붙인 조합
→ 제외: 주가·채용·공채·지역매장·{brand}의 다른 제품군

[product 타입] 권장 1~2개 — {products_str} 구매 직전 소비자, 각 20~40개(목표치, 상한 아님 —
  실제 검색될 법하다면 더 폭넓게 뽑아도 된다)
→ 브랜드 + 모델명/스펙/용도/특성 조합
→ 구체적 제품명·서비스명 중심 (한글·영문·혼용 표기 포함)
→ 제외: 이 캠페인 제품 외 {brand}의 다른 제품
→ 실제 검색량이 있을 법한 표현이 20개가 안 되면 그만큼만 생성한다 (억지로 채우지 않는다)

[general 타입] 권장 1개 — {category} 카테고리 탐색 잠재 구매자, 20~40개(목표치, 상한 아님 —
  실제 검색될 법하다면 더 폭넓게 뽑아도 된다)
→ {category} 단독, 추천, 가격, 비교, 순위, 후기
→ 용도/특성/스펙별 {category} 조합 (한글/영문 표기 쌍)

[competitor 타입] 선택 1개 — {competitors_str} 검색자 전환 유도, 10~25개(목표치, 상한 아님)
→ 각 경쟁사 + {category}/모델/가격/추천/비교/구매 (경쟁사당 최소 4개)
→ 경쟁사 목록이 짧으면 {category} 시장 주요 브랜드로 보완

그룹명은 한국어, 이 광고주 업종에 맞게 구체적으로 명명한다.
예: "{brand} 브랜드" / "{products_str} 제품" / "{category} 카테고리" / "경쟁사"
target_rank: brand=1, product=1~2, general=2~4, competitor=4~5

━━━ 출력 형식 (JSON만, 마크다운 없음) ━━━
{{
  "category_configs": [
    {{"name": "그룹명", "type": "brand|product|general|competitor", "target_rank": 1, "description": "한 문장"}}
  ],
  "keywords_by_category": {{
    "그룹명": ["키워드1", "키워드2"]
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

    cat_cfgs_raw         = data.get("category_configs", [])
    keywords_by_category = data.get("keywords_by_category", {})

    cleaned = _dedupe_keywords_by_category(keywords_by_category)
    if not cat_cfgs_raw:
        cat_cfgs_raw = _DEFAULT_CAT_CONFIGS_RAW[:]
    category_config = _enrich_cat_configs(cat_cfgs_raw)
    for cat in category_config:
        cleaned.setdefault(cat["name"], [])

    # 1차: 규칙 기반 필터 (SNS, 부정의도, forbidden_fragments)
    cleaned = _rule_based_brand_filter(cleaned, profile)
    # 2차: AI 검증 — 동음이의어·무관 카테고리 키워드 제거 (Haiku로 빠르게)
    cleaned = _verify_keywords_by_ai(cleaned, brand, category, brand_identity, products)

    selected_categories   = [c["name"] for c in category_config]
    category_descriptions = {c["name"]: c.get("description", "") for c in category_config}
    result = {
        "selected_categories":   selected_categories,
        "category_descriptions": category_descriptions,
        "category_config":       category_config,
        "keywords_by_category":  cleaned,
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