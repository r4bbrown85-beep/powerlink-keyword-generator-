# -*- coding: utf-8 -*-
"""네이버 GFA / SA 월 목표 → 일별 필요 매출 시뮬레이터.

매달 네이버에서 월 목표가 내려오면 이 모듈로 "일별로 얼마씩 해야 목표를 달성하는가"를 산출한다.

    from agent.naver_target_simulator import NaverTargetSimulator

    sim = NaverTargetSimulator.load(refresh=True)        # 전월 실적까지 반영
    sim.report("2026-11", gfa_target=3_800_000_000, sa_target=950_000_000)

→ C:\\Users\\Administrator\\Desktop\\00. 클로드코드 생성물\\네이버 일단위 매출 트래킹\\
   네이버_2026-11_일별목표_MMDD기준.xlsx

월 중간에 다시 돌리면 그때까지의 실적을 반영해 잔여일 필요액을 재배분한다(as_of 자동 감지).

────────────────────────────────────────────────────────────────────────
일별 배분 방식 — 전부 실측 검증으로 결정했다 (validate() 로 재현)

 ■ GFA: 균등 배분
   일별 점유율 예측 오차(MAE) 비교 — 균등 38.4bp / 공휴일보정 38.4 / 공휴일+요일 38.5 /
   전년동월형태 42.7 / 전체월평균형태 37.6. 21개월 중 11개월에서 균등이 최선이었다.
   => 월내 형태(상순 0.948·하순 1.051)는 세일이 있던 달(3·6·10월)에서만 나온 평균적 경향이고
      11월은 상순 1.089 > 하순 0.984, 12월은 중순이 최고라 월별로 방향이 뒤집힌다.
      특정 월에 이 형태를 적용하면 오차가 커진다.

 ■ SA: 요일지수 × 공휴일계수
   균등 25.2bp / 공휴일보정 25.5 / 공휴일+요일 23.0 → 요일 보정이 9% 개선. 7개월 중 5개월 최선.
   요일지수 일 1.068 · 월 1.057 · 금 0.924 (쇼핑검색 주말 수요), 공휴일 1.063(영향 없음).

 ■ 월 총량 전망(참고용)은 "월초 N일 평균 × 배수 분포"
   21개월 leave-one-month-out: GFA N=4 MAPE 15.3%(최악 42%) / N=7 14.3% / N=10 12.9% /
   N=14 9.3% / N=21 5.8%. SA는 N=4에 이미 7.3%.
   => 월초 전망은 방향성용이고 14일 누적 시점에 재산출해야 한다.

 ■ 쓰지 않기로 한 것
   요일·월내위치·공휴일 완전분해 모델(agent/revenue_forecast.py 백테스트에서
   MAPE 11.56% vs 단순 최근7일 9.47%로 열등). revenue_forecast.forecast_month_end()는
   '월말 며칠 남았을 때' 전용이라 월초 호출 시 동작하지 않는다.

 ■ 세일 구간(참고 정보로만 제공)
   월중위 대비 120%+ 3일 이상 기준 2025-01~2026-10에 9건. 7건이 21일 이후 시작
   (시작일 중위 26일), 상승률 중위 +28.3%. 6월 넵다세일(6/22~6/30) 때 SA는 무반응
   => 세일은 GFA 전용 변수. 일별 목표 배분에는 넣지 않고(예측 불가) 체크포인트로만 안내한다.
────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import json
import os
import re
from calendar import monthrange
from datetime import date, timedelta
from statistics import mean, median

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_PATH = os.path.join(BASE_DIR, "data", "cache", "naver_target_sim.json")
SHEET_ID = "1V-gAyGok-H29rzXtvpE5UTFjhh-DYNbL6SW74dBrwNs"
TOKEN_PATH = os.path.join(BASE_DIR, "config", "briefing_token.json")
OUT_DIR = r"C:\Users\Administrator\Desktop\00. 클로드코드 생성물\네이버 일단위 매출 트래킹"
EPOCH = date(1899, 12, 30)
WD = ["월", "화", "수", "목", "금", "토", "일"]
MIN_MONTH_DAYS = 25


# ══════════════════════════════════════════════════════════════════
# 데이터 로딩
# ══════════════════════════════════════════════════════════════════
def _svc():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    creds = Credentials.from_authorized_user_file(TOKEN_PATH)  # scopes 생략(공유토큰 규칙)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_PATH, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
    return build("sheets", "v4", credentials=creds)


def _date_in(row, maxc=3):
    for j in range(min(maxc, len(row))):
        v = row[j]
        if isinstance(v, (int, float)) and 44000 < v < 48000:
            return EPOCH + timedelta(days=int(v))
    return None


def fetch_from_sheet() -> dict:
    """매출현황 스프레드시트 월별 탭에서 일별 GFA/SA/테무를 수집.

    탭 이름(`25년 10월 매출 현황` / `26년 9월 네이버 매출 현황` / `25년 4-5월 매출 현황`)과
    일별표 헤더 행 위치(29·30·39행)가 월마다 달라 둘 다 동적 탐색한다. 대시보드에도 'GFA'
    라벨이 있으므로 바로 아래에 날짜 시리얼이 오는 행만 헤더로 인정한다.
    """
    svc = _svc()
    titles = [s["properties"]["title"] for s in svc.spreadsheets().get(
        spreadsheetId=SHEET_ID, fields="sheets(properties(title))").execute()["sheets"]]

    targets = []
    for t in titles:
        m = re.match(r"^(\d{2})년\s*(\d{1,2})월\s*(네이버\s*)?매출 현황$", t.strip())
        if m:
            targets.append((2000 + int(m.group(1)), [int(m.group(2))], t))
            continue
        m = re.match(r"^(\d{2})년\s*(\d{1,2})-(\d{1,2})월\s*매출 현황$", t.strip())
        if m:
            targets.append((2000 + int(m.group(1)), [int(m.group(2)), int(m.group(3))], t))

    series, holidays = {}, {}
    for yr, mths, tab in sorted(targets):
        try:
            rows = svc.spreadsheets().values().get(
                spreadsheetId=SHEET_ID, range=f"'{tab}'!A1:V90",
                valueRenderOption="UNFORMATTED_VALUE").execute().get("values", [])
        except Exception:
            continue
        hidx = None
        for i, row in enumerate(rows):
            if any(isinstance(c, str) and c.strip() == "GFA" for c in row) and \
                    any(_date_in(rows[k]) for k in range(i + 1, min(i + 4, len(rows)))):
                hidx = i
                break
        if hidx is None:
            continue
        cols = {}
        for j, c in enumerate(rows[hidx]):
            if isinstance(c, str):
                s = c.strip()
                if s == "GFA":
                    cols["GFA"] = j
                elif s.startswith("SA"):
                    cols["SA"] = j
                elif s.replace(" ", "") in ("테무_GFA", "테무GFA"):
                    cols["TG"] = j
                elif s.replace(" ", "") in ("테무_SA", "테무SA"):
                    cols["TS"] = j
        for row in rows[hidx + 1:]:
            d = _date_in(row)
            if d is None or d.year != yr or d.month not in mths:
                continue

            def num(key):
                c = cols.get(key)
                if c is None or c >= len(row):
                    return None
                v = row[c]
                return float(v) if isinstance(v, (int, float)) else None

            g = num("GFA")
            if not g:
                continue
            series[d.isoformat()] = {"GFA": g, "SA": num("SA"), "TG": num("TG"), "TS": num("TS")}

    for row in svc.spreadsheets().values().get(
            spreadsheetId=SHEET_ID, range="'★공휴일'!A1:D300").execute().get("values", []):
        if len(row) >= 3 and re.match(r"^20\d\d", str(row[0]).strip()):
            try:
                p = [int(x) for x in re.findall(r"\d+", str(row[0]))]
                holidays[date(p[0], p[1], p[2]).isoformat()] = str(row[2]).strip()
            except Exception:
                pass
    return {"series": series, "holidays": holidays}


# ══════════════════════════════════════════════════════════════════
class NaverTargetSimulator:
    def __init__(self, series: dict, holidays: dict):
        self.G = {date.fromisoformat(k): v["GFA"] for k, v in series.items() if v.get("GFA")}
        self.S = {date.fromisoformat(k): v["SA"] for k, v in series.items() if v.get("SA")}
        self.TG = {date.fromisoformat(k): v["TG"] for k, v in series.items() if v.get("TG")}
        self.HOL = {date.fromisoformat(k): v for k, v in holidays.items()}
        self.fit()

    @classmethod
    def load(cls, refresh: bool = False) -> "NaverTargetSimulator":
        if not refresh and os.path.exists(CACHE_PATH):
            with open(CACHE_PATH, encoding="utf-8") as f:
                raw = json.load(f)
        else:
            raw = fetch_from_sheet()
            os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
            with open(CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(raw, f, ensure_ascii=False)
        return cls(raw["series"], raw["holidays"])

    # ---------------- 학습 ----------------
    def _src(self, metric):
        return self.G if metric == "GFA" else self.S

    def _full_months(self, metric="GFA"):
        src = self._src(metric)
        out = []
        for y, m in sorted({(d.year, d.month) for d in src}):
            days = sorted(d for d in src if d.year == y and d.month == m)
            if len(days) >= MIN_MONTH_DAYS:
                out.append((y, m, days))
        return out

    def fit(self):
        # 월 총량 전망용 배수 분포
        self.ratios = {}
        for metric in ("GFA", "SA"):
            src = self._src(metric)
            self.ratios[metric] = {}
            for n in (4, 7, 10, 14, 21):
                vals = [mean(src[d] for d in days) / mean(src[d] for d in days[:n])
                        for _, _, days in self._full_months(metric) if len(days) >= n + 3]
                self.ratios[metric][n] = sorted(vals)

        # SA 요일지수 / 공휴일계수 (GFA는 균등 배분이라 불필요하나 참고용으로 둘 다 계산)
        self.wd, self.hol_coef = {}, {}
        for metric in ("GFA", "SA"):
            src = self._src(metric)
            wd = {i: [] for i in range(7)}
            hr = []
            for y, m, days in self._full_months(metric):
                ok = [d for d in days if d not in self.HOL]
                if not ok:
                    continue
                avg = mean(src[d] for d in ok)
                if not avg:
                    continue
                for d in ok:
                    wd[d.weekday()].append(src[d] / avg)
                for d in days:
                    if d in self.HOL and d.weekday() < 5:
                        same = [x for x in ok if x.weekday() == d.weekday()]
                        if same:
                            hr.append(src[d] / mean(src[x] for x in same))
            self.wd[metric] = {i: (mean(v) if v else 1.0) for i, v in wd.items()}
            self.hol_coef[metric] = median(hr) if hr else 1.0

        # 세일 구간(참고 정보)
        self.sales = []
        for y, m, days in self._full_months("GFA"):
            b = median(self.G[d] for d in days)
            hot = [d for d in days if self.G[d] / b >= 1.20]
            if not hot:
                continue
            grp, cur = [], [hot[0]]
            for p, n in zip(hot, hot[1:]):
                (cur.append(n) if (n - p).days <= 1 else (grp.append(cur), cur.clear(), cur.append(n)))
            grp.append(list(cur))
            for g in grp:
                if len(g) >= 3:
                    self.sales.append({"start": g[0], "end": g[-1], "days": len(g),
                                       "lift": mean(self.G[d] for d in g) / b - 1})
        self.sale_lift = median([s["lift"] for s in self.sales]) if self.sales else 0.0
        self.sale_start = median([s["start"].day for s in self.sales]) if self.sales else 26

    # ---------------- 일별 가중치 (검증 결과 반영) ----------------
    def weights(self, days, metric):
        """GFA는 균등, SA는 요일지수×공휴일계수. 합이 1이 되도록 정규화."""
        if metric == "GFA":
            w = {d: 1.0 for d in days}
        else:
            hc = self.hol_coef["SA"]
            w = {d: self.wd["SA"][d.weekday()] * (hc if (d in self.HOL and d.weekday() < 5) else 1.0)
                 for d in days}
        s = sum(w.values()) or 1.0
        return {d: v / s for d, v in w.items()}

    # ---------------- 검증 ----------------
    def backtest(self, metric="GFA"):
        """월 총량 전망(월초 N일 × 배수) 오차."""
        src = self._src(metric)
        months = self._full_months(metric)
        out = []
        for n in (4, 7, 10, 14, 21):
            errs = []
            for i, (y, m, days) in enumerate(months):
                if len(days) < n + 3:
                    continue
                others = [mean(src[d] for d in dd) / mean(src[d] for d in dd[:n])
                          for j, (_, _, dd) in enumerate(months) if j != i and len(dd) >= n + 3]
                if not others:
                    continue
                pred = mean(src[d] for d in days[:n]) * median(others)
                act = mean(src[d] for d in days)
                errs.append((pred - act) / act)
            if errs:
                out.append({"N": n, "MAPE%": mean(abs(e) for e in errs) * 100,
                            "최악%": max(abs(e) for e in errs) * 100, "n": len(errs)})
        return out

    def validate_weights(self, metric="GFA"):
        """일별 배분 방식 비교(균등 vs 공휴일 vs 공휴일+요일). 단위 bp."""
        src = self._src(metric)
        months = self._full_months(metric)
        acc = {"균등": [], "공휴일": [], "공휴일+요일": []}
        for k, (y, m, days) in enumerate(months):
            tot = sum(src[d] for d in days)
            act = {d: src[d] / tot for d in days}
            ok = [d for d in days if d not in self.HOL]
            hr, wd = [], {i: [] for i in range(7)}
            for j, (_, _, dd) in enumerate(months):
                if j == k:
                    continue
                o2 = [d for d in dd if d not in self.HOL]
                if not o2:
                    continue
                a2 = mean(src[d] for d in o2)
                for d in o2:
                    wd[d.weekday()].append(src[d] / a2)
                for d in dd:
                    if d in self.HOL and d.weekday() < 5:
                        sm = [x for x in o2 if x.weekday() == d.weekday()]
                        if sm:
                            hr.append(src[d] / mean(src[x] for x in sm))
            hc = median(hr) if hr else 1.0
            wdi = {i: (mean(v) if v else 1.0) for i, v in wd.items()}

            def norm(w):
                s = sum(w.values())
                return {d: v / s for d, v in w.items()}

            cand = {
                "균등": norm({d: 1.0 for d in days}),
                "공휴일": norm({d: (hc if (d in self.HOL and d.weekday() < 5) else 1.0) for d in days}),
                "공휴일+요일": norm({d: (hc if (d in self.HOL and d.weekday() < 5) else 1.0)
                                 * wdi[d.weekday()] for d in days}),
            }
            for nm, p in cand.items():
                acc[nm].append(mean(abs(p[d] - act[d]) for d in days))
        return {nm: mean(v) * 10000 for nm, v in acc.items()}

    # ---------------- 시뮬레이션 ----------------
    def simulate(self, month: str, gfa_target: float | None = None,
                 sa_target: float | None = None, as_of: str | None = None) -> dict:
        y, m = (int(x) for x in month.split("-"))
        ndays = monthrange(y, m)[1]
        all_days = [date(y, m, i + 1) for i in range(ndays)]
        asof = date.fromisoformat(as_of) if as_of else None

        out = {"month": month, "ndays": ndays, "metrics": {},
               "sale": {"start_day": int(self.sale_start), "lift": self.sale_lift,
                        "n": len(self.sales)}}

        for metric, target in (("GFA", gfa_target), ("SA", sa_target)):
            if not target:
                continue
            src = self._src(metric)
            done = [d for d in all_days if d in src and (asof is None or d <= asof)]
            remain = [d for d in all_days if d not in done]
            cum = sum(src[d] for d in done)
            need = target - cum
            w = self.weights(remain, metric) if remain else {}

            # 참고 전망: 월초 N일 실적이 있으면 배수 분포 적용
            proj = {}
            if done:
                avg_done = cum / len(done)
                ns = [n for n in self.ratios[metric] if self.ratios[metric][n]]
                n_use = min(ns, key=lambda n: abs(n - len(done)))
                dist = self.ratios[metric][n_use]
                qf = lambda p: dist[min(len(dist) - 1, int(len(dist) * p))]
                proj = {"n_use": n_use, "avg_done": avg_done,
                        "P10": avg_done * qf(0.10) * ndays,
                        "P50": avg_done * median(dist) * ndays,
                        "P90": avg_done * qf(0.90) * ndays}

            # 전년 동월 실적
            prev = [d for d in src if d.year == y - 1 and d.month == m]
            prev_tot = sum(src[d] for d in prev) if len(prev) >= MIN_MONTH_DAYS else None

            rows = []
            run = cum
            for d in all_days:
                if d in done:
                    rows.append({"date": d, "actual": src[d], "need": None,
                                 "cum_need": None, "actual_cum": run + src[d]})
                    run += src[d]
                else:
                    v = need * w[d]
                    run += v
                    rows.append({"date": d, "actual": None, "need": v,
                                 "cum_need": run, "actual_cum": None})

            out["metrics"][metric] = {
                "target": target, "cum_done": cum, "n_done": len(done), "n_remain": len(remain),
                "need": need, "need_daily": need / len(remain) if remain else 0,
                "daily_even": target / ndays, "rows": rows, "proj": proj,
                "prev_total": prev_tot,
                "prev_daily": (prev_tot / len(prev)) if prev_tot else None,
                "weight_mode": "균등" if metric == "GFA" else "요일지수×공휴일계수",
            }
            bt = {x["N"]: x for x in self.backtest(metric)}
            if done and bt:
                out["metrics"][metric]["accuracy"] = bt[min(bt, key=lambda n: abs(n - len(done)))]
        return out

    # ---------------- 산출물 ----------------
    def report(self, month: str, gfa_target: float | None = None,
               sa_target: float | None = None, as_of: str | None = None,
               out_path: str | None = None) -> str:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter

        r = self.simulate(month, gfa_target, sa_target, as_of)
        if out_path is None:
            tag = (as_of or date.today().isoformat()).replace("-", "")[4:]
            out_path = os.path.join(OUT_DIR, f"네이버_{month}_일별목표_{tag}기준.xlsx")

        HF = PatternFill("solid", fgColor="4F81BD"); HFONT = Font(bold=True, color="FFFFFF", size=11)
        YF = PatternFill("solid", fgColor="FFFF99"); AF = PatternFill("solid", fgColor="BDD7EE")
        BF = PatternFill("solid", fgColor="DEEAF1"); GF = PatternFill("solid", fgColor="E2EFDA")
        B = Font(bold=True, size=11); NM = Font(size=11)
        TH = Border(*[Side(style="thin", color="BFBFBF")] * 4)
        M, PC = "#,##0", "0.0%"

        def put(ws, i, j, v, font=NM, fill=None, fmt=None, bd=True):
            c = ws.cell(i, j, v); c.font = font
            if fill: c.fill = fill
            if fmt: c.number_format = fmt
            if bd: c.border = TH
            return c

        def head(ws, i, cols):
            for j, h in enumerate(cols, start=1):
                put(ws, i, j, h, HFONT, HF)
            return i + 1

        def note(ws, i, t, w, h=36):
            c = ws.cell(i, 1, t); c.font = NM
            c.alignment = Alignment(wrap_text=True, vertical="top")
            ws.merge_cells(start_row=i, start_column=1, end_row=i, end_column=w)
            ws.row_dimensions[i].height = h
            return i + 1

        wb = Workbook()
        ws = wb.active; ws.title = "요약"
        for j, w_ in enumerate([30, 20, 20, 18, 16, 30], start=1):
            ws.column_dimensions[get_column_letter(j)].width = w_
        i = 1
        put(ws, i, 1, f"● {month} 네이버 일별 목표 시뮬레이션", Font(bold=True, size=14), bd=False); i += 2

        for metric in ("GFA", "SA"):
            if metric not in r["metrics"]:
                continue
            t = r["metrics"][metric]
            put(ws, i, 1, f"[{metric}]  일별 배분 방식: {t['weight_mode']}", B, bd=False); i += 1
            i = head(ws, i, ["항목", "값", "비고", "", "", ""])
            items = [("월 목표", t["target"], "", M),
                     ("단순 일평균(목표/일수)", t["daily_even"], f"{r['ndays']}일", M)]
            if t["n_done"]:
                items += [(f"실적 누적({t['n_done']}일)", t["cum_done"], "", M),
                          ("잔여 필요액", t["need"], f"잔여 {t['n_remain']}일", M),
                          ("잔여 필요 일평균", t["need_daily"], "", M)]
            if t["prev_daily"]:
                items += [("전년 동월 실적", t["prev_total"], "", M),
                          ("전년 동월 일평균", t["prev_daily"], "", M),
                          ("목표 일평균 / 전년 일평균", t["daily_even"] / t["prev_daily"],
                           "1을 넘으면 전년보다 높은 수준 필요", PC)]
            if t["proj"]:
                p = t["proj"]
                items += [("참고 전망 P10", p["P10"], "현 추세 하단", M),
                          ("참고 전망 P50", p["P50"], "현 추세 중심", M),
                          ("참고 전망 P90", p["P90"], "현 추세 상단", M)]
            for lb, v, memo, fmt in items:
                fill = YF if "필요" in lb else (AF if "실적 누적" in lb else None)
                put(ws, i, 1, lb, fill=fill); put(ws, i, 2, round(v) if fmt == M else v, fmt=fmt, fill=fill)
                put(ws, i, 3, memo); put(ws, i, 4, ""); put(ws, i, 5, ""); put(ws, i, 6, "")
                i += 1
            acc = t.get("accuracy")
            if acc:
                i = note(ws, i, f"참고 전망의 과거 오차: {t['n_done']}일 실적 기준 MAPE "
                                f"{acc['MAPE%']:.1f}%(최악 {acc['최악%']:.1f}%, 표본 {acc['n']}개월). "
                                f"14일 누적 시점에 재산출 권장.", 6, 34)
            i += 1

        i = note(ws, i, f"[세일 체크포인트] 과거 세일 구간 {r['sale']['n']}건의 시작일 중위는 "
                        f"{r['sale']['start_day']}일이고 구간 상승률 중위는 {r['sale']['lift']:+.1%}다. "
                        f"세일은 GFA에만 영향을 주고 SA는 무반응이다. 예측이 불가능하므로 일별 배분에는 "
                        f"넣지 않았으며, 해당월 {r['sale']['start_day']}일 전후 흐름으로 진입 여부를 확인하라.", 6, 44)
        i = note(ws, i, "[일별 배분 근거] GFA는 균등 배분이 과거 21개월 검증에서 가장 정확했다"
                        "(균등 38.4bp vs 공휴일+요일 38.5 vs 전년동월형태 42.7). SA는 요일·공휴일 보정이 "
                        "9% 개선됐다(25.2 → 23.0bp). 상세는 '방법론·검증' 시트 참고.", 6, 40)

        for metric in ("GFA", "SA"):
            if metric not in r["metrics"]:
                continue
            t = r["metrics"][metric]
            w2 = wb.create_sheet(f"{metric} 일별")
            for j, w_ in enumerate([13, 7, 16, 18, 18, 18, 14], start=1):
                w2.column_dimensions[get_column_letter(j)].width = w_
            k = 1
            put(w2, k, 1, f"● {month} {metric} 일별 필요 매출", Font(bold=True, size=13), bd=False); k += 2
            k = note(w2, k, f"배분 방식: {t['weight_mode']}. '필요 매출' 열 금액을 매일 달성하면 "
                            f"월 목표({t['target']:,.0f}원)에 도달한다. 실적이 입력된 날(파란 배경)은 "
                            f"실제 매출이고, 이후 날짜의 필요액은 잔여 목표를 재배분한 값이다.", 7, 36)
            k = head(w2, k, ["날짜", "요일", "구분", "필요 매출", "누적 필요", "실적", "누적 달성률"])
            for row in t["rows"]:
                d = row["date"]
                hol = self.HOL.get(d)
                kind = hol if hol else ("주말" if d.weekday() >= 5 else "영업일")
                is_act = row["actual"] is not None
                fill = AF if is_act else (BF if (d.weekday() >= 5 or hol) else None)
                put(w2, k, 1, d.isoformat(), fill=fill)
                put(w2, k, 2, WD[d.weekday()], fill=fill)
                put(w2, k, 3, kind, fill=fill)
                if is_act:
                    put(w2, k, 4, "-"); put(w2, k, 5, "-")
                    put(w2, k, 6, round(row["actual"]), B, fmt=M, fill=AF)
                    put(w2, k, 7, row["actual_cum"] / t["target"], fmt=PC, fill=AF)
                else:
                    put(w2, k, 4, round(row["need"]), fmt=M, fill=YF)
                    put(w2, k, 5, round(row["cum_need"]), fmt=M)
                    put(w2, k, 6, "-")
                    put(w2, k, 7, row["cum_need"] / t["target"], fmt=PC)
                k += 1
            put(w2, k, 1, "합계", B); put(w2, k, 2, "", B); put(w2, k, 3, "", B)
            put(w2, k, 4, round(t["need"]), B, fmt=M, fill=YF)
            put(w2, k, 5, round(t["target"]), B, fmt=M, fill=YF)
            put(w2, k, 6, round(t["cum_done"]), B, fmt=M, fill=AF)
            put(w2, k, 7, 1.0, B, fmt=PC)

        # 시즌 참고
        w3 = wb.create_sheet("시즌 참고")
        for j, w_ in enumerate([10, 18, 18, 14, 4, 13, 7, 18, 14], start=1):
            w3.column_dimensions[get_column_letter(j)].width = w_
        k = 1
        put(w3, k, 1, "● 월별 추이와 전년 동월 일별 실적", Font(bold=True, size=13), bd=False); k += 2
        k = head(w3, k, ["월", "GFA 일평균", "SA 일평균", "테무GFA 비중", "", "", "", "", ""])
        for y, m, days in self._full_months("GFA"):
            sa = [d for d in days if d in self.S]
            tg = [d for d in days if d in self.TG]
            put(w3, k, 1, f"{y}-{m:02d}")
            put(w3, k, 2, round(mean(self.G[d] for d in days)), fmt=M)
            put(w3, k, 3, round(mean(self.S[d] for d in sa)) if sa else "-", fmt=M if sa else None)
            put(w3, k, 4, (sum(self.TG[d] for d in tg) / sum(self.G[d] for d in tg)) if tg else "-",
                fmt=PC if tg else None)
            for j in (5, 6, 7, 8, 9):
                put(w3, k, j, "")
            k += 1
        k += 1
        y, m = (int(x) for x in month.split("-"))
        prev = sorted(d for d in self.G if d.year == y - 1 and d.month == m)
        if prev:
            put(w3, k, 1, f"[전년 동월 {y-1}-{m:02d} 일별 실적]", B, bd=False); k += 1
            k = head(w3, k, ["날짜", "요일", "GFA", "월중위 대비", "", "SA", "요일", "", ""])
            mb = median(self.G[d] for d in prev)
            for d in prev:
                put(w3, k, 1, d.isoformat()); put(w3, k, 2, WD[d.weekday()])
                put(w3, k, 3, round(self.G[d]), fmt=M,
                    fill=YF if self.G[d] / mb >= 1.2 else None)
                put(w3, k, 4, self.G[d] / mb, fmt=PC)
                put(w3, k, 5, "")
                put(w3, k, 6, round(self.S[d]) if d in self.S else "-", fmt=M if d in self.S else None)
                put(w3, k, 7, ""); put(w3, k, 8, ""); put(w3, k, 9, "")
                k += 1
        k += 1
        put(w3, k, 1, "[세일 구간 이력]", B, bd=False); k += 1
        k = head(w3, k, ["시작", "종료", "일수", "월중위 대비", "", "", "", "", ""])
        for s in self.sales:
            put(w3, k, 1, s["start"].isoformat()); put(w3, k, 2, s["end"].isoformat())
            put(w3, k, 3, s["days"]); put(w3, k, 4, s["lift"], fmt=PC)
            for j in (5, 6, 7, 8, 9):
                put(w3, k, j, "")
            k += 1

        # 방법론
        w4 = wb.create_sheet("방법론·검증")
        w4.column_dimensions["A"].width = 100
        k = 1
        put(w4, k, 1, "● 모델 설계 근거", Font(bold=True, size=13), bd=False); k += 2
        k = note(w4, k, f"학습 데이터: GFA {len(self.G)}일 / SA {len(self.S)}일 "
                        f"({min(self.G)} ~ {max(self.G)}), 완결 월 GFA {len(self._full_months('GFA'))}개 / "
                        f"SA {len(self._full_months('SA'))}개", 1, 22)
        k += 1
        put(w4, k, 1, "[일별 배분 방식 비교] 일별 점유율 오차 MAE, 단위 bp(0.01%p), 낮을수록 정확",
            B, bd=False); k += 1
        for metric in ("GFA", "SA"):
            v = self.validate_weights(metric)
            k = note(w4, k, f"  {metric}: " + "  ".join(f"{nm} {x:.1f}" for nm, x in v.items())
                     + f"   → 채택: {'균등' if metric == 'GFA' else '공휴일+요일'}", 1, 22)
        k += 1
        put(w4, k, 1, "[월 총량 전망 오차] 월초 N일 평균 × 배수, leave-one-month-out", B, bd=False); k += 1
        for metric in ("GFA", "SA"):
            for x in self.backtest(metric):
                k = note(w4, k, f"  {metric} N={x['N']:>2}일: MAPE {x['MAPE%']:.1f}%  "
                                f"최악 {x['최악%']:.1f}%  (표본 {x['n']}개월)", 1, 20)
        k += 1
        for blk in __doc__.split("────")[1].strip().split("\n\n"):
            k = note(w4, k, " ".join(blk.split()), 1, 48)

        wb.save(out_path)
        self.log_prediction(r, out_path)
        return out_path

    # ══════════════════════════════════════════════════════════════
    # 예측 기록 → 실적 대조 → 재보정 루프
    # ══════════════════════════════════════════════════════════════
    def log_prediction(self, sim_result: dict, out_path: str | None = None) -> None:
        """report()/simulate() 결과를 예측 로그에 적재한다(같은 월·같은 as_of는 덮어씀)."""
        log = self._load_log()
        month = sim_result["month"]
        for metric, t in sim_result["metrics"].items():
            as_of = max((row["date"] for row in t["rows"] if row["actual"] is not None),
                        default=None)
            key = f"{month}|{metric}|{as_of.isoformat() if as_of else 'pre'}"
            log[key] = {
                "month": month, "metric": metric,
                "as_of": as_of.isoformat() if as_of else None,
                "logged_at": date.today().isoformat(),
                "target": t["target"], "weight_mode": t["weight_mode"],
                "n_done": t["n_done"], "cum_done": t["cum_done"],
                "proj_P50": t["proj"].get("P50") if t["proj"] else None,
                "proj_P10": t["proj"].get("P10") if t["proj"] else None,
                "proj_P90": t["proj"].get("P90") if t["proj"] else None,
                "daily_need": {row["date"].isoformat(): row["need"]
                               for row in t["rows"] if row["need"] is not None},
                "out_path": out_path,
            }
        self._save_log(log)

    @staticmethod
    def _log_path():
        return os.path.join(BASE_DIR, "data", "cache", "naver_pred_log.json")

    def _load_log(self) -> dict:
        p = self._log_path()
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_log(self, log: dict) -> None:
        p = self._log_path()
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=1)

    def evaluate(self, month: str | None = None) -> list:
        """기록된 예측을 실적과 대조한다.

        두 가지를 채점한다.
          1) 월 총량 전망(P50) 오차 — 월이 끝났으면 확정, 진행 중이면 현재 페이스 기준 잠정
          2) 일별 배분 오차 — 예측 배분 점유율 vs 실제 점유율(MAE, bp).
             '균등이 맞다'는 선택이 새 데이터에서도 유지되는지 보는 지표다.
        """
        log = self._load_log()
        out = []
        for key, e in sorted(log.items()):
            if month and e["month"] != month:
                continue
            src = self._src(e["metric"])
            y, m = (int(x) for x in e["month"].split("-"))
            ndays = monthrange(y, m)[1]
            act_days = sorted(d for d in src if d.year == y and d.month == m)
            if not act_days:
                continue
            actual_total = sum(src[d] for d in act_days)
            complete = len(act_days) >= ndays

            row = {"key": key, "month": e["month"], "metric": e["metric"],
                   "as_of": e["as_of"], "target": e["target"],
                   "weight_mode": e["weight_mode"], "complete": complete,
                   "actual_days": len(act_days), "actual_total": actual_total,
                   "target_hit": actual_total >= e["target"] if complete else None}

            if e.get("proj_P50"):
                row["proj_P50"] = e["proj_P50"]
                if complete:
                    row["proj_err%"] = (e["proj_P50"] - actual_total) / actual_total * 100
                    row["in_band"] = (e.get("proj_P10", 0) <= actual_total <= e.get("proj_P90", 0))

            # 일별 배분 채점: 예측 대상일 중 실적이 들어온 날만
            nd = {date.fromisoformat(k): v for k, v in e["daily_need"].items()}
            scored = [d for d in nd if d in src]
            if len(scored) >= 3:
                pred_sum = sum(nd[d] for d in scored)
                act_sum = sum(src[d] for d in scored)
                if pred_sum and act_sum:
                    pw = {d: nd[d] / pred_sum for d in scored}
                    aw = {d: src[d] / act_sum for d in scored}
                    row["shape_mae_bp"] = mean(abs(pw[d] - aw[d]) for d in scored) * 10000
                    row["shape_n"] = len(scored)
                    # 균등 배분을 같은 날짜에 적용했을 때와 비교
                    ew = {d: 1 / len(scored) for d in scored}
                    row["shape_mae_even_bp"] = mean(abs(ew[d] - aw[d]) for d in scored) * 10000
                    # 일별 달성률(실적/필요)
                    row["daily_ratio"] = act_sum / pred_sum
            out.append(row)
        return out

    def recalibrate(self) -> dict:
        """최신 데이터로 배분 방식·배수 분포를 재검증하고 현재 설정과 비교한다."""
        res = {"data_through": max(self.G).isoformat(), "weights": {}, "ratios": {}, "flags": []}
        for metric in ("GFA", "SA"):
            v = self.validate_weights(metric)
            best = min(v, key=v.get)
            cur = "균등" if metric == "GFA" else "공휴일+요일"
            res["weights"][metric] = {"scores_bp": v, "best": best, "current": cur}
            if best != cur:
                gain = (v[cur] - v[best]) / v[cur] * 100
                res["flags"].append(
                    f"{metric} 일별 배분 최적안이 '{cur}' → '{best}'로 바뀜(개선 {gain:.1f}%). "
                    f"weights() 수정 검토 필요.")
            res["ratios"][metric] = {n: {"중위": median(d), "n": len(d)}
                                     for n, d in self.ratios[metric].items() if d}
        for metric in ("GFA", "SA"):
            bt = self.backtest(metric)
            if bt:
                res["ratios"][metric]["backtest"] = bt
        ev = self.evaluate()
        done = [x for x in ev if x.get("complete") and "proj_err%" in x]
        if done:
            res["realized_proj_err"] = {
                "n": len(done),
                "MAPE%": mean(abs(x["proj_err%"]) for x in done),
                "편향%": mean(x["proj_err%"] for x in done),
                "밴드적중률": sum(1 for x in done if x.get("in_band")) / len(done),
            }
            if abs(res["realized_proj_err"]["편향%"]) > 10:
                res["flags"].append(
                    f"실제 전망 편향 {res['realized_proj_err']['편향%']:+.1f}% — "
                    f"배수 분포가 현재 추세를 못 따라가고 있을 수 있음(최근 월 가중 검토).")
        shaped = [x for x in ev if "shape_mae_bp" in x]
        if shaped:
            worse = [x for x in shaped if x["shape_mae_bp"] > x["shape_mae_even_bp"] * 1.1]
            res["realized_shape"] = {
                "n": len(shaped),
                "평균_MAE_bp": mean(x["shape_mae_bp"] for x in shaped),
                "균등대비_열위건수": len(worse),
            }
            if len(worse) >= max(2, len(shaped) // 2):
                res["flags"].append(
                    "기록된 예측의 일별 배분이 균등 배분보다 자주 나빴음 — 배분 방식 재검토 필요.")
        if not res["flags"]:
            res["flags"].append("현재 설정 유지가 타당(이상 신호 없음).")
        return res

    def tracking_report(self, out_path: str | None = None) -> str:
        """예측 vs 실적 대조표 + 재보정 결과를 엑셀로 출력."""
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter

        ev = self.evaluate()
        rc = self.recalibrate()
        if out_path is None:
            out_path = os.path.join(OUT_DIR,
                                    f"네이버_예측정확도_추적_{date.today().strftime('%m%d')}.xlsx")
        HF = PatternFill("solid", fgColor="4F81BD"); HFONT = Font(bold=True, color="FFFFFF", size=11)
        YF = PatternFill("solid", fgColor="FFFF99"); RF = PatternFill("solid", fgColor="F8CBAD")
        GF = PatternFill("solid", fgColor="E2EFDA")
        B = Font(bold=True, size=11); NM = Font(size=11)
        TH = Border(*[Side(style="thin", color="BFBFBF")] * 4)
        M, PC = "#,##0", "0.0%"

        wb = Workbook(); ws = wb.active; ws.title = "예측 정확도"
        for j, w in enumerate([12, 8, 12, 18, 18, 18, 12, 14, 14, 14, 16], start=1):
            ws.column_dimensions[get_column_letter(j)].width = w

        def put(i, j, v, font=NM, fill=None, fmt=None):
            c = ws.cell(i, j, v); c.font = font
            if fill: c.fill = fill
            if fmt: c.number_format = fmt
            c.border = TH
            return c

        i = 1
        ws.cell(i, 1, "● 예측 vs 실적 대조").font = Font(bold=True, size=14); i += 2
        for j, h in enumerate(["월", "지표", "기준일", "월 목표", "전망 P50", "실적 합계",
                               "전망오차%", "밴드적중", "배분MAE(bp)", "균등MAE(bp)",
                               "일별달성률"], start=1):
            put(i, j, h, HFONT, HF)
        i += 1
        for x in ev:
            put(i, 1, x["month"]); put(i, 2, x["metric"]); put(i, 3, x["as_of"] or "-")
            put(i, 4, round(x["target"]), fmt=M)
            put(i, 5, round(x["proj_P50"]) if x.get("proj_P50") else "-",
                fmt=M if x.get("proj_P50") else None)
            put(i, 6, round(x["actual_total"]), fmt=M,
                fill=GF if x.get("target_hit") else (RF if x.get("complete") else None))
            put(i, 7, x.get("proj_err%", "-"), fmt="0.0" if "proj_err%" in x else None)
            put(i, 8, "O" if x.get("in_band") else ("X" if x.get("complete") else "-"))
            put(i, 9, round(x["shape_mae_bp"], 1) if "shape_mae_bp" in x else "-")
            put(i, 10, round(x["shape_mae_even_bp"], 1) if "shape_mae_even_bp" in x else "-")
            put(i, 11, x.get("daily_ratio", "-"), fmt=PC if "daily_ratio" in x else None)
            i += 1
        i += 1

        def note(t, h=38):
            nonlocal i
            c = ws.cell(i, 1, t); c.font = NM
            c.alignment = Alignment(wrap_text=True, vertical="top")
            ws.merge_cells(start_row=i, start_column=1, end_row=i, end_column=11)
            ws.row_dimensions[i].height = h
            i += 1

        note("[열 설명] 전망오차% = (전망 P50 − 실적)/실적. 월이 끝난 건만 계산된다. "
             "밴드적중 = 실적이 P10~P90 안에 들어왔는지. 배분MAE = 일별 필요액 배분의 점유율 오차이고 "
             "균등MAE와 비교해 현재 배분 방식이 균등보다 나은지 본다. "
             "일별달성률 = 해당 기간 실적합 / 필요액합.")
        i += 1
        ws.cell(i, 1, "● 재보정 결과").font = Font(bold=True, size=13); i += 2
        note(f"데이터 기준일: {rc['data_through']}")
        for metric, w in rc["weights"].items():
            note(f"[{metric}] 일별 배분 오차(bp): "
                 + ", ".join(f"{k} {v:.1f}" for k, v in w["scores_bp"].items())
                 + f"  → 최적 '{w['best']}' / 현재 '{w['current']}'")
        if "realized_proj_err" in rc:
            r0 = rc["realized_proj_err"]
            note(f"[실현 전망 오차] 완료된 예측 {r0['n']}건: MAPE {r0['MAPE%']:.1f}%, "
                 f"편향 {r0['편향%']:+.1f}%, 밴드 적중률 {r0['밴드적중률']:.0%}")
        if "realized_shape" in rc:
            r1 = rc["realized_shape"]
            note(f"[실현 배분 오차] {r1['n']}건 평균 {r1['평균_MAE_bp']:.1f}bp, "
                 f"균등 대비 열위 {r1['균등대비_열위건수']}건")
        for f in rc["flags"]:
            c = ws.cell(i, 1, "※ " + f)
            c.font = Font(size=11, bold=True)
            c.alignment = Alignment(wrap_text=True, vertical="top")
            ws.merge_cells(start_row=i, start_column=1, end_row=i, end_column=11)
            ws.row_dimensions[i].height = 34
            i += 1

        wb.save(out_path)
        return out_path
