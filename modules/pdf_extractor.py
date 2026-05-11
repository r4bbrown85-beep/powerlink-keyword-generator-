# -*- coding: utf-8 -*-
"""
pdf_extractor.py

PDF / 문서 파일에서 텍스트를 추출하고 키워드 시드를 반환한다.

지원 형식:
  - PDF (텍스트 레이어 있음) → pdfplumber 직접 추출
  - PDF (이미지 스캔본)     → fitz로 페이지 이미지화 → Claude Vision OCR
  - .txt / .md             → 직접 읽기

반환:
  {
    "raw_text": str,           # 추출된 전체 텍스트
    "keywords": list[str],     # 키워드 시드 (중복 제거, 최대 80개)
    "products": list[str],     # 제품/장비명 추출
    "summary":  str,           # 문서 요약 (200자 이내)
    "page_count": int,
  }
"""
import base64
import io
import os
import re
from pathlib import Path

import fitz                    # pymupdf
import pdfplumber

from dotenv import load_dotenv
load_dotenv()


_STOP_KO = {
    "위해", "통해", "대한", "위한", "있는", "하는", "등의", "또한",
    "현재", "모든", "경우", "이후", "있음", "없음", "이상", "이하",
    "기반", "방식", "수준", "관련", "제공", "운영", "관리", "지원",
    "서비스", "시스템", "솔루션", "플랫폼", "전문", "최적", "활용",
}


def _clean(text: str) -> str:
    text = re.sub(r"[^가-힣a-zA-Z0-9\s\-\/\(\)]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _extract_keywords_from_text(text: str, max_kw: int = 80) -> list:
    """텍스트에서 2~12자 한국어/영문 단어 빈도 기반 키워드 추출."""
    tokens = re.findall(r"[가-힣]{2,12}|[A-Za-z]{2,15}(?:[-/][A-Za-z]{2,10})*", text)
    freq: dict = {}
    for t in tokens:
        if t.upper() not in _STOP_KO and t.lower() not in _STOP_KO:
            freq[t] = freq.get(t, 0) + 1
    sorted_kws = sorted(freq.items(), key=lambda x: -x[1])
    return [k for k, _ in sorted_kws if freq[k] >= 2][:max_kw]


def _page_to_png_bytes(page: fitz.Page, dpi: int = 150) -> bytes:
    """fitz Page → PNG bytes."""
    mat  = fitz.Matrix(dpi / 72, dpi / 72)
    pix  = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
    return pix.tobytes("png")


def _ocr_pages_with_claude(pages_png: list[bytes]) -> str:
    """Claude Vision으로 이미지 PDF 페이지 OCR."""
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        return ""

    import anthropic
    client = anthropic.Anthropic(api_key=anthropic_key)

    all_text = []
    # 최대 8페이지 OCR (비용 및 속도 최적화)
    for i, png in enumerate(pages_png[:8]):
        b64 = base64.standard_b64encode(png).decode()
        try:
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2048,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "이 문서 이미지의 텍스트를 그대로 추출해줘. "
                                "표, 리스트, 제목, 본문 모두 포함. "
                                "불필요한 설명 없이 텍스트만 출력."
                            ),
                        },
                    ],
                }],
            )
            page_text = msg.content[0].text
            all_text.append(f"[Page {i+1}]\n{page_text}")
            print(f"    [PDF OCR] Page {i+1} 완료 ({len(page_text)}자)")
        except Exception as e:
            print(f"    [PDF OCR] Page {i+1} 실패: {e}")

    return "\n\n".join(all_text)


def _summarize_with_claude(text: str, category: str = "") -> str:
    """추출된 텍스트에서 핵심 요약 생성."""
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key or not text.strip():
        return ""
    import anthropic
    client = anthropic.Anthropic(api_key=anthropic_key)
    try:
        context = f"(카테고리: {category})" if category else ""
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            messages=[{
                "role": "user",
                "content": (
                    f"아래 문서{context}에서 "
                    "① 사업 유형 ② 주요 취급 제품/장비 ③ 타깃 고객 ④ 핵심 키워드 10개를 "
                    "JSON으로 추출해줘.\n\n"
                    f"문서:\n{text[:4000]}\n\n"
                    '{"business_type":"","products":[],"target_customers":"","keywords":[]}'
                ),
            }],
        )
        raw = msg.content[0].text
        # JSON 파싱 시도
        import json, re as _re
        m = _re.search(r'\{.*\}', raw, _re.DOTALL)
        if m:
            d = json.loads(m.group())
            parts = [
                d.get("business_type", ""),
                "제품: " + ", ".join(d.get("products", [])[:8]),
                "타깃: " + d.get("target_customers", ""),
            ]
            return " | ".join(p for p in parts if p.strip(" |"))
        return raw[:200]
    except Exception:
        return text[:200]


