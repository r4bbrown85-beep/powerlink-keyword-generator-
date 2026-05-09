import json
import os
from datetime import datetime

from dotenv import load_dotenv

from modules.naver_estimate_api import (
    get_exposure_minimum_bid_keyword,
    try_estimate_patterns,
)

load_dotenv()


def save_json(data, filename):
    os.makedirs("output", exist_ok=True)
    path = os.path.join("output", filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def main():
    keyword = "프레데릭말"
    bids = [300, 420]
    devices = ["PC", "MOBILE"]

    print("================================")
    print("1) 최소노출입찰가 테스트")
    print("================================")
    for device in devices:
        res = get_exposure_minimum_bid_keyword([keyword], device=device)
        status = "✅" if res["ok"] else "❌"
        print(f"[{device}] {status} status={res['status_code']}")
        print(res["data"])

        save_path = save_json(
            res,
            f"estimate_min_bid_{device}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        print("saved:", save_path)

    print()
    print("================================")
    print("2) performance-bulk 패턴 테스트")
    print("================================")

    # 패턴 테스트는 PC / bid=300 한 번만 해도 충분
    # 성공 패턴 찾으면 거기서 끝
    found_pattern = None

    for bid in bids[:1]:  # 300원만 우선 테스트
        for device in devices[:1]:  # PC만 우선 테스트
            print(f"\n[{device}] bid={bid} 테스트 중...")
            res = try_estimate_patterns(keyword, bid, device=device)

            for item in res["results"]:
                status = "✅ 성공" if item["ok"] else "❌ 실패"
                print(f"  {status} | {item['name']} | HTTP {item['status_code']}")

                if item["ok"]:
                    print("  >>> 응답 데이터:", json.dumps(item["data"], ensure_ascii=False, indent=4))
                    found_pattern = item["name"]
                else:
                    # 실패 이유 간략히
                    detail = item["data"].get("detail", "")
                    fields = item["data"].get("fields", "")
                    if detail or fields:
                        print(f"       이유: {detail} | {fields}")

            save_path = save_json(
                res,
                f"estimate_probe_{device}_{bid}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            print(f"\n  결과 저장: {save_path}")

    print()
    print("================================")
    if found_pattern:
        print(f"🎉 성공 패턴: {found_pattern}")
        print("→ 이 패턴을 naver_estimate.py에 적용하면 됩니다!")
    else:
        print("❌ 모든 패턴 실패")
        print("→ output 폴더의 JSON 파일을 확인하고 에러 메시지를 공유해주세요")
    print("================================")


if __name__ == "__main__":
    main()
