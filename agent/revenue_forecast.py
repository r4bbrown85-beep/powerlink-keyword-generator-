# -*- coding: utf-8 -*-
"""매체 공통 일단위 매출 예측 / 목표 달성률 모듈.

2026-09-27에 네이버 GFA 54개월(2022-04~2026-09, 1,640일) 실측으로 설계·검증했다.
핵심 검증 결과(재현 방법은 backtest() 참고):

  1) 평상시 '월 마지막 N일' 예측은 **단순 최근 7일 평균이 가장 정확**했다
     (53개월 leave-one-month-out: 최근7일 MAPE 9.5% vs 요일·월내위치·공휴일
      완전분해 모델 15.8%). 정교한 모델을 기본값으로 쓰지 말 것.
  2) 단 **최근 창에 연휴가 끼면 모든 단순법이 +13~18% 과대예측**한다.
     이때는 명절 회복곡선(festive curve) 방식으로 자동 전환한다.
  3) "연휴 끝나면 원래 수준 회복" 가정은 편향 +17.3%로 기각됐다. 실제로는
     연휴 후에도 며칠간 15~19% 낮은 수준이 지속된다.
  4) 그 해 연휴중 실측(k0)으로 과거 패턴을 스케일링하면 불확실성이 크게 준다
     (회복수준 자체 CV 23% -> k0 대비 비율 CV 7%).

사용법:
    from agent.revenue_forecast import RevenueForecaster, load_holidays

    fc = RevenueForecaster(series, holidays=load_holidays())   # series: index=날짜, value=일매출
    print(fc.backtest())                                       # 이 매체에서도 방법 선택이 맞는지 검증
    result = fc.forecast_month_end("2026-09", target=3_237_000_000)
"""
from __future__ import annotations

import json
import os
import re
from datetime import date, timedelta

import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, "data", "cache", "forecast")
REVENUE_SHEET_ID = "1V-gAyGok-H29rzXtvpE5UTFjhh-DYNbL6SW74dBrwNs"  # 네이버/매체 매출 현황 스프레드시트
TOKEN_PATH = os.path.join(BASE_DIR, "config", "briefing_token.json")

# 시트 '★공휴일' 탭은 2023-09부터라 그 이전 주요 공휴일은 여기서 보완한다.
_EXTRA_HOLIDAYS = [
    "2022-05-05", "2022-06-06", "2022-08-15", "2022-09-09", "2022-09-10", "2022-09-11",
    "2022-09-12", "2022-10-03", "2022-10-10", "2022-12-25", "2023-01-01", "2023-01-21",
    "2023-01-22", "2023-01-23", "2023-01-24", "2023-03-01", "2023-05-05", "2023-05-27",
    "2023-05-29", "2023-06-06", "2023-08-15",
]

# 명절 시즌 판정용(설·추석이 걸리는 달). 회복 패턴이 일반 공휴일과 다르다.
FESTIVE_MONTHS = (1, 2, 9, 10)


# --------------------------------------------------------------------------
# 데이터 로딩
# --------------------------------------------------------------------------
def _sheets_service():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    # scopes 인자 생략 = 토큰 파일 스코프 그대로 사용(공유 토큰 사고 방지 규칙)
    creds = Credentials.from_authorized_user_file(TOKEN_PATH)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("sheets", "v4", credentials=creds)


def load_holidays(refresh: bool = False) -> set:
    """한국 공휴일 집합. 시트 '★공휴일' 탭 + 2023-09 이전 보완분."""
    path = os.path.join(CACHE_DIR, "holidays.json")
    if not refresh and os.path.exists(path):
        raw = json.load(open(path, encoding="utf-8"))
    else:
        svc = _sheets_service()
        resp = svc.spreadsheets().values().get(
            spreadsheetId=REVENUE_SHEET_ID, range="'★공휴일'!A1:C300").execute()
        raw = []
        for row in resp.get("values", [])[1:]:
            if row and row[0].strip():
                m = re.match(r"(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})", row[0].strip())
                if m:
                    raw.append(date(*map(int, m.groups())).isoformat())
        raw = sorted(set(raw) | set(_EXTRA_HOLIDAYS))
        os.makedirs(CACHE_DIR, exist_ok=True)
        json.dump(raw, open(path, "w", encoding="utf-8"))
    return {pd.Timestamp(d) for d in raw}


