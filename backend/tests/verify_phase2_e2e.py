import asyncio
import json
import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from app.main import app
from db import database


async def main():
    await database.init()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        print("--- [1] Checking API Health ---")
        health_resp = await client.get("/health")
        print("Health:", health_resp.status_code, health_resp.json())
        assert health_resp.status_code == 200

        print("\n--- [2] Uploading Real Resume (Nasdaq.pdf) ---")
        with open("tests/fixtures/Nasdaq.pdf", "rb") as f:
            pdf_bytes = f.read()

        upload_resp = await client.post(
            "/api/resume/upload",
            files={"file": ("Nasdaq.pdf", pdf_bytes, "application/pdf")}
        )
        print("Upload status:", upload_resp.status_code)
        assert upload_resp.status_code == 200
        upload_data = upload_resp.json()
        cand_id = upload_data["candidate_id"]
        print(f"Candidate ID: {cand_id}")
        print("Candidate Name:", upload_data["profile"]["personal"]["name"])
        print("Education Extracted:", json.dumps(upload_data["profile"]["education"], indent=2))

        print("\n--- [3] Fetching Detailed Profile Validation ---")
        val_resp = await client.get(f"/api/profile/{cand_id}/validation")
        assert val_resp.status_code == 200
        val_data = val_resp.json()
        print("Experience Level:", val_data["experience_level"])
        print("Completeness Score:", val_data["completeness_score"])
        print("Warnings:", val_data["warnings"])
        print("Suggestions:", val_data["suggestions"])

        print("\n--- [4] Generating Fine-Tuned SBERT Career Role Recommendations ---")
        rec_resp = await client.post(f"/api/profile/{cand_id}/recommendations?top_n=5")
        assert rec_resp.status_code == 200
        rec_data = rec_resp.json()
        print(f"Total Recommendations: {rec_data['total_recommended']}")
        for idx, rec in enumerate(rec_data["recommendations"]):
            print(f"  #{idx+1}: {rec['role_title']} (Similarity: {rec['similarity_score']})")
            print(f"      Matching Skills: {rec['matching_skills']}")
            print(f"      Missing Skills:  {rec['missing_skills'][:3]}")
            print(f"      Explanation:     {rec['explanation']}")

        print("\n--- [5] Retrieving Persisted Recommendations from DB ---")
        get_rec_resp = await client.get(f"/api/profile/{cand_id}/recommendations")
        assert get_rec_resp.status_code == 200
        assert len(get_rec_resp.json()["recommendations"]) == len(rec_data["recommendations"])
        print("Persistence check PASSED! Stored recommendations successfully retrieved.")

    print("\nALL PHASE 2 E2E CHECKS PASSED PERFECTLY!")


if __name__ == "__main__":
    asyncio.run(main())
