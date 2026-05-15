import os
from datetime import datetime

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


# ── 색상 ───────────────────────────────────────────────────────
COLOR_TITLE_BG    = "1F4E79"
COLOR_TITLE_FG    = "FFFFFF"
COLOR_CAT_BRAND   = "BDD7EE"
COLOR_CAT_PRODUCT = "C6EFCE"
COLOR_CAT_GENERAL = "FFF2CC"
COLOR_CAT_COMP    = "FCE4D6"
COLOR_HEADER_BG   = "D9E2F3"
COLOR_SUBTOTAL_BG = "F2F2F2"
COLOR_FALLBACK_BG = "FFF9C4"


def _cat_color(category):
    s = str(category)
    if "브랜드" in s:   return COLOR_CAT_BRAND
    if "상품"   in s:   return COLOR_CAT_PRODUCT
    if "경쟁사" in s:   return COLOR_CAT_COMP
    return COLOR_CAT_GENERAL


def _bd():
    s = Side(style="thin")
    return Border(left=s, right=s, top=s, bottom=s)


def _fill(hex_color):
    return PatternFill("solid", fgColor=hex_color)


def _safe_int(v):
    try:
        return int(float(v)) if v not in ("", None) else 0
    except Exception:
        return 0


def _safe_float(v):
    try:
        return float(v) if v not in ("", None) else 0.0
    except Exception:
        return 0.0


def _write_cell(ws, row, col, value, bold=False, bg=None,
                align_h="center", num_fmt=None, font_size=10,
                italic=False, font_color="000000"):
    """병합된 셀이면 건드리지 않는 안전한 쓰기 헬퍼."""
    from openpyxl.cell.cell import MergedCell
    cell = ws.cell(row=row, column=col)
    if isinstance(cell, MergedCell):
        return cell
    cell.value     = value
    cell.font      = Font(bold=bold, size=font_size,
                          color=font_color, italic=italic)
    cell.alignment = Alignment(horizontal=align_h, vertical="center")
    cell.border    = _bd()
    if bg:
        cell.fill = _fill(bg)
    if num_fmt:
        cell.number_format = num_fmt
    return cell


# ── 메인 ──────────────────────────────────────────────────────
def save_proposal_excel(rows, recommended_rows, category_desc,
                        summary_text, advertiser, standby_rows=None,
                        scenario_data=None):
    os.makedirs("output", exist_ok=True)
    ts          = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"output/{advertiser}_proposal_keywords_{ts}.xlsx"

    CAT_ORDER = ["브랜드 키워드", "상품 키워드", "일반 키워드", "경쟁사 키워드"]

    # 예산외(not_selected) 키워드는 제안서 본문에서 제외
    # → 전체키워드 시트에는 남아있으므로 필요시 참고 가능
    rec_proposal = [r for r in recommended_rows if not r.get("not_selected", False)]
    rec_sorted = sorted(
        rec_proposal,
        key=lambda x: (
            CAT_ORDER.index(x.get("category", "일반 키워드"))
            if x.get("category", "일반 키워드") in CAT_ORDER else 99,
            -_safe_int(x.get("sim_cost", 0))
        )
    )

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    _write_proposal_sheet(wb.create_sheet("제안서"),    rec_sorted, advertiser, category_desc)
    _write_summary_sheet( wb.create_sheet("요약"),      rec_sorted, advertiser)
    _write_all_sheet(     wb.create_sheet("전체키워드"), rows)

    # 등록 대기 키워드 시트 추가 (검색량 없음)
    if standby_rows:
        _write_standby_sheet(wb.create_sheet("등록대기"), standby_rows, advertiser)

    # 확장 제안 시트 추가
    if scenario_data:
        _write_expanded_sheet(wb.create_sheet("확장제안"), scenario_data, advertiser, recommended_rows)

    wb.save(output_path)
    print(f"✅ 엑셀 저장 완료: {output_path}")


# ── 제안서 시트 ───────────────────────────────────────────────
# 컬럼 레이아웃 (A=여백, B~J=데이터):
#  B:키워드  C:구분  D:매체  E:입찰가  F:노출  G:클릭  H:비용  I:순위  J:비고
_PROP_LAST_COL = 10  # J