def _extract_product_names(text: str) -> list:
    """기기/장비명 패턴 추출."""
    patterns = [
        r'\b[A-Z]{2,6}[-\s]?\d{3,6}[A-Z]?\b',           # HPLC-1260, UV2600
        r'\b[A-Z][a-z]+[-\s][A-Z]{2,}\b',                  # Agilent HPLC
        r'[가-힣]{2,6}\s?(?:분석기|측정기|장비|기기|시스템|크로마토그래프|스펙트로)',
        r'\b(?:HPLC|GC|LC|MS|NMR|UV|IR|XRD|PCR|ELISA|SDS|PAGE|GPC|SEC|ICP|AAS|FT-IR|FTIR)\b',
    ]
    found = []
    for pat in patterns:
        found.extend(re.findall(pat, text))
    return list(dict.fromkeys(found))[:20]


# ── 공개 API ──────────────────────────────────────────────────────────────────

def extract_from_pdf(file_path: str, category: str = "") -> dict:
    """
    PDF 파일에서 텍스트/키워드를 추출한다.

    1단계: pdfplumber로 텍스트 추출 시도
    2단계: 텍스트가 없으면 fitz로 페이지 이미지화 → Claude Vision OCR
    """
    path = Path(file_path)
    result = {
        "raw_text": "",
        "keywords": [],
        "products": [],
        "summary":  "",
        "page_count": 0,
        "ocr_used": False,
    }

    if not path.exists():
        print(f"    [PDF] 파일 없음: {file_path}")
        return result

    # 1단계: pdfplumber 텍스트 추출
    try:
        with pdfplumber.open(file_path) as pdf:
            result["page_count"] = len(pdf.pages)
            texts = []
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    texts.append(t)
            raw = "\n\n".join(texts)
    except Exception as e:
        print(f"    [PDF] pdfplumber 실패: {e}")
        raw = ""

    # 2단계: 텍스트가 너무 적으면 OCR
    MIN_CHARS = 200
    if len(raw.strip()) < MIN_CHARS:
        print(f"    [PDF] 텍스트 레이어 부족 ({len(raw.strip())}자) → Claude Vision OCR 시도")
        result["ocr_used"] = True
        try:
            doc = fitz.open(file_path)
            pages_png = [_page_to_png_bytes(doc[i]) for i in range(min(len(doc), 10))]
            raw = _ocr_pages_with_claude(pages_png)
        except Exception as e:
            print(f"    [PDF] OCR 실패: {e}")
            raw = ""

    result["raw_text"] = raw
    if raw:
        cleaned = _clean(raw)
        result["keywords"] = _extract_keywords_from_text(cleaned)
        result["products"] = _extract_product_names(raw)
        result["summary"]  = _summarize_with_claude(raw, category)
        print(f"    [PDF] 추출 완료: {len(result['keywords'])}개 키워드, {len(result['products'])}개 제품명")
    else:
        print("    [PDF] 텍스트 추출 실패")

    return result


def extract_from_text_file(file_path: str) -> dict:
    """TXT / MD 파일에서 키워드 추출."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            raw = f.read()
    except Exception as e:
        return {"raw_text": "", "keywords": [], "products": [], "summary": "", "page_count": 1}

    cleaned = _clean(raw)
    return {
        "raw_text": raw,
        "keywords": _extract_keywords_from_text(cleaned),
        "products": _extract_product_names(raw),
        "summary":  raw[:200],
        "page_count": 1,
    }


def extract_from_uploaded_bytes(file_bytes: bytes, filename: str, category: str = "") -> dict:
    """
    Streamlit st.file_uploader에서 받은 bytes를 처리.
    임시 파일에 저장 후 extract_from_pdf / text_file 호출.
    """
    import tempfile
    suffix = Path(filename).suffix.lower()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        if suffix == ".pdf":
            return extract_from_pdf(tmp_path, category)
        elif suffix in (".txt", ".md"):
            return extract_from_text_file(tmp_path)
        else:
            return {"raw_text": "", "keywords": [], "products": [], "summary": "", "page_count": 0}
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
