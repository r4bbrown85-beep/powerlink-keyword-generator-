# -*- coding: utf-8 -*-
"""
pre_cache.py
업종별 핵심 키워드를 매주 자동으로 사전 캐싱.
Windows 작업 스케줄러로 매주 월요일 새벽 실행.

실행: python pre_cache.py
     python pre_cache.py --industry 향수    # 특정 업종만
     python pre_cache.py --dry-run          # 캐시 현황만 확인
"""
import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── 설정 ──────────────────────────────────────────────────────
CACHE_DIR_ESTIMATE = Path("data/cache/estimate")
CACHE_DIR_KEYWORD  = Path("data/cache/keyword_stats")
CACHE_DAYS_KEYWORD = 28   # keywordstool: 월간 데이터라 4주 캐시
CACHE_DAYS_ESTIMATE = 7   # Estimate: 실시간 경매 데이터라 1주 캐시

LOG_FILE = Path("data/pre_cache_log.json")

# ── 업종별 핵심 키워드 정의 ────────────────────────────────────
# 현업에서 자주 다루는 업종들. 필요시 추가.
INDUSTRY_KEYWORDS = {
    "향수": [
        # 브랜드
        "향수", "니치향수", "명품향수", "퍼퓸", "오드퍼퓸",
        "향수 추천", "향수 선물", "향수 구매", "향수 쇼핑몰", "향수 브랜드",
        "향수 종류", "향수 매장", "향수 정품", "향수 직구", "향수 면세",
        "남자향수", "여자향수", "남성향수", "여성향수",
        "시트러스향수", "플로럴향수", "머스크향수", "우디향수", "로즈향수",
        "니치향수 추천", "니치향수 브랜드", "니치향수 매장", "니치향수 시향",
        "명품향수 추천", "명품향수 브랜드",
        # 경쟁사
        "딥디크", "딥디크 향수", "딥디크향수",
        "조말론", "조말론 향수",
        "르라보", "르라보 향수",
        "바이레도", "바이레도 향수",
        "크리드", "크리드 향수",
        "메종 프란시스 커정",
        "프레데릭말", "프레데릭말 향수",
        # 라이프스타일
        "차량용방향제", "명품차량용방향제", "고급차량용방향제",
        "룸스프레이", "방향제", "명품방향제",
        "핸드크림", "명품핸드크림", "바디워시", "핸드워시",
    ],
    "스킨케어": [
        "스킨케어", "화장품", "기초화장품", "에센스", "세럼",
        "토너", "로션", "크림", "선크림", "자외선차단제",
        "클렌징", "폼클렌저", "미셀라워터",
        "앰플", "마스크팩", "시트마스크",
        "아이크림", "립밤", "미스트",
        "수분크림", "보습크림", "재생크림",
        "여드름 화장품", "민감성 화장품", "건성 화장품",
        "한방화장품", "비건화장품", "천연화장품",
        "설화수", "후", "헤라", "이니스프리", "라네즈",
        "닥터지", "코스알엑스", "아누아", "티르티르",
    ],
    "핸드크림": [
        "핸드크림", "명품핸드크림", "니치향수핸드크림",
        "핸드크림 추천", "핸드크림 선물", "핸드로션",
        "조말론 핸드크림", "딥디크 핸드크림", "바이레도 핸드크림",
        "로레알 핸드크림", "뉴트로지나 핸드크림",
        "아토팜 핸드크림", "세타필 핸드크림",
        "건조한 손", "손 보습", "손 갈라짐",
    ],
    "건강기능식품": [
        "건강기능식품", "영양제", "비타민", "유산균", "오메가3",
        "콜라겐", "루테인", "아연", "마그네슘", "칼슘",
        "홍삼", "홍삼 추천", "홍삼 효능",
        "프로바이오틱스", "장건강", "면역력",
        "다이어트 보조제", "단백질 보충제", "BCAA",
        "멀티비타민", "비타민C", "비타민D",
    ],
    "패션": [
        "명품", "명품가방", "명품지갑", "명품신발",
        "루이비통", "샤넬", "구찌", "프라다", "에르메스",
        "코트", "패딩", "점퍼", "자켓",
        "청바지", "슬랙스", "원피스",
        "운동화", "구두", "부츠", "샌들",
        "패션 쇼핑몰", "의류 쇼핑몰",
    ],
}


def _is_cache_fresh(cache_path: Path, max_days: int) -> bool:
    """캐시가 유효한지 확인."""
    if not cache_path.exists():
        return False
    try:
        with open(cache_path, encoding="utf-8") as f:
            d = json.load(f)
        cached_at = datetime.fromisoformat(d["cached_at"])
        age_days = (datetime.now() - cached_at).days
        return age_days < max_days
    except Exception:
        return False