def _write_proposal_sheet(ws, rec_sorted, advertiser, category_desc):
    widths = {1:3, 2:26, 3:12, 4:5, 5:11, 6:10, 7:8, 8:12, 9:6, 10:8}
    for c, w in widths.items():
        ws.column_dimensions[get_column_letter(c)].width = w

    LAST = _PROP_LAST_COL
    LAST_L = get_column_letter(LAST)

    row = 1

    # 타이틀
    ws.merge_cells(f"B{row}:{LAST_L}{row}")
    _write_cell(ws, row, 2,
                f"■ {advertiser} 검색광고 캠페인 운영 제안",
                bold=True, bg=COLOR_TITLE_BG,
                font_color=COLOR_TITLE_FG, font_size=14, align_h="left")
    ws.row_dimensions[row].height = 24
    row += 2

    # 카테고리 전략 설명
    if isinstance(category_desc, dict):
        for i, (cat, desc) in enumerate(category_desc.items(), 1):
            ws.merge_cells(f"B{row}:{LAST_L}{row}")
            _write_cell(ws, row, 2, f"{i}. {cat}", bold=True, align_h="left")
            row += 1
            ws.merge_cells(f"B{row}:{LAST_L}{row}")
            _write_cell(ws, row, 2, f"   - {desc}",
                        font_size=9, font_color="595959", align_h="left")
            row += 1
        row += 1

    # 전체 요약 표 (TOTAL / PC / MO)
    ws.merge_cells(f"B{row}:D{row}")
    _write_cell(ws, row, 2, "* 예상 성과", bold=True, align_h="left")
    ws.merge_cells(f"H{row}:{LAST_L}{row}")
    _write_cell(ws, row, 8, "(VAT 포함가)", align_h="right")
    row += 1

    for i, h in enumerate(["구분","평균 입찰가","노출","클릭","CTR","비용","평균 순위"]):
        _write_cell(ws, row, 2+i, h, bold=True, bg=COLOR_HEADER_BG)
    row += 1

    def agg(lst): return int(sum(lst)/len(lst)) if lst else 0
    def ctr_val(c, i): return round(c/i, 4) if i > 0 else 0.0

    pc_bids, pc_imp, pc_clk, pc_cost, pc_rnk = [], [], [], [], []
    mo_bids, mo_imp, mo_clk, mo_cost, mo_rnk = [], [], [], [], []
    for r in rec_sorted:
        pc_bid_r = _safe_int(r.get("proposed_bid_pc", 0) or r.get("proposed_bid", 0))
        mo_bid_r = _safe_int(r.get("proposed_bid_mo", 0) or r.get("proposed_bid", 0))
        if _safe_int(r.get("pc_sim_impressions", 0)) > 0:
            pc_bids.append(pc_bid_r)
            pc_imp.append( _safe_int(r.get("pc_sim_impressions", 0)))
            pc_clk.append( _safe_int(r.get("pc_sim_clicks", 0)))
            pc_cost.append(_safe_int(r.get("pc_sim_cost", 0)))
            pc_rnk.append( _safe_int(r.get("proposed_rank_pc", 0)))
        if _safe_int(r.get("mo_sim_impressions", 0)) > 0:
            mo_bids.append(mo_bid_r)
            mo_imp.append( _safe_int(r.get("mo_sim_impressions", 0)))
            mo_clk.append( _safe_int(r.get("mo_sim_clicks", 0)))
            mo_cost.append(_safe_int(r.get("mo_sim_cost", 0)))
            mo_rnk.append( _safe_int(r.get("proposed_rank_mo", 0)))

    for label, bids, imp, clk, cost, rnk in [
        ("TOTAL", pc_bids+mo_bids, pc_imp+mo_imp, pc_clk+mo_clk, pc_cost+mo_cost, pc_rnk+mo_rnk),
        ("PC",    pc_bids, pc_imp, pc_clk, pc_cost, pc_rnk),
        ("MO",    mo_bids, mo_imp, mo_clk, mo_cost, mo_rnk),
    ]:
        _write_cell(ws, row, 2, label, bold=(label=="TOTAL"), bg=COLOR_SUBTOTAL_BG)
        _write_cell(ws, row, 3, agg(bids),                    bg=COLOR_SUBTOTAL_BG, num_fmt="#,##0")
        _write_cell(ws, row, 4, sum(imp),                     bg=COLOR_SUBTOTAL_BG, num_fmt="#,##0")
        _write_cell(ws, row, 5, sum(clk),                     bg=COLOR_SUBTOTAL_BG, num_fmt="#,##0")
        _write_cell(ws, row, 6, ctr_val(sum(clk), sum(imp)),  bg=COLOR_SUBTOTAL_BG, num_fmt="0.00%")
        _write_cell(ws, row, 7, sum(cost),                    bg=COLOR_SUBTOTAL_BG, num_fmt="#,##0")
        _write_cell(ws, row, 8, agg(rnk),                     bg=COLOR_SUBTOTAL_BG, num_fmt="#,##0.0")
        row += 1
    row += 1

    # 키워드별 상세 타이틀
    ws.merge_cells(f"B{row}:D{row}")
    _write_cell(ws, row, 2, "* 키워드별 상세 예상 성과", bold=True, align_h="left")
    ws.merge_cells(f"H{row}:{LAST_L}{row}")
    _write_cell(ws, row, 8, "(VAT 포함가)", align_h="right")
    row += 1

    # ── 카테고리별 키워드 출력 ─────────────────────────────
    CAT_ORDER = ["브랜드 키워드", "상품 키워드", "일반 키워드", "경쟁사 키워드"]
    cat_groups = {}
    for r in rec_sorted:
        cat_groups.setdefault(r.get("category", "일반 키워드"), []).append(r)

    for cat_num, cat in enumerate(CAT_ORDER, 1):
        if cat not in cat_groups:
            continue
        kws = cat_groups[cat]
        cc  = _cat_color(cat)

        # 카테고리 소제목
        ws.merge_cells(f"B{row}:{LAST_L}{row}")
        _write_cell(ws, row, 2, f"{cat_num}. {cat}",
                    bold=True, bg=cc, align_h="left")
        ws.row_dimensions[row].height = 16
        row += 1

        # 칼럼 헤더
        for _ci, _lbl in enumerate(["키워드","구분","매체","입찰가","노출","클릭","비용","순위","비고"]):
            _write_cell(ws, row, 2+_ci, _lbl, bold=True, bg=COLOR_HEADER_BG)
        ws.row_dimensions[row].height = 14
        row += 1

        for kw_row in kws:
            fb           = kw_row.get("is_fallback", False)
            not_selected = kw_row.get("not_selected", False)
            if fb:
                bg = COLOR_FALLBACK_BG
            elif not_selected:
                bg = "EEEEEE"
            else:
                bg = None

            pc_bid = _safe_int(kw_row.get("proposed_bid_pc", 0) or kw_row.get("proposed_bid", 0))
            mo_bid = _safe_int(kw_row.get("proposed_bid_mo", 0) or kw_row.get("proposed_bid", 0))

            pc_impr   = _safe_int(kw_row.get("pc_sim_impressions", 0))
            pc_clicks = _safe_int(kw_row.get("pc_sim_clicks", 0))
            pc_cost   = _safe_int(kw_row.get("pc_sim_cost", 0))
            pc_rank   = _safe_int(kw_row.get("proposed_rank_pc", 0))
            mo_impr   = _safe_int(kw_row.get("mo_sim_impressions", 0))
            mo_clicks = _safe_int(kw_row.get("mo_sim_clicks", 0))
            mo_cost   = _safe_int(kw_row.get("mo_sim_cost", 0))
            mo_rank   = _safe_int(kw_row.get("proposed_rank_mo", 0))

            show_pc = pc_bid > 0 or pc_impr > 0
            show_mo = mo_bid > 0 or mo_impr > 0
            if not show_pc and not show_mo:
                show_pc = True  # 최소 1행 표시

            has_perf      = not fb and not not_selected
            has_rank_only = fb and not not_selected

            def _v(val, is_rank=False):
                if has_perf:
                    return val if val else ""
                if has_rank_only and is_rank:
                    return val if val else ""
                return ""

            note = "입찰가제안" if fb else ("예산외" if not_selected else "")
            keyword_str  = kw_row.get("keyword", "")
            category_str = kw_row.get("category", "")

            num_rows = (1 if show_pc else 0) + (1 if show_mo else 0)
            first_data_row = row

            if show_pc:
                _write_cell(ws, row, 2, keyword_str,               bg=bg, align_h="left")
                _write_cell(ws, row, 3, category_str,              bg=bg)
                _write_cell(ws, row, 4, "PC",                      bg=bg, bold=True)
                _write_cell(ws, row, 5, pc_bid if pc_bid else "",  bg=bg, num_fmt="#,##0")
                _write_cell(ws, row, 6, _v(pc_impr),               bg=bg, num_fmt="#,##0")
                _write_cell(ws, row, 7, _v(pc_clicks),             bg=bg, num_fmt="#,##0")
                _write_cell(ws, row, 8, _v(pc_cost),               bg=bg, num_fmt="#,##0")
                _write_cell(ws, row, 9, _v(pc_rank, is_rank=True), bg=bg, num_fmt="#,##0")
                _write_cell(ws, row, 10, note if not show_mo else "", bg=bg)
                row += 1

            if show_mo:
                _write_cell(ws, row, 2, keyword_str,               bg=bg, align_h="left")
                _write_cell(ws, row, 3, category_str,              bg=bg)
                _write_cell(ws, row, 4, "MO",                      bg=bg, bold=True)
                _write_cell(ws, row, 5, mo_bid if mo_bid else "",  bg=bg, num_fmt="#,##0")
                _write_cell(ws, row, 6, _v(mo_impr),               bg=bg, num_fmt="#,##0")
                _write_cell(ws, row, 7, _v(mo_clicks),             bg=bg, num_fmt="#,##0")
                _write_cell(ws, row, 8, _v(mo_cost),               bg=bg, num_fmt="#,##0")
                _write_cell(ws, row, 9, _v(mo_rank, is_rank=True), bg=bg, num_fmt="#,##0")
                _write_cell(ws, row, 10, note,                     bg=bg)
                row += 1

            # keyword/category 열을 PC+MO 행에 걸쳐 병합 (둘 다 있을 때)
            if show_pc and show_mo:
                ws.merge_cells(f"B{first_data_row}:B{first_data_row+1}")
                ws.merge_cells(f"C{first_data_row}:C{first_data_row+1}")

        # 카테고리 소계
        c_pc_imp  = sum(_safe_int(r.get("pc_sim_impressions",0)) for r in kws)
        c_pc_clk  = sum(_safe_int(r.get("pc_sim_clicks",0))      for r in kws)
        c_pc_cost = sum(_safe_int(r.get("pc_sim_cost",0))        for r in kws)
        c_mo_imp  = sum(_safe_int(r.get("mo_sim_impressions",0)) for r in kws)
        c_mo_clk  = sum(_safe_int(r.get("mo_sim_clicks",0))      for r in kws)
        c_mo_cost = sum(_safe_int(r.get("mo_sim_cost",0))        for r in kws)

        ws.merge_cells(f"B{row}:C{row}")
        _write_cell(ws, row, 2, f"◀ {cat} 소계 ({len(kws)}개)", bold=True, bg=COLOR_SUBTOTAL_BG, align_h="left")
        _write_cell(ws, row, 4, "PC",        bold=True, bg=COLOR_SUBTOTAL_BG)
        _write_cell(ws, row, 5, "",          bg=COLOR_SUBTOTAL_BG)
        _write_cell(ws, row, 6, c_pc_imp,   bg=COLOR_SUBTOTAL_BG, num_fmt="#,##0")
        _write_cell(ws, row, 7, c_pc_clk,   bg=COLOR_SUBTOTAL_BG, num_fmt="#,##0")
        _write_cell(ws, row, 8, c_pc_cost,  bg=COLOR_SUBTOTAL_BG, num_fmt="#,##0")
        _write_cell(ws, row, 9, "",          bg=COLOR_SUBTOTAL_BG)
        _write_cell(ws, row, 10, "",         bg=COLOR_SUBTOTAL_BG)
        row += 1

        ws.merge_cells(f"B{row}:C{row}")
        _write_cell(ws, row, 2, "",          bg=COLOR_SUBTOTAL_BG)
        _write_cell(ws, row, 4, "MO",        bold=True, bg=COLOR_SUBTOTAL_BG)
        _write_cell(ws, row, 5, "",          bg=COLOR_SUBTOTAL_BG)
        _write_cell(ws, row, 6, c_mo_imp,   bg=COLOR_SUBTOTAL_BG, num_fmt="#,##0")
        _write_cell(ws, row, 7, c_mo_clk,   bg=COLOR_SUBTOTAL_BG, num_fmt="#,##0")
        _write_cell(ws, row, 8, c_mo_cost,  bg=COLOR_SUBTOTAL_BG, num_fmt="#,##0")
        _write_cell(ws, row, 9, "",          bg=COLOR_SUBTOTAL_BG)
        _write_cell(ws, row, 10, "",         bg=COLOR_SUBTOTAL_BG)
        row += 2

    # 전체 PC/MO 예산 합계
    total_pc_budget  = sum(_safe_int(r.get("pc_sim_cost", 0)) for r in rec_sorted)
    total_mo_budget  = sum(_safe_int(r.get("mo_sim_cost", 0)) for r in rec_sorted)
    total_budget_sum = total_pc_budget + total_mo_budget

    ws.merge_cells(f"B{row}:C{row}")
    _write_cell(ws, row, 2, "PC 캠페인 예산", bold=True, bg="E3F2FD", align_h="left")
    _write_cell(ws, row, 5, total_pc_budget,  bold=True, bg="E3F2FD", num_fmt="#,##0")
    row += 1
    ws.merge_cells(f"B{row}:C{row}")
    _write_cell(ws, row, 2, "MO 캠페인 예산", bold=True, bg="E8F5E9", align_h="left")
    _write_cell(ws, row, 5, total_mo_budget,  bold=True, bg="E8F5E9", num_fmt="#,##0")
    row += 1
    ws.merge_cells(f"B{row}:C{row}")
    _write_cell(ws, row, 2, "합계",            bold=True, bg=COLOR_SUBTOTAL_BG, align_h="left")
    _write_cell(ws, row, 5, total_budget_sum,  bold=True, bg=COLOR_SUBTOTAL_BG, num_fmt="#,##0")
    row += 2

    ws.merge_cells(f"B{row}:{LAST_L}{row}")
    _write_cell(ws, row, 2,
                "※ '추정' 표시 항목은 네이버 Estimate API 미지원 키워드로, 노출/클릭 데이터 기반 추정값입니다.",
                font_size=9, font_color="595959", italic=True, align_h="left")


