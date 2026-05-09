import re
import requests


def normalize_text(text):
    text = text.lower()
    text = re.sub(r"[^a-zA-Z0-9가-힣 ]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_words(text):
    words = text.split()
    return [w for w in words if len(w) >= 2]


def crawl_page_text(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        r = requests.get(url, headers=headers, timeout=10)

        if r.status_code != 200:
            return ""

        html = r.text

        # HTML 태그 제거
        text = re.sub(r"<[^>]*>", " ", html)

        return normalize_text(text)

    except Exception:
        return ""


def extract_product_candidates(text, brand_name):
    words = extract_words(text)
    candidates = set()

    for w in words:
        if brand_name and brand_name.lower().replace(" ", "") in w.replace(" ", ""):
            continue

        if len(w) >= 4:
            candidates.add(w)

    return list(candidates)


def build_brand_variants(brand_name):
    variants = set()

    if not brand_name:
        return []

    variants.add(brand_name)
    variants.add(brand_name.replace(" ", ""))

    # 띄어쓰기 버전 자동 생성
    compact = brand_name.replace(" ", "")
    if " " not in brand_name and len(compact) >= 4:
        for i in range(2, len(compact) - 1):
            variants.add(compact[:i] + " " + compact[i:])

    # 영문 브랜드 예외 대응
    variants.add(brand_name.lower())
    variants.add(brand_name.upper())

    return list(variants)


def enrich_brand_profile(profile):
    brand = profile.get("brand_name", "")
    urls = profile.get("brand_urls", []) or []

    full_text = ""

    for u in urls:
        page = crawl_page_text(u)
        full_text += " " + page

    crawled_products = extract_product_candidates(full_text, brand)
    existing_products = profile.get("products", []) or []

    merged_products = []
    seen = set()

    for p in existing_products + crawled_products:
        p = str(p).strip()
        if not p:
            continue
        if p not in seen:
            merged_products.append(p)
            seen.add(p)

    variants = build_brand_variants(brand)

    return {
        "brand_variants": variants,
        "products": merged_products[:50]
    }