def check_cache_status(industries: list = None) -> dict:
    """캐시 현황 확인."""
    if industries is None:
        industries = list(INDUSTRY_KEYWORDS.keys())

    status = {}
    for ind in industries:
        keywords = INDUSTRY_KEYWORDS.get(ind, [])
        kt_fresh = 0
        est_fresh = 0
        kt_stale  = 0
        est_stale = 0

        for kw in keywords:
            import re
            safe_kw = re.sub(r'[\\/:*?"<>|]', "_", kw)
            kt_path  = CACHE_DIR_KEYWORD  / f"{safe_kw}.json"
            est_path = CACHE_DIR_ESTIMATE / f"{safe_kw}_rank_estimates.json"

            if _is_cache_fresh(kt_path, CACHE_DAYS_KEYWORD):
                kt_fresh += 1
            else:
                kt_stale += 1

            if _is_cache_fresh(est_path, CACHE_DAYS_ESTIMATE):
                est_fresh += 1
            else:
                est_stale += 1

        status[ind] = {
            "total": len(keywords),
            "kt_fresh": kt_fresh,
            "kt_stale": kt_stale,
            "est_fresh": est_fresh,
            "est_stale": est_stale,
            "kt_rate": f"{kt_fresh/len(keywords)*100:.0f}%" if keywords else "0%",
            "est_rate": f"{est_fresh/len(keywords)*100:.0f}%" if keywords else "0%",
        }
    return status


def run_pre_cache(industries: list = None, force: bool = False):
    """사전 캐싱 실행."""
    from modules.naver_keyword_api import get_keyword_stats
    from modules.naver_estimate import get_rank_based_estimates

    api_key     = os.getenv("NAVER_API_KEY", "")
    secret      = os.getenv("NAVER_SECRET_KEY", "")
    customer_id = os.getenv("NAVER_CUSTOMER_ID", "")

    if not api_key or not secret or not customer_id:
        print("❌ API 키 없음 (.env 확인)")
        return

    if industries is None:
        industries = list(INDUSTRY_KEYWORDS.keys())

    start_time = datetime.now()
    total_kt  = 0
    total_est = 0
    skipped   = 0

    print(f"{'='*60}")
    print(f"사전 캐싱 시작: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"대상 업종: {industries}")
    print(f"{'='*60}")

    for industry in industries:
        keywords = INDUSTRY_KEYWORDS.get(industry, [])
        if not keywords:
            print(f"\n[{industry}] 키워드 없음, 스킵")
            continue

        print(f"\n[{industry}] {len(keywords)}개 키워드 처리 중...")

        # 1단계: keywordstool 캐싱
        import re
        kt_need = []
        for kw in keywords:
            safe_kw = re.sub(r'[\\/:*?"<>|]', "_", kw)
            kt_path = CACHE_DIR_KEYWORD / f"{safe_kw}.json"
            if force or not _is_cache_fresh(kt_path, CACHE_DAYS_KEYWORD):
                kt_need.append(kw)
            else:
                skipped += 1

        if kt_need:
            print(f"  keywordstool 조회: {len(kt_need)}개 (캐시없음/만료)")
            # 5개씩 배치 처리
            for i in range(0, len(kt_need), 5):
                batch = kt_need[i:i+5]
                try:
                    get_keyword_stats(batch, api_key, secret, customer_id)
                    total_kt += len(batch)
                    print(f"  ✅ keywordstool {i+len(batch)}/{len(kt_need)}개 완료")
                except Exception as e:
                    print(f"  ❌ keywordstool 실패: {e}")
                time.sleep(0.3)
        else:
            print(f"  keywordstool: 모두 캐시 유효 ({len(keywords)}개 스킵)")

        # 2단계: Estimate 캐싱 (rank 기반)
        # keywordstool에서 가져온 검색량으로 rank estimate 캐싱
        from modules.naver_keyword_api import get_keyword_stats as _get_kt
        kt_data = _get_kt(keywords, api_key, secret, customer_id)

        est_need = []
        for kw in keywords:
            safe_kw = re.sub(r'[\\/:*?"<>|]', "_", kw)
            est_path = CACHE_DIR_ESTIMATE / f"{safe_kw}_rank_estimates.json"
            if force or not _is_cache_fresh(est_path, CACHE_DAYS_ESTIMATE):
                est_need.append(kw)

        if est_need:
            print(f"  Estimate 순위 탐색: {len(est_need)}개")
            for idx, kw in enumerate(est_need):
                kt = kt_data.get(kw, {})
                pc_impr = kt.get("pc_impr", 0)
                mo_impr = kt.get("mo_impr", 0)

                if pc_impr <= 0 and mo_impr <= 0:
                    print(f"  ⏭ [{kw}] 검색량 없음, 스킵")
                    continue

                try:
                    from modules.naver_estimate import get_rank_based_estimates_cached
                    get_rank_based_estimates_cached(
                        kw, api_key, secret, customer_id,
                        target_ranks=[1,2,3,4,5],
                        kt_pc_impr=pc_impr,
                        kt_mo_impr=mo_impr,
                    )
                    total_est += 1
                    if (idx+1) % 10 == 0:
                        print(f"  ✅ Estimate {idx+1}/{len(est_need)}개 완료")
                except Exception as e:
                    print(f"  ❌ [{kw}] Estimate 실패: {e}")
                time.sleep(0.2)

            print(f"  Estimate 완료: {total_est}개")
        else:
            print(f"  Estimate: 모두 캐시 유효 ({len(keywords)}개 스킵)")

    end_time = datetime.now()
    elapsed  = (end_time - start_time).seconds

    # 로그 저장
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    log = {
        "last_run":    end_time.isoformat(),
        "industries":  industries,
        "kt_cached":   total_kt,
        "est_cached":  total_est,
        "skipped":     skipped,
        "elapsed_sec": elapsed,
    }
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"완료: {end_time.strftime('%H:%M:%S')} (소요 {elapsed}초)")
    print(f"keywordstool 캐싱: {total_kt}개 / Estimate 캐싱: {total_est}개 / 스킵: {skipped}개")
    print(f"{'='*60}")


