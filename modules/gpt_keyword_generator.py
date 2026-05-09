import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_gpt_keywords(profile, categories):

    brand = profile.get("brand_name", "")
    industry = profile.get("industry", "")
    products = profile.get("products", [])
    competitors = profile.get("competitors", [])

    prompt = f"""
너는 네이버 검색광고 키워드 전략 전문가다.

광고주 정보

브랜드: {brand}
업종: {industry}
상품: {products}
경쟁사: {competitors}

다음 카테고리별로 광고 키워드를 생성하라

{categories}

조건

1 광고 클릭 가능성이 높은 키워드
2 실제 검색할 법한 키워드
3 정보성 키워드 금지
4 각 카테고리 최소 20개

JSON 형식만 출력

예시

{{
"브랜드 키워드": ["브랜드명 가격"],
"일반 키워드": ["골프레슨 추천"]
}}
"""

    response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[
            {"role": "system", "content": "너는 네이버 광고 키워드 전문가다"},
            {"role": "user", "content": prompt}
        ]
    )

    text = response.choices[0].message.content.strip()

    try:

        data = json.loads(text)

        clean = {}

        for c, kws in data.items():

            clean[c] = list(dict.fromkeys([k.strip() for k in kws]))

        return clean

    except:

        return {c: [] for c in categories}