import json
import urllib.request
import urllib.error
import sys

BASE_URL = "http://127.0.0.1:8000"

def make_request(method, endpoint, data=None, token=None):
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    encoded_data = json.dumps(data).encode("utf-8") if data else None
    
    req = urllib.request.Request(url, data=encoded_data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as e:
        return e.code, e.reason
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def login(email, password):
    url = f"{BASE_URL}/auth/login"
    
    # Endpoint expects JSON (UserLogin schema), not form data
    data = json.dumps({
        "email": email,      # Schema uses "email", not "username"
        "password": password
    }).encode("utf-8")
    
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    
    try:
        with urllib.request.urlopen(req) as resp:
            return json.load(resp)["access_token"]
    except urllib.error.HTTPError as e:
        print(f"Login failed for {email}: {e.code} {e.reason}")
        print(e.read().decode("utf-8"))
        sys.exit(1)

def test_security():
    print("Logging in...")
    token_admin1 = login("admin_c1@example.com", "password123")
    token_auditor1 = login("auditor_c1@example.com", "password123")
    token_admin2 = login("admin_c2@example.com", "password123")

    print("\n[TEST 1] Auditor trying Admin API (Create Site)...")
    status, _ = make_request("POST", "/site/create", {"name": "Hacker Site", "location": "Unknown"}, token_auditor1)
    if status == 403:
        print("✅ Blocked correctly (403)")
    else:
        print(f"❌ FAILED: Got {status}")

    print("\n[TEST 2] Cross-Company Usage (Admin1 accessing Admin2 User)...")
    # Get Admin2's user ID by searching list as Admin2
    _, users = make_request("GET", "/user/list", token=token_admin2)
    admin2_id = users[0]["id"]
    
    # Try using PUT (Update) since GET /user/{id} doesn't exist
    status, _ = make_request("PUT", f"/user/{admin2_id}", {"name": "Hacked Name"}, token=token_admin1)
    if status == 404:
        print("✅ Blocked correctly (id hidden -> 404)")
    else:
        print(f"❌ FAILED: Got {status} (Expected 404)")

    print("\n[TEST 3] Enumeration (Auditor1 -> Unassigned Audit)...")
    # Admin1 creates site and audit
    _, site_resp = make_request("POST", "/site/create", {"name": "Safe Site", "location": "Here"}, token_admin1)
    site_id = site_resp.get("id") if isinstance(site_resp, dict) else None
    
    if site_id:
        _, audit_resp = make_request("POST", "/audit/create", {
            "title": "Secret Audit", "audit_type": "Internal", "site_id": site_id,
            "scope": "All", "start_date": "2026-01-01T00:00:00", "end_date": "2026-01-01T00:00:00"
        }, token_admin1)
        audit_id = audit_resp.get("audit_id")

        # Auditor1 tries to view it
        status, _ = make_request("GET", f"/audit/detail/{audit_id}", token=token_auditor1)
        if status == 404:
            print("✅ Blocked correctly (id hidden -> 404)")
        else:
            print(f"❌ FAILED: Got {status} (Expected 404)")

        print("\n[TEST 4] Safe Delete (Audit with Findings)...")
        # Add finding
        make_request("POST", "/finding/create", {
            "audit_id": audit_id, "category": "Safety", "finding_type": "NC",
            "description": "Bad thing", "likelihood": 5, "severity": 5, "area": "Lab"
        }, token_admin1)
        
        # Try delete
        status, _ = make_request("DELETE", f"/audit/{audit_id}", token=token_admin1)
        if status == 400:
            print("✅ Blocked correctly (Current findings -> 400)")
        else:
            print(f"❌ FAILED: Got {status} (Expected 400)")
    else:
        print("Skipping dependent tests (Site creation failed)")

    print("\n[TEST 5] Integrity (Remove Assigned Auditor)...")
    # create a new auditor for this test to avoid conflicts
    _, user_resp = make_request("POST", "/user/create", {
        "email": "victim@example.com", "password": "password123", "role": "auditor", "name": "Victim"
    }, token_admin1)
    auditor_id = user_resp.get("user_id")

    if auditor_id and audit_id:
        # Assign to audit
        make_request("PUT", f"/audit/team/{audit_id}", [auditor_id], token_admin1)
        
        # Try delete
        status, _ = make_request("DELETE", f"/user/{auditor_id}", token=token_admin1)
        if status == 400:
             print("✅ Blocked correctly (Assigned to audit -> 400)")
        else:
             print(f"❌ FAILED: Got {status} (Expected 400)")
    else:
        print("Skipping Test 5 (User creation failed)")

if __name__ == "__main__":
    test_security()
