# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import json, os, sys, io
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

try:
    for k, v in st.secrets.items():
        os.environ.setdefault(k, str(v))
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(
    page_title="PowerLink Planner",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── 기본 Streamlit UI 요소 완전 제거 ── */
#MainMenu,
footer,
.stDeployButton,
header[data-testid="stHeader"],
[data-testid="stSidebar"],
[data-testid="collapsedControl"],
[data-testid="stSidebarNav"]             { display: none !important; }

/* ── 레이아웃 ── */
.block-container {
    padding: 0 2.75rem 6rem !important;
    max-width: 1100px !important;
}

/* ─────────────────────────────────────────
   앱 바  (상단 다크 네이비 바)
───────────────────────────────────────── */
.pl-bar {
    background: #0F172A;
    margin: 0 -2.75rem 3rem -2.75rem;
    padding: 0 2.75rem;
    height: 58px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid #1E293B;
}
.pl-bar-l       { display: flex; align-items: center; gap: 10px; }
.pl-bar-icon    {
    width: 28px; height: 28px; border-radius: 7px;
    background: linear-gradient(135deg,#3B82F6,#1D4ED8);
    display: flex; align-items: center; justify-content: center;
    font-size: 13px; font-weight: 800; color:#fff;
}
.pl-bar-name    { font-size:15px; font-weight:700; color:#F1F5F9; letter-spacing:-.02em; }
.pl-bar-sep     { width:1px; height:16px; background:#334155; margin:0 6px; }
.pl-bar-sub     { font-size:12px; color:#64748B; }
.pl-bar-r       { display:flex; align-items:center; gap:8px; }
.pl-pill        { font-size:11px; font-weight:600; padding:3px 10px; border-radius:999px; letter-spacing:.03em; }
.pl-pill-ai     { background:#1E293B; color:#94A3B8; }
.pl-pill-beta   { background:rgba(59,130,246,.15); color:#60A5FA; }

/* ─────────────────────────────────────────
   섹션 헤더
───────────────────────────────────────── */
.pl-sec {
    display: flex; align-items: flex-start; gap: 14px;
    padding-bottom: 16px;
    border-bottom: 1px solid #E2E8F0;
    margin-bottom: 24px;
}
.pl-sec-num {
    width: 26px; height: 26px; border-radius: 50%;
    background: #1D4ED8; color: #fff;
    display: flex; align-items: center; justify-content: center;
    font-size: 12px; font-weight: 700; flex-shrink: 0; margin-top: 1px;
}
.pl-sec-title   { font-size:16px; font-weight:700; color:#0F172A; letter-spacing:-.02em; margin:0 0 3px; }
.pl-sec-desc    { font-size:13px; color:#94A3B8; margin:0; line-height:1.5; }

/* ─────────────────────────────────────────
   구분선
───────────────────────────────────────── */
hr { border:none !important; border-top:1px solid #E2E8F0 !important; margin:38px 0 !important; }

/* ─────────────────────────────────────────
   인풋 / 라벨
───────────────────────────────────────── */
label[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] {
    font-weight: 500 !important;
    font-size: 13px !important;
    color: #475569 !important;
    margin-bottom: 5px !important;
    letter-spacing: 0 !important;
}
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {
    border-radius: 8px !important;
    border: 1px solid #E2E8F0 !important;
    font-size: 14px !important;
    color: #0F172A !important;
    transition: border-color .15s, box-shadow .15s !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus {
    border-color: #1D4ED8 !important;
    box-shadow: 0 0 0 3px rgba(29,78,216,.10) !important;
}
[data-testid="stTextArea"] textarea {
    border-radius: 8px !important;
    border: 1px solid #E2E8F0 !important;
    font-size: 14px !important;
    color: #0F172A !important;
}

/* ─────────────────────────────────────────
   Expander (브랜드 폼)
───────────────────────────────────────── */
[data-testid="stExpander"] {
    border: 1px solid #E2E8F0 !important;
    border-radius: 12px !important;
    margin-bottom: 10px !important;
    overflow: hidden !important;
    box-shadow: 0 1px 3px rgba(15,23,42,.05) !important;
}
[data-testid="stExpander"] summary {
    font-weight: 600 !important;
    font-size: 14px !important;
    color: #0F172A !important;
    padding: 16px 20px !important;
    background: #fff !important;
}
[data-testid="stExpander"] summary:hover { background: #F8FAFC !important; }
[data-testid="stExpander"] > div > div   { padding: 0 20px 20px !important; }

/* ─────────────────────────────────────────
   버튼 – Primary
───────────────────────────────────────── */
div[data-testid="stButton"] > button[kind="primary"] {
    background: #1D4ED8 !important;
    color: #fff !important;
    border: none !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    border-radius: 8px !important;
    padding: .65rem 1.5rem !important;
    box-shadow: 0 1px 3px rgba(29,78,216,.28) !important;
    transition: all .15s ease !important;
    letter-spacing: 0 !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    background: #1E40AF !important;
    box-shadow: 0 4px 14px rgba(29,78,216,.32) !important;
    transform: translateY(-1px) !important;
}

/* ─────────────────────────────────────────
   버튼 – Secondary
───────────────────────────────────────── */
div[data-testid="stButton"] > button[kind="secondary"] {
    background: #fff !important;
    border: 1px solid #E2E8F0 !important;
    color: #475569 !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    border-radius: 8px !important;
    transition: all .15s ease !important;
}
div[data-testid="stButton"] > button[kind="secondary"]:hover {
    border-color: #CBD5E1 !important;
    background: #F8FAFC !important;
}

/* ─────────────────────────────────────────
   다운로드 버튼
───────────────────────────────────────── */
div[data-testid="stDownloadButton"] > button {
    background: #059669 !important;
    color: #fff !important;
    border: none !important;
    font-weight: 700 !important;
    font-size: 15px !important;
    border-radius: 8px !important;
    padding: .75rem 1.5rem !important;
    box-shadow: 0 1px 3px rgba(5,150,105,.28) !important;
    transition: all .15s ease !important;
}
div[data-testid="stDownloadButton"] > button:hover {
    background: #047857 !important;
    box-shadow: 0 4px 14px rgba(5,150,105,.32) !important;
    transform: translateY(-1px) !important;
}

/* ─────────────────────────────────────────
   탭
───────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    border-bottom: 1px solid #E2E8F0;
    background: transparent;
}
.stTabs [data-baseweb="tab"] {
    font-weight: 500 !important;
    font-size: 13.5px !important;
    color: #94A3B8 !important;
    padding: 10px 22px !important;
    border-radius: 0 !important;
    border: none !important;
}
.stTabs [aria-selected="true"] {
    color: #1D4ED8 !important;
    font-weight: 600 !important;
    border-bottom: 2px solid #1D4ED8 !important;
}

/* ─────────────────────────────────────────
   프로그레스바
───────────────────────────────────────── */
[data-testid="stProgressBar"] > div {
    background: #1D4ED8 !important;
    border-radius: 4px !important;
}

/* ─────────────────────────────────────────
   알림
───────────────────────────────────────── */
[data-testid="stAlert"] {
    border-radius: 8px !important;
    font-size: 13.5px !important;
}

/* ─────────────────────────────────────────
   정보 박스
───────────────────────────────────────── */
.pl-info {
    background: #EFF6FF;
    border: 1px solid #BFDBFE;
    border-radius: 10px;
    padding: 16px 22px;
    margin-bottom: 20px;
}
.pl-info-t { font-size:13px; font-weight:700; color:#1D4ED8; margin-bottom:6px; }
.pl-info-b { font-size:13px; color:#3B82F6; line-height:1.65; }

/* ─────────────────────────────────────────
   KPI 카드 그리드
───────────────────────────────────────── */
.pl-kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
    margin-bottom: 28px;
}
.pl-kpi-card {
    background: #fff;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 20px 22px;
    box-shadow: 0 1px 3px rgba(15,23,42,.05);
}
.pl-kpi-lbl {
    font-size: 11px;
    font-weight: 600;
    color: #94A3B8;
    text-transform: uppercase;
    letter-spacing: .07em;
    margin-bottom: 9px;
}
.pl-kpi-val {
    font-size: 24px;
    font-weight: 800;
    color: #0F172A;
    letter-spacing: -.04em;
    line-height: 1;
    margin-bottom: 4px;
}
.pl-kpi-sub { font-size:12px; color:#94A3B8; }
.pl-kpi-card.accent .pl-kpi-val { color:#1D4ED8; }

/* 브랜드별 KPI 요약 */
.pl-brand-kpi {
    background: #fff;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 22px 24px;
    margin-bottom: 12px;
    box-shadow: 0 1px 3px rgba(15,23,42,.05);
}
.pl-brand-kpi-head {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid #F1F5F9;
}
.pl-brand-kpi-name {
    font-size: 15px; font-weight: 700; color: #0F172A; letter-spacing: -.02em;
}
.pl-brand-kpi-cat {
    font-size: 11px; font-weight: 600; color: #94A3B8; text-transform: uppercase;
    background: #F8FAFC; border: 1px solid #E2E8F0;
    padding: 3px 10px; border-radius: 999px; letter-spacing: .06em;
}
.pl-brand-kpi-row {
    display: grid; grid-template-columns: repeat(4,1fr); gap: 0;
}
.pl-brand-kpi-cell { padding: 0 16px 0 0; }
.pl-brand-kpi-cell:first-child { padding-left: 0; }
.pl-brand-kpi-cell + .pl-brand-kpi-cell {
    border-left: 1px solid #F1F5F9; padding-left: 16px;
}
.pl-bkc-lbl { font-size:11px; color:#94A3B8; margin-bottom:5px; }
.pl-bkc-val { font-size:18px; font-weight:800; color:#0F172A; letter-spacing:-.03em; }
.pl-bkc-val.blue { color:#1D4ED8; }
.pl-bkc-sub { font-size:11px; color:#94A3B8; margin-top:2px; }

/* ─────────────────────────────────────────
   다운로드 박스
───────────────────────────────────────── */
.pl-dl-box {
    background: linear-gradient(135deg, #F0FDF4 0%, #ECFDF5 100%);
    border: 1px solid #A7F3D0;
    border-radius: 12px;
    padding: 22px 26px;
    margin-bottom: 16px;
    display: flex; align-items: center; justify-content: space-between;
}
.pl-dl-info {}
.pl-dl-t { font-size:15px; font-weight:700; color:#065F46; margin-bottom:4px; }
.pl-dl-s { font-size:13px; color:#059669; }
.pl-dl-icon { font-size:28px; opacity:.6; }

/* ─────────────────────────────────────────
   캡션
───────────────────────────────────────── */
small, .st-emotion-cache-s1r2mm { color:#94A3B8 !important; font-size:12px !important; }
</style>
""", unsafe_allow_html=True)

# ─── 앱 바 ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="pl-bar">
  <div class="pl-bar-l">
    <div class="pl-bar-icon">⚡</div>
    <span class="pl-bar-name">PowerLink Planner</span>
    <span class="pl-bar-sep"></span>
    <span class="pl-bar-sub">Naver Search Advertising · AI Keyword Intelligence</span>
  </div>
  <div class="pl-bar-r">
    <span class="pl-pill pl-pill-ai">Claude AI</span>
    <span class="pl-pill pl-pill-beta">BETA</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ─── 세션 초기화 ──────────────────────────────────────────────────────────────
for key, default in [
    ("brand_results", None), ("client_name", ""),
    ("excel_bytes", None),   ("filename", ""),
    ("brands", [{}]),        ("custom_add_kws", {}),
    ("custom_exc_kws", {}),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ─────────────────────────────────────────────────────────────────
# SECTION 1 · 광고주 기본 정보
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="pl-sec">
  <div class="pl-sec-num">1</div>
  <div>
    <div class="pl-sec-title">광고주 기본 정보</div>
    <div class="pl-sec-desc">캠페인 전체 예산과 목표를 설정합니다</div>
  </div>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2, gap="large")
with col1:
    client_name = st.text_input("광고주명 *", placeholder="예) LG전자")
    monthly_budget = st.number_input(
        "월 예산 (원) *",
        min_value=100_000, max_value=100_000_000,
        value=st.session_state.get("_prev_budget", 5_000_000),
        step=100_000, format="%d", key="global_budget"
    )
    if monthly_budget != st.session_state.get("_prev_budget"):
        st.session_state["_prev_budget"] = monthly_budget
        for idx in range(len(st.session_state.get("brands", []))):
            st.session_state[f"bgt_{idx}"] = monthly_budget
with col2:
    campaign_goals = st.multiselect(
        "캠페인 목표",
        ["구매전환", "브랜드인지도", "트래픽 유입", "신제품 출시",
         "앱 다운로드", "리타겟팅", "시즌 프로모션", "리드 수집"],
        default=["구매전환"]
    )
    new_product_info = ""
    season_info = ""
    if "신제품 출시" in campaign_goals:
        new_product_info = st.text_input("신제품 정보",
            placeholder="예) LG그램 Pro 2026, 초경량 AI 노트북, 2026년 5월 출시")
    if "시즌 프로모션" in campaign_goals:
        season_info = st.text_input("시즌/이슈 내용",
            placeholder="예) 여름 휴가 시즌, 블랙프라이데이 할인")

st.divider()

# ─────────────────────────────────────────────────────────────────
# SECTION 2 · 브랜드 정보
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="pl-sec">
  <div class="pl-sec-num">2</div>
  <div>
    <div class="pl-sec-title">브랜드 정보</div>
    <div class="pl-sec-desc">브랜드별로 독립된 제안서 시트가 생성됩니다. 여러 브랜드를 동시에 추가할 수 있습니다</div>
  </div>
</div>
""", unsafe_allow_html=True)

AWARENESS_MAP = {
    "신규 / 저인지도": "low",
    "중간 (집행 경험 있음)": "medium",
    "높음 (브랜드 인지도 있음)": "high",
}
AW_LABELS = list(AWARENESS_MAP.keys())
AW_VALS   = list(AWARENESS_MAP.values())

def brand_form(idx, data={}):
    label = data.get("brand_name") or "브랜드명 미입력"
    with st.expander(f"Brand {idx + 1}  ·  {label}", expanded=(idx == 0)):
        c1, c2 = st.columns(2, gap="large")
        with c1:
            brand_name  = st.text_input("브랜드명 *",
                value=data.get("brand_name", ""), key=f"bname_{idx}")
            category    = st.text_input("카테고리 *",
                value=data.get("category", ""), key=f"cat_{idx}",
                placeholder="예) 노트북, 헤어드라이기, 로봇청소기")
            products    = st.text_input("제품명 / 모델명 (쉼표 구분)",
                value=", ".join(data.get("products", [])), key=f"prod_{idx}",
                placeholder="예) 그램, 그램Pro, 그램16")
            competitors = st.text_input("주요 경쟁사 (쉼표 구분)",
                value=", ".join(data.get("competitors", [])), key=f"comp_{idx}",
                placeholder="예) 삼성, 레노버, 애플")
        with c2:
            brand_budget = st.number_input(
                "브랜드 월 예산 (원)",
                min_value=100_000, max_value=100_000_000,
                value=data.get("monthly_budget", monthly_budget),
                step=100_000, format="%d", key=f"bgt_{idx}",
                help="Step 1 총 예산이 자동 반영됩니다"
            )
            cur_aw  = data.get("brand_awareness", "low")
            aw_idx  = AW_VALS.index(cur_aw) if cur_aw in AW_VALS else 0
            aw_sel  = st.selectbox("브랜드 인지도", AW_LABELS, index=aw_idx, key=f"aw_{idx}")
            awareness = AWARENESS_MAP[aw_sel]
            brand_urls = st.text_area(
                "브랜드 / 상품 URL (한 줄에 하나씩)",
                value="\n".join(data.get("brand_urls", [])),
                key=f"url_{idx}",
                placeholder="https://brand.naver.com/example\nhttps://smartstore.naver.com/example",
                height=88,
                help="입력 시 해당 페이지에서 키워드 자동 추출"
            )
            url_list = [u.strip() for u in brand_urls.splitlines() if u.strip()]
            must_kws = st.text_input(
                "필수 포함 키워드 (쉼표 구분)",
                value=", ".join([
                    m.get("keyword","") if isinstance(m,dict) else str(m)
                    for m in data.get("must_keywords",[])
                ]),
                key=f"must_{idx}",
                placeholder="예) LG그램, LG노트북 추천"
            )
            must_list = [
                {"keyword": k.strip(), "target_rank": 3, "device": "BOTH"}
                for k in must_kws.split(",") if k.strip()
            ]

        # ── 캠페인 특이사항 ──────────────────────────────────────────────
        campaign_notes = st.text_area(
            "캠페인 특이사항 / AI 참고 메모",
            value=data.get("campaign_notes", ""),
            key=f"notes_{idx}",
            height=90,
            placeholder=(
                "예) 신학기(2~3월) 대학생 타깃 캠페인입니다. "
                "경쟁사 대비 초경량·긴 배터리가 강점이며, 학생 교육비 카드 할인 프로모션을 병행합니다. "
                "주력 노출 기기는 모바일이고 주요 타깃은 수도권 20대입니다."
            ),
            help="AI가 키워드 생성 시 이 내용을 참고합니다. 타깃 고객, 강점, 지역, 시즌 이슈 등 자유롭게 기입하세요.",
        )

        # ── 참고 문서 업로드 ─────────────────────────────────────────────
        uploaded_doc = st.file_uploader(
            "참고 문서 업로드 (PDF / TXT / MD)",
            type=["pdf", "txt", "md"],
            key=f"doc_{idx}",
            help="제품 카탈로그, 마케팅 제안서 등 — Claude가 문서 내용을 참고하여 키워드를 생성합니다",
        )
        doc_context = ""
        _cache_key = f"doc_result_{idx}"
        if uploaded_doc is not None:
            _sig = f"{uploaded_doc.name}_{uploaded_doc.size}"
            _cached = st.session_state.get(_cache_key, {})
            if _cached.get("sig") != _sig:
                from modules.pdf_extractor import extract_from_uploaded_bytes
                with st.spinner(f"문서 분석 중… {uploaded_doc.name}"):
                    _doc_res = extract_from_uploaded_bytes(
                        uploaded_doc.read(), uploaded_doc.name, category
                    )
                st.session_state[_cache_key] = {"sig": _sig, "result": _doc_res}
            else:
                _doc_res = _cached["result"]

            doc_context = _doc_res.get("raw_text", "")
            _ocr_tag = " · OCR" if _doc_res.get("ocr_used") else ""
            st.caption(
                f"문서 분석 완료{_ocr_tag}: "
                f"{_doc_res.get('page_count', 0)}페이지 · "
                f"키워드 {len(_doc_res.get('keywords', []))}개 추출"
            )
            if _doc_res.get("summary"):
                st.caption(f"요약: {_doc_res['summary'][:150]}")
        elif st.session_state.get(_cache_key):
            # 업로드 취소됐으면 캐시도 비움
            del st.session_state[_cache_key]

        return {
            "brand_name":             brand_name,
            "brand_key":              brand_name.replace(" ","_").lower() or f"brand_{idx}",
            "category":               category,
            "products":               [p.strip() for p in products.split(",") if p.strip()],
            "brand_variants":         [],
            "typo_variants":          [],
            "competitors":            [c.strip() for c in competitors.split(",") if c.strip()],
            "celebrities":            [],
            "must_keywords":          must_list,
            "product_lines":          [],
            "general_keyword_themes": [],
            "keyword_categories":     [],
            "exclude_keywords":       [],
            "monthly_budget":         brand_budget,
            "brand_awareness":        awareness,
            "competitor_budget_ratio": 0.1,
            "target_rank_general":    [3, 4, 5],
            "target_rank_brand":      [1, 2, 3],
            "brand_urls":             url_list,
            "doc_context":            doc_context,
            "campaign_notes":         campaign_notes,
        }

brand_configs = []
for i in range(len(st.session_state.brands)):
    bc = brand_form(i, st.session_state.brands[i])
    brand_configs.append(bc)

ca, cb = st.columns(2)
with ca:
    if st.button("+ 브랜드 추가", use_container_width=True):
        st.session_state.brands.append({"monthly_budget": monthly_budget})
        st.rerun()
with cb:
    if len(st.session_state.brands) > 1:
        if st.button("마지막 브랜드 삭제", use_container_width=True):
            st.session_state.brands.pop()
            st.rerun()

st.divider()

# ─────────────────────────────────────────────────────────────────
# SECTION 3 · 제안서 생성
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="pl-sec">
  <div class="pl-sec-num">3</div>
  <div>
    <div class="pl-sec-title">제안서 생성</div>
    <div class="pl-sec-desc">AI 키워드 생성 → 네이버 광고 데이터 조회 → 예산 최적화 순서로 자동 진행됩니다</div>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="pl-info">
  <div class="pl-info-t">시작 전 확인사항</div>
  <div class="pl-info-b">
    브랜드명과 카테고리는 필수 입력 항목입니다.<br>
    경쟁사를 입력할수록 경쟁사 키워드 품질이 높아집니다.<br>
    생성 중에는 페이지를 닫거나 새로고침하지 마세요 — 네이버 API 호출에 수 분 소요될 수 있습니다.
  </div>
</div>
""", unsafe_allow_html=True)

if st.button("⚡  제안서 생성 시작", type="primary", use_container_width=True):
    valid = True
    if not client_name.strip():
        st.error("광고주명을 입력해주세요.")
        valid = False
    for i, bc in enumerate(brand_configs):
        if not bc["brand_name"] or not bc["category"]:
            st.error(f"Brand {i+1}: 브랜드명과 카테고리는 필수입니다.")
            valid = False

    if valid:
        goal_str = ", ".join(campaign_goals)
        if new_product_info: goal_str += f" | 신제품: {new_product_info}"
        if season_info:       goal_str += f" | 시즌: {season_info}"

        client_profile = {
            "client":           client_name,
            "monthly_budget":   monthly_budget,
            "sales_channels":   [],
            "campaign_goal":    goal_str,
            "new_product_info": new_product_info,
            "season_info":      season_info,
            "brands":           brand_configs,
        }

        brand_results = []
        progress      = st.progress(0)
        status        = st.empty()
        total         = len(brand_configs)

        try:
            from main_multi import run_single_brand, make_brand_profile, save_multi_brand_excel
            from modules.url_extractor import extract_keywords_from_urls
            from modules.setup_profile import enrich_brand_config

            for i, brand_cfg in enumerate(brand_configs):
                bname = brand_cfg["brand_name"]

                url_result = {}
                if brand_cfg.get("brand_urls"):
                    status.info(f"[{i+1}/{total}] **{bname}** — URL 분석 중...")
                    try:
                        url_result = extract_keywords_from_urls(brand_cfg["brand_urls"])
                        for p in url_result.get("products", []):
                            if p not in brand_cfg.get("products", []):
                                brand_cfg.setdefault("products", []).append(p)
                    except Exception as e:
                        st.warning(f"URL 분석 실패: {e}")

                status.info(f"[{i+1}/{total}] **{bname}** — 브랜드 분석 중...")
                try:
                    brand_cfg = enrich_brand_config(brand_cfg,
                        url_keywords=url_result.get("keywords", []))
                except Exception as e:
                    st.warning(f"브랜드 분석 실패: {e}")

                if url_result.get("keywords"):
                    brand_cfg["general_keyword_themes"] = list(set(
                        brand_cfg.get("general_keyword_themes", [])
                        + url_result["keywords"][:15]
                    ))

                exc_kws = st.session_state.custom_exc_kws.get(bname, [])
                if exc_kws:
                    brand_cfg["exclude_keywords"] = list(set(
                        brand_cfg.get("exclude_keywords", []) + exc_kws))

                brand_profile = make_brand_profile(client_profile, brand_cfg)

                add_kws = st.session_state.custom_add_kws.get(bname, [])
                if add_kws:
                    brand_profile["must_keywords"] = brand_profile.get("must_keywords", []) + [
                        {"keyword": k, "target_rank": 3, "device": "BOTH"} for k in add_kws]

                status.info(f"[{i+1}/{total}] **{bname}** — AI 키워드 생성 및 성과 시뮬레이션 중...")
                result = run_single_brand(brand_profile, bname)
                brand_results.append(result)
                progress.progress((i + 1) / total)

            status.info("엑셀 파일 생성 중...")
            ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"output/{client_name}_proposal_{ts}.xlsx"
            os.makedirs("output", exist_ok=True)
            save_multi_brand_excel(brand_results, filename, client_name)

            with open(filename, "rb") as f:
                excel_bytes = f.read()

            st.session_state.brand_results = brand_results
            st.session_state.client_name   = client_name
            st.session_state.excel_bytes   = excel_bytes
            st.session_state.filename      = filename

            progress.progress(1.0)
            status.empty()

            n_kw = sum(
                len([r for r in res["recommended"] if not r.get("not_selected")])
                for res in brand_results
            )
            st.success(f"제안서 생성 완료 — {len(brand_results)}개 브랜드 · 추천 키워드 {n_kw}개")

        except Exception as e:
            st.error(f"오류: {e}")
            import traceback
            st.code(traceback.format_exc())

# ─────────────────────────────────────────────────────────────────
# SECTION 4 · 결과 확인
# ─────────────────────────────────────────────────────────────────
if st.session_state.brand_results:
    st.divider()
    brand_results = st.session_state.brand_results

    st.markdown("""
<div class="pl-sec">
  <div class="pl-sec-num">4</div>
  <div>
    <div class="pl-sec-title">결과 요약</div>
    <div class="pl-sec-desc">브랜드별 예상 성과 및 예산 배분을 확인합니다</div>
  </div>
</div>
""", unsafe_allow_html=True)

    # 전체 집계 KPI
    total_cost  = sum(res["total_cost"] for res in brand_results)
    total_kw    = sum(len([r for r in res["recommended"] if not r.get("not_selected")]) for res in brand_results)
    total_impr  = sum(
        sum((r.get("pc_sim_impressions") or 0) + (r.get("mo_sim_impressions") or 0)
            for r in res["recommended"] if not r.get("not_selected") and not r.get("is_fallback"))
        for res in brand_results
    )
    total_click = sum(
        sum((r.get("pc_sim_clicks") or 0) + (r.get("mo_sim_clicks") or 0)
            for r in res["recommended"] if not r.get("not_selected") and not r.get("is_fallback"))
        for res in brand_results
    )

    st.markdown(f"""
<div class="pl-kpi-grid">
  <div class="pl-kpi-card accent">
    <div class="pl-kpi-lbl">예상 월 비용</div>
    <div class="pl-kpi-val">{total_cost:,}</div>
    <div class="pl-kpi-sub">원 (네이버 파워링크)</div>
  </div>
  <div class="pl-kpi-card">
    <div class="pl-kpi-lbl">추천 키워드</div>
    <div class="pl-kpi-val">{total_kw}</div>
    <div class="pl-kpi-sub">개 · {len(brand_results)}개 브랜드</div>
  </div>
  <div class="pl-kpi-card">
    <div class="pl-kpi-lbl">예상 노출 (Estimate)</div>
    <div class="pl-kpi-val">{total_impr:,}</div>
    <div class="pl-kpi-sub">월 / PC+MO 합산</div>
  </div>
  <div class="pl-kpi-card">
    <div class="pl-kpi-lbl">예상 클릭 (Estimate)</div>
    <div class="pl-kpi-val">{total_click:,}</div>
    <div class="pl-kpi-sub">월 / PC+MO 합산</div>
  </div>
</div>
""", unsafe_allow_html=True)

    # 브랜드별 KPI 카드
    for res in brand_results:
        active  = [r for r in res["recommended"] if not r.get("not_selected")]
        standby = res.get("standby_rows", [])
        ratio   = res["total_cost"] / res["monthly_budget"] * 100 if res["monthly_budget"] else 0
        b_impr  = sum((r.get("pc_sim_impressions") or 0) + (r.get("mo_sim_impressions") or 0)
                      for r in active if not r.get("is_fallback"))
        b_click = sum((r.get("pc_sim_clicks") or 0) + (r.get("mo_sim_clicks") or 0)
                      for r in active if not r.get("is_fallback"))
        st.markdown(f"""
<div class="pl-brand-kpi">
  <div class="pl-brand-kpi-head">
    <span class="pl-brand-kpi-name">{res['brand_name']}</span>
    <span class="pl-brand-kpi-cat">{res['brand_category']}</span>
  </div>
  <div class="pl-brand-kpi-row">
    <div class="pl-brand-kpi-cell">
      <div class="pl-bkc-lbl">예상 월 비용</div>
      <div class="pl-bkc-val blue">{res['total_cost']:,}</div>
      <div class="pl-bkc-sub">예산 대비 {ratio:.0f}%</div>
    </div>
    <div class="pl-brand-kpi-cell">
      <div class="pl-bkc-lbl">추천 / 대기</div>
      <div class="pl-bkc-val">{len(active)}<span style="font-size:13px;font-weight:400;color:#94A3B8"> / {len(standby)}</span></div>
      <div class="pl-bkc-sub">키워드 수</div>
    </div>
    <div class="pl-brand-kpi-cell">
      <div class="pl-bkc-lbl">예상 노출</div>
      <div class="pl-bkc-val">{b_impr:,}</div>
      <div class="pl-bkc-sub">월 (Estimate)</div>
    </div>
    <div class="pl-brand-kpi-cell">
      <div class="pl-bkc-lbl">예상 클릭</div>
      <div class="pl-bkc-val">{b_click:,}</div>
      <div class="pl-bkc-sub">월 (Estimate)</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    st.divider()

    # 키워드 상세 탭
    st.markdown("""
<div class="pl-sec">
  <div class="pl-sec-num" style="background:#475569;">📋</div>
  <div>
    <div class="pl-sec-title">추천 키워드 상세</div>
    <div class="pl-sec-desc">포함 체크를 해제하면 해당 키워드가 제외됩니다. 키워드를 추가로 입력하고 재생성할 수 있습니다</div>
  </div>
</div>
""", unsafe_allow_html=True)

    tabs = st.tabs([r["brand_name"] for r in brand_results])

    for tab, res in zip(tabs, brand_results):
        with tab:
            bname    = res["brand_name"]
            active   = [r for r in res["recommended"] if not r.get("not_selected")]
            standby  = res.get("standby_rows", [])
            all_rows = active + standby
            exc_set  = set(st.session_state.custom_exc_kws.get(bname, []))

            rows = []
            for r in all_rows:
                kw = r.get("keyword", "")
                rows.append({
                    "포함":      kw not in exc_set,
                    "키워드":    kw,
                    "그룹":      r.get("category", ""),
                    "구분":      r.get("keyword_type_label", r.get("keyword_type", "")),
                    "PC 검색수": int(r.get("pc_impr", 0) or 0),
                    "MO 검색수": int(r.get("mo_impr", 0) or 0),
                    "경쟁도":    r.get("competition", "-"),
                    "예상비용":  int((r.get("pc_cost") or 0) + (r.get("mo_cost") or 0)),
                    "상태":      "대기" if r.get("not_selected") else "추천",
                })

            df = pd.DataFrame(rows)
            st.caption(f"총 {len(all_rows)}개 키워드 (추천 {len(active)}개 / 대기 {len(standby)}개)")
            edited = st.data_editor(
                df,
                column_config={
                    "포함":      st.column_config.CheckboxColumn("포함", width="small"),
                    "키워드":    st.column_config.TextColumn("키워드", width="medium"),
                    "그룹":      st.column_config.TextColumn("그룹", width="medium"),
                    "구분":      st.column_config.TextColumn("구분", width="small"),
                    "PC 검색수": st.column_config.NumberColumn("PC 검색수", format="%d"),
                    "MO 검색수": st.column_config.NumberColumn("MO 검색수", format="%d"),
                    "경쟁도":    st.column_config.TextColumn("경쟁도", width="small"),
                    "예상비용":  st.column_config.NumberColumn("예상비용", format="%d원"),
                    "상태":      st.column_config.TextColumn("상태", width="small"),
                },
                hide_index=True,
                use_container_width=True,
                key=f"tbl_{bname}"
            )

            excluded = edited[edited["포함"] == False]["키워드"].tolist()
            st.session_state.custom_exc_kws[bname] = excluded
            if excluded:
                st.caption(f"제외됨: {', '.join(excluded[:6])}{'...' if len(excluded)>6 else ''}")

            st.divider()
            st.markdown("**키워드 추가**")
            add_input = st.text_area(
                "추가할 키워드 (쉼표 또는 줄바꿈으로 구분)",
                key=f"add_{bname}",
                placeholder="예) LG그램 신제품\n학생 노트북 추천",
                height=76
            )
            add_kws = [k.strip() for k in add_input.replace(",","\n").splitlines() if k.strip()]
            if st.button(f"'{bname}' 커스텀 적용 후 재생성", key=f"regen_{bname}"):
                st.session_state.custom_add_kws[bname] = add_kws
                st.info("저장 완료. Section 3에서 '제안서 생성 시작'을 다시 클릭하세요.")

    st.divider()

    # SECTION 5 · 다운로드
    st.markdown("""
<div class="pl-sec">
  <div class="pl-sec-num">5</div>
  <div>
    <div class="pl-sec-title">제안서 다운로드</div>
    <div class="pl-sec-desc">네이버 파워링크 캠페인 제안서를 엑셀 파일로 저장합니다</div>
  </div>
</div>
""", unsafe_allow_html=True)

    today = datetime.now().strftime("%Y%m%d")
    st.markdown(f"""
<div class="pl-dl-box">
  <div class="pl-dl-info">
    <div class="pl-dl-t">제안서 준비 완료</div>
    <div class="pl-dl-s">{st.session_state.client_name} · {len(brand_results)}개 브랜드 · {total_kw}개 추천 키워드 · {today}</div>
  </div>
  <div class="pl-dl-icon">📊</div>
</div>
""", unsafe_allow_html=True)

    st.download_button(
        label="⬇  엑셀 제안서 다운로드",
        data=st.session_state.excel_bytes,
        file_name=f"{st.session_state.client_name}_proposal_{today}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
    st.caption("예상 성과(노출수·클릭수·비용)는 네이버 Estimate API 기반 시뮬레이션 수치입니다. 실제 운영 성과는 광고 품질지수·예산 집행 속도에 따라 달라질 수 있습니다.")
