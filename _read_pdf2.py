# -*- coding: utf-8 -*-
import sys, pdfplumber
sys.stdout.reconfigure(encoding="utf-8")

pdf_path = "C:/Users/Administrator/Downloads/중고 분석장비 매입 확대를 위한 디지털 마케팅 제안_CQ.pdf"

with pdfplumber.open(pdf_path) as pdf:
    print(f"Pages: {len(pdf.pages)}")
    all_text = []
    for i, page in enumerate(pdf.pages):
        t = page.extract_text()
        words = page.extract_words()
        if words:
            print(f"\n=== Page {i+1} ({len(words)} words) ===")
            text_sample = " ".join(w["text"] for w in words[:50])
            print(text_sample)
            if t:
                all_text.append(t)
        else:
            print(f"Page {i+1}: no extractable text (image?)")

    if all_text:
        print("\n\n===== FULL TEXT =====")
        full = "\n".join(all_text)
        print(full[:8000])
