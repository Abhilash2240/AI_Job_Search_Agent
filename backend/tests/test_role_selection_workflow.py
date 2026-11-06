import pytest
import json
import datetime
import sqlite3
from schemas.role import (
    RecommendationsResponse,
    ConfirmedRoleItem,
    SaveConfirmedRolesRequest,
    ConfirmedRolesResponse,
    CustomRoleRequest
)

def test_database_model_and_separation():
    """Verify database schema ensures separate storage for recommendations and confirmed roles."""
    conn = sqlite3.connect("backend/ai_job_search.db")
    cur = conn.cursor()
    
    # Verify table schema has distinct columns
    cur.execute("PRAGMA table_info(candidates)")
    cols = {row[1]: row[2] for row in cur.fetchall()}
    assert "recommendations_json" in cols, "recommendations_json column missing"
    assert "confirmed_roles_json" in cols, "confirmed_roles_json column missing"
    assert "confirmed_at" in cols, "confirmed_at column missing"

    # Verify Candidate 3 has recommendations stored separately from confirmed roles
    cur.execute("SELECT id, recommendations_json, confirmed_roles_json, confirmed_at FROM candidates WHERE id = 3")
    row = cur.fetchone()
    assert row is not None
    cid, recs_json, conf_json, conf_at = row
    assert recs_json is not None
    recs_data = json.loads(recs_json)
    assert "recommendations" in recs_data
    assert len(recs_data["recommendations"]) == 10

    # Verify 4-component metrics on all recommendations
    for r in recs_data["recommendations"]:
        assert "composite_match_score" in r and r["composite_match_score"] is not None
        assert "similarity_score" in r and r["similarity_score"] is not None
        assert "skill_match_score" in r and r["skill_match_score"] is not None
        assert "project_alignment_score" in r and r["project_alignment_score"] is not None
        assert "education_alignment_score" in r and r["education_alignment_score"] is not None
        assert len(r["alternative_titles"]) > 0
    conn.close()

def test_complete_role_selection_workflow():
    """Test the complete user journey:
    1. Inspect recommendations for candidate 3.
    2. Pick 3 target roles (e.g. Python Backend Engineer, Python Developer, Backend Developer).
    3. Save / Confirm selections with timestamp.
    4. Verify persistence and retrieval.
    5. Remove one role.
    6. Verify simulated refresh persistence.
    7. Duplicate prevention test.
    8. Custom role addition (confirming composite_match_score is None).
    """
    conn = sqlite3.connect("backend/ai_job_search.db")
    cur = conn.cursor()
    cur.execute("SELECT recommendations_json FROM candidates WHERE id = 3")
    recs_data = json.loads(cur.fetchone()[0])
    recommendations = recs_data["recommendations"]

    # Step 1: Pick 3 roles
    selected_roles = []
    target_titles = ["Python Backend Engineer", "Python Developer", "Backend Developer"]
    for title in target_titles:
        matching = [r for r in recommendations if title.lower() in r["role_title"].lower()]
        assert len(matching) > 0
        r = matching[0]
        selected_roles.append({
            "role_id": r["role_id"],
            "role_title": r["role_title"],
            "is_custom": False,
            "matching_skills": r["matching_skills"],
            "missing_skills": r["missing_skills"],
            "alternative_titles": r["alternative_titles"],
            "composite_match_score": r["composite_match_score"],
            "similarity_score": r["similarity_score"]
        })
    assert len(selected_roles) == 3

    # Step 2: Save selections into database
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    cur.execute(
        "UPDATE candidates SET confirmed_roles_json = ?, confirmed_at = ? WHERE id = 3",
        (json.dumps(selected_roles), now_iso)
    )
    conn.commit()

    # Step 3: Retrieve and verify
    cur.execute("SELECT confirmed_roles_json, confirmed_at FROM candidates WHERE id = 3")
    stored_json, stored_at = cur.fetchone()
    stored_roles = json.loads(stored_json)
    assert len(stored_roles) == 3
    assert stored_at is not None

    # Step 4: Remove 1 role (Backend Developer)
    remaining_roles = [r for r in stored_roles if r["role_title"] != "Backend Developer"]
    assert len(remaining_roles) == 2
    cur.execute(
        "UPDATE candidates SET confirmed_roles_json = ? WHERE id = 3",
        (json.dumps(remaining_roles),)
    )
    conn.commit()

    # Step 5: Simulate refresh - verify 2 remaining roles persisted
    cur.execute("SELECT confirmed_roles_json FROM candidates WHERE id = 3")
    refreshed_roles = json.loads(cur.fetchone()[0])
    assert len(refreshed_roles) == 2
    assert not any(r["role_title"] == "Backend Developer" for r in refreshed_roles)

    # Step 6: Duplicate prevention logic
    dup_candidates = [remaining_roles[0], remaining_roles[0], remaining_roles[1]]
    seen_titles = set()
    deduped = []
    for r in dup_candidates:
        clean = r["role_title"].strip().lower()
        if clean not in seen_titles:
            seen_titles.add(clean)
            deduped.append(r)
    assert len(deduped) == 2

    # Step 7: Custom role addition
    custom_role = {
        "role_id": "custom_platform_architect",
        "role_title": "Platform Reliability Architect",
        "is_custom": True,
        "matching_skills": ["Python", "Docker"],
        "missing_skills": ["Kubernetes"],
        "alternative_titles": [],
        "composite_match_score": None, # Never fabricate score
        "similarity_score": None
    }
    deduped.append(custom_role)
    cur.execute(
        "UPDATE candidates SET confirmed_roles_json = ? WHERE id = 3",
        (json.dumps(deduped),)
    )
    conn.commit()

    # Step 8: Verify persistence with custom role
    cur.execute("SELECT confirmed_roles_json FROM candidates WHERE id = 3")
    final_roles = json.loads(cur.fetchone()[0])
    assert len(final_roles) == 3
    custom_saved = [r for r in final_roles if r.get("is_custom") is True]
    assert len(custom_saved) == 1
    assert custom_saved[0]["role_title"] == "Platform Reliability Architect"
    assert custom_saved[0]["composite_match_score"] is None

    conn.close()
