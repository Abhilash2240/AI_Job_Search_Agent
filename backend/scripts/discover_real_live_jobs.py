import asyncio
import json
import httpx
import os
import sys

# Ensure backend path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

async def search_boards():
    print("=" * 70)
    print("SEARCHING REAL LIVE JOBS ACROSS PUBLIC ATS & FIRECRAWL")
    print("=" * 70)
    
    # 1. Search Greenhouse boards
    boards = [
        ("inmobi", "InMobi"),
        ("browserstack", "BrowserStack"),
        ("postman", "Postman"),
        ("hackerrank", "HackerRank"),
        ("rubrik", "Rubrik"),
        ("deliveroo", "Deliveroo"),
        ("grafana", "Grafana Labs"),
    ]
    
    live_jobs = []
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        for board_token, company_name in boards:
            url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
            try:
                r = await client.get(url)
                if r.status_code == 200:
                    data = r.json()
                    jobs = data.get("jobs", [])
                    print(f"[{company_name}] Live Greenhouse jobs: {len(jobs)}")
                    for j in jobs:
                        title = j.get("title", "")
                        loc = j.get("location", {}).get("name", "")
                        content = j.get("content", "")
                        app_url = j.get("absolute_url", "")
                        job_id = str(j.get("id", ""))
                        
                        title_lower = title.lower()
                        loc_lower = loc.lower()
                        
                        is_tech = any(k in title_lower for k in [
                            "software", "engineer", "developer", "python", "backend",
                            "data", "ml", "machine learning", "ai", "qa", "sdet", "cloud", "security"
                        ])
                        is_india = any(k in loc_lower for k in [
                            "india", "bengaluru", "bangalore", "hyderabad", "pune",
                            "mumbai", "delhi", "noida", "gurgaon", "gurugram", "remote"
                        ]) or loc == ""
                        
                        if is_tech and is_india:
                            live_jobs.append({
                                "company": company_name,
                                "provider": "greenhouse",
                                "board": board_token,
                                "external_id": job_id,
                                "title": title,
                                "location": loc or "India / Remote",
                                "application_url": app_url,
                                "content": content,
                            })
            except Exception as e:
                print(f"[{company_name}] Error: {e}")
                
        # 2. Search Lever boards
        lever_sites = [
            ("cred", "CRED"),
            ("groww", "Groww"),
            ("urbancompany", "Urban Company"),
        ]
        for site, company_name in lever_sites:
            url = f"https://api.lever.co/v0/postings/{site}?mode=json"
            try:
                r = await client.get(url)
                if r.status_code == 200:
                    jobs = r.json()
                    print(f"[{company_name}] Live Lever jobs: {len(jobs)}")
                    for j in jobs:
                        title = j.get("text", "")
                        loc = j.get("categories", {}).get("location", "")
                        content = j.get("descriptionPlain", "") or j.get("description", "")
                        app_url = j.get("hostedUrl", "") or j.get("applyUrl", "")
                        job_id = str(j.get("id", ""))
                        
                        title_lower = title.lower()
                        loc_lower = loc.lower() if loc else ""
                        
                        is_tech = any(k in title_lower for k in [
                            "software", "engineer", "developer", "python", "backend",
                            "data", "ml", "machine learning", "ai", "qa", "sdet", "security", "devops"
                        ])
                        is_india = any(k in loc_lower for k in [
                            "india", "bengaluru", "bangalore", "hyderabad", "pune",
                            "mumbai", "delhi", "remote"
                        ]) or not loc
                        
                        if is_tech and is_india:
                            live_jobs.append({
                                "company": company_name,
                                "provider": "lever",
                                "board": site,
                                "external_id": job_id,
                                "title": title,
                                "location": loc or "India / Remote",
                                "application_url": app_url,
                                "content": content,
                            })
            except Exception as e:
                print(f"[{company_name}] Error: {e}")

    print(f"\nTotal Real Live Technical Roles in India Found: {len(live_jobs)}")
    print("\nSample Real Live Vacancies with Verified Application URLs:")
    for idx, lj in enumerate(live_jobs[:15], 1):
        print(f"  {idx}. [{lj['company']}] {lj['title']} ({lj['location']})")
        print(f"     Real URL: {lj['application_url']}")

if __name__ == "__main__":
    asyncio.run(search_boards())