def print_schedule_guide():
    """Windows 작업 스케줄러 등록 가이드 출력."""
    script_path = Path(__file__).resolve()
    python_path = sys.executable

    print("""
=== Windows 작업 스케줄러 등록 방법 ===

1. 작업 스케줄러 열기: Win+R → taskschd.msc

2. [기본 작업 만들기] 클릭

3. 설정:
   - 이름: Powerlink 키워드 사전 캐싱
   - 트리거: 매주 월요일 오전 3:00
   - 동작: 프로그램 시작
""")
    print(f'   프로그램: {python_path}')
    print(f'   인수: "{script_path}"')
    print(f'   시작 위치: {script_path.parent}')
    print("""
4. [마침] 클릭

또는 PowerShell로 자동 등록:
""")
    print(f'''$action  = New-ScheduledTaskAction -Execute "{python_path}" -Argument "{script_path}" -WorkingDirectory "{script_path.parent}"
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At "03:00"
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 2)
Register-ScheduledTask -TaskName "Powerlink_PreCache" -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest''')


def main():
    parser = argparse.ArgumentParser(description="Powerlink 키워드 사전 캐싱")
    parser.add_argument("--industry", "-i", nargs="+",
                        help=f"캐싱할 업종 (기본: 전체). 선택: {list(INDUSTRY_KEYWORDS.keys())}")
    parser.add_argument("--dry-run", "-d", action="store_true",
                        help="캐시 현황만 확인 (API 호출 없음)")
    parser.add_argument("--force", "-f", action="store_true",
                        help="캐시 유효기간 무시하고 강제 갱신")
    parser.add_argument("--schedule", "-s", action="store_true",
                        help="Windows 작업 스케줄러 등록 가이드 출력")
    parser.add_argument("--add-industry", "-a", nargs="+",
                        metavar="KEYWORD",
                        help="업종 키워드 추가 (예: --add-industry 업종명 키워드1 키워드2)")
    args = parser.parse_args()

    if args.schedule:
        print_schedule_guide()
        return

    industries = args.industry or list(INDUSTRY_KEYWORDS.keys())

    # 업종 추가
    if args.add_industry and len(args.add_industry) >= 2:
        ind_name = args.add_industry[0]
        kws = args.add_industry[1:]
        INDUSTRY_KEYWORDS[ind_name] = kws
        print(f"✅ [{ind_name}] 업종 추가: {kws}")

    if args.dry_run:
        print("=== 캐시 현황 ===")
        status = check_cache_status(industries)
        for ind, s in status.items():
            print(f"\n[{ind}] 총 {s['total']}개 키워드")
            print(f"  keywordstool: {s['kt_fresh']}개 유효 / {s['kt_stale']}개 만료 ({s['kt_rate']})")
            print(f"  Estimate:     {s['est_fresh']}개 유효 / {s['est_stale']}개 만료 ({s['est_rate']})")

        if LOG_FILE.exists():
            with open(LOG_FILE) as f:
                log = json.load(f)
            print(f"\n마지막 실행: {log.get('last_run', '없음')}")
        return

    run_pre_cache(industries=industries, force=args.force)


if __name__ == "__main__":
    main()