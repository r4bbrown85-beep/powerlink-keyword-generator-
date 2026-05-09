import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def classify_keywords(keywords, categories):

    prompt = f"""
다음 키워드를 아래 카테고리 중 하나로 분류하라.

카테고리:
{", ".join(categories)}

키워드:
{", ".join(keywords)}

출력 형식
키워드 | 카테고리
"""

    response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[
            {"role":"system","content":"검색광고 키워드 분석가"},
            {"role":"user","content":prompt}
        ]
    )

    text = response.choices[0].message.content

    result = []

    for line in text.split("\n"):
        if "|" in line:
            k,c = line.split("|")
            result.append((k.strip(),c.strip()))

    return result