# ── 요약 시트 ─────────────────────────────────────────────────
def _write_summary_sheet(ws, rec_sorted, advertiser):
    for col, w in {1:3, 2:26, 3:18, 4:18, 5:18}.items():
        ws.column_dimensions[get_column_letter(col)].width = w

    row = 1
    ws.merge_cells(f"B{row}:E{row}")
    _write_cell(ws, row, 2, f"■ {advertiser} SA 광고 제안 요약",
                bold=True, font_size=13, bg=COLOR_TITLE_BG,
                font_color=COLOR_TITLE_FG, align_h="left")
    ws.row_dimensions[row].height = 22
    row += 2

    _write_cell(ws, row, 2, "생성일시", bold=True, bg=COLOR_HEADER_BG)
    ws.merge_cells(f"C{row}:E{row}")
    _write_cell(ws, row, 3, datetime.now().strftime("%Y-%m-%d %H:%M"), align_h="left")
    row += 2

    total_kw      = len(rec_sorted)
    total_impr    = sum(_safe_int(r.get("sim_impressions",0))    for r in rec_sorted)
    total_clk     = sum(_safe_int(r.get("sim_clicks",0))         for r in rec_sorted)
    total_cost    = sum(_safe_int(r.get("sim_cost",0))           for r in rec_sorted)
    total_pc_clk  = sum(_safe_int(r.get("pc_sim_clicks",0))      for r in rec_sorted)
    total_mo_clk  = sum(_safe_int(r.get("mo_sim_clicks",0))      for r in rec_sorted)
    total_pc_cost = sum(_safe_int(r.get("pc_sim_cost",0))        for r in rec_sorted)
    total_mo_cost = sum(_safe_int(r.get("mo_sim_cost",0))        for r in rec_sorted)
    avg_cpc       = int(total_cost / total_clk) if total_clk > 0 else 0
    avg_ctr       = round(total_clk / total_impr, 4) if total_impr > 0 else 0.0
    fb_cnt        = sum(1 for r in rec_sorted if r.get("is_fallback", False))

    # 실제 운영 예산 = pc_sim_cost + mo_sim_cost (PC/MO 분리 캠페인 기준)
    real_total_cost = total_pc_cost + total_mo_cost

    for label, value, fmt in [
        ("제안 키워드 수",   total_kw,        "#,##0"),
        ("추정값 키워드 수", fb_cnt,          "#,##0"),
        ("예상 총 노출수",   total_impr,      "#,##0"),
        ("예상 총 클릭수",   total_clk,       "#,##0"),
        ("  ├ PC 클릭수",    total_pc_clk,    "#,##0"),
        ("  └ MO 클릭수",    total_mo_clk,    "#,##0"),
        ("평균 CPC",         avg_cpc,         "#,##0"),
        ("평균 CTR",         avg_ctr,         "0.00%"),
    ]:
        is_sub = "  " in label
        _write_cell(ws, row, 2, label, bold=not is_sub,
                    bg=COLOR_HEADER_BG if not is_sub else None)
        _write_cell(ws, row, 3, value, num_fmt=fmt, align_h="right")
        row += 1

    row += 1
    # 운영 예산 섹션 (PC/MO 캠페인 분리 기준)
    ws.merge_cells(f"B{row}:E{row}")
    _write_cell(ws, row, 2, "■ 운영 예산 (PC/MO 캠페인 분리 기준)",
                bold=True, align_h="left")
    row += 1

    ws.merge_cells(f"C{row}:E{row}")
    _write_cell(ws, row, 2, "PC 캠페인 예산", bold=True, bg=COLOR_HEADER_BG)
    _write_cell(ws, row, 3, total_pc_cost, num_fmt="#,##0", align_h="right",
                bg="E3F2FD", bold=True)
    row += 1

    ws.merge_cells(f"C{row}:E{row}")
    _write_cell(ws, row, 2, "MO 캠페인 예산", bold=True, bg=COLOR_HEADER_BG)
    _write_cell(ws, row, 3, total_mo_cost, num_fmt="#,##0", align_h="right",
                bg="E8F5E9", bold=True)
    row += 1

    ws.merge_cells(f"C{row}:E{row}")
    _write_cell(ws, row, 2, "합계", bold=True, bg=COLOR_SUBTOTAL_BG)
    _write_cell(ws, row, 3, real_total_cost, num_fmt="#,##0", align_h="right",
                bg=COLOR_SUBTOTAL_BG, bold=True)
    row += 1

    # 안내 문구
    ws.merge_cells(f"B{row}:E{row}")
    _write_cell(ws, row, 2,
                f"※ PC/MO 캠페인 분리 운영 기준입니다. 총 예산 내에서 PC {total_pc_cost:,}원 / MO {total_mo_cost:,}원으로 배분하여 운영하세요.",
                font_size=8, font_color="595959", italic=True, align_h="left")
    row += 1

    row += 1
    ws.merge_cells(f"B{row}:E{row}")
    _write_cell(ws, row, 2, "■ 카테고리별 예상 성과", bold=True, align_h="left")
    row += 1

    for i, h in enumerate(["카테고리","키워드수","예상클릭","예상비용"]):
        _write_cell(ws, row, 2+i, h, bold=True, bg=COLOR_HEADER_BG)
    row += 1

    CAT_ORDER = ["브랜드 키워드","상품 키워드","일반 키워드","경쟁사 키워드"]
    cat_groups = {}
    for r in rec_sorted:
        cat_groups.setdefault(r.get("category","일반 키워드"), []).append(r)

    for cat in CAT_ORDER:
        if cat not in cat_groups:
            continue
        kws = cat_groups[cat]
        bg  = _cat_color(cat)
        _write_cell(ws, row, 2, cat, bg=bg)
        _write_cell(ws, row, 3, len(kws), bg=bg, num_fmt="#,##0")
        _write_cell(ws, row, 4, sum(_safe_int(r.get("sim_clicks",0)) for r in kws), bg=bg, num_fmt="#,##0")
        _write_cell(ws, row, 5, sum(_safe_int(r.get("sim_cost",0))   for r in kws), bg=bg, num_fmt="#,##0")
        row += 1


