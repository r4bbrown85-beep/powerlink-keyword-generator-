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
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────────────────────────
# CSS  (Inter 폰트는 config.toml이 처리 — 여기선 레이아웃만)
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── 전역 ── */
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none !important; }
.block-container {
    padding: 2.5rem 3rem 5rem !important;
    max-width: 1100px !important;
}

/* ── 사이드바 ── */
[data-testid="stSidebar"] {
    background: #0B1120 !important;
    border-right: none !important;
}
[data-testid="stSidebar"] * {
    color: #94A3B8 !important;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] strong {
    color: #F1F5F9 !important;
}
[data-testid="stSidebar"] hr {
    border-color: #1E293B !important;
}
[data-testid="stSidebarNav"] { display: none !important; }

/* ── 헤더 영역 ── */
.pl-header {
    padding: 0 0 28px 0;
    margin-bottom: 44px;
    border-bottom: 1.5px solid #E5E7EB;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.pl-brand {
    display: flex;
    align-items: center;
    gap: 16px;
}
.pl-logo {
    width: 42px; height: 42px;
    background: linear-gradient(135deg, #1677FF 0%, #0958D9 100%);
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    color: #fff;
    font-size: 14px;
    font-weight: 800;
    letter-spacing: 0.02em;
    flex-shrink: 0;
}
.pl-name {
    font-size: 18px;
    font-weight: 700;
    color: #0B1120;
    letter-spacing: -0.02em;
    line-height: 1;
    margin-bottom: 5px;
}
.pl-sub {
    font-size: 12px;
    color: #9CA3AF;
    letter-spacing: 0.01em;
}
.pl-chips {
    display: flex;
    align-items: center;
    gap: 8px;
}
.pl-chip {
    font-size: 11px;
    font-weight: 500;
    padding: 5px 12px;
    border-radius: 999px;
    letter-spacing: 0.01em;
}
.pl-chip-model {
    background: #F3F4F6;
    color: #6B7280;
}
.pl-chip-beta {
    background: #EFF6FF;
    color: #1677FF;
    font-weight: 700;
    letter-spacing: 0.1em;
}

/* ── 스텝 헤더 ── */
.pl-step {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    margin-bottom: 28px;
}
.pl-step-num {
    width: 30px; height: 30px;
    background: #1677FF;
    color: #fff;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 13px; font-weight: 700;
    flex-shrink: 0; margin-top: 1px;
}
.pl-step-body {}
.pl-step-title {
    font-size: 17px;
    font-weight: 700;
    color: #0B1120;
    letter-spacing: -0.02em;
    margin: 0 0 4px;
    line-height: 1.2;
}
.pl-step-desc {
    font-size: 13px;
    color: #6B7280;
    margin: 0;
    line-height: 1.5;
}

/* ── 구분선 ── */
hr {
    border: none !important;
    border-top: 1px solid #F1F5F9 !important;
    margin: 40px 0 !important;
}

/* ── Primary 버튼 ── */
div[data-testid="stButton"] > button[kind="primary"] {
    background: #1677FF !important;
    color: #fff !important;
    border: none !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    border-radius: 8px !important;
    padding: 0.6rem 1.4rem !important;
    letter-spacing: 0 !important;
    box-shadow: 0 1px 3px rgba(22,119,255,0.25) !important;
    transition: background .15s ease, box-shadow .15s ease !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    background: #0958D9 !important;
    box-shadow: 0 3px 8px rgba(22,119,255,0.3) !important;
}

/* ── Secondary 버튼 ── */
div[data-testid="stButton"] > button[kind="secondary"] {
    background: #fff !important;
    border: 1px solid #E5E7EB !important;
    color: #374151 !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    border-radius: 8px !important;
}
div[data-testid="stButton"] > button[kind="secondary"]:hover {
    border-color: #D1D5DB !important;
    background: #F9FAFB !important;
}

/* ── 다운로드 버튼 ── */
div[data-testid="stDownloadButton"] > button {
    background: #059669 !important;
    color: #fff !important;
    border: none !important;
    font-weight: 600 !important;
    font-size: 15px !important;
    border-radius: 8px !important;
    padding: 0.7rem 1.5rem !important;
    box-shadow: 0 1px 3px rgba(5,150,105,0.25) !important;
}
div[data-testid="stDownloadButton"] > button:hover {
    background: #047857 !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    border: 1px solid #E5E7EB !important;
    border-radius: 10px !important;
    margin-bottom: 10px !important;
    overflow: hidden !important;
}
[data-testid="stExpander"] summary {
    font-weight: 600 !important;
    font-size: 14px !important;
    color: #111827 !important;
    padding: 14px 18px !important;
    background: #fff !important;
}
[data-testid="stExpander"] summary:hover {
    background: #F9FAFB !important;
}

/* ── 탭 ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    border-bottom: 1px solid #E5E7EB;
}
.stTabs [data-baseweb="tab"] {
    font-weight: 500 !important;
    font-size: 13.5px !important;
    color: #6B7280 !important;
    padding: 10px 20px !important;
    border-radius: 0 !important;
    border: none !important;
}
.stTabs [aria-selected="true"] {
    color: #1677FF !important;
    font-weight: 600 !important;
    border-bottom: 2px solid #1677FF !important;
}

/* ── 인풋 레이블 ── */
label[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] {
    font-weight: 500 !important;
    font-size: 13.5px !important;
    color: #374151 !important;
    margin-bottom: 4px !important;
}

/* ── 알림 ── */
[data-testid="stAlert"] {
    border-radius: 8px !important;
    font-size: 13.5px !important;
    font-weight: 500 !important;
}

/* ── 프로그레스 ── */
[data-testid="stProgressBar"] > div {
    background: #1677FF !important;
    border-radius: 4px !important;
}

/* ── 캡션 ── */
small, .st-emotion-cache-s1r2mm { color: #9CA3AF !important; font-size: 12px !important; }

/* ── 인포 카드 (HTML) ── */
.pl-infobox {
    background: #F0F7FF;
    border: 1px solid #BAD7FF;
    border-radius: 10px;
    padding: 20px 24px;
    margin-bottom: 18px;
}
.pl-infobox-title { font-size: 14px; font-weight: 700; color: #0B1120; margin-bottom: 6px; }
.pl-infobox-desc  { font-size: 13px; color: #4B6FA8; line-height: 1.6; }

/* ── KPI 카드 ── */
.pl-kpi {
    background: #fff;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
    padding: 22px 24px;
    height: 100%;
}
.pl-kpi-cat   { font-size: 11px; font-weight: 600; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 10px; }
.pl-kpi-brand { font-size: 15px; font-weight: 700; color: #111827; margin-bottom: 14px; letter-spacing: -0.01em; }
.pl-kpi-value { font-size: 26px; font-weight: 800; color: #1677FF; letter-spacing: -0.04em; line-height: 1; margin-bottom: 3px; }
.pl-kpi-label { font-size: 12px; color: #6B7280; margin-bottom: 14px; }
.pl-kpi-row   { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 7px; }
.pl-kpi-row-k { font-size: 12.5px; color: #6B7280; }
.pl-kpi-row-v { font-size: 13px; font-weight: 600; color: #111827; }

/* ── 다운로드 섹션 ── */
.pl-dl-box {
    background: #F0FDF4;
    border: 1px solid #6EE7B7;
    border-radius: 10px;
    padding: 20px 24px;
    margin-bottom: 16px;
}
.pl-dl-title { font-size: 15px; font-weight: 700; color: #065F46; margin-bottom: 4px; }
.pl-dl-desc  { font-size: 13px; color: #047857; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# 사이드바
# ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚡ PowerLink Planner")
    st.markdown("---")
    st.markdown("**사용 방법**")
    st.markdown("""
1. 광고주명·예산 입력
2. 브랜드 정보 입력
3. 제안서 생성 실행
4. 결과 확인 후 다운로드
""")
    st.markdown("---")
    st.markdown("**키워드 그룹**")
    st.markdown("""
- **브랜드 키워드** — 브랜드명 검색자
- **상품 키워드** — 구매 의향 높은 검색자
- **일반 키워드** — 카테고리 잠재 고객
- **경쟁사 키워드** — 경쟁사 비교 검색자
""")
    st.markdown("---")
    st.markdown("**참고**")
    st.caption("예상 성과는 네이버 API 데이터 기반 시뮬레이션입니다.")
    st.caption("같은 브랜드 재실행 시 7일간 캐시가 사용됩니다.")
    st.markdown("---")
    st.caption("Powered by Claude AI · Naver Search API")

# ─────────────────────────────────────────────────────────────────
# 헤더
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="pl-header">
  <div class="pl-brand">
    <div class="pl-logo">PL</div>
    <div>
      <div class="pl-name">PowerLink Planner</div>
      <div class="pl-sub">Naver Search Advertising · AI Keyword Intelligence</div>
    </div>
  </div>
  <div class="pl-chips">
    <span class="pl-chip pl-chip-model">Claude AI</span>
    <span class="pl-chip pl-chip-beta">BETA</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# 세션 초기화
# ─────────────────────────────────────────────────────────────────
for key, default in [
    ("brand_results", None), ("client_name", ""),
    ("excel_bytes", None),   ("filename", ""),
    ("brands", [{}]),        ("custom_add_kws", {}),
    ("custom_exc_kws", {}),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ─────────────────────────────────────────────────────────────────
# STEP 1 · 광고주 기본 정보
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="pl-step">
  <div class="pl-step-num">1</div>
  <div class="pl-step-body">
    <div class="pl-step-title">광고주 기본 정보</div>
    <div class="pl-step-desc">캠페인 전체 예산과 목표를 설정합니다</div>
  </div>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2, gap="large")
with col1:
    client_name = st.text_input("광고주명 *", placeholder="예) 드리미코리아")
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
            placeholder="예) 드리미 V20, 초경량 무선청소기, 2026년 5월 출시")
    if "시즌 프로모션" in campaign_goals:
        season_info = st.text_input("시즌/이슈 내용",
            placeholder="예) 여름 휴가 시즌, 블랙프라이데이 할인")

st.divider()

# ─────────────────────────────────────────────────────────────────
# STEP 2 · 브랜드 정보
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="pl-step">
  <div class="pl-step-num">2</div>
  <div class="pl-step-body">
    <div class="pl-step-title">브랜드 정보</div>
    <div class="pl-step-desc">브랜드별로 독립된 제안서 시트가 생성됩니다. 여러 브랜드를 동시에 추가할 수 있습니다</div>
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
# STEP 3 · 제안서 생성
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="pl-step">
  <div class="pl-step-num">3</div>
  <div class="pl-step-body">
    <div class="pl-step-title">제안서 생성</div>
    <div class="pl-step-desc">AI 키워드 생성 → 네이버 광고 데이터 조회 → 예산 최적화 순서로 자동 진행됩니다</div>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="pl-infobox">
  <div class="pl-infobox-title">생성 전 체크리스트</div>
  <div class="pl-infobox-desc">
    브랜드명과 카테고리는 필수 입력 항목입니다.<br>
    경쟁사를 입력할수록 경쟁사 키워드 품질이 향상됩니다.<br>
    진행 중에는 페이지를 닫지 마세요.
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

                status.info(f"[{i+1}/{total}] **{bname}** — AI 키워드 생성 중...")
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
# STEP 4 · 결과 확인
# ─────────────────────────────────────────────────────────────────
if st.session_state.brand_results:
    st.divider()
    brand_results = st.session_state.brand_results

    st.markdown("""
<div class="pl-step">
  <div class="pl-step-num">4</div>
  <div class="pl-step-body">
    <div class="pl-step-title">결과 요약</div>
    <div class="pl-step-desc">브랜드별 키워드 성과 및 예산 배분을 확인합니다</div>
  </div>
</div>
""", unsafe_allow_html=True)

    # KPI 카드
    cols = st.columns(len(brand_results), gap="medium")
    for i, res in enumerate(brand_results):
        with cols[i]:
            active  = [r for r in res["recommended"] if not r.get("not_selected")]
            standby = res.get("standby_rows", [])
            ratio   = res["total_cost"] / res["monthly_budget"] * 100 if res["monthly_budget"] else 0
            t_impr  = sum((r.get("pc_sim_impressions") or 0) + (r.get("mo_sim_impressions") or 0)
                          for r in active if not r.get("is_fallback"))
            t_clk   = sum((r.get("pc_sim_clicks") or 0) + (r.get("mo_sim_clicks") or 0)
                          for r in active if not r.get("is_fallback"))
            st.markdown(f"""
<div class="pl-kpi">
  <div class="pl-kpi-cat">{res['brand_category']}</div>
  <div class="pl-kpi-brand">{res['brand_name']}</div>
  <div class="pl-kpi-value">{res['total_cost']:,}</div>
  <div class="pl-kpi-label">예상 월 비용 (원) · 예산 대비 {ratio:.0f}%</div>
  <div class="pl-kpi-row"><span class="pl-kpi-row-k">추천 키워드</span><span class="pl-kpi-row-v">{len(active)}개</span></div>
  <div class="pl-kpi-row"><span class="pl-kpi-row-k">대기 키워드</span><span class="pl-kpi-row-v">{len(standby)}개</span></div>
  <div class="pl-kpi-row"><span class="pl-kpi-row-k">예상 노출</span><span class="pl-kpi-row-v">{t_impr:,}</span></div>
  <div class="pl-kpi-row"><span class="pl-kpi-row-k">예상 클릭</span><span class="pl-kpi-row-v">{t_clk:,}</span></div>
</div>
""", unsafe_allow_html=True)

    st.divider()

    # 키워드 상세 탭
    st.markdown("**추천 키워드 상세**")
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
            st.caption(f"총 {len(all_rows)}개 키워드 — 포함 체크 해제 시 제외됩니다")
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
                st.info("저장 완료. Step 3에서 '제안서 생성 시작'을 다시 클릭하세요.")

    st.divider()

    # ─── STEP 5 · 다운로드 ───────────────────────────────────────
    st.markdown("""
<div class="pl-step">
  <div class="pl-step-num">5</div>
  <div class="pl-step-body">
    <div class="pl-step-title">제안서 다운로드</div>
    <div class="pl-step-desc">네이버 파워링크 캠페인 제안서를 엑셀 파일로 저장합니다</div>
  </div>
</div>
""", unsafe_allow_html=True)

    today = datetime.now().strftime("%Y%m%d")
    st.markdown(f"""
<div class="pl-dl-box">
  <div class="pl-dl-title">제안서 준비 완료</div>
  <div class="pl-dl-desc">{st.session_state.client_name} · {len(brand_results)}개 브랜드 · {today}</div>
</div>
""", unsafe_allow_html=True)

    st.download_button(
        label="⬇  엑셀 제안서 다운로드",
        data=st.session_state.excel_bytes,
        file_name=f"{st.session_state.client_name}_proposal_{today}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
    st.caption("예상 성과(노출수·클릭수·비용)는 네이버 API 데이터 기반 시뮬레이션 수치입니다.")
