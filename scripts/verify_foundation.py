"""
Automated Verification Script for Phase 1: Workspace Audit and Flask Foundation.
Complies with Permanent Engineering Rules A-G.
"""
import sys
import os
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Force UTF-8 encoding for Windows console compatibility
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def run_verification():
    passed = 0
    total = 0

    print("=" * 65)
    print(" [CAMPUSQUERY] PHASE 1 FOUNDATION VERIFICATION REPORT")
    print("=" * 65)

    # 1. Dependency Imports Check
    print("\n[1/6] Checking Required Dependencies...")
    dependencies = [
        ("Flask", "flask"),
        ("Flask-SQLAlchemy", "flask_sqlalchemy"),
        ("mysql-connector-python", "mysql.connector"),
        ("PyMySQL (Pure Python Driver)", "pymysql"),
        ("Cryptography", "cryptography"),
        ("python-dotenv", "dotenv"),
        ("Werkzeug", "werkzeug"),
        ("Google GenAI SDK", "google.genai"),
    ]
    for name, module in dependencies:
        total += 1
        try:
            __import__(module)
            print(f"  [PASS] {name:<32} Loaded successfully")
            passed += 1
        except ImportError as e:
            print(f"  [FAIL] {name:<32} Failed: {e}")

    # 2. Directory Structure Check (Phase 1 structure)
    print("\n[2/6] Checking Directory Structure...")
    directories = [
        "app",
        "app/auth",
        "app/student",
        "app/admin",
        "app/assistant",
        "app/documents",
        "app/flowcharts",
        "app/models",
        "app/static/css",
        "app/static/js",
        "app/templates/auth",
        "app/templates/admin",
        "app/templates/student",
        "app/templates/errors",
        "uploads/documents",
        "uploads/flowcharts",
        "scripts",
    ]
    for d in directories:
        total += 1
        target = PROJECT_ROOT / d
        if target.is_dir():
            print(f"  [PASS] Directory: {d:<26} Exists")
            passed += 1
        else:
            print(f"  [FAIL] Directory: {d:<26} Missing!")

    # 3. Critical Files Check
    print("\n[3/6] Checking Configuration & Source Files...")
    files = [
        ".env",
        ".env.example",
        ".gitignore",
        "schema.sql",
        "requirements.txt",
        "run.py",
        "README.md",
        "ENGINEERING_RULES.md",
        "app/__init__.py",
        "app/config.py",
        "app/database.py",
        "app/auth/__init__.py",
        "app/auth/routes.py",
        "app/student/__init__.py",
        "app/student/routes.py",
        "app/admin/__init__.py",
        "app/admin/routes.py",
        "app/templates/base.html",
        "app/templates/student/index.html",
        "app/templates/auth/login.html",
        "app/templates/admin/dashboard.html",
        "app/templates/errors/404.html",
        "app/templates/errors/500.html",
        "app/static/css/style.css",
        "app/static/js/main.js",
    ]
    for f in files:
        total += 1
        target = PROJECT_ROOT / f
        if target.is_file():
            print(f"  [PASS] File: {f:<31} Exists ({target.stat().st_size} bytes)")
            passed += 1
        else:
            print(f"  [FAIL] File: {f:<31} Missing!")

    # 4. Configuration Validation Behavior (Task 6)
    print("\n[4/6] Testing Configuration Validation Behavior...")
    from app.config import Config, ProductionConfig

    # Test dev validation
    total += 1
    dev_val = Config.validate(env_name="development")
    if dev_val["valid"]:
        print(f"  [PASS] Development Config Validation Passed (Warnings: {len(dev_val['warnings'])})")
        passed += 1
    else:
        print(f"  [FAIL] Development Config Validation Failed: {dev_val['issues']}")

    # Test invalid config raises error in production
    total += 1
    try:
        orig_key = ProductionConfig.SECRET_KEY
        ProductionConfig.SECRET_KEY = ""
        try:
            ProductionConfig.validate(env_name="production")
            print("  [FAIL] Production validation did not reject empty SECRET_KEY")
        except ValueError:
            print("  [PASS] Production validation correctly rejected empty SECRET_KEY")
            passed += 1
        finally:
            ProductionConfig.SECRET_KEY = orig_key
    except Exception as e:
        print(f"  [FAIL] Unexpected error during validation test: {e}")

    # 5. Flask App Factory & Route Execution
    print("\n[5/6] Testing Flask Application Factory & Endpoints...")
    total += 1
    try:
        from app import create_app
        test_app = create_app("testing")
        print("  [PASS] Flask App Factory instance created successfully")
        passed += 1
    except Exception as e:
        print(f"  [FAIL] App creation failed: {e}")
        test_app = None

    if test_app:
        client = test_app.test_client()

        # Test GET / (Student Landing)
        total += 1
        res_home = client.get("/")
        if res_home.status_code == 200 and b"Campus" in res_home.data:
            print("  [PASS] GET / (Landing Page)           HTTP 200 OK & Content Verified")
            passed += 1
        else:
            print(f"  [FAIL] GET / failed: Status {res_home.status_code}")

        # Test GET /health (Standard Healthcheck)
        total += 1
        res_health = client.get("/health")
        if res_health.status_code == 200 and res_health.is_json:
            data = res_health.json
            if data.get("app") == "CampusQuery" and "database" in data and "status" in data:
                # Security check: ensure no password in healthcheck output
                raw_text = res_health.data.decode("utf-8")
                if "password" not in raw_text.lower() and "secret" not in raw_text.lower():
                    print(f"  [PASS] GET /health (Secure Health)    HTTP 200 OK (Status: {data.get('status')}, Secrets Masked)")
                    passed += 1
                else:
                    print("  [FAIL] Security alert: Health endpoint contains credential keywords")
            else:
                print("  [FAIL] Health JSON missing required keys")
        else:
            print(f"  [FAIL] GET /health failed: Status {res_health.status_code}")

        # Test GET /api/health alias
        total += 1
        res_api_health = client.get("/api/health")
        if res_api_health.status_code == 200 and res_api_health.is_json:
            print("  [PASS] GET /api/health (Alias)        HTTP 200 OK & Consistent")
            passed += 1
        else:
            print(f"  [FAIL] GET /api/health failed: Status {res_api_health.status_code}")

        # Test Custom 404 Handler (JSON for API path)
        total += 1
        res_404_api = client.get("/api/non-existent-endpoint")
        if res_404_api.status_code == 404 and res_404_api.is_json:
            print("  [PASS] GET /api/404 (JSON Error)      HTTP 404 & JSON Payload Returned")
            passed += 1
        else:
            print(f"  [FAIL] 404 API handler failed: Status {res_404_api.status_code}")

        # Test Custom 404 Handler (HTML for browser path)
        total += 1
        res_404_html = client.get("/non-existent-page")
        if res_404_html.status_code == 404 and b"Notice or Page Not Found" in res_404_html.data:
            print("  [PASS] GET /page/404 (HTML Error)     HTTP 404 & Custom Template Rendered")
            passed += 1
        else:
            print(f"  [FAIL] 404 HTML handler failed: Status {res_404_html.status_code}")

    # 6. Security & Secret Leakage Inspection (Rule E)
    print("\n[6/6] Checking Git Ignore & Secret Exclusion...")
    total += 1
    gitignore_path = PROJECT_ROOT / ".gitignore"
    if gitignore_path.is_file():
        gi_content = gitignore_path.read_text(encoding="utf-8")
        if ".env" in gi_content and ".venv" in gi_content and "*.log" in gi_content:
            print("  [PASS] .gitignore Rules               .env, .venv, *.log properly excluded")
            passed += 1
        else:
            print("  [FAIL] .gitignore missing critical exclusions")
    else:
        print("  [FAIL] .gitignore not found")

    print("\n" + "=" * 65)
    print(f" VERIFICATION SUMMARY: {passed} / {total} CHECKS PASSED")
    print("=" * 65)

    if passed == total:
        print("\n*** PHASE 1 VERIFICATION SUCCESSFUL: Foundation is fully solid! ***")
        return 0
    else:
        print(f"\n[WARNING] PHASE 1 VERIFICATION INCOMPLETE: {total - passed} checks failed.")
        return 1


if __name__ == "__main__":
    sys.exit(run_verification())