# ── 전체키워드 시트 ───────────────────────────────────────────
def _write_all_sheet(ws, rows):
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 14
    for i in range(3, 15):
        ws.column_dimensions[get_column_letter(i)].width = 13

    # pc_impr/mo_impr = 월간 검색량(쿼리수), 광고 노출수 아님
    # pc_click/mo_click = 시장 전체 평균 클릭수 (키워드툴 API 기준)
    headers = ["키워드","카테고리","키워드유형","기본점수","추천점수","소스",
               "PC월검색량","MO월검색량","PC평균클릭(시장)","MO평균클릭(시장)","CTR",
               "경쟁도","기준입찰가","월검색량합계"]
    for i, h in enumerate(headers, 1):
        _write_cell(ws, 1, i, h, bold=True, bg=COLOR_HEADER_BG)

    for idx, r in enumerate(rows, 2):
        values = [
            r.get("keyword",""),
            r.get("category",""),
            r.get("keyword_type",""),
            _safe_int(r.get("score",0)),
            _safe_int(r.get("recommendation_score",0)),
            r.get("source",""),
            _safe_int(r.get("pc_impr",0)),
            _safe_int(r.get("mo_impr",0)),
            _safe_float(r.get("pc_click",0)),
            _safe_float(r.get("mo_click",0)),
            _safe_float(r.get("ctr",0)),
            r.get("competition",""),
            _safe_int(r.get("topOfPageBid",0)),
            _safe_int(r.get("monthlySearchVolume",0)),
        ]
        for ci, val in enumerate(values, 1):
            _write_cell(ws, idx, ci, val,
                        align_h="left" if ci <= 2 else "center",
                        font_size=9)

