"""
Production WSGI Entry Point for CampusQuery.
Runs with Waitress production WSGI server on Windows/Linux.
Supports multi-threading and handles production traffic efficiently.
"""
import os
import sys
import socket
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app

env = os.getenv("FLASK_ENV", "production")
app = create_app(env)

# Ensure database tables and seed data exist upon cloud startup
try:
    with app.app_context():
        from app.database import db
        from app.models.user import User
        from scripts.seed_demo import seed_demo_data
        db.create_all()
        if not User.query.first():
            seed_demo_data(app=app, verbose=True)
except Exception as e:
    app.logger.warning("Database cloud auto-init notice: %s", e)

def get_lan_ip():
    """Detect local network IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

if __name__ == "__main__":
    from waitress import serve
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 5000))
    lan_ip = get_lan_ip()

    print("=" * 65)
    print(" [CAMPUSQUERY] PRODUCTION WSGI SERVER (Waitress)")
    print("=" * 65)
    print(f">> Environment:    {env}")
    print(f">> Local URL:      http://127.0.0.1:{port}")
    print(f">> Localhost URL:  http://localhost:{port}")
    print(f">> Network/LAN URL:http://{lan_ip}:{port}")
    print(f">> Bound Host:     {host}:{port}")
    print(f">> Worker Threads: 8")
    print("=" * 65)
    print(">> Server is live and accepting front-end & API requests.")
    print(">> Press Ctrl+C to stop the server.")

    serve(app, host=host, port=port, threads=8)
