# -*- coding: utf-8 -*-
"""
setup_profile.py

브랜드 정체성 문서(Brand Identity Document) 생성.

핵심 설계 원칙:
- 브랜드 변형을 "생성"하지 않음 → 오염 방지
- 입력된 정보를 바탕으로 이 브랜드가 "무엇인지"를 명확히 정의
- 이 정의 문서가 키워드 생성/검증의 공통 컨텍스트로 사용됨
"""
import json
import os
import re

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _strip_fence(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z0-9_]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    return text.strip()


def build_brand_identity(brand_cfg: dict, url_keywords: list = None) -> dict:
    """
    브랜드 정체성 문서 생성.

    입력된 정보(브랜드명, 카테고리, 제품, 경쟁사)를 기반으로
    GPT가 이 브랜드가 "무엇인지" 명확하게 정의하는 문서를 만든다.

    반환:
    {
        "identity_statement": "이 브랜드가 무엇인지 1~2문장 정의",
        "category_context": "이 카테고리가 어떤 시장인지 설명",
        "what_this_brand_is_not": "이 브랜드와 혼동될 수 있는 무관한 것들",
        "korean_names": ["한글 표기 목록 - 입력된 것만"],
        "products": ["실제 제품 목록"],
        "competitors": ["실제 경쟁사 목록"],
        "keyword_themes": ["카테고리 내 핵심 검색 테마"],
    }
    """
    brand_name  = brand_cfg.get("brand_name", "")
    category    = brand_cfg.get("category", "")
    products    = brand_cfg.get("products", [])
    competitors = brand_cfg.get("competitors", [])
    brand_variants = brand_cfg.get("brand_variants", [])
    url_kw_str  = ", ".join((url_keywords or [])[:20]) or "없음"

    products_str    = ", ".join(products) if products else "정보 없음 (카테고리 기반으로 추정 필요)"
    competitors_str = ", ".join(competitors) if competitors else "정보 없음 (카테고리 기반으로 추정 필요)"
    variants_str    = ", ".join(brand_variants) if brand_variants else "없음 (생성 금지)"

    prompt = f"""너는 한국 네이버 검색광고 전문가다.
아래 브랜드 정보를 바탕으로 "브랜드 정체성 문서"를 작성하라.
이 문서는 키워드 생성 AI에게 브랜드가 무엇인지 정확히 알려주기 위한 컨텍스트다.

━━━ 입력된 브랜드 정보 ━━━
브랜드명: {brand_name}
카테고리: {category}
사용자가 입력한 제품/모델: {products_str}
사용자가 입력한 경쟁사: {competitors_str}
사용자가 입력한 브랜드 변형: {variants_str}
URL 추출 키워드: {url_kw_str}

━━━ 작성 지침 ━━━

[identity_statement]
- "{brand_name}은(는) {category} 브랜드로, ~를 판매합니다" 형식으로 1~2문장
- 브랜드명이 영문 약어라면 어떤 제품 카테고리 브랜드인지 명시
- 예) "ENB는 외장SSD, 외장하드를 판매하는 IT 스토리지 브랜드입니다"

[category_context]
- 이 카테고리({category})가 어떤 시장인지 1문장 설명
- 어떤 소비자가 어떤 목적으로 검색하는지 포함

[what_this_brand_is_not]
- 브랜드명과 혼동될 수 있는 무관한 것들을 명시
- 브랜드명이 영문 약어라면 같은 약어를 쓰는 다른 브랜드/용어 나열
- 예) ENB → "에너지회사 Enbridge(ENB), CJ ENM, 의학용어 ENBD 등과 무관"
- 이 항목이 키워드 생성 시 혼동을 막는 핵심 역할을 함

[korean_names]
- 사용자가 입력한 브랜드 변형({variants_str})만 포함
- 입력이 없으면 브랜드명의 자연스러운 한글 표기 1~2개만
- 절대로 다른 회사명/브랜드명 생성 금지
- 예) ENB → ["이엔비"] 만 생성. "이앤비쇼핑", "삼신이앤비" 절대 금지

[products]
- 입력된 제품 정보가 있으면 그대로 사용
- 없으면 {category} 카테고리에서 이 브랜드가 팔 법한 제품 추정 (최대 5개)

[competitors]
- 입력된 경쟁사가 있으면 그대로 사용
- 없으면 {category} 시장의 실제 경쟁 브랜드 추정 (최대 5개)
- 주가/채용/금융 관련 회사 절대 금지, 순수 제품 경쟁사만

[keyword_themes]
- {category} 카테고리에서 실제 검색 수요가 있는 테마 4~6개
- 용량별/용도별/특성별/가격대별 등 구체적으로
- 반드시 {category} 카테고리 내 테마만

반드시 JSON만 출력. 마크다운 없음.

{{
  "identity_statement": "브랜드 정의 1~2문장",
  "category_context": "카테고리 시장 설명 1문장",
  "what_this_brand_is_not": "혼동 방지 항목들",
  "korean_names": ["한글표기1"],
  "products": ["제품1", "제품2"],
  "competitors": ["경쟁사1", "경쟁사2"],
  "keyword_themes": ["테마1", "테마2", "테마3", "테마4"]
}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "너는 한국 네이버 검색광고 전문가다. "
                        "브랜드 정체성 문서를 정확하게 작성한다. "
                        "절대로 입력되지 않은 브랜드명/회사명을 생성하지 않는다. "
                        "반드시 JSON만 출력한다."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # 낮은 temperature로 일관성 확보
        )
        content = _strip_fence(response.choices[0].message.content)
        result  = json.loads(content)
        print(f"    [브랜드정의] {brand_name}: {result.get('identity_statement', '')}")
        return result

    except Exception as e:
        print(f"    [브랜드정의] 실패 ({e}), 기본값 사용")
        return {
            "identity_statement": f"{brand_name}은(는) {category} 브랜드입니다.",
            "category_context":   f"{category} 카테고리 제품을 검색하는 소비자를 대상으로 합니다.",
            "what_this_brand_is_not": "정보 없음",
            "korean_names":    brand_variants or [],
            "products":        products or [category],
            "competitors":     competitors or [],
            "keyword_themes":  [f"{category} 추천", f"{category} 가격", f"{category} 비교", f"{category} 후기"],
        }


def enrich_brand_config(brand_cfg: dict, url_keywords: list = None) -> dict:
    """
    brand_cfg에 브랜드 정체성 문서를 추가해서 반환.
    기존 입력값은 그대로 유지하고, identity 문서만 추가.
    """
    brand_name = brand_cfg.get("brand_name", "")
    category   = brand_cfg.get("category", "")

    if not brand_name or not category:
        return brand_cfg

    print(f"    [브랜드정의] '{brand_name}' 브랜드 정체성 분석 중...")

    identity = build_brand_identity(brand_cfg, url_keywords)

    enriched = dict(brand_cfg)

    # 브랜드 정체성 문서 추가 (키워드 생성 컨텍스트로 사용)
    enriched["brand_identity"] = identity

    # 제품/경쟁사/테마: 입력된 게 없을 때만 보강
    if not enriched.get("products") or enriched["products"] == [brand_name]:
        enriched["products"] = identity.get("products", [])

    if not enriched.get("competitors"):
        enriched["competitors"] = identity.get("competitors", [])

    if not enriched.get("general_keyword_themes"):
        enriched["general_keyword_themes"] = identity.get("keyword_themes", [])

    # 한글 표기: 입력된 게 없을 때만, identity에서 가져옴
    if not enriched.get("brand_variants"):
        enriched["brand_variants"] = identity.get("korean_names", [])

    return enriched