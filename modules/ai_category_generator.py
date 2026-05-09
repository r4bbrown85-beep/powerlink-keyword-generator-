import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_keyword_categories(profile):
    brand = profile.get("brand_name", "") or profile.get("brand", "")
    industry = profile.get("industry", "")
    products = profile.get("products", [])

    prompt = f"""
너는 네이버 파워링크 광고 전략가다.

아래 광고주에 적합한 키워드 카테고리를 선택하라.

광고주: {brand}
업종: {industry}
상품: {products}

[선택 가능한 카테고리]
- 브랜드
- 일반서비스
- 지역
- 가격비용
- 후기추천
- 예약문의
- 비교경쟁
- 상품유형
- 타겟별
- 시즌이슈

조건:
1. 반드시 위 목록 안에서만 선택
2. 광고주에 맞는 카테고리만 6~8개 선택
3. 결과는 JSON 배열만 출력

예시:
["브랜드", "일반서비스", "지역", "가격비용", "후기추천", "예약문의"]
"""

    response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[
            {"role": "system", "content": "너는 검색광고 카테고리 설계 전문가다."},
            {"role": "user", "content": prompt}
        ]
    )

    text = response.choices[0].message.content.strip()

    try:
        categories = json.loads(text)
        if isinstance(categories, list):
            return list(dict.fromkeys([str(c).strip() for c in categories if str(c).strip()]))
    except:
        pass

    # fallback
    return ["브랜드", "일반서비스", "지역", "가격비용", "후기추천", "예약문의", "비교경쟁"]