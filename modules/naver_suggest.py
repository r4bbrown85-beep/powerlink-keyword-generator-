import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_naver_suggestions(query):
    query = str(query).strip()
    if not query:
        return []

    url = "https://ac.search.naver.com/nx/ac"
    params = {
        "q": query,
        "con": 0,
        "frm": "nv",
        "ans": 2,
        "r_format": "json",
        "r_enc": "UTF-8",
        "st": 100
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://search.naver.com/"
    }

    try:
        r = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=10,
            verify=False
        )

        print(f"[NAVER] query={query} status={r.status_code}")

        if r.status_code != 200:
            print("[NAVER] HTTP ERROR")
            return []

        data = r.json()
        items = data.get("items", [])

        if not items:
            print("[NAVER] no items")
            return []

        suggestions = []

        for item in items[0]:
            if isinstance(item, list) and len(item) >= 1:
                kw = str(item[0]).strip()
                if kw:
                    suggestions.append(kw)

        suggestions = list(dict.fromkeys(suggestions))
        print(f"[NAVER] suggestions={len(suggestions)}")

        return suggestions

    except Exception as e:
        print("[NAVER] ERROR:", e)
        return []