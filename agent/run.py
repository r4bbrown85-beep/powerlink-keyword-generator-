# -*- coding: utf-8 -*-
"""
run.py — 자동화 태스크 실행기

사용법:
  python agent/run.py --task report_to_sheets --sheet_url "https://docs.google.com/..."
  python agent/run.py --task campaign_stats --days 7
  python agent/run.py --task keyword_stats  --days 7 --top 100
  python agent/run.py --task daily_trend    --days 30

태스크 목록:
  report_to_sheets  : 캠페인/키워드 실적을 구글 시트에 업데이트
  campaign_stats    : 캠페인별 실적 출력
  keyword_stats     : 키워드별 실적 출력
  daily_trend       : 일별 트렌드 출력
"""
import argparse
import json
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.naver_reporter import (
    get_creds_from_env,
    get_campaign_stats,
    get_keyword_stats,
    get_daily_trend,
)


def _print_table(rows: list, max_rows: int = 30):
    if not rows:
        print("  (데이터 없음)")
        return
    headers = list(rows[0].keys())
    widths  = {h: max(len(str(h)), max(len(str(r.get(h, ""))) for r in rows[:max_rows])) for h in headers}
    fmt     = "  " + "  ".join(f"{{:<{widths[h]}}}" for h in headers)
    print(fmt.format(*headers))
    print("  " + "-" * (sum(widths.values()) + 2 * len(headers)))
    for r in rows[:max_rows]:
        print(fmt.format(*[str(r.get(h, "")) for h in headers]))
    if len(rows) > max_rows:
        print(f"  ... ({len(rows) - max_rows}개 더)")


# ── 태스크 함수들 ────────────────────────────────────────────────────────────

def task_campaign_stats(creds, days: int = 7, **kwargs):
    print(f"\n[캠페인별 실적] 최근 {days}일\n")
    rows = get_campaign_stats(creds, days=days)
    _print_table(rows)
    return rows


def task_keyword_stats(creds, days: int = 7, top: int = 50, **kwargs):
    print(f"\n[키워드별 실적] 최근 {days}일, top {top}\n")
    rows = get_keyword_stats(creds, days=days, top_n=top)
    _print_table(rows)
    return rows


def task_daily_trend(creds, days: int = 30, **kwargs):
    print(f"\n[일별 트렌드] 최근 {days}일\n")
    rows = get_daily_trend(creds, days=days)
    _print_table(rows)
    return rows


def task_report_to_sheets(creds, sheet_url: str, days: int = 7, top: int = 100, **kwargs):
    """캠페인/키워드/일별 트렌드를 구글 시트에 업데이트"""
    if not sheet_url:
        print("[오류] --sheet_url 이 필요합니다.")
        return

    from agent.google_sheets import SheetsWriter
    print(f"\n[시트 업데이트] {sheet_url[:60]}...")
    writer = SheetsWriter(sheet_url)

    camp_rows = get_campaign_stats(creds, days=days)
    kw_rows   = get_keyword_stats(creds, days=days, top_n=top)
    day_rows  = get_daily_trend(creds, days=30)

    writer.update_tab("캠페인실적", camp_rows)
    writer.update_tab("키워드실적", kw_rows)
    writer.update_tab("일별트렌드", day_rows)
    print("\n구글 시트 업데이트 완료!")


# ── 메인 ────────────────────────────────────────────────────────────────────

TASKS = {
    "campaign_stats":    task_campaign_stats,
    "keyword_stats":     task_keyword_stats,
    "daily_trend":       task_daily_trend,
    "report_to_sheets":  task_report_to_sheets,
}


def main():
    parser = argparse.ArgumentParser(description="Naver SA 자동화 에이전트")
    parser.add_argument("--task",      required=True, choices=list(TASKS.keys()),
                        help="실행할 태스크")
    parser.add_argument("--days",      type=int, default=7,   help="조회 기간(일)")
    parser.add_argument("--top",       type=int, default=100, help="키워드 상위 N개")
    parser.add_argument("--sheet_url", type=str, default="",  help="구글 시트 URL 또는 ID")
    args = parser.parse_args()

    creds = get_creds_from_env()
    if not creds[0]:
        print("[오류] NAVER_API_KEY 환경변수가 없습니다. .env 파일을 확인하세요.")
        sys.exit(1)

    fn = TASKS[args.task]
    fn(creds=creds, days=args.days, top=args.top, sheet_url=args.sheet_url)


if __name__ == "__main__":
    main()
