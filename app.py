# -*- coding: utf-8 -*-
"""
파워링크 SA 키워드 제안서 생성기 - Streamlit UI v2
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
    page_title="파워링크 키워드 제안서 생성기",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 네이버 파워링크 키워드 제안서 생성기")
st.markdown("광고주 정보를 입력하면 AI가 키워드를 자동으로 추천하고 제안서를 생성합니다.")
st.divider()

# ── 세션 상태 초기화 ──────────────────────────────────────────────
for key, default in [
    ("brand_results", None),
    ("client_name", ""),
    ("excel_bytes", None),
    ("filename", ""),
    ("brands", [{}]),
    ("custom_add_kws", {}),    # 브랜드별 추가 키워드
    ("custom_exc_kws", {}),    # 브랜드별 제외 키워드
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Step 1: 광고주 기본 정보 ──────────────────────────────────────
st.subheader("📋 Step 1. 광고주 기본 정보")

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
    # Step 1 예산이 바뀌면 Step 2 브랜드 예산 위젯도 동기화
    if monthly_budget != st.session_state.get("_prev_global_budget"):
        st.session_state["_prev_global_budget"] = monthly_budget
        for idx in range(len(st.session_state.get("brands", []))):
            st.session_state[f"bgt_{idx}"] = monthly_budget
with col2:
    campaign_goals = st.multiselect(
        "캠페인 목표 (복수 선택 가능)",
        [
            "구매전환", "브랜드인지도", "트래픽 유입",
            "신제품 출시", "앱 다운로드", "리타겟팅",
            "시즌 프로모션", "리드 수집"
        ],
        default=["구매전환"]
    )

    # 목표별 추가 입력
    new_product_info = ""
    season_info = ""
    if "신제품 출시" in campaign_goals:
        new_product_info = st.text_input(
            "🆕 신제품 정보",
            placeholder="예) 드리미 V20, 초경량 무선청소기, 2026년 5월 출시",
            help="신제품명, 주요 특징, 출시일 등을 입력하면 관련 키워드가 더 잘 생성됩니다."
        )
    if "시즌 프로모션" in campaign_goals:
        season_info = st.text_input(
            "🗓️ 시즌/이슈 내용",
            placeholder="예) 여름 휴가 시즌, 캠핑 트렌드 / 블랙프라이데이 할인",
            help="어떤 시즌이나 이슈를 타겟하는지 입력하면 시즌 키워드가 반영됩니다."
        )

st.divider()

# ── Step 2: 브랜드 정보 입력 ──────────────────────────────────────
st.subheader("🏷️ Step 2. 브랜드 정보 입력")
st.caption("여러 브랜드를 추가할 수 있어요. 브랜드별로 별도 제안서 시트가 생성됩니다.")

AWARENESS_OPTIONS = {
    "신규/저인지도 (파워링크 집행 경험 없음)": "low",
    "중간 (일부 인지도 있음, 집행 경험 있음)": "medium",
    "높음 (브랜드 인지도 있음)": "high",
}
AWARENESS_LABELS = list(AWARENESS_OPTIONS.keys())
AWARENESS_VALS   = list(AWARENESS_OPTIONS.values())

def brand_form(idx, brand_data={}):
    label = brand_data.get("brand_name", "(미입력)")
    with st.expander(f"브랜드 {idx+1}: {label}", expanded=(idx == 0)):

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

            # URL 입력
            brand_urls = st.text_area(
                "브랜드/상품 URL (한 줄에 하나씩)\n※ 입력 시 해당 페이지에서 키워드 자동 추출",
                value="\n".join(brand_data.get("brand_urls", [])),
                key=f"url_{idx}",
                placeholder="예)\nhttps://brand.naver.com/dreame\nhttps://smartstore.naver.com/dreame",
                height=100
            )
            url_list = [u.strip() for u in brand_urls.splitlines() if u.strip()]

            # 필수 키워드
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

col_a, col_b = st.columns(2)
with col_a:
    if st.button("➕ 브랜드 추가"):
        st.session_state.brands.append({"monthly_budget": monthly_budget})
        st.rerun()
with col_b:
    if len(st.session_state.brands) > 1:
        if st.button("➖ 마지막 브랜드 삭제"):
            st.session_state.brands.pop()
            st.rerun()

st.divider()

# ── Step 3: 제안서 생성 ───────────────────────────────────────────
st.subheader("🚀 Step 3. 제안서 생성")

if st.button("📊 제안서 생성 시작", type="primary", use_container_width=True):

    valid = True
    if not client_name:
        st.error("광고주명을 입력해주세요.")
        valid = False
    for i, bc in enumerate(brand_configs):
        if not bc["brand_name"] or not bc["category"]:
            st.error(f"브랜드 {i+1}: 브랜드명과 카테고리는 필수입니다.")
            valid = False

    if valid:
        # 캠페인 목표 상세 정보 합산
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

                # URL 크롤링 (네이버 브랜드스토어/스마트스토어 전용 파서)
                url_result = {}
                urls = brand_cfg.get("brand_urls", [])
                if urls:
                    try:
                        status_text.text(f"[{i+1}/{len(brand_configs)}] URL 분석 중...")
                        url_result = extract_keywords_from_urls(urls)
                        # URL에서 추출한 제품명 보강
                        if url_result.get("products"):
                            existing = set(brand_cfg.get("products", []))
                            for p in url_result["products"]:
                                if p not in existing:
                                    brand_cfg.setdefault("products", []).append(p)
                    except Exception as e:
                        st.warning(f"URL 분석 실패: {e}")

                # 브랜드 자동 프로파일 보강 (GPT)
                status_text.text(f"[{i+1}/{len(brand_configs)}] '{brand_name}' 브랜드 분석 중...")
                try:
                    brand_cfg = enrich_brand_config(
                        brand_cfg,
                        url_keywords=url_result.get("keywords", [])
                    )
                except Exception as e:
                    st.warning(f"브랜드 분석 실패: {e}")

                # URL 키워드를 general_keyword_themes에 추가
                url_keywords = url_result.get("keywords", [])
                if url_keywords:
                    brand_cfg["general_keyword_themes"] = list(set(
                        brand_cfg.get("general_keyword_themes", []) + url_keywords[:15]
                    ))

                # 커스텀 추가/제외 키워드 반영
                add_kws = st.session_state.custom_add_kws.get(brand_name, [])
                exc_kws = st.session_state.custom_exc_kws.get(brand_name, [])
                if exc_kws:
                    brand_cfg["exclude_keywords"] = list(set(
                        brand_cfg.get("exclude_keywords", []) + exc_kws
                    ))

                brand_profile = make_brand_profile(client_profile, brand_cfg)

                # 커스텀 추가 키워드를 must_keywords로 추가
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
            st.success(f"✅ 제안서 생성 완료! 총 {len(brand_results)}개 브랜드")

        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
            import traceback
            st.code(traceback.format_exc())

# ── Step 4: 결과 확인 ─────────────────────────────────────────────
if st.session_state.brand_results:
    st.divider()
    st.subheader("📈 Step 4. 결과 요약")

    brand_results = st.session_state.brand_results

    # 브랜드별 요약 카드
    cols = st.columns(len(brand_results))
    for i, result in enumerate(brand_results):
        with cols[i]:
            used_ratio = result['total_cost'] / result['monthly_budget'] * 100
            st.metric(
                label=result["brand_name"],
                value=f"{result['total_cost']:,}원",
                delta=f"예산 대비 {used_ratio:.0f}%"
            )
            st.caption(f"카테고리: {result['brand_category']}")
            active_kws = [r for r in result['recommended'] if not r.get('not_selected')]
            st.caption(f"추천 키워드: {len(active_kws)}개")

    st.divider()

    # 브랜드별 키워드 상세 탭
    st.subheader("📋 추천 키워드 상세")
    tabs = st.tabs([r["brand_name"] for r in brand_results])

    for tab, result in zip(tabs, brand_results):
        with tab:
            brand_name = result["brand_name"]
            recommended = result["recommended"]

            # 활성/대기 구분
            active_rows  = [r for r in recommended if not r.get("not_selected")]
            standby_rows = result.get("standby_rows", [])

            # 키워드 테이블 데이터 구성
            def make_kw_df(rows):
                data = []
                for r in rows:
                    pc_cost = r.get("pc_cost", 0) or 0
                    mo_cost = r.get("mo_cost", 0) or 0
                    data.append({
                        "키워드":     r.get("keyword", ""),
                        "구분":       r.get("keyword_type_label", r.get("keyword_type", "")),
                        "PC 검색수":  int(r.get("pc_impr", 0) or 0),
                        "MO 검색수":  int(r.get("mo_impr", 0) or 0),
                        "PC 클릭수":  int(r.get("pc_clicks", 0) or 0),
                        "MO 클릭수":  int(r.get("mo_clicks", 0) or 0),
                        "경쟁도":     r.get("competition", "-"),
                        "예상비용":   int(pc_cost + mo_cost),
                    })
                return pd.DataFrame(data)

            # ── 키워드 테이블 (체크박스 포함) ───────────────────
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
            st.markdown(f"**키워드 목록 ({len(all_rows_combined)}개)** — 포함 체크 해제 시 제외됩니다")
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

            # 체크 해제된 키워드 자동 저장
            excluded = edited_table[edited_table["포함"] == False]["키워드"].tolist()
            st.session_state.custom_exc_kws[brand_name] = excluded
            if excluded:
                st.caption(f"❌ 제외된 키워드 {len(excluded)}개: {', '.join(excluded[:5])}{'...' if len(excluded)>5 else ''}")

            st.divider()

            # ── 키워드 추가 ────────────────────────────────────────
            st.markdown("**➕ 키워드 추가**")
            add_input = st.text_area(
                "추가할 키워드 입력 (쉼표 또는 줄바꿈으로 구분)",
                key=f"add_{brand_name}",
                placeholder="예) LG그램 신제품\n학생 노트북 추천",
                height=80
            )
            add_kws = [k.strip() for k in add_input.replace(",","\n").splitlines() if k.strip()]

            if st.button(f"🔄 '{brand_name}' 커스텀 적용 후 재생성", key=f"regen_{brand_name}"):
                st.session_state.custom_add_kws[brand_name] = add_kws
                st.info("커스텀 설정이 저장되었습니다. Step 3에서 '제안서 생성 시작'을 다시 눌러주세요.")

    st.divider()

    # ── 다운로드 ──────────────────────────────────────────────────
    st.subheader("📥 Step 5. 다운로드")
    today = datetime.now().strftime("%Y%m%d")
    st.download_button(
        label="📥 제안서 엑셀 다운로드",
        data=st.session_state.excel_bytes,
        file_name=f"{st.session_state.client_name}_proposal_{today}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        use_container_width=True
    )
    st.caption("※ 예상 성과(노출수/클릭수/비용)는 네이버 API 확인 후 업데이트 예정입니다.")