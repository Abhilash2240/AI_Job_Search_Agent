import httpx

lever_sites = ["atlassian", "netflix", "postman", "coupa", "affirm", "cloudflare", "palantir", "auth0", "lever"]
for s in lever_sites:
    try:
        r = httpx.get(f"https://api.lever.co/v0/postings/{s}?mode=json", timeout=5.0)
        print(s, "Lever status:", r.status_code, "Jobs:", len(r.json()) if r.status_code == 200 else 0)
    except Exception as e:
        print(s, "error:", e)

