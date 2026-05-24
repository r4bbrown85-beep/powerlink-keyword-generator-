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


def _split_keywords(text: str) -> list[str]:
    """쉼표·줄바꿈·탭 중 어떤 구분자로 붙여넣어도 키워드 리스트로 변환."""
    import re
    return [k.strip() for k in re.split(r'[,\n\t]+', text or "") if k.strip()]

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

# ─── 현재 페이지 결정 ─────────────────────────────────────────────────────────
_page = st.query_params.get("page", "main")

# ─── 페이지 네비게이션 ─────────────────────────────────────────────────────────
if _page == "simulator":
    st.markdown("""
<div style="display:flex;gap:8px;margin-bottom:16px;">
  <a href="?page=main" target="_self" style="
    flex:1;display:flex;align-items:center;justify-content:center;gap:6px;
    padding:10px 0;border-radius:8px;font-size:14px;font-weight:600;text-decoration:none;
    background:#F1F5F9;color:#475569;border:1px solid #E2E8F0;">
    🤖&nbsp; AI 키워드 제안서
  </a>
  <a href="?page=simulator" target="_self" style="
    flex:1;display:flex;align-items:center;justify-content:center;gap:6px;
    padding:10px 0;border-radius:8px;font-size:14px;font-weight:700;text-decoration:none;
    background:#1D4ED8;color:#fff;border:none;">
    📊&nbsp; 예산 시뮬레이터
  </a>
</div>
""", unsafe_allow_html=True)
else:
    st.markdown("""
<div style="display:flex;gap:8px;margin-bottom:16px;">
  <a href="?page=main" target="_self" style="
    flex:1;display:flex;align-items:center;justify-content:center;gap:6px;
    padding:10px 0;border-radius:8px;font-size:14px;font-weight:700;text-decoration:none;
    background:#1D4ED8;color:#fff;border:none;">
    🤖&nbsp; AI 키워드 제안서
  </a>
  <a href="?page=simulator" target="_self" style="
    flex:1;display:flex;align-items:center;justify-content:center;gap:6px;
    padding:10px 0;border-radius:8px;font-size:14px;font-weight:600;text-decoration:none;
    background:#F1F5F9;color:#475569;border:1px solid #E2E8F0;">
    📊&nbsp; 예산 시뮬레이터
  </a>
</div>
""", unsafe_allow_html=True)
st.divider()

