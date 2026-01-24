import urllib.request
import urllib.error
import sys
import time

BASE_URL = "http://127.0.0.1:8001"

def test_endpoint(endpoint, description):
    print(f"Testing {description} ({endpoint})...", end=" ")
    try:
        url = f"{BASE_URL}{endpoint}"
        req = urllib.request.Request(url) # No headers = No token
        with urllib.request.urlopen(req) as resp:
            print(f"FAILED: Got {resp.status} (Expected 401)")
            return False
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print("PASSED (Got 401)")
            return True
        else:
            print(f"FAILED: Got {e.code} (Expected 401)")
            return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def verify():
    # Wait for server to be ready
    print("Waiting for server...")
    for _ in range(10):
        try:
            urllib.request.urlopen(f"{BASE_URL}/")
            print("Server is up!")
            break
        except:
            time.sleep(1)
    else:
        print("Server failed to start")
        sys.exit(1)

    results = []
    results.append(test_endpoint("/audit/list", "List Audits (No Token)"))
    results.append(test_endpoint("/user/list", "List Users (No Token)"))
    results.append(test_endpoint("/site/all", "List Sites (No Token)"))
    
    if all(results):
        print("\nAll Auth Checks PASSED")
    else:
        print("\nSome Auth Checks FAILED")
        sys.exit(1)

if __name__ == "__main__":
    verify()