# ── 등록 대기 키워드 시트 ──────────────────────────────────────────────────
def _write_standby_sheet(ws, standby_rows, advertiser):
    """
    검색량이 없어서 성과 추정이 불가능한 키워드.
    브랜드/제품 인지도가 올라가면 자동으로 노출되기 시작하는 키워드들.
    입찰가만 등록해두는 '씨앗 키워드' 개념.
    """
    for col, w in {1:3, 2:35, 3:18, 4:12}.items():
        ws.column_dimensions[get_column_letter(col)].width = w

    row = 1

    # 타이틀
    ws.merge_cells(f"B{row}:D{row}")
    _write_cell(ws, row, 2,
                f"▪ {advertiser} 등록 대기 키워드",
                bold=True, bg=COLOR_TITLE_BG,
                font_color=COLOR_TITLE_FG, font_size=13, align_h="left")
    ws.row_dimensions[row].height = 22
    row += 1

    # 안내문
    ws.merge_cells(f"B{row}:D{row}")
    _write_cell(ws, row, 2,
                "현재 검색량이 없어 예상 성과 산출이 불가한 키워드입니다. ",
                font_size=9, font_color="595959", italic=True, align_h="left")
    row += 1
    ws.merge_cells(f"B{row}:D{row}")
    _write_cell(ws, row, 2,
                "브랜드/제품 인지도 상승 시 자연스럽게 검색량이 발생하므로 사전에 등록해두는 것을 권장합니다.",
                font_size=9, font_color="595959", italic=True, align_h="left")
    row += 2

    # 카테고리별 정렬
    CAT_ORDER = ["브랜드 키워드", "상품 키워드", "일반 키워드", "경쟁사 키워드"]
    cat_groups = {}
    for r in standby_rows:
        cat = r.get("category", "일반 키워드")
        cat_groups.setdefault(cat, []).append(r)

    total = 0
    for cat in CAT_ORDER:
        if cat not in cat_groups:
            continue
        kws = cat_groups[cat]
        cc  = _cat_color(cat)

        # 카테고리 소제목
        ws.merge_cells(f"B{row}:D{row}")
        _write_cell(ws, row, 2, cat,
                    bold=True, bg=cc, align_h="left")
        ws.row_dimensions[row].height = 16
        row += 1

        # 헤더
        for col, label in [(2, "키워드"), (3, "구분"), (4, "권장입찰가")]:
            _write_cell(ws, row, col, label, bold=True, bg=COLOR_HEADER_BG)
        row += 1

        for kw_row in sorted(kws, key=lambda x: x.get("keyword", "")):
            _write_cell(ws, row, 2, kw_row.get("keyword", ""), align_h="left")
            _write_cell(ws, row, 3, cat)
            _write_cell(ws, row, 4, 70, num_fmt="#,##0")  # 최소 입찰가 70원
            row += 1
            total += 1

        # 소계 (키워드 칼럼 비워서 오인 방지)
        _write_cell(ws, row, 2, "", bg=COLOR_SUBTOTAL_BG, align_h="left")
        _write_cell(ws, row, 3, f"◀ {cat} 소계 ({len(kws)}개)",
                    bold=True, bg=COLOR_SUBTOTAL_BG, align_h="left")
        _write_cell(ws, row, 4, "", bg=COLOR_SUBTOTAL_BG)
        row += 2

    # 합계
    ws.merge_cells(f"B{row}:D{row}")
    _write_cell(ws, row, 2,
                f"총 {total}개 키워드 | 검색량 발생 시 자동 노출 시작",
                bold=True, bg=COLOR_SUBTOTAL_BG, align_h="left")