# ─── 세션 초기화 ──────────────────────────────────────────────────────────────
for key, default in [
    ("brand_results", None), ("client_name", ""),
    ("excel_bytes", None),   ("filename", ""),
    ("brands", [{}]),        ("custom_add_kws", {}),
    ("custom_exc_kws", {}),  ("custom_rank_kws", {}),
    ("sim_result", None),    ("sim_excel_bytes", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ─────────────────────────────────────────────────────────────────
# 예산 시뮬레이터 페이지
# ─────────────────────────────────────────────────────────────────
if _page == "simulator":
    st.markdown("""
<div class="pl-sec">
  <div class="pl-sec-num">1</div>
  <div>
    <div class="pl-sec-title">기본 정보 입력</div>
    <div class="pl-sec-desc">확정된 키워드 리스트와 월 예산을 입력합니다</div>
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div class="pl-info">
  <div class="pl-info-t">사용 방법</div>
  <div class="pl-info-b">
    이미 확정된 키워드가 있는 경우 사용합니다.<br>
    엑셀에서 키워드 열을 복사해 아래에 붙여넣으면 됩니다 (줄바꿈·쉼표·탭 모두 인식).<br>
    AI 키워드 생성 없이 네이버 API 데이터 조회 + 예산 최적화만 실행합니다.
  </div>
</div>
""", unsafe_allow_html=True)

    with st.form("budget_sim_form", clear_on_submit=False):
        fc1, fc2 = st.columns([1, 1], gap="large")
        with fc1:
            f_client = st.text_input("광고주명 *", placeholder="예) LG전자")
            f_budget = st.number_input(
                "월 예산 (원) *",
                min_value=100_000, max_value=100_000_000,
                value=5_000_000, step=100_000,
            )
        with fc2:
            f_kw_raw = st.text_area(
                "키워드 리스트 * (엑셀 열 복붙 가능)",
                height=200,
                placeholder=(
                    "예)\nLG그램\nLG 노트북 추천\n그램 가격\n노트북 추천\n"
                    "삼성 노트북 비교\n...\n\n"
                    "줄바꿈·쉼표·탭 모두 가능"
                ),
            )

        _has_result = st.session_state.sim_result is not None
        _btn_label  = "🔄  재실행" if _has_result else "📊  시뮬레이션 시작"
        _btn_type   = "secondary" if _has_result else "primary"
        submitted   = st.form_submit_button(_btn_label, type=_btn_type, use_container_width=True)

    st.divider()

    if submitted:
        f_keywords = _split_keywords(f_kw_raw)
        st.caption(f"인식된 키워드: {len(f_keywords)}개")

        if not f_client.strip():
            st.error("광고주명을 입력해주세요.")
        elif not f_keywords:
            st.error("키워드를 1개 이상 입력해주세요.")
        else:
            with st.spinner(f"'{f_client}' 시뮬레이션 실행 중... ({len(f_keywords)}개 키워드)"):
                try:
                    from main_multi import run_budget_simulation, save_multi_brand_excel
                    result = run_budget_simulation(f_keywords, int(f_budget), f_client)

                    if result is None:
                        st.error("유효한 키워드가 없습니다. 키워드를 확인해주세요.")
                    else:
                        excel_bytes = save_multi_brand_excel(
                            [result], None, f_client, return_bytes=True
                        )
                        st.session_state.sim_result      = result
                        st.session_state.sim_excel_bytes = excel_bytes

                        n_active = len([r for r in result["recommended"] if not r.get("not_selected")])
                        st.success(
                            f"시뮬레이션 완료 — 추천 키워드 {n_active}개 / "
                            f"예상 비용 {result['total_cost']:,}원"
                        )

                except Exception as _sim_err:
                    import traceback
                    st.error(f"시뮬레이션 오류: {_sim_err}")
                    with st.expander("오류 상세 (개발자용)"):
                        st.code(traceback.format_exc())

    if st.session_state.sim_result:
        try:
            res = st.session_state.sim_result

            st.markdown("""
<div class="pl-sec">
  <div class="pl-sec-num">3</div>
  <div>
    <div class="pl-sec-title">결과 요약</div>
    <div class="pl-sec-desc">예산 내 최적 운영 시나리오 기준 예상 성과입니다</div>
  </div>
</div>
""", unsafe_allow_html=True)

            active  = [r for r in res["recommended"] if not r.get("not_selected")]
            standby = res.get("standby_rows", [])
            total_impr = sum(
                (r.get("pc_sim_impressions") or 0) + (r.get("mo_sim_impressions") or 0)
                for r in active if not r.get("is_fallback")
            )
            total_click = sum(
                (r.get("pc_sim_clicks") or 0) + (r.get("mo_sim_clicks") or 0)
                for r in active if not r.get("is_fallback")
            )
            budget_ratio = (
                res["total_cost"] / res["monthly_budget"] * 100
                if res.get("monthly_budget") else 0
            )

            st.markdown(f"""
<div class="pl-kpi-grid">
  <div class="pl-kpi-card accent">
    <div class="pl-kpi-lbl">예상 월 비용</div>
    <div class="pl-kpi-val">{res['total_cost']:,}</div>
    <div class="pl-kpi-sub">원 · 예산 대비 {budget_ratio:.0f}%</div>
  </div>
  <div class="pl-kpi-card">
    <div class="pl-kpi-lbl">운영 키워드</div>
    <div class="pl-kpi-val">{len(active)}</div>
    <div class="pl-kpi-sub">개 (대기 {len(standby)}개)</div>
  </div>
  <div class="pl-kpi-card">
    <div class="pl-kpi-lbl">예상 노출</div>
    <div class="pl-kpi-val">{total_impr:,}</div>
    <div class="pl-kpi-sub">월 / PC+MO 합산</div>
  </div>
  <div class="pl-kpi-card">
    <div class="pl-kpi-lbl">예상 클릭</div>
    <div class="pl-kpi-val">{total_click:,}</div>
    <div class="pl-kpi-sub">월 / PC+MO 합산</div>
  </div>
</div>
""", unsafe_allow_html=True)

            rows_disp = []
            for r in active:
                pc_bid = int(r.get("proposed_bid_pc") or 0)
                mo_bid = int(r.get("proposed_bid_mo") or 0)
                impr   = int((r.get("pc_sim_impressions") or 0) + (r.get("mo_sim_impressions") or 0))
                clk    = int((r.get("pc_sim_clicks") or 0) + (r.get("mo_sim_clicks") or 0))
                cost   = int((r.get("pc_sim_cost") or 0) + (r.get("mo_sim_cost") or 0))
                rows_disp.append({
                    "키워드":    r.get("keyword", ""),
                    "PC 순위":   str(r.get("proposed_rank_pc", "-")),
                    "MO 순위":   str(r.get("proposed_rank_mo", "-")),
                    "PC 입찰가": f"{pc_bid:,}원",
                    "MO 입찰가": f"{mo_bid:,}원",
                    "예상 노출": f"{impr:,}",
                    "예상 클릭": f"{clk:,}",
                    "예상 비용": f"{cost:,}원",
                })
            if rows_disp:
                st.dataframe(
                    pd.DataFrame(rows_disp),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "키워드":    st.column_config.TextColumn("키워드", width="medium"),
                        "PC 순위":   st.column_config.TextColumn("PC 순위", width="small"),
                        "MO 순위":   st.column_config.TextColumn("MO 순위", width="small"),
                        "PC 입찰가": st.column_config.TextColumn("PC 입찰가"),
                        "MO 입찰가": st.column_config.TextColumn("MO 입찰가"),
                        "예상 노출": st.column_config.TextColumn("예상 노출"),
                        "예상 클릭": st.column_config.TextColumn("예상 클릭"),
                        "예상 비용": st.column_config.TextColumn("예상 비용"),
                    },
                )

            st.divider()

            st.markdown("""
<div class="pl-sec">
  <div class="pl-sec-num">4</div>
  <div>
    <div class="pl-sec-title">제안서 다운로드</div>
    <div class="pl-sec-desc">현재 예산 제안 + 50% 확장 + 100% 확장 + 무제한 최적 효율 시트 포함</div>
  </div>
</div>
""", unsafe_allow_html=True)

            today = datetime.now().strftime("%Y%m%d")
            st.markdown(f"""
<div class="pl-dl-box">
  <div class="pl-dl-info">
    <div class="pl-dl-t">제안서 준비 완료</div>
    <div class="pl-dl-s">{res['brand_name']} · {len(active)}개 운영 키워드 · {today}</div>
  </div>
  <div class="pl-dl-icon">📊</div>
</div>
""", unsafe_allow_html=True)

            st.download_button(
                label="⬇  엑셀 제안서 다운로드",
                data=st.session_state.sim_excel_bytes,
                file_name=f"{res['brand_name']}_budget_sim_{today}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="sim_dl_btn",
            )
            st.caption(
                "예상 성과(노출수·클릭수·비용)는 네이버 Estimate API 기반 시뮬레이션 수치입니다. "
                "실제 운영 성과는 광고 품질지수·예산 집행 속도에 따라 달라질 수 있습니다."
            )

        except Exception as _render_err:
            import traceback
            st.error(f"결과 표시 오류: {_render_err}")
            with st.expander("오류 상세"):
                st.code(traceback.format_exc())

    st.stop()

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
        [
            "구매전환", "브랜드인지도", "트래픽 유입",
            "신제품 출시", "앱 다운로드", "리타겟팅",
            "시즌 프로모션", "리드 수집",
            "사전예약/사전등록", "런칭/서비스 오픈", "신작/개봉 홍보",
            "문의/상담 유도", "가입자수 확대", "무료체험 신청", "방문/예약 유도",
        ],
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
            products    = st.text_area("제품명 / 모델명",
                value="\n".join(data.get("products", [])), key=f"prod_{idx}",
                placeholder="예) 그램\n그램Pro\n그램16\n(줄바꿈·쉼표·탭 모두 가능 — 엑셀 복붙 OK)",
                height=100)
            competitors = st.text_area("주요 경쟁사",
                value="\n".join(data.get("competitors", [])), key=f"comp_{idx}",
                placeholder="예) 삼성\n레노버\n애플\n(줄바꿈·쉼표·탭 모두 가능 — 엑셀 복붙 OK)",
                height=100)
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
            must_kws = st.text_area(
                "필수 포함 키워드",
                value="\n".join([
                    m.get("keyword","") if isinstance(m,dict) else str(m)
                    for m in data.get("must_keywords",[])
                ]),
                key=f"must_{idx}",
                placeholder="예) LG그램\nLG노트북 추천\n그램16\n(줄바꿈·쉼표·탭 모두 가능 — 엑셀 열 복붙 OK)",
                height=120,
            )
            must_list = [
                {"keyword": k.strip(), "target_rank": 3, "device": "BOTH"}
                for k in _split_keywords(must_kws) if k.strip()
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
        uploaded_docs = st.file_uploader(
            "참고 문서 업로드 (PDF / TXT / MD, 여러 파일 가능)",
            type=["pdf", "txt", "md"],
            accept_multiple_files=True,
            key=f"doc_{idx}",
            help="제품 카탈로그, 마케팅 제안서 등 — Claude가 문서 내용을 참고하여 키워드를 생성합니다",
        )
        doc_context = ""
        _cache_key = f"doc_result_{idx}"
        if uploaded_docs:
            from modules.pdf_extractor import extract_from_uploaded_bytes
            # 파일별 캐시: {sig: raw_text} 딕셔너리로 관리
            _cached = st.session_state.get(_cache_key, {})
            _new_cache = {}
            _all_texts = []
            _total_pages = 0
            _total_kws = 0
            _ocr_used = False
            for _f in uploaded_docs:
                _sig = f"{_f.name}_{_f.size}"
                if _sig in _cached:
                    _doc_res = _cached[_sig]
                else:
                    with st.spinner(f"문서 분석 중… {_f.name}"):
                        _doc_res = extract_from_uploaded_bytes(_f.read(), _f.name, category)
                _new_cache[_sig] = _doc_res
                if _doc_res.get("raw_text"):
                    _all_texts.append(f"[{_f.name}]\n{_doc_res['raw_text']}")
                _total_pages += _doc_res.get("page_count", 0)
                _total_kws  += len(_doc_res.get("keywords", []))
                if _doc_res.get("ocr_used"):
                    _ocr_used = True
            st.session_state[_cache_key] = _new_cache
            doc_context = "\n\n".join(_all_texts)
            _ocr_tag = " · OCR" if _ocr_used else ""
            st.caption(
                f"문서 분석 완료{_ocr_tag}: "
                f"{len(uploaded_docs)}개 파일 · {_total_pages}페이지 · 키워드 {_total_kws}개 추출"
            )
        elif st.session_state.get(_cache_key):
            del st.session_state[_cache_key]

        return {
            "brand_name":             brand_name,
            "brand_key":              brand_name.replace(" ","_").lower() or f"brand_{idx}",
            "category":               category,
            "products":               _split_keywords(products),
            "brand_variants":         [],
            "typo_variants":          [],
            "competitors":            _split_keywords(competitors),
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

if not st.session_state.brand_results:
    _gen_btn = st.button("⚡  제안서 생성 시작", type="primary", use_container_width=True)
else:
    st.info("💡 키워드 조정은 아래 **추천 키워드 상세**에서 체크박스·추가 키워드 수정 후 **재생성** 버튼을 클릭하세요. 브랜드 설정을 변경한 경우에만 아래 버튼을 사용하세요.")
    _gen_btn = st.button("🔄  설정 변경 후 처음부터 재생성", use_container_width=True)

# 버튼 클릭 직후 ~ 생성 실행 전 사이: 화면 상단에 즉시 피드백 (Streamlit rerun 지연 보완)
if _gen_btn and not st.session_state.get("_gen_pending"):
    st.info("⏳ 입력 값 확인 중... 잠시 후 생성이 시작됩니다.")

# AI 캐시 관리
with st.expander("AI 키워드 캐시 관리 (7일 유효)"):
    from modules.ai_keyword_generator import list_ai_cached_brands, clear_ai_cache_for_brand, clear_all_ai_cache
    cached_brands = list_ai_cached_brands()
    if not cached_brands:
        st.caption("저장된 AI 키워드 캐시 없음")
    else:
        st.caption(f"캐시된 브랜드 {len(cached_brands)}개 — 브랜드 정보·경쟁사가 바뀌었거나 AI 개선 후 최신 결과를 원할 때 삭제하세요.")
        for cb in cached_brands:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{cb['brand_name']}**  <span style='color:gray;font-size:0.85em'>{cb['cached_at']}  파일 {cb['files']}개</span>", unsafe_allow_html=True)
            with col2:
                if st.button("삭제", key=f"_cache_del_{cb['brand_name']}"):
                    n = clear_ai_cache_for_brand(cb["brand_name"])
                    st.success(f"삭제 완료 ({n}개)")
                    st.rerun()
    if cached_brands:
        if st.button("전체 캐시 삭제", type="secondary"):
            n = clear_all_ai_cache()
            st.success(f"전체 삭제 완료 ({n}개)")
            st.rerun()

if _gen_btn:
    valid = True
    _err_msgs = []

    if not client_name.strip():
        _err_msgs.append("광고주명을 입력해주세요.")
        valid = False

    for i, bc in enumerate(brand_configs):
        # 위젯 세션스테이트 키로 폴백 — 버튼 즉시 클릭 시 값 누락 대비
        _bname = bc.get("brand_name") or st.session_state.get(f"bname_{i}", "")
        _cat   = bc.get("category")  or st.session_state.get(f"cat_{i}", "")
        if not _bname or not _cat:
            _err_msgs.append(f"Brand {i+1}: 브랜드명과 카테고리를 입력해주세요.")
            valid = False

    if _err_msgs:
        for _msg in _err_msgs:
            st.error(_msg)
        try:
            st.toast(" | ".join(_err_msgs), icon="❌")
        except Exception:
            pass

    if valid:
        # 버튼 클릭 상태가 rerun 중 유실되지 않도록 세션 플래그로 저장
        st.session_state._gen_client_name   = client_name
        st.session_state._gen_brand_configs = brand_configs
        st.session_state._gen_goal_str      = (
            ", ".join(campaign_goals)
            + (f" | 신제품: {new_product_info}" if new_product_info else "")
            + (f" | 시즌: {season_info}" if season_info else "")
        )
        st.session_state._gen_pending = True
        st.rerun()

if st.session_state.get("_gen_pending"):
    st.session_state._gen_pending = False
    client_name   = st.session_state.get("_gen_client_name", "")
    brand_configs = st.session_state.get("_gen_brand_configs", [])
    goal_str      = st.session_state.get("_gen_goal_str", "")
    if not client_name or not brand_configs:
        st.error("생성 정보가 손실되었습니다. 다시 버튼을 클릭해주세요.")
        st.stop()

    client_profile = {
        "client":           client_name,
        "monthly_budget":   monthly_budget,
        "sales_channels":   [],
        "campaign_goal":    goal_str,
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

            status.info(f"[{i+1}/{total}] **{bname}** — 브랜드 분석 중 (AI)...")
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

            rank_ov = st.session_state.custom_rank_kws.get(bname, {})
            if rank_ov:
                brand_profile["rank_overrides"] = rank_ov

            status.info(f"[{i+1}/{total}] **{bname}** — AI 키워드 생성 중... (30~60초 소요)")

            brand_base = i / total
            brand_span = 1.0 / total

            def _brand_progress(step: str, pct: float, _base=brand_base, _span=brand_span):
                overall = _base + pct * _span
                progress.progress(min(overall, 0.99))
                status.info(f"[{i+1}/{total}] **{bname}** — {step}")

            result = run_single_brand(brand_profile, bname, progress_cb=_brand_progress)
            brand_results.append(result)
            progress.progress((i + 1) / total)

        status.info("엑셀 파일 생성 중...")
        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"output/{client_name}_proposal_{ts}.xlsx"
        os.makedirs("output", exist_ok=True)
        save_multi_brand_excel(brand_results, filename, client_name)

        with open(filename, "rb") as f:
            excel_bytes = f.read()

        # 재생성 시 키워드 에디터 초기 df 캐시 초기화
        for _k in [k for k in st.session_state if k.startswith("_df_init_")]:
            del st.session_state[_k]

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
# 키워드 에디터 Fragment — 체크박스 클릭 시 이 블록만 리런 (스크롤 유지)
# ─────────────────────────────────────────────────────────────────
@st.fragment
def _kw_editor_fragment(bname, all_rows, active_count, standby_count):
    _init_key = f"_df_init_{bname}"

    # 초기 df를 최초 1회만 생성해 고정 — 매번 재생성하면 data_editor 상태 충돌
    if _init_key not in st.session_state:
        exc_set  = set(st.session_state.custom_exc_kws.get(bname, []))
        rank_map = st.session_state.custom_rank_kws.get(bname, {})
        rows = []
        for r in all_rows:
            kw = r.get("keyword", "")
            cur_rank = r.get("proposed_rank") or r.get("rank", "")
            # 이전에 저장된 순위 override가 있으면 그 값 사용, 없으면 "자동"
            saved_rank = rank_map.get(kw)
            rank_label = f"{saved_rank}위" if saved_rank else "자동"
            rows.append({
                "포함":      kw not in exc_set,
                "키워드":    kw,
                "그룹":      r.get("category", ""),
                "구분":      r.get("keyword_type_label", r.get("keyword_type", "")),
                "PC 검색수": int(r.get("pc_impr", 0) or 0),
                "MO 검색수": int(r.get("mo_impr", 0) or 0),
                "경쟁도":    r.get("competition", "-"),
                "예상비용":  int((r.get("pc_cost") or 0) + (r.get("mo_cost") or 0)),
                "현재 순위": str(cur_rank) if cur_rank else "-",
                "목표 순위": rank_label,
                "상태":      "대기" if r.get("not_selected") else "추천",
            })
        st.session_state[_init_key] = pd.DataFrame(rows)

    _RANK_OPTIONS = ["자동", "1위", "2위", "3위", "4위", "5위"]

    st.caption(f"총 {len(all_rows)}개 키워드 (추천 {active_count}개 / 대기 {standby_count}개)")
    edited = st.data_editor(
        st.session_state[_init_key],
        column_config={
            "포함":      st.column_config.CheckboxColumn("포함", width="small"),
            "키워드":    st.column_config.TextColumn("키워드", width="medium"),
            "그룹":      st.column_config.TextColumn("그룹", width="medium"),
            "구분":      st.column_config.TextColumn("구분", width="small"),
            "PC 검색수": st.column_config.NumberColumn("PC 검색수", format="%d"),
            "MO 검색수": st.column_config.NumberColumn("MO 검색수", format="%d"),
            "경쟁도":    st.column_config.TextColumn("경쟁도", width="small"),
            "예상비용":  st.column_config.NumberColumn("예상비용", format="%d원"),
            "현재 순위": st.column_config.TextColumn("현재 순위", width="small", disabled=True),
            "목표 순위": st.column_config.SelectboxColumn(
                "목표 순위", options=_RANK_OPTIONS, width="small",
                help="자동: 예산 최적화가 결정 / 1~5위: 해당 순위로 고정"
            ),
            "상태":      st.column_config.TextColumn("상태", width="small"),
        },
        hide_index=True,
        use_container_width=True,
        key=f"tbl_{bname}",
    )

    excluded = edited[edited["포함"] == False]["키워드"].tolist()
    st.session_state.custom_exc_kws[bname] = excluded
    if excluded:
        st.caption(f"제외됨: {', '.join(excluded[:6])}{'...' if len(excluded) > 6 else ''}")

    # 목표 순위 override 저장 ("자동" 아닌 것만)
    rank_overrides = {}
    for _, row in edited.iterrows():
        v = row.get("목표 순위", "자동")
        if v and v != "자동":
            try:
                rank_overrides[row["키워드"]] = int(v.replace("위", ""))
            except ValueError:
                pass
    st.session_state.custom_rank_kws[bname] = rank_overrides
    if rank_overrides:
        st.caption(f"순위 고정: {', '.join(f'{k}→{v}위' for k, v in list(rank_overrides.items())[:4])}{'...' if len(rank_overrides) > 4 else ''}")

    st.divider()
    st.markdown("**키워드 추가**")
    add_input = st.text_area(
        "추가할 키워드 (쉼표 또는 줄바꿈으로 구분)",
        key=f"add_{bname}",
        placeholder="예) LG그램 신제품\n학생 노트북 추천",
        height=76,
    )
    add_kws = [k.strip() for k in add_input.replace(",", "\n").splitlines() if k.strip()]
    if st.button(f"⚡  {bname} — 커스텀 적용 후 재생성", key=f"regen_{bname}", type="primary", use_container_width=True):
        # 버튼 클릭 시점에 모든 커스텀 설정을 명시적으로 저장 (타이밍 이슈 방지)
        st.session_state.custom_exc_kws[bname] = edited[edited["포함"] == False]["키워드"].tolist()
        st.session_state.custom_add_kws[bname] = add_kws
        # 목표 순위 override 재저장
        _rank_ov = {}
        for _, row in edited.iterrows():
            v = row.get("목표 순위", "자동")
            if v and v != "자동":
                try:
                    _rank_ov[row["키워드"]] = int(v.replace("위", ""))
                except ValueError:
                    pass
        st.session_state.custom_rank_kws[bname] = _rank_ov
        st.session_state._gen_pending = True
        st.rerun(scope="app")


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
            _kw_editor_fragment(bname, active + standby, len(active), len(standby))

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
