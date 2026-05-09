def build_local_keywords(profile):

    regions = profile.get("regions", [])

    services = profile.get("products", [])

    result = []

    for r in regions:

        for s in services:

            result.append(f"{r} {s}")
            result.append(f"{r} {s} 가격")
            result.append(f"{r} {s} 추천")
            result.append(f"{r} {s} 후기")

    return list(dict.fromkeys(result))