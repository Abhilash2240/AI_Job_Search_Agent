import sqlite3
import httpx

conn = sqlite3.connect("backend/ai_job_search.db")
cur = conn.cursor()

# Get first 60 companies
cur.execute("SELECT id, canonical_name FROM companies LIMIT 60")
companies = cur.fetchall()
conn.close()

found_lever = []
with httpx.Client(timeout=3.0) as client:
    for cid, name in companies:
        slug = name.lower().replace(" ", "").replace(".", "").replace(",", "").replace("-", "")
        if len(slug) < 3:
            continue
        try:
            r = client.get(f"https://api.lever.co/v0/postings/{slug}?mode=json")
            if r.status_code == 200 and len(r.json()) > 0:
                print(f"FOUND LEVER: {name} (ID: {cid}, slug: {slug}) -> {len(r.json())} jobs")
                found_lever.append((cid, name, slug, len(r.json())))
        except Exception:
            pass

print("Total found Lever:", len(found_lever))