# 네이버 매출 현황 스프레드시트의 일단위 표가 들어 있는 탭들
NAVER_TABS = [
    "22년 2분기", "22년 3분기", "22년 4분기",
    "23년 1분기", "23년 2분기", "23년 3분기", "23년 4분기",
    "24년 1~3분기",
    "24년 10월 매출 프로모션", "24년 11월 매출 프로모션", "24년 12월 매출 프로모션",
    "25년 1월 매출 현황", "25년 2월 매출 현황", "25년 3월 매출 현황", "25년 4-5월 매출 현황",
    "25년 6월 매출 현황", "25년 7월 매출 현황", "25년 8월 매출 현황", "25년 9월 매출 현황",
    "25년 10월 매출 현황", "25년 11월 매출 현황", "25년 12월 매출 현황",
    "26년 1월 매출 현황", "26년 2월 매출 현황", "26년 3월 매출 현황", "26년 4월 매출 현황",
    "26년 5월 매출 현황", "26년 6월 매출 현황", "26년 7월 매출 현황",
    "26년 8월 네이버 매출 현황", "26년 9월 네이버 매출 현황",
]

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def load_naver_series(metric: str = "GFA", tabs=None, refresh: bool = False) -> pd.Series:
    """네이버 매출 현황 시트에서 지표 하나의 일단위 시계열을 모아 온다.

    metric 예: "GFA", "SA(파워링크+쇼핑검색)", "테무_GFA".
    탭마다 (a) 대시보드 높이가 달라 헤더 행 위치가 다르고 (b) 날짜 열이 B 또는 C이며
    (c) 지표 열 위치도 제각각이라, 헤더 행에서 metric 문자열을 찾아 열을 잡는다.
    """
    cache = os.path.join(CACHE_DIR, f"naver_{re.sub(r'[^A-Za-z0-9가-힣]', '_', metric)}.json")
    if not refresh and os.path.exists(cache):
        raw = json.load(open(cache, encoding="utf-8"))
        return pd.Series({pd.Timestamp(k): v for k, v in raw.items()}).sort_index()

    svc = _sheets_service()
    tabs = tabs or NAVER_TABS
    found: dict[str, float] = {}
    for start in range(0, len(tabs), 8):
        chunk = tabs[start:start + 8]
        resp = svc.spreadsheets().values().batchGet(
            spreadsheetId=REVENUE_SHEET_ID,
            ranges=[f"'{t}'!A1:P400" for t in chunk]).execute()
        for vr in resp.get("valueRanges", []):
            found.update(_parse_metric_blocks(vr.get("values", []), metric))

    os.makedirs(CACHE_DIR, exist_ok=True)
    json.dump(found, open(cache, "w", encoding="utf-8"), ensure_ascii=False, sort_keys=True)
    return pd.Series({pd.Timestamp(k): v for k, v in found.items()}).sort_index()


def _parse_metric_blocks(rows, metric: str) -> dict:
    out = {}
    for i, row in enumerate(rows):
        cols = [j for j, c in enumerate(row) if str(c).strip() == metric]
        if not cols:
            continue
        mcol = cols[0]
        for r2 in rows[i + 1:]:
            dcell = ""
            for dc in (1, 2):  # 날짜 열이 탭마다 B 또는 C
                if len(r2) > dc and _DATE_RE.match(str(r2[dc]).strip()):
                    dcell = str(r2[dc]).strip()
                    break
            if not dcell:
                break
            s = str(r2[mcol]).replace(",", "").strip() if len(r2) > mcol else ""
            if s in ("", "-", "#DIV/0!", "#REF!"):
                continue
            try:
                out[dcell] = float(s)
            except ValueError:
                continue
    return out


