# -*- coding: utf-8 -*-
import streamlit as st
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

try:
    for k, v in st.secrets.items():
        os.environ.setdefault(k, str(v))
except Exception:
    pass

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

st.set_page_config(
    page_title="예산 시뮬레이터 · PowerLink Planner",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
#MainMenu, footer, .stDeployButton,
header[data-testid="stHeader"],
[data-testid="stSidebar"],
[data-testid="collapsedControl"],
[data-testid="stSidebarNav"] { display: none !important; }

.block-container { padding: 0 2.75rem 6rem !important; max-width: 1100px !important; }

.pl-bar {
    background: #0F172A;
    margin: 0 -2.75rem 2rem -2.75rem;
    padding: 0 2.75rem;
    height: 58px;
    display: flex; align-items: center; justify-content: space-between;
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

.pl-sec { display:flex; align-items:flex-start; gap:14px; margin:28px 0 18px; }
.pl-sec-num {
    min-width:32px; height:32px; border-radius:8px;
    background:linear-gradient(135deg,#3B82F6,#1D4ED8);
    display:flex; align-items:center; justify-content:center;
    font-size:14px; font-weight:800; color:#fff;
}
.pl-sec-title { font-size:16px; font-weight:700; color:#0F172A; letter-spacing:-.02em; }
.pl-sec-desc  { font-size:13px; color:#64748B; margin-top:3px; }

.pl-info {
    background:#F0F9FF; border:1px solid #BAE6FD; border-radius:10px;
    padding:14px 18px; margin-bottom:20px;
}
.pl-info-t { font-size:13px; font-weight:700; color:#0369A1; margin-bottom:5px; }
.pl-info-b { font-size:13px; color:#0284C7; line-height:1.7; }

.pl-kpi-grid {
    display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:20px;
}
.pl-kpi-card {
    background:#fff; border:1px solid #E2E8F0; border-radius:12px;
    padding:16px 18px;
}
.pl-kpi-card.accent { background:linear-gradient(135deg,#EFF6FF,#DBEAFE); border-color:#BFDBFE; }
.pl-kpi-lbl { font-size:11px; font-weight:600; color:#94A3B8; text-transform:uppercase; letter-spacing:.06em; margin-bottom:6px; }
.pl-kpi-val { font-size:24px; font-weight:800; color:#0F172A; letter-spacing:-.03em; }
.pl-kpi-sub { font-size:11px; color:#94A3B8; margin-top:3px; }

.pl-dl-box {
    background:linear-gradient(135deg,#F0FDF4,#ECFDF5);
    border:1px solid #A7F3D0; border-radius:12px;
    padding:22px 26px; margin-bottom:16px;
    display:flex; align-items:center; justify-content:space-between;
}
.pl-dl-t { font-size:15px; font-weight:700; color:#065F46; margin-bottom:4px; }
.pl-dl-s { font-size:13px; color:#059669; }
.pl-dl-icon { font-size:28px; opacity:.6; }

small { color:#94A3B8 !important; font-size:12px !important; }
</style>
""", unsafe_allow_html=True)

# ─── 앱 바 ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="pl-bar">
  <div class="pl-bar-l">
    <div class="pl-bar-icon">📊</div>
    <span class="pl-bar-name">PowerLink Planner</span>
    <span class="pl-bar-sep"></span>
    <span class="pl-bar-sub">예산 시뮬레이터 · Budget Optimizer</span>
  </div>
  <div class="pl-bar-r">
    <span class="pl-pill pl-pill-ai">Naver SA API</span>
    <span class="pl-pill pl-pill-beta">BETA</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ─── 페이지 네비게이션 ─────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex;gap:8px;margin-bottom:16px;">
  <a href="/" target="_self" style="
    flex:1;display:flex;align-items:center;justify-content:center;gap:6px;
    padding:10px 0;border-radius:8px;font-size:14px;font-weight:600;text-decoration:none;
    background:#F1F5F9;color:#475569;border:1px solid #E2E8F0;">
    🤖&nbsp; AI 키워드 제안서
  </a>
  <a href="/budget_simulator" target="_self" style="
    flex:1;display:flex;align-items:center;justify-content:center;gap:6px;
    padding:10px 0;border-radius:8px;font-size:14px;font-weight:700;text-decoration:none;
    background:#1D4ED8;color:#fff;border:none;">
    📊&nbsp; 예산 시뮬레이터
  </a>
</div>
""", unsafe_allow_html=True)
st.divider()

# ─── 세션 초기화 ──────────────────────────────────────────────────────────────
if "sim_result" not in st.session_state:
    st.session_state.sim_result = None
if "sim_excel_bytes" not in st.session_state:
    st.session_state.sim_excel_bytes = None



def _split_keywords(text: str) -> list:
    import re
    return [k.strip() for k in re.split(r'[,\n\t]+', text or "") if k.strip()]


# ─────────────────────────────────────────────────────────────────
# SECTION 1 · 입력 (st.form으로 감싸 — 위젯 변경 시 불필요한 rerun 차단)
# ─────────────────────────────────────────────────────────────────
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

# ─────────────────────────────────────────────────────────────────
# SECTION 2 · 시뮬레이션 실행
# ─────────────────────────────────────────────────────────────────
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

            except Exception as e:
                import traceback
                st.error(f"시뮬레이션 오류: {e}")
                with st.expander("오류 상세 (개발자용)"):
                    st.code(traceback.format_exc())

# ─────────────────────────────────────────────────────────────────
# SECTION 3 · 결과 확인
# ─────────────────────────────────────────────────────────────────
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

        import pandas as pd
        rows_disp = []
        for r in active:
            rows_disp.append({
                "키워드":        r.get("keyword", ""),
                "PC 순위":       str(r.get("proposed_rank_pc", "-")),
                "MO 순위":       str(r.get("proposed_rank_mo", "-")),
                "PC 입찰가":     int(r.get("proposed_bid_pc") or 0),
                "MO 입찰가":     int(r.get("proposed_bid_mo") or 0),
                "예상 노출":     int((r.get("pc_sim_impressions") or 0) + (r.get("mo_sim_impressions") or 0)),
                "예상 클릭":     int((r.get("pc_sim_clicks") or 0) + (r.get("mo_sim_clicks") or 0)),
                "예상 비용(원)": int((r.get("pc_sim_cost") or 0) + (r.get("mo_sim_cost") or 0)),
            })
        if rows_disp:
            st.dataframe(
                pd.DataFrame(rows_disp),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "키워드":        st.column_config.TextColumn("키워드", width="medium"),
                    "PC 순위":       st.column_config.TextColumn("PC 순위", width="small"),
                    "MO 순위":       st.column_config.TextColumn("MO 순위", width="small"),
                    "PC 입찰가":     st.column_config.NumberColumn("PC 입찰가", format="%d원"),
                    "MO 입찰가":     st.column_config.NumberColumn("MO 입찰가", format="%d원"),
                    "예상 노출":     st.column_config.NumberColumn("예상 노출"),
                    "예상 클릭":     st.column_config.NumberColumn("예상 클릭"),
                    "예상 비용(원)": st.column_config.NumberColumn("예상 비용", format="%d원"),
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
            key="dl_btn",
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
