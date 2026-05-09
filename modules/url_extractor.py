# -*- coding: utf-8 -*-
"""
url_extractor.py

네이버 브랜드스토어/스마트스토어 전용 크롤링 강화.
일반 URL도 지원.
"""
import re
import time
import requests
from bs4 import BeautifulSoup


DEFAULT_STOPWORDS = {
    "본문바로가기", "서브메뉴", "메뉴", "전체메뉴", "소개", "브랜드",
    "공지사항", "홍보", "고객센터", "회사소개", "이용약관", "개인정보",
    "처리방침", "오시는길", "채용", "제휴", "문의", "FAQ", "검색",
    "로그인", "회원가입", "사이트맵", "바로가기", "더보기", "닫기",
    "장바구니", "찜하기", "구매", "주문", "결제", "배송", "반품",
    "리뷰", "후기", "별점", "평점", "최저가", "할인", "쿠폰", "적립",
}

NAVER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
}


def _clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^0-9A-Za-z가-힣\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _tokenize(text: str, min_len=2, max_len=20):
    return [t for t in text.split() if min_len <= len(t) <= max_len]


def _is_naver_brand_store(url: str) -> bool:
    return "brand.naver.com" in url


def _is_naver_smart_store(url: str) -> bool:
    return "smartstore.naver.com" in url


def _extract_naver_brand_store(url: str) -> dict:
    """
    네이버 브랜드스토어 크롤링.
    brand.naver.com/{brand_id} 구조.
    상품 카테고리, 브랜드명, 제품명 추출.
    """
    result = {"brand_name": "", "products": [], "categories": [], "keywords": []}

    try:
        # 메인 페이지
        resp = requests.get(url, headers=NAVER_HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")

        # 브랜드명
        for sel in ["h1.brand-name", ".brand_name", "title", "h1"]:
            el = soup.select_one(sel)
            if el:
                result["brand_name"] = el.get_text(strip=True)
                break

        # 카테고리/제품 탭
        cats = soup.select(".category-item, .tab-item, .gnb-item, [class*='category']")
        for c in cats:
            t = c.get_text(strip=True)
            if t and 2 <= len(t) <= 15:
                result["categories"].append(t)

        # 상품명
        products = soup.select(
            ".product-name, .goods-name, [class*='product_name'], "
            "[class*='goods_name'], .item_name, [class*='itemname']"
        )
        for p in products[:30]:
            t = p.get_text(strip=True)
            if t and 2 <= len(t) <= 30:
                result["products"].append(t)

        # 전체 텍스트에서 키워드 추출
        raw = soup.get_text(" ", strip=True)
        text = _clean_text(raw)
        tokens = _tokenize(text)
        stopwords = DEFAULT_STOPWORDS

        freq = {}
        for t in tokens:
            if t not in stopwords and not re.fullmatch(r"\d+", t):
                freq[t] = freq.get(t, 0) + 1

        result["keywords"] = [w for w, _ in sorted(freq.items(), key=lambda x: -x[1])[:40]]

        # 상품 목록 페이지 추가 크롤링 시도
        time.sleep(0.5)
        all_url = url.rstrip("/") + "/all"
        try:
            resp2 = requests.get(all_url, headers=NAVER_HEADERS, timeout=10)
            soup2 = BeautifulSoup(resp2.text, "html.parser")
            for p in soup2.select("[class*='product_name'], [class*='goods_name'], .item_name")[:20]:
                t = p.get_text(strip=True)
                if t and 2 <= len(t) <= 30 and t not in result["products"]:
                    result["products"].append(t)
        except Exception:
            pass

    except Exception as e:
        print(f"    [URL추출] 브랜드스토어 크롤링 실패: {e}")

    return result


def _extract_naver_smart_store(url: str) -> dict:
    """네이버 스마트스토어 크롤링."""
    result = {"brand_name": "", "products": [], "categories": [], "keywords": []}
    try:
        resp = requests.get(url, headers=NAVER_HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")

        # 스토어명
        for sel in [".store_name", "h1", "title", "[class*='storeName']"]:
            el = soup.select_one(sel)
            if el:
                result["brand_name"] = el.get_text(strip=True)
                break

        # 상품명
        for p in soup.select("[class*='product'], [class*='goods'], [class*='item']")[:30]:
            t = p.get_text(strip=True)
            if 2 <= len(t) <= 30:
                result["products"].append(t)

        raw  = soup.get_text(" ", strip=True)
        text = _clean_text(raw)
        tokens = _tokenize(text)
        freq = {}
        for t in tokens:
            if t not in DEFAULT_STOPWORDS and not re.fullmatch(r"\d+", t):
                freq[t] = freq.get(t, 0) + 1
        result["keywords"] = [w for w, _ in sorted(freq.items(), key=lambda x: -x[1])[:40]]

    except Exception as e:
        print(f"    [URL추출] 스마트스토어 크롤링 실패: {e}")
    return result


def _extract_general(url: str) -> dict:
    """일반 URL 크롤링."""
    result = {"brand_name": "", "products": [], "categories": [], "keywords": []}
    try:
        resp = requests.get(url, headers=NAVER_HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")

        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()

        raw  = soup.get_text(" ", strip=True)
        text = _clean_text(raw)
        tokens = _tokenize(text)
        freq = {}
        for t in tokens:
            if t not in DEFAULT_STOPWORDS and not re.fullmatch(r"\d+", t):
                freq[t] = freq.get(t, 0) + 1
        result["keywords"] = [w for w, _ in sorted(freq.items(), key=lambda x: -x[1])[:40]]

    except Exception as e:
        print(f"    [URL추출] 일반 크롤링 실패: {e}")
    return result


def extract_from_url(url: str) -> dict:
    """
    URL 타입 자동 감지 후 적합한 크롤러 실행.
    반환: {brand_name, products, categories, keywords}
    """
    url = url.strip()
    if not url:
        return {}

    print(f"    [URL추출] {url}")

    if _is_naver_brand_store(url):
        return _extract_naver_brand_store(url)
    elif _is_naver_smart_store(url):
        return _extract_naver_smart_store(url)
    else:
        return _extract_general(url)


def extract_keywords_from_urls(urls: list) -> dict:
    """
    여러 URL에서 통합 추출.
    반환: {brand_name, products, keywords}
    """
    all_keywords = []
    all_products = []
    brand_name   = ""

    for url in urls:
        result = extract_from_url(url)
        if not brand_name and result.get("brand_name"):
            brand_name = result["brand_name"]
        all_keywords.extend(result.get("keywords", []))
        all_products.extend(result.get("products", []))
        time.sleep(0.3)

    # 중복 제거
    seen = set()
    unique_kws = []
    for k in all_keywords:
        if k not in seen:
            unique_kws.append(k)
            seen.add(k)

    seen2 = set()
    unique_prods = []
    for p in all_products:
        if p not in seen2:
            unique_prods.append(p)
            seen2.add(p)

    return {
        "brand_name": brand_name,
        "products":   unique_prods[:20],
        "keywords":   unique_kws[:50],
    }


# 기존 호환 함수
def extract_keywords_from_url(url: str, top_n: int = 40, extra_stopwords=None) -> list:
    result = extract_from_url(url)
    return result.get("keywords", [])[:top_n]


def build_phrases(tokens, max_phrases=40):
    out, seen = [], set()
    for i in range(min(len(tokens), 20)):
        for j in range(i + 1, min(len(tokens), 20)):
            phrase = f"{tokens[i]} {tokens[j]}"
            if phrase not in seen:
                out.append(phrase)
                seen.add(phrase)
            if len(out) >= max_phrases:
                return out
    return out