# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8")
import pdfplumber

pdf_path = r"C:\Users\Administrator\Downloads\중고 분석장비 매입 확대를 위한 디지털 마케팅 제안_CQ.pdf"
with pdfplumber.open(pdf_path) as pdf:
    print(f"총 페이지: {len(pdf.pages)}")
    for i, page in enumerate(pdf.pages[:15]):
        text = page.extract_text()
        if text and text.strip():
            print(f"\n=== PAGE {i+1} ===")
            print(text[:3000])
