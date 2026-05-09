import requests
import re
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_daum_suggestions(query):
    query = str(query).strip()
    if not query:
        return []

    url = "https://suggest.search.daum.net/suggest"
    params = {
        "q": query,
        "mod": "json",
        "code": "utf_in_out"
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://search.daum.net/"
    }

    try:
        r = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=10,
            verify=False
        )

        print(f"[DAUM] query={query} status={r.status_code}")

        if r.status_code != 200:
            print("[DAUM] HTTP ERROR")
            return []

        text = r.text

        m = re.search(r'"items"\s*:\s*\[(.*?)\]', text, re.S)

        if not m:
            print("[DAUM] no match")
            return []

        raw = m.group(1)
        found = re.findall(r'"([^"]+)"', raw)

        suggestions = list(dict.fromkeys([x.strip() for x in found if x.strip()]))

        print(f"[DAUM] suggestions={len(suggestions)}")

        return suggestions

    except Exception as e:
        print("[DAUM] ERROR:", e)
        return []