# ── 확장 제안 시트 (개편) ──────────────────────────────────────────────────
def _write_expanded_sheet(ws, scenario_data, advertiser, recommended_rows):
    """
    3섹션 구성:
      섹션 1: 예산 시나리오 비교 (현재/+40%/+100%)
      섹션 2: 예산 추가시 진입 가능한 신규 키워드
      섹션 3: 현재 키워드 중 입찰가 올리면 좋은 것들
    """
    for col, w in {1:3, 2:32, 3:12, 4:10, 5:10, 6:9, 7:9, 8:9, 9:9, 10:8, 11:8, 12:10, 13:10}.items():
        ws.column_dimensions[get_column_letter(col)].width = w

    bid_up_rows = scenario_data.get("bid_up_rows", [])
    new_kw_rows = scenario_data.get("new_kw_rows", [])
    scenarios   = scenario_data.get("scenarios", [])

    row = 1

    # ── 타이틀 ──
    ws.merge_cells(f"B{row}:J{row}")
    _write_cell(ws, row, 2, f"▪ {advertiser} 확장 제안",
                bold=True, bg=COLOR_TITLE_BG, font_color=COLOR_TITLE_FG,
                font_size=13, align_h="left")
    ws.row_dimensions[row].height = 22
    row += 1
    ws.merge_cells(f"B{row}:J{row}")
    _write_cell(ws, row, 2,
                "현재 예산 기준 제안과 예산 확대 시 추가 효과를 시나리오별로 비교합니다.",
                font_size=9, font_color="595959", italic=True, align_h="left")
    row += 2

    # ══════════════════════════════════════════════
    # 섹션 1: 예산 시나리오 비교
    # ══════════════════════════════════════════════
    ws.merge_cells(f"B{row}:J{row}")
    _write_cell(ws, row, 2, "▶ SECTION 1. 예산 시나리오 비교",
                bold=True, bg="1F4E79", font_color="FFFFFF", font_size=11, align_h="left")
    ws.row_dimensions[row].height = 20
    row += 1

    # 헤더
    for col, label in [(2,"시나리오"), (3,"예산"), (4,"총 키워드"), (5,"예상 클릭"), (6,"예상 비용"),
                        (7,"추가 키워드"), (8,"추가 클릭"), (9,"클릭 증가율")]:
        _write_cell(ws, row, col, label, bold=True, bg=COLOR_HEADER_BG)
    row += 1

    base_clicks = scenarios[0]["clicks"] if scenarios else 1
    for i, sc in enumerate(scenarios):
        bg = "E8F5E9" if i == 0 else ("FFF9C4" if i == 1 else "FFF3E0")
        click_rate = f"+{(sc['clicks']/base_clicks - 1)*100:.0f}%" if i > 0 else "기준"
        _write_cell(ws, row, 2, sc["label"],       bg=bg, align_h="left", bold=(i==0))
        _write_cell(ws, row, 3, sc["budget"],      bg=bg, num_fmt="#,##0")
        _write_cell(ws, row, 4, sc["kw_count"],    bg=bg, num_fmt="#,##0")
        _write_cell(ws, row, 5, sc["clicks"],      bg=bg, num_fmt="#,##0")
        _write_cell(ws, row, 6, sc["cost"],        bg=bg, num_fmt="#,##0")
        _write_cell(ws, row, 7, sc["add_kws"] if i > 0 else "-",    bg=bg)
        _write_cell(ws, row, 8, sc["add_clicks"] if i > 0 else "-", bg=bg, num_fmt="#,##0")
        _write_cell(ws, row, 9, click_rate,        bg=bg, bold=(i>0))
        row += 1
    row += 2

    # ══════════════════════════════════════════════
    # 섹션 2: 신규 진입 가능 키워드
    # ══════════════════════════════════════════════
    # 현재 제안 비용 (섹션1 첫번째 시나리오)
    cur_cost = scenarios[0]["cost"] if scenarios else 0
    ws.merge_cells(f"B{row}:J{row}")
    _write_cell(ws, row, 2, "▶ SECTION 2. 예산 확대 시 신규 진입 가능 키워드",
                bold=True, bg="1F4E79", font_color="FFFFFF", font_size=11, align_h="left")
    ws.row_dimensions[row].height = 20
    row += 1
    ws.merge_cells(f"B{row}:J{row}")
    _write_cell(ws, row, 2,
                "현재 예산 초과로 제외된 키워드입니다. 예산 추가 시 우선순위 순으로 진입을 권장합니다.",
                font_size=9, font_color="595959", italic=True, align_h="left")
    row += 1

    if not new_kw_rows:
        ws.merge_cells(f"B{row}:J{row}")
        _write_cell(ws, row, 2, "신규 진입 가능 키워드가 없습니다.", font_color="888888", align_h="left")
        row += 2
    else:
        # 헤더
        # 시나리오 라벨 추출 (2번째, 3번째 시나리오)
        sc_labels = [sc["label"] for sc in scenarios[1:3]] if len(scenarios) > 1 else []
        sc_budgets = [sc["budget"] for sc in scenarios[1:3]] if len(scenarios) > 1 else []

        for col, label in [(2,"키워드"), (3,"구분"), (4,"PC입찰가"), (5,"MO입찰가"),
                            (6,"PC클릭"), (7,"MO클릭"), (8,"PC비용"), (9,"MO비용"),
                            (10,"PC순위"), (11,"MO순위")]:
            _write_cell(ws, row, col, label, bold=True, bg=COLOR_HEADER_BG)
        # 시나리오별 포함여부 헤더
        for i, sc_label in enumerate(sc_labels):
            _write_cell(ws, row, 12+i, sc_label, bold=True, bg="FFF9C4")
        row += 1

        # 카테고리별로 묶어서 출력
        CAT_ORDER = ["브랜드 키워드", "상품 키워드", "일반 키워드", "경쟁사 키워드"]
        cat_groups = {}
        for r in new_kw_rows:
            cat = r.get("category", "일반 키워드")
            cat_groups.setdefault(cat, []).append(r)

        cumul_cost = 0
        cumul_kw   = 0
        # 시나리오별 누적 비용: 카테고리를 넘어 전체 누적으로 포함여부 판단
        sc_cumul_carry = [0] * len(sc_budgets)

        for cat in CAT_ORDER:
            if cat not in cat_groups:
                continue
            kws = cat_groups[cat]
            cc  = _cat_color(cat)
            ws.merge_cells(f"B{row}:J{row}")
            _write_cell(ws, row, 2, cat, bold=True, bg=cc, align_h="left")
            row += 1

            for kw_row in kws:
                kw_cost = kw_row.get("pc_cost", 0) + kw_row.get("mo_cost", 0)
                cumul_cost += kw_cost
                cumul_kw   += 1

                # 시나리오별 포함 여부 계산
                # 현재 예산에서 각 시나리오 추가 예산 내에 들어오는지
                sc_status = []
                for i, sc_budget in enumerate(sc_budgets):
                    add_budget = sc_budget - cur_cost  # 추가 가능 예산
                    sc_cumul_carry[i] += kw_cost
                    if sc_cumul_carry[i] <= add_budget:
                        sc_status.append(("포함", "E8F5E9"))   # 초록
                    else:
                        sc_status.append(("예산초과", "FFEBEE"))  # 빨강

                _write_cell(ws, row, 2, kw_row.get("keyword", ""),     align_h="left")
                _write_cell(ws, row, 3, cat)
                _write_cell(ws, row, 4, kw_row.get("pc_bid", 0),       num_fmt="#,##0")
                _write_cell(ws, row, 5, kw_row.get("mo_bid", 0),       num_fmt="#,##0")
                _write_cell(ws, row, 6, kw_row.get("pc_clicks", 0),    num_fmt="#,##0")
                _write_cell(ws, row, 7, kw_row.get("mo_clicks", 0),    num_fmt="#,##0")
                _write_cell(ws, row, 8, kw_row.get("pc_cost", 0),      num_fmt="#,##0")
                _write_cell(ws, row, 9, kw_row.get("mo_cost", 0),      num_fmt="#,##0")
                _write_cell(ws, row, 10, kw_row.get("rank_pc", "-"))
                _write_cell(ws, row, 11, kw_row.get("rank_mo", "-"))
                for i, (status, bg) in enumerate(sc_status):
                    _write_cell(ws, row, 12 + i, status, bg=bg, bold=(status == "포함"))
                row += 1

        # 소계
        _write_cell(ws, row, 2, f"신규 진입 키워드 합계: {cumul_kw}개",
                    bold=True, bg=COLOR_SUBTOTAL_BG, align_h="left")
        ws.merge_cells(f"C{row}:G{row}")
        _write_cell(ws, row, 3, f"추가 예상 비용: {cumul_cost:,}원",
                    bold=True, bg=COLOR_SUBTOTAL_BG, align_h="left")
        row += 2

    # ══════════════════════════════════════════════
    # 섹션 3: 입찰가 올리면 좋은 키워드
    # ══════════════════════════════════════════════
    ws.merge_cells(f"B{row}:J{row}")
    _write_cell(ws, row, 2, "▶ SECTION 3. 입찰가 상향 시 순위 개선 가능 키워드",
                bold=True, bg="1F4E79", font_color="FFFFFF", font_size=11, align_h="left")
    ws.row_dimensions[row].height = 20
    row += 1
    ws.merge_cells(f"B{row}:J{row}")
    _write_cell(ws, row, 2,
                "현재 집행 중인 키워드 중 입찰가를 올리면 순위 개선 효과가 있는 키워드입니다.",
                font_size=9, font_color="595959", italic=True, align_h="left")
    row += 1

    if not bid_up_rows:
        ws.merge_cells(f"B{row}:J{row}")
        _write_cell(ws, row, 2, "입찰가 상향 추천 키워드가 없습니다.", font_color="888888", align_h="left")
        row += 2
    else:
        # 헤더
        for col, label in [(2,"키워드"), (3,"구분"),
                            (4,"현재 PC입찰가"), (5,"현재 MO입찰가"), (6,"현재 PC순위"), (7,"현재 MO순위"),
                            (8,"권장 PC입찰가"), (9,"권장 MO입찰가"), (10,"예상 PC순위"), (11,"예상 MO순위")]:
            _write_cell(ws, row, col, label, bold=True, bg=COLOR_HEADER_BG)
        row += 1

        for kw_row in sorted(bid_up_rows, key=lambda x: x.get("category","")):
            cat = kw_row.get("category","")
            cc  = _cat_color(cat)
            improved = kw_row.get("rank_pc", 5) < (kw_row.get("cur_pc_rank") or 5)
            bg = "E8F5E9" if improved else None
            _write_cell(ws, row, 2, kw_row.get("keyword",""),         bg=bg, align_h="left")
            _write_cell(ws, row, 3, cat,                               bg=bg)
            _write_cell(ws, row, 4, kw_row.get("cur_pc_bid", 0),      bg=bg, num_fmt="#,##0")
            _write_cell(ws, row, 5, kw_row.get("cur_mo_bid", 0),      bg=bg, num_fmt="#,##0")
            _write_cell(ws, row, 6, kw_row.get("cur_pc_rank", "-"),   bg=bg)
            _write_cell(ws, row, 7, kw_row.get("cur_mo_rank", "-"),   bg=bg)
            _write_cell(ws, row, 8, kw_row.get("pc_bid", 0),          bg=bg, num_fmt="#,##0", bold=True)
            _write_cell(ws, row, 9, kw_row.get("mo_bid", 0),          bg=bg, num_fmt="#,##0", bold=True)
            _write_cell(ws, row, 10, kw_row.get("rank_pc", "-"),      bg=bg, bold=improved)
            _write_cell(ws, row, 11, kw_row.get("rank_mo", "-"),      bg=bg, bold=improved)
            row += 1