# --------------------------------------------------------------------------
# 예측기
# --------------------------------------------------------------------------
class RevenueForecaster:
    """일단위 매출 시계열 -> 월말 예측 / 목표 달성 확률.

    어떤 매체든 pd.Series(index=날짜, value=일매출)만 있으면 쓸 수 있다.
    """

    def __init__(self, series: pd.Series, holidays: set | None = None):
        self.s = series.sort_index().astype(float)
        self.holidays = holidays if holidays is not None else load_holidays()
        self.feat = self._build_features(self.s.index)
        self.feat["value"] = self.s
        self._fit()

    # ---------- 특성 ----------
    def _off(self, ts) -> bool:
        return (ts in self.holidays) or ts.dayofweek >= 5

    def _cluster_len_back(self, ts):
        n, t = 0, ts - timedelta(days=1)
        while self._off(t):
            n += 1
            t -= timedelta(days=1)
        return n

    def _cluster_len_fwd(self, ts):
        n, t = 0, ts + timedelta(days=1)
        while self._off(t):
            n += 1
            t += timedelta(days=1)
        return n

    def _build_features(self, idx) -> pd.DataFrame:
        rows = []
        for ts in idx:
            dim = ts.days_in_month
            isoff = self._off(ts)
            pre = post = 0
            if not isoff:
                if self._cluster_len_fwd(ts) >= 3:
                    pre = 1
                back = self._cluster_len_back(ts)
                if back >= 3:
                    post = 1
                else:  # 연휴 후 2·3번째 영업일인지 역추적
                    cnt, t = 1, ts - timedelta(days=1)
                    while cnt <= 2:
                        while self._off(t):
                            t -= timedelta(days=1)
                        if self._cluster_len_back(t) >= 3:
                            post = cnt + 1
                            break
                        cnt += 1
                        t -= timedelta(days=1)
            wknd_cl = 0
            if ts.dayofweek >= 5 and ts not in self.holidays:
                if self._cluster_len_back(ts) + self._cluster_len_fwd(ts) + 1 >= 3:
                    wknd_cl = 1
            rows.append({
                "ts": ts, "dow": ts.dayofweek, "ym": ts.to_period("M"), "dom": ts.day,
                "dim": dim, "dte": dim - ts.day, "prog": (ts.day - 1) / (dim - 1),
                "is_hol": ts in self.holidays, "off": isoff,
                "pre": pre, "post": post, "wknd_cl": wknd_cl,
            })
        df = pd.DataFrame(rows).set_index("ts")
        df["normal"] = (~df["is_hol"]) & (df["pre"] == 0) & (df["post"] == 0) & (df["wknd_cl"] == 0)
        return df

    # ---------- 요인 추정 ----------
    def _fit(self, data: pd.DataFrame | None = None):
        d = self.feat if data is None else data
        dn = d[d["normal"]].copy()
        dn["rel"] = dn["value"] / dn.groupby("ym")["value"].transform("mean")
        dow = dn.groupby("dow")["rel"].mean()
        self.dow_f = (dow / dow.mean()).to_dict()
        dn["rel_dw"] = dn["rel"] / dn["dow"].map(self.dow_f)
        dn["b"] = (dn["prog"] * 20).clip(0, 19.999).astype(int)
        self.prof = dn.groupby("b")["rel_dw"].mean().reindex(range(20)).interpolate().bfill().ffill().to_dict()
        self.festive_curve, self.festive_patterns = self._fit_festive(d)

    def _clusters(self, d: pd.DataFrame):
        """3일 이상 연속 휴무이면서 공휴일을 포함하는 구간."""
        idx = list(d.index)
        res, i = [], 0
        while i < len(idx):
            if d["off"].iloc[i]:
                j = i
                while j + 1 < len(idx) and d["off"].iloc[j + 1] and (idx[j + 1] - idx[j]).days == 1:
                    j += 1
                if (j - i + 1) >= 3 and any(d["is_hol"].iloc[k] for k in range(i, j + 1)):
                    res.append((idx[i], idx[j]))
                i = j + 1
            else:
                i += 1
        return res

    def _fit_festive(self, d: pd.DataFrame):
        """명절 연휴 전후 회복곡선: 연휴 직전 정상 영업일 10일(요일보정) = 1.0 기준."""
        idx = list(d.index)
        patterns = []
        for a, b in self._clusters(d):
            if a.month not in FESTIVE_MONTHS:
                continue
            pre_days = [t for t in idx if t < a and d.loc[t, "normal"]][-10:]
            if len(pre_days) < 5:
                continue
            base = np.mean([d.loc[t, "value"] / self.dow_f[d.loc[t, "dow"]] for t in pre_days])
            if not np.isfinite(base) or base <= 0:
                continue
            p = {}
            inner = [t for t in idx if a <= t <= b]
            if inner:
                p[0] = float(np.mean([(d.loc[t, "value"] / self.dow_f[d.loc[t, "dow"]]) / base for t in inner]))
            for k, t in enumerate([t for t in idx if t > b][:3], start=1):
                p[k] = float((d.loc[t, "value"] / self.dow_f[d.loc[t, "dow"]]) / base)
            if all(k in p for k in (0, 1, 2, 3)):
                patterns.append(p)
        curve = {k: float(np.mean([p[k] for p in patterns])) for k in (0, 1, 2, 3)} if patterns else {}
        return curve, patterns

    # ---------- 일별 배율 ----------
    def _mult(self, row, use_prof=True) -> float:
        m = self.dow_f[row["dow"]]
        if use_prof:
            m *= self.prof[int(min(row["prog"] * 20, 19.999))]
        return m

    # ---------- 백테스트 ----------
    def backtest(self, horizon: int = 4) -> pd.DataFrame:
        """'월 마지막 horizon일 합계' 예측 과제로 방법들을 비교한다.

        이 매체에서도 단순법이 이기는지 확인하는 용도. 월별 leave-one-out으로
        요인을 재추정하므로 look-ahead가 없다.
        """
        rows = []
        for ym in sorted(self.feat["ym"].unique()):
            md = self.feat[self.feat["ym"] == ym]
            if len(md) < md["dim"].iloc[0] or len(md) <= horizon + 7:
                continue
            known, tgt = md.iloc[:-horizon], md.iloc[-horizon:]
            saved = (self.dow_f, self.prof, self.festive_curve, self.festive_patterns)
            self._fit(self.feat[self.feat["ym"] != ym])  # leave-one-month-out
            mk = known.apply(self._mult, axis=1)
            lvl = (known["value"] / mk).iloc[-10:].mean()
            model = float((lvl * tgt.apply(self._mult, axis=1)).sum())
            self.dow_f, self.prof, self.festive_curve, self.festive_patterns = saved
            rows.append({
                "ym": str(ym),
                "actual": float(tgt["value"].sum()),
                "recent7": float(known["value"].iloc[-7:].mean() * horizon),
                "recent14": float(known["value"].iloc[-14:].mean() * horizon),
                "model": model,
                "win_has_holiday": int((~known.iloc[-7:]["normal"]).any()),
            })
        res = pd.DataFrame(rows)
        for c in ("recent7", "recent14", "model"):
            res[c + "_err"] = (res[c] - res["actual"]) / res["actual"]
        return res

    @staticmethod
    def summarize_backtest(res: pd.DataFrame) -> pd.DataFrame:
        rows = []
        for c in [c for c in res.columns if c.endswith("_err")]:
            for label, sub in (("전체", res), ("연휴낀월", res[res["win_has_holiday"] == 1])):
                if len(sub) == 0:
                    continue
                e = sub[c]
                rows.append({"방법": c[:-4], "구간": label, "n": len(sub),
                             "MAPE%": round(e.abs().mean() * 100, 2),
                             "중앙절대%": round(e.abs().median() * 100, 2),
                             "편향%": round(e.mean() * 100, 2)})
        return pd.DataFrame(rows).sort_values(["구간", "MAPE%"])

    # ---------- 예측 ----------
    def forecast_month_end(self, month: str, target: float | None = None,
                           n_sims: int = 20000, seed: int = 7) -> dict:
        """해당 월의 미관측 잔여일을 예측하고 월 합계 분포를 낸다.

        최근 구간에 연휴가 끼어 있으면 명절 회복곡선 방식, 아니면 최근 7일 평균
        방식을 자동 선택한다(백테스트에서 각각 우세했던 방법).
        """
        per = pd.Period(month, freq="M")
        md = self.feat[self.feat["ym"] == per]
        if md.empty:
            raise ValueError(f"{month} 데이터 없음")
        dim = int(md["dim"].iloc[0])
        observed_days = int(md["dom"].max())
        if observed_days >= dim:
            return {"method": "완료", "total": float(md["value"].sum()), "remaining": []}

        remaining = [pd.Timestamp(date(per.year, per.month, d)) for d in range(observed_days + 1, dim + 1)]
        rfeat = self._build_features(pd.DatetimeIndex(remaining))
        observed_sum = float(md["value"].sum())

        recent_has_holiday = bool((~md.iloc[-7:]["normal"]).any())
        rng = np.random.default_rng(seed)

        if recent_has_holiday and self.festive_patterns:
            res = self._forecast_festive(md, rfeat, rng, n_sims)
            res["method"] = "명절 회복곡선(최근 구간에 연휴 있음)"
        elif recent_has_holiday:
            # 자체 명절 이력이 없는 매체(이력 짧음). 다른 매체 곡선을 빌려오면 안 된다 --
            # 2026-09 실측에서 GFA(디스플레이)는 연휴중 0.78로 정체한 반면
            # SA(검색)는 0.94까지 자체 회복해, 매체별 연휴 반응이 확연히 달랐다.
            res = self._forecast_own_recovery(md, rfeat, rng, n_sims)
            res["method"] = "자체 연휴 회복추세 외삽(명절 이력 부족 · 신뢰도 낮음)"
        else:
            res = self._forecast_recent(md, rfeat, rng, n_sims)
            res["method"] = "최근 7일 평균(평상시 최우수)"

        res["observed_sum"] = observed_sum
        res["total_p50"] = observed_sum + res["rem_p50"]
        res["total_mean"] = observed_sum + res["rem_mean"]
        res["total_p10"] = observed_sum + res["rem_p10"]
        res["total_p90"] = observed_sum + res["rem_p90"]
        if target:
            res["target"] = target
            res["p_target"] = float((observed_sum + res["_sims"] >= target).mean())
            res["gap_vs_target"] = res["total_p50"] - target
        res.pop("_sims", None)
        return res

    def _forecast_recent(self, md, rfeat, rng, n_sims) -> dict:
        """평상시: 최근 7일 평균 수준 유지 + 요일 보정. 불확실성은 과거 동일과제 오차분포."""
        recent = md["value"].iloc[-7:]
        lvl = float(recent.mean() / np.mean([self.dow_f[d] for d in md["dow"].iloc[-7:]]))
        days = {t.strftime("%Y-%m-%d"): lvl * self.dow_f[r["dow"]] for t, r in rfeat.iterrows()}
        point = float(sum(days.values()))
        bt = self.backtest(horizon=max(len(rfeat), 1))
        errs = bt[bt["win_has_holiday"] == 0]["recent7_err"].values
        if len(errs) < 5:
            errs = bt["recent7_err"].values
        sims = point / (1 + rng.choice(errs, n_sims)) if len(errs) else np.full(n_sims, point)
        return self._pack(days, point, sims)

    def _forecast_festive(self, md, rfeat, rng, n_sims) -> dict:
        """연휴 구간: 연휴 직전 수준 x 과거 명절 회복곡선. 올해 연휴중 실측으로 캘리브레이션."""
        idx = list(self.feat[self.feat["ym"] == md["ym"].iloc[0]].index)
        cl = self._clusters(self.feat)
        recent_cluster = [c for c in cl if (md.index[-1] - c[1]).days <= 7 and c[1] <= md.index[-1]]
        cl_start = recent_cluster[-1][0] if recent_cluster else None

        pre_days = [t for t in idx if (cl_start is None or t < cl_start) and self.feat.loc[t, "normal"]][-10:]
        base = float(np.mean([self.feat.loc[t, "value"] / self.dow_f[self.feat.loc[t, "dow"]] for t in pre_days]))

        inner = [t for t in idx if cl_start is not None and cl_start <= t <= md.index[-1] and self.feat.loc[t, "off"]]
        k0_obs = float(np.mean([(self.feat.loc[t, "value"] / self.dow_f[self.feat.loc[t, "dow"]]) / base
                                for t in inner])) if inner else None

        # 잔여일의 연휴 상대위치 k (0=연휴중, 1~3=연휴 후 n번째 영업일)
        ks = []
        biz = 0
        for t, r in rfeat.iterrows():
            if r["off"]:
                ks.append(0)
            else:
                biz += 1
                ks.append(min(biz, 3))

        sims = np.zeros(n_sims)
        day_draws = {t.strftime("%Y-%m-%d"): [] for t in rfeat.index}
        for i in range(n_sims):
            p = self.festive_patterns[rng.integers(len(self.festive_patterns))]
            scale = 1.0
            if k0_obs and p.get(0):
                scale = float(np.clip(k0_obs / p[0], 0.7, 1.4))
            tot = 0.0
            for (t, r), k in zip(rfeat.iterrows(), ks):
                v = base * self.dow_f[r["dow"]] * p[k] * scale
                tot += v
                if i < 2000:
                    day_draws[t.strftime("%Y-%m-%d")].append(v)
            sims[i] = tot
        days = {d: float(np.median(v)) for d, v in day_draws.items()}
        return self._pack(days, float(np.median(sims)), sims,
                          extra={"baseline_level": base, "k0_observed": k0_obs,
                                 "festive_curve": self.festive_curve,
                                 "n_patterns": len(self.festive_patterns)})

    def _forecast_own_recovery(self, md, rfeat, rng, n_sims) -> dict:
        """명절 이력이 없는 매체: 이번 연휴 중 자체 관측된 회복 기울기를 외삽한다.

        하한은 '마지막 관측 수준 유지', 상한은 '연휴 전 수준 완전 회복'으로 잡고
        그 사이를 균등 샘플링해 불확실성을 정직하게 넓게 둔다.
        """
        idx = list(md.index)
        cl = self._clusters(self.feat)
        recent = [c for c in cl if c[1] <= md.index[-1] and (md.index[-1] - c[1]).days <= 7]
        cl_start = recent[-1][0] if recent else md.index[-1]
        pre_days = [t for t in idx if t < cl_start and self.feat.loc[t, "normal"]][-10:]
        base = float(np.mean([self.feat.loc[t, "value"] / self.dow_f[self.feat.loc[t, "dow"]]
                              for t in pre_days])) if pre_days else float(md["value"].mean())

        inner = [t for t in idx if t >= cl_start]
        rels = [(self.feat.loc[t, "value"] / self.dow_f[self.feat.loc[t, "dow"]]) / base for t in inner]
        last_rel = float(rels[-1]) if rels else 0.85
        if len(rels) >= 2:  # 연휴 중 회복 기울기
            slope = float(np.polyfit(range(len(rels)), rels, 1)[0])
        else:
            slope = 0.0

        sims = np.zeros(n_sims)
        day_draws = {t.strftime("%Y-%m-%d"): [] for t in rfeat.index}
        for i in range(n_sims):
            w = rng.uniform(0.0, 1.0)  # 0=수준유지, 1=완전회복
            tot = 0.0
            for step, (t, r) in enumerate(rfeat.iterrows(), start=1):
                trend = min(last_rel + max(slope, 0.0) * step, 1.0)
                rel = last_rel + w * (max(trend, last_rel) - last_rel)
                v = base * self.dow_f[r["dow"]] * rel
                tot += v
                if i < 2000:
                    day_draws[t.strftime("%Y-%m-%d")].append(v)
            sims[i] = tot
        days = {d: float(np.median(v)) for d, v in day_draws.items()}
        return self._pack(days, float(np.median(sims)), sims,
                          extra={"baseline_level": base, "k0_observed": last_rel,
                                 "own_recovery_slope": slope, "n_patterns": 0})

    @staticmethod
    def _pack(days, point, sims, extra=None) -> dict:
        res = {
            "remaining": days,
            "rem_point": point,
            "rem_p50": float(np.percentile(sims, 50)),
            "rem_mean": float(np.mean(sims)),
            "rem_p10": float(np.percentile(sims, 10)),
            "rem_p90": float(np.percentile(sims, 90)),
            "_sims": sims,
        }
        if extra:
            res.update(extra)
        return res


def format_report(res: dict, unit: str = "억") -> str:
    """forecast_month_end 결과를 사람이 읽는 형태로."""
    div = 1e8 if unit == "억" else 1
    lines = [f"방법: {res['method']}"]
    if "baseline_level" in res:
        lines.append(f"연휴 직전 기준수준: {res['baseline_level']:,.0f}원/일"
                     + (f" · 올해 연휴중 실측비 {res['k0_observed']:.3f}" if res.get("k0_observed") else ""))
    lines.append("잔여일 예측:")
    for d, v in res["remaining"].items():
        lines.append(f"  {d}: {v:,.0f}")
    lines.append(f"잔여 합계: {res['rem_p50']:,.0f}")
    lines.append(f"월 총계(중앙): {res['total_p50']/div:.2f}{unit}  "
                 f"[10~90분위 {res['total_p10']/div:.2f}~{res['total_p90']/div:.2f}{unit}]")
    if "target" in res:
        lines.append(f"목표 {res['target']/div:.2f}{unit} 대비 {res['gap_vs_target']/div:+.2f}{unit} "
                     f"· 달성확률 {res['p_target']*100:.1f}%")
    return "\n".join(lines)
