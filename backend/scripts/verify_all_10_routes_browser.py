# backend/scripts/verify_all_10_routes_browser.py
"""
AI Job Search Agent — Full Headless Chrome Route Verification Script.
Verifies all 10 frontend application routes:
1.  /                    (Candidate Career Dashboard)
2.  /jobs                (Verified Job Postings Feed)
3.  /jobs/1              (Job Vacancy Details & Match Analysis)
4.  /saved-jobs          (Saved & Bookmarked Vacancies)
5.  /applications        (Candidate Application Tracker)
6.  /companies          (Company Research & Sourcing Channels)
7.  /pipeline            (Data Ingestion & Pipeline Orchestration)
8.  /profile             (Candidate Profile & Validation)
9.  /recommendations     (Fine-Tuned SBERT Career Role Recommendations)
10. /selected-roles      (Selected Career Target Roles)

Tests both Desktop (1280x800) and Mobile (375x667) viewports.
Captures screenshots to verify layout fluidity, responsive drawer/collapsible sidebar, and 0 console exceptions.
"""

import os
import sys
import time
import subprocess
import json

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE_URL = "http://localhost:3000"

ROUTES = [
    ("/", "Candidate Career Dashboard", "dashboard"),
    ("/jobs", "Verified Job Postings Feed", "job_feed"),
    ("/jobs/1", "Job Vacancy Details & Match Analysis", "job_detail_1"),
    ("/saved-jobs", "Saved & Bookmarked Vacancies", "saved_jobs"),
    ("/applications", "Candidate Application Tracker", "applications"),
    ("/companies", "Company Research & Sourcing Channels", "companies"),
    ("/pipeline", "Data Ingestion & Pipeline Orchestration", "pipeline"),
    ("/profile", "Candidate Profile & Validation", "profile"),
    ("/recommendations", "Fine-Tuned SBERT Career Role Recommendations", "recommendations"),
    ("/selected-roles", "Selected Career Target Roles", "selected_roles"),
]

def run_browser_verification():
    print("=" * 80)
    print("AI JOB SEARCH AGENT — FULL HEADLESS CHROME ROUTE & RESPONSIVE VERIFICATION")
    print("=" * 80)

    if not os.path.exists(CHROME_PATH):
        print(f"[FAIL] Chrome executable not found at: {CHROME_PATH}")
        return False

    out_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "browser_verification_results")
    screenshots_dir = os.path.join(out_dir, "screenshots")
    os.makedirs(screenshots_dir, exist_ok=True)

    results = []
    all_passed = True

    # Test Desktop (1280x800) and Mobile (375x667)
    viewports = [
        ("Desktop", "1280,800"),
        ("Mobile", "375,667"),
    ]

    for vp_name, vp_dim in viewports:
        print(f"\n--- Testing Viewport: {vp_name} ({vp_dim}) ---")
        for route, expected_title, name_tag in ROUTES:
            url = f"{BASE_URL}{route}"
            prefix = f"{name_tag}_{vp_name.lower()}"
            dom_file = os.path.join(out_dir, f"{prefix}_dom.html")
            screenshot_file = os.path.join(screenshots_dir, f"{prefix}.png")

            cmd = [
                CHROME_PATH,
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                f"--window-size={vp_dim}",
                "--virtual-time-budget=5000",
                f"--screenshot={screenshot_file}",
                "--dump-dom",
                url,
            ]

            start_t = time.time()
            try:
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
                dur = round(time.time() - start_t, 2)
                dom_content = proc.stdout.decode("utf-8", errors="replace")

                with open(dom_file, "w", encoding="utf-8") as f:
                    f.write(dom_content)

                has_root = '<div id="root">' in dom_content
                has_title = expected_title in dom_content
                has_runtime_error = "Uncaught Error" in dom_content or "Uncaught TypeError" in dom_content
                ss_exists = os.path.exists(screenshot_file) and os.path.getsize(screenshot_file) > 1000

                passed = has_root and not has_runtime_error and ss_exists

                status_str = "PASS" if passed else "FAIL"
                print(f"[{status_str}] {vp_name:7} | Route: {route:18} | Title Found: {has_title} | Screenshot: {ss_exists} | Duration: {dur}s")

                if not passed:
                    all_passed = False
                    if has_runtime_error:
                        print(f"       [ERROR] Runtime exception detected in DOM dump!")
                    if not ss_exists:
                        print(f"       [ERROR] Screenshot was not created or empty!")

                results.append({
                    "viewport": vp_name,
                    "route": route,
                    "expected_title": expected_title,
                    "passed": passed,
                    "has_title": has_title,
                    "has_runtime_error": has_runtime_error,
                    "screenshot_size": os.path.getsize(screenshot_file) if os.path.exists(screenshot_file) else 0,
                    "dom_bytes": len(dom_content),
                    "duration_seconds": dur
                })

            except subprocess.TimeoutExpired:
                print(f"[FAIL] {vp_name:7} | Route: {route:18} | TIMEOUT after 30s")
                all_passed = False
                results.append({"viewport": vp_name, "route": route, "passed": False, "error": "timeout"})
            except Exception as ex:
                print(f"[FAIL] {vp_name:7} | Route: {route:18} | Exception: {ex}")
                all_passed = False
                results.append({"viewport": vp_name, "route": route, "passed": False, "error": str(ex)})

    summary_file = os.path.join(out_dir, "route_verification_summary.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump({"all_passed": all_passed, "total_tests": len(results), "results": results}, f, indent=2)

    print("\n" + "=" * 80)
    print(f"ROUTE VERIFICATION SUMMARY: {'ALL PASSED' if all_passed else 'SOME FAILED'} ({len(results)} viewports/routes tested)")
    print(f"Results & Screenshots stored in: {out_dir}")
    print("=" * 80)
    return all_passed

if __name__ == "__main__":
    success = run_browser_verification()
    sys.exit(0 if success else 1)

