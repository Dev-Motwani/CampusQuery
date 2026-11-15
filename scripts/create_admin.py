"""
Controlled Admin Account Creation Script for CampusQuery (Phase 3).
Permits creating or updating administrator accounts safely with password hashing.
Usage:
    python scripts/create_admin.py --email admin@campusqueri.edu --name "Admin Name" --password "StrongPass123"
    Or run interactively without arguments.
"""
import sys
import argparse
import getpass
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

from app import create_app
from app.database import db
from app.models.user import User


def create_or_update_admin(email, name, password, app=None):
    """Creates or updates an admin user in the database."""
    if app is None:
        app = create_app("development")

    with app.app_context():
        if len(password) < 8:
            print(">> [ERROR] Password must be at least 8 characters long.")
            return False

        user = User.query.filter_by(email=email).first()
        if user:
            print(f">> Existing account found for '{email}'. Updating to administrator role and resetting password...")
            user.full_name = name
            user.role = "admin"
            user.is_active = True
            user.set_password(password)
        else:
            print(f">> Creating new administrator account for '{email}'...")
            user = User(
                email=email,
                full_name=name,
                roll_number=None,
                role="admin",
                is_active=True
            )
            user.set_password(password)
            db.session.add(user)

        try:
            db.session.commit()
            print(f">> [PASS] Administrator account '{email}' configured successfully!")
            return True
        except Exception as e:
            db.session.rollback()
            print(f">> [ERROR] Failed to save administrator to database: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description="Create or update a CampusQuery administrator account.")
    parser.add_argument("--email", help="Administrator email address")
    parser.add_argument("--name", help="Administrator full name")
    parser.add_argument("--password", help="Administrator password")

    args = parser.parse_args()

    email = args.email
    name = args.name
    password = args.password

    if not email:
        email = input("Enter Administrator Email: ").strip().lower()
    if not name:
        name = input("Enter Administrator Full Name: ").strip()
    if not password:
        password = getpass.getpass("Enter Administrator Password (min 8 chars): ")
        confirm = getpass.getpass("Confirm Password: ")
        if password != confirm:
            print(">> [ERROR] Passwords do not match.")
            sys.exit(1)

    app = create_app("development")
    success = create_or_update_admin(email, name, password, app)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
