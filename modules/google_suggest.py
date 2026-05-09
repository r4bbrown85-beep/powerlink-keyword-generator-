import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_google_suggestions(query):
    query = str(query).strip()
    if not query:
        return []

    url = "https://suggestqueries.google.com/complete/search"
    params = {
        "client": "firefox",
        "hl": "ko",
        "q": query
    }

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        r = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=10,
            verify=False
        )

        print(f"[GOOGLE] query={query} status={r.status_code}")

        if r.status_code != 200:
            print("[GOOGLE] HTTP ERROR")
            return []

        data = r.json()

        if len(data) < 2:
            print("[GOOGLE] invalid response")
            return []

        suggestions = data[1]

        if not isinstance(suggestions, list):
            print("[GOOGLE] not list")
            return []

        suggestions = list(dict.fromkeys([str(x).strip() for x in suggestions if str(x).strip()]))

        print(f"[GOOGLE] suggestions={len(suggestions)}")

        return suggestions

    except Exception as e:
        print("[GOOGLE] ERROR:", e)
        return []