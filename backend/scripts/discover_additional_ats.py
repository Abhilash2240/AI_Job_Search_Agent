import sqlite3
import httpx

conn = sqlite3.connect("backend/ai_job_search.db")
c = conn.cursor()

c.execute("SELECT id, canonical_name FROM companies WHERE id <= 100")
companies = c.fetchall()

found = []
with httpx.Client(timeout=4.0) as client:
    for cid, name in companies:
        slug = name.lower().replace(" ", "").replace(".", "").replace(",", "").replace("-", "")
        if len(slug) < 3:
            continue
        try:
            r = client.get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs")
            if r.status_code == 200 and len(r.json().get("jobs", [])) > 0:
                print(f"[FOUND GREENHOUSE] ID: {cid} | {name} | slug: {slug} | jobs: {len(r.json().get('jobs', []))}")
                found.append((cid, "greenhouse", slug))
                continue
        except Exception:
            pass
        try:
            r = client.get(f"https://api.lever.co/v0/postings/{slug}?mode=json")
            if r.status_code == 200 and len(r.json()) > 0:
                print(f"[FOUND LEVER] ID: {cid} | {name} | slug: {slug} | jobs: {len(r.json())}")
                found.append((cid, "lever", slug))
                continue
        except Exception:
            pass

print("Total ATS detected:", len(found))
conn.close()

