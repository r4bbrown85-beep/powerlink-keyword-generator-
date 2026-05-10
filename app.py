# -*- coding: utf-8 -*-
"""
파워링크 SA 키워드 제안서 생성기 - Streamlit UI v3
"""
import streamlit as st
import pandas as pd
import json, os, sys, io
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Streamlit Cloud 배포 시 secrets → 환경변수로 주입
try:
    for k, v in st.secrets.items():
        os.environ.setdefault(k, str(v))
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(
    page_title="파워링크 제안서 생성기",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── 전문적 UI CSS ──────────────────────────────────────────────────
st.markdown("""
<style>
/* ── 기본 리셋 ── */
#MainMenu, footer { visibility: hidden; }
.stDeployButton { display: none; }
.block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1100px; }

/* ── 앱 헤더 ── */
.app-header {
    background: #0F1929;
    color: white;
    padding: 28px 32px;
    border-radius: 10px;
    margin-bottom: 36px;
}
.app-header-eyebrow {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.15em;
    color: #4B9EFF;
    text-transform: uppercase;
    margin-bottom: 6px;
}
.app-header-title {
    font-size: 26px;
    font-weight: 800;
    color: #FFFFFF;
    margin: 0 0 6px;
    line-height: 1.2;
}
.app-header-sub {
    font-size: 13px;
    color: #8FA3BF;
    margin: 0;
}

/* ── 섹션 헤더 ── */
.section-wrap { margin: 8px 0 20px; }
.section-badge {
    display: inline-block;
    background: #0F1929;
    color: #4B9EFF;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.12em;
    padding: 3px 10px;
    border-radius: 4px;
    margin-bottom: 8px;
}
.section-title {
    font-size: 18px;
    font-weight: 700;
    color: #0F1929;
    margin: 0 0 4px;
}
.section-desc {
    font-size: 13px;
    color: #64748B;
    margin: 0;
}

/* ── 구분선 ── */
hr { border-color: #E8ECF2 !important; margin: 28px 0 !important; }

/* ── 버튼 ── */
div[data-testid="stButton"] > button[kind="primary"] {
    background: #0F1929 !important;
    color: white !important;
    border: none !important;
    font-weight: 700 !important;
    letter-spacing: 0.03em !important;
    border-radius: 6px !important;
    padding: 0.65rem 1.5rem !important;
    font-size: 14px !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    background: #1A2E4A !important;
}
div[data-testid="stButton"] > button[kind="secondary"] {
    border: 1px solid #CBD5E1 !important;
    color: #374151 !important;
    font-weight: 600 !important;
    border-radius: 6px !important;
}

/* ── 다운로드 버튼 ── */
div[data-testid="stDownloadButton"] > button {
    background: #1A56DB !important;
    color: white !important;
    border: none !important;
    font-weight: 700 !important;
    border-radius: 6px !important;
    padding: 0.65rem 1.5rem !important;
    font-size: 14px !important;
    letter-spacing: 0.02em !important;
}
div[data-testid="stDownloadButton"] > button:hover {
    background: #1648C8 !important;
}

/* ── Expander ── */
[data-testid="stExpander"] summary {
    font-weight: 700 !important;
    color: #0F1929 !important;
    font-size: 14px !important;
}
[data-testid="stExpander"] {
    border: 1px solid #E8ECF2 !important;
    border-radius: 8px !important;
    margin-bottom: 10px !important;
}

/* ── 탭 ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    border-bottom: 2px solid #E8ECF2;
}
.stTabs [data-baseweb="tab"] {
    font-weight: 600 !important;
    color: #64748B !important;
    font-size: 13px !important;
    padding: 8px 18px !important;
    border-radius: 6px 6px 0 0 !important;
}
.stTabs [aria-selected="true"] {
    color: #0F1929 !important;
    border-bottom: 2px solid #0F1929 !important;
}

/* ── 메트릭 카드 ── */
.metric-card {
    background: white;
    border: 1px solid #E8ECF2;
    border-radius: 10px;
    padding: 20px 24px;
    box-shadow: 0 1px 4px rgba(15,25,41,0.06);
}
.metric-label {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: #94A3B8;
    text-transform: uppercase;
    margin-bottom: 6px;
}
.metric-value {
    font-size: 22px;
    font-weight: 800;
    color: #0F1929;
    margin-bottom: 2px;
}
.metric-sub {
    font-size: 12px;
    color: #64748B;
}

/* ── 성공/오류 메시지 ── */
[data-testid="stAlert"] {
    border-radius: 8px !important;
    font-weight: 500 !important;
}

/* ── Progress ── */
[data-testid="stProgressBar"] > div {
    background: #1A56DB !important;
    border-radius: 4px !important;
}

/* ── Input labels ── */
[data-testid="stWidgetLabel"] {
    font-weight: 600 !important;
    color: #374151 !important;
    font-size: 13px !important;
}

/* ── 키워드 테이블 헤더 ── */
.kw-table-header {
    font-size: 13px;
    font-weight: 700;
    color: #0F1929;
    margin-bottom: 8px;
    padding-bottom: 8px;
    border-bottom: 1px solid #E8ECF2;
}
</style>
""", unsafe_allow_html=True)

# ── 앱 헤더 ──────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <div class="app-header-eyebrow">Naver Powerlink · AI Keyword Planner</div>
    <div class="app-header-title">파워링크 키워드 제안서 생성기</div>
    <div class="app-header-sub">광고주 정보를 입력하면 AI가 키워드를 자동 추천하고 네이버 데이터 기반 제안서를 생성합니다</div>
</div>
""", unsafe_allow_html=True)

# ── 세션 상태 초기화 ──────────────────────────────────────────────
for key, default in [
    ("brand_results", None),
    ("client_name", ""),
    ("excel_bytes", None),
    ("filename", ""),
    ("brands", [{}]),
    ("custom_add_kws", {}),
    ("custom_exc_kws", {}),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Step 1: 광고주 기본 정보 ──────────────────────────────────────
st.markdown("""
<div class="section-wrap">
    <div class="section-badge">STEP 01</div>
    <div class="section-title">광고주 기본 정보</div>
    <div class="section-desc">캠페인 전체 예산과 목표를 설정합니다</div>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    client_name = st.text_input("광고주명 *", placeholder="예) 드리미코리아")
    monthly_budget = st.number_input(
        "월 예산 (원) *",
        min_value=100000, max_value=100000000,
        value=st.session_state.get("_prev_global_budget", 5000000),
        step=100000, format="%d",
        key="global_budget_input"
    )
    if monthly_budget != st.session_state.get("_prev_global_budget"):
        st.session_state["_prev_global_budget"] = monthly_budget
        for idx in range(len(st.session_state.get("brands", []))):
            st.session_state[f"bgt_{idx}"] = monthly_budget
with col2:
    campaign_goals = st.multiselect(
        "캠페인 목표",
        [
            "구매전환", "브랜드인지도", "트래픽 유입",
            "신제품 출시", "앱 다운로드", "리타겟팅",
            "시즌 프로모션", "리드 수집"
        ],
        default=["구매전환"]
    )
    new_product_info = ""
    season_info = ""
    if "신제품 출시" in campaign_goals:
        new_product_info = st.text_input(
            "신제품 정보",
            placeholder="예) 드리미 V20, 초경량 무선청소기, 2026년 5월 출시",
            help="신제품명, 주요 특징, 출시일 등을 입력하면 관련 키워드가 더 잘 생성됩니다."
        )
    if "시즌 프로모션" in campaign_goals:
        season_info = st.text_input(
            "시즌/이슈 내용",
            placeholder="예) 여름 휴가 시즌, 캠핑 트렌드 / 블랙프라이데이 할인",
            help="어떤 시즌이나 이슈를 타겟하는지 입력하면 시즌 키워드가 반영됩니다."
        )

st.divider()

# ── Step 2: 브랜드 정보 입력 ──────────────────────────────────────
st.markdown("""
<div class="section-wrap">
    <div class="section-badge">STEP 02</div>
    <div class="section-title">브랜드 정보</div>
    <div class="section-desc">브랜드별 제안서 시트가 생성됩니다. 여러 브랜드를 동시에 추가할 수 있습니다</div>
</div>
""", unsafe_allow_html=True)

AWARENESS_OPTIONS = {
    "신규/저인지도 (집행 경험 없음)": "low",
    "중간 (일부 인지도 있음, 집행 경험 있음)": "medium",
    "높음 (브랜드 인지도 있음)": "high",
}
AWARENESS_LABELS = list(AWARENESS_OPTIONS.keys())
AWARENESS_VALS   = list(AWARENESS_OPTIONS.values())

def brand_form(idx, brand_data={}):
    label = brand_data.get("brand_name", "브랜드명 미입력")
    with st.expander(f"브랜드 {idx+1}  ·  {label}", expanded=(idx == 0)):
        c1, c2 = st.columns(2)
        with c1:
            brand_name  = st.text_input("브랜드명 *", value=brand_data.get("brand_name",""), key=f"bname_{idx}")
            category    = st.text_input("카테고리 *", value=brand_data.get("category",""), key=f"cat_{idx}", placeholder="예) 헤어드라이기")
            products    = st.text_input("제품명/모델명 (쉼표 구분)", value=", ".join(brand_data.get("products",[])), key=f"prod_{idx}", placeholder="예) 드리미포켓드라이기, 포켓드라이기")
            competitors = st.text_input("주요 경쟁사 (쉼표 구분)", value=", ".join(brand_data.get("competitors",[])), key=f"comp_{idx}", placeholder="예) 다이슨, JMW, 파나소닉")

        with c2:
            brand_budget = st.number_input(
                "브랜드 월 예산 (원)",
                help="Step 1 총 예산이 자동 반영됩니다. 브랜드가 여러 개면 분배 예산을 직접 수정하세요.",
                min_value=100000, max_value=100000000,
                value=brand_data.get("monthly_budget", monthly_budget),
                step=100000, format="%d", key=f"bgt_{idx}"
            )
            cur_aw  = brand_data.get("brand_awareness", "low")
            aw_idx  = AWARENESS_VALS.index(cur_aw) if cur_aw in AWARENESS_VALS else 0
            aw_sel  = st.selectbox("브랜드 인지도", AWARENESS_LABELS, index=aw_idx, key=f"aw_{idx}")
            awareness = AWARENESS_OPTIONS[aw_sel]

            brand_urls = st.text_area(
                "브랜드/상품 URL (한 줄에 하나씩)\n입력 시 해당 페이지에서 키워드 자동 추출",
                value="\n".join(brand_data.get("brand_urls", [])),
                key=f"url_{idx}",
                placeholder="예)\nhttps://brand.naver.com/dreame\nhttps://smartstore.naver.com/dreame",
                height=100
            )
            url_list = [u.strip() for u in brand_urls.splitlines() if u.strip()]

            must_kws = st.text_input(
                "필수 포함 키워드 (쉼표 구분)",
                value=", ".join([m.get("keyword","") if isinstance(m,dict) else str(m) for m in brand_data.get("must_keywords",[])]),
                key=f"must_{idx}",
                placeholder="예) 드리미 포켓, 드리미 헤어드라이기"
            )
            must_kw_list = [{"keyword": k.strip(), "target_rank": 3, "device": "BOTH"}
                           for k in must_kws.split(",") if k.strip()]

        return {
            "brand_name":             brand_name,
            "brand_key":              brand_name.replace(" ","_").lower() if brand_name else f"brand_{idx}",
            "category":               category,
            "products":               [p.strip() for p in products.split(",") if p.strip()],
            "brand_variants":         [],
            "typo_variants":          [],
            "competitors":            [c.strip() for c in competitors.split(",") if c.strip()],
            "celebrities":            [],
            "must_keywords":          must_kw_list,
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

col_a, col_b = st.columns([1, 1])
with col_a:
    if st.button("브랜드 추가", use_container_width=True):
        st.session_state.brands.append({"monthly_budget": monthly_budget})
        st.rerun()
with col_b:
    if len(st.session_state.brands) > 1:
        if st.button("마지막 브랜드 삭제", use_container_width=True):
            st.session_state.brands.pop()
            st.rerun()

st.divider()

# ── Step 3: 제안서 생성 ───────────────────────────────────────────
st.markdown("""
<div class="section-wrap">
    <div class="section-badge">STEP 03</div>
    <div class="section-title">제안서 생성</div>
    <div class="section-desc">AI 키워드 생성 → 네이버 데이터 조회 → 예산 최적화 순서로 진행됩니다 (약 2~5분 소요)</div>
</div>
""", unsafe_allow_html=True)

if st.button("제안서 생성 시작", type="primary", use_container_width=True):

    valid = True
    if not client_name:
        st.error("광고주명을 입력해주세요.")
        valid = False
    for i, bc in enumerate(brand_configs):
        if not bc["brand_name"] or not bc["category"]:
            st.error(f"브랜드 {i+1}: 브랜드명과 카테고리는 필수입니다.")
            valid = False

    if valid:
        goal_detail = ", ".join(campaign_goals)
        if new_product_info:
            goal_detail += f" | 신제품: {new_product_info}"
        if season_info:
            goal_detail += f" | 시즌: {season_info}"

        client_profile = {
            "client":           client_name,
            "monthly_budget":   monthly_budget,
            "sales_channels":   [],
            "campaign_goal":    goal_detail,
            "new_product_info": new_product_info,
            "season_info":      season_info,
            "brands":           brand_configs,
        }

        brand_results = []
        progress_bar  = st.progress(0)
        status_text   = st.empty()

        try:
            from main_multi import run_single_brand, make_brand_profile, save_multi_brand_excel
            from modules.url_extractor import extract_keywords_from_urls
            from modules.setup_profile import enrich_brand_config

            for i, brand_cfg in enumerate(brand_configs):
                brand_name = brand_cfg["brand_name"]
                status_text.text(f"[{i+1}/{len(brand_configs)}] '{brand_name}' 처리 중...")

                url_result = {}
                urls = brand_cfg.get("brand_urls", [])
                if urls:
                    try:
                        status_text.text(f"[{i+1}/{len(brand_configs)}] URL 분석 중...")
                        url_result = extract_keywords_from_urls(urls)
                        if url_result.get("products"):
                            existing = set(brand_cfg.get("products", []))
                            for p in url_result["products"]:
                                if p not in existing:
                                    brand_cfg.setdefault("products", []).append(p)
                    except Exception as e:
                        st.warning(f"URL 분석 실패: {e}")

                status_text.text(f"[{i+1}/{len(brand_configs)}] '{brand_name}' 브랜드 분석 중...")
                try:
                    brand_cfg = enrich_brand_config(
                        brand_cfg,
                        url_keywords=url_result.get("keywords", [])
                    )
                except Exception as e:
                    st.warning(f"브랜드 분석 실패: {e}")

                url_keywords = url_result.get("keywords", [])
                if url_keywords:
                    brand_cfg["general_keyword_themes"] = list(set(
                        brand_cfg.get("general_keyword_themes", []) + url_keywords[:15]
                    ))

                add_kws = st.session_state.custom_add_kws.get(brand_name, [])
                exc_kws = st.session_state.custom_exc_kws.get(brand_name, [])
                if exc_kws:
                    brand_cfg["exclude_keywords"] = list(set(
                        brand_cfg.get("exclude_keywords", []) + exc_kws
                    ))

                brand_profile = make_brand_profile(client_profile, brand_cfg)

                if add_kws:
                    brand_profile["must_keywords"] = brand_profile.get("must_keywords", []) + [
                        {"keyword": k, "target_rank": 3, "device": "BOTH"} for k in add_kws
                    ]

                status_text.text(f"[{i+1}/{len(brand_configs)}] '{brand_name}' 키워드 생성 중...")
                result = run_single_brand(brand_profile, brand_name)
                brand_results.append(result)
                progress_bar.progress((i + 1) / len(brand_configs))

            status_text.text("엑셀 파일 생성 중...")
            today    = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"output/{client_name}_proposal_{today}.xlsx"
            os.makedirs("output", exist_ok=True)
            save_multi_brand_excel(brand_results, filename, client_name)

            with open(filename, "rb") as f:
                excel_bytes = f.read()

            st.session_state.brand_results = brand_results
            st.session_state.client_name   = client_name
            st.session_state.excel_bytes   = excel_bytes
            st.session_state.filename      = filename

            progress_bar.progress(1.0)
            status_text.text("")

            active_kw_total = sum(
                len([r for r in res['recommended'] if not r.get('not_selected')])
                for res in brand_results
            )
            st.success(
                f"제안서 생성 완료 — {len(brand_results)}개 브랜드 · 추천 키워드 {active_kw_total}개"
            )

        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
            import traceback
            st.code(traceback.format_exc())

# ── Step 4: 결과 확인 ─────────────────────────────────────────────
if st.session_state.brand_results:
    st.divider()
    st.markdown("""
<div class="section-wrap">
    <div class="section-badge">STEP 04</div>
    <div class="section-title">결과 요약</div>
</div>
""", unsafe_allow_html=True)

    brand_results = st.session_state.brand_results

    # 브랜드별 요약 카드
    cols = st.columns(len(brand_results))
    for i, result in enumerate(brand_results):
        with cols[i]:
            used_ratio  = result['total_cost'] / result['monthly_budget'] * 100
            active_kws  = [r for r in result['recommended'] if not r.get('not_selected')]
            st.markdown(f"""
<div class="metric-card">
    <div class="metric-label">{result['brand_category']}</div>
    <div class="metric-value">{result['brand_name']}</div>
    <div class="metric-sub">예상 월 비용 <strong>{result['total_cost']:,}원</strong> · 예산 대비 {used_ratio:.0f}%</div>
    <div class="metric-sub" style="margin-top:4px">추천 키워드 <strong>{len(active_kws)}개</strong></div>
</div>
""", unsafe_allow_html=True)

    st.divider()

    # 브랜드별 키워드 상세 탭
    st.markdown('<div class="kw-table-header">추천 키워드 상세</div>', unsafe_allow_html=True)
    tabs = st.tabs([r["brand_name"] for r in brand_results])

    for tab, result in zip(tabs, brand_results):
        with tab:
            brand_name   = result["brand_name"]
            recommended  = result["recommended"]
            active_rows  = [r for r in recommended if not r.get("not_selected")]
            standby_rows = result.get("standby_rows", [])

            all_rows_combined = active_rows + standby_rows
            exc_set = set(st.session_state.custom_exc_kws.get(brand_name, []))

            table_data = []
            for r in all_rows_combined:
                pc_cost = r.get("pc_cost", 0) or 0
                mo_cost = r.get("mo_cost", 0) or 0
                kw = r.get("keyword", "")
                table_data.append({
                    "포함":      kw not in exc_set,
                    "키워드":    kw,
                    "구분":      r.get("keyword_type_label", r.get("keyword_type", "")),
                    "PC 검색수": int(r.get("pc_impr", 0) or 0),
                    "MO 검색수": int(r.get("mo_impr", 0) or 0),
                    "경쟁도":    r.get("competition", "-"),
                    "예상비용":  int(pc_cost + mo_cost),
                    "상태":      "대기" if r.get("not_selected") else "추천",
                })

            df_table = pd.DataFrame(table_data)
            st.caption(f"키워드 {len(all_rows_combined)}개 — 포함 체크 해제 시 제외됩니다")
            edited_table = st.data_editor(
                df_table,
                column_config={
                    "포함":      st.column_config.CheckboxColumn("포함", width="small"),
                    "키워드":    st.column_config.TextColumn("키워드", width="medium"),
                    "구분":      st.column_config.TextColumn("구분", width="small"),
                    "PC 검색수": st.column_config.NumberColumn("PC 검색수", format="%d"),
                    "MO 검색수": st.column_config.NumberColumn("MO 검색수", format="%d"),
                    "경쟁도":    st.column_config.TextColumn("경쟁도", width="small"),
                    "예상비용":  st.column_config.NumberColumn("예상비용", format="%d원"),
                    "상태":      st.column_config.TextColumn("상태", width="small"),
                },
                hide_index=True,
                use_container_width=True,
                key=f"kw_table_{brand_name}"
            )

            excluded = edited_table[edited_table["포함"] == False]["키워드"].tolist()
            st.session_state.custom_exc_kws[brand_name] = excluded
            if excluded:
                st.caption(f"제외된 키워드 {len(excluded)}개: {', '.join(excluded[:5])}{'...' if len(excluded)>5 else ''}")

            st.divider()

            st.markdown("**키워드 추가**")
            add_input = st.text_area(
                "추가할 키워드 입력 (쉼표 또는 줄바꿈으로 구분)",
                key=f"add_{brand_name}",
                placeholder="예) LG그램 신제품\n학생 노트북 추천",
                height=80
            )
            add_kws = [k.strip() for k in add_input.replace(",","\n").splitlines() if k.strip()]

            if st.button(f"'{brand_name}' 커스텀 적용 후 재생성", key=f"regen_{brand_name}"):
                st.session_state.custom_add_kws[brand_name] = add_kws
                st.info("커스텀 설정이 저장되었습니다. Step 3에서 '제안서 생성 시작'을 다시 눌러주세요.")

    st.divider()

    # ── 다운로드 ──────────────────────────────────────────────────
    st.markdown("""
<div class="section-wrap">
    <div class="section-badge">STEP 05</div>
    <div class="section-title">제안서 다운로드</div>
</div>
""", unsafe_allow_html=True)
    today = datetime.now().strftime("%Y%m%d")
    st.download_button(
        label="엑셀 제안서 다운로드",
        data=st.session_state.excel_bytes,
        file_name=f"{st.session_state.client_name}_proposal_{today}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        use_container_width=True
    )
    st.caption("예상 성과(노출수/클릭수/비용)는 네이버 API 데이터를 기반으로 시뮬레이션된 수치입니다.")
