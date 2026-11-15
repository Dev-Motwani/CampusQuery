"""
Entry point for running the CampusQuery Flask application.
Supports both development server (with auto-reload) and production WSGI server.
"""
import os
import sys
import socket
from app import create_app

# Choose config based on FLASK_ENV environment variable
env = os.getenv("FLASK_ENV", "development")
app = create_app(env)

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
    is_prod = "--prod" in sys.argv or os.getenv("PRODUCTION", "").lower() in ("true", "1", "yes")
    debug_mode = (not is_prod) and os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")
    
    host = os.getenv("HOST", "0.0.0.0")
    try:
        port = int(os.getenv("PORT", 5000))
    except (ValueError, TypeError):
        port = 5000

    lan_ip = get_lan_ip()

    print("=" * 65)
    print(">> CampusQuery Application Server starting...")
    print(f">> Mode:         {'PRODUCTION (Waitress WSGI)' if is_prod else 'DEVELOPMENT (Flask)'}")
    print(f">> Environment:  {env}")
    print(f">> Debug Mode:   {debug_mode}")
    print(f">> Local URL:    http://127.0.0.1:{port}")
    print(f">> Localhost:    http://localhost:{port}")
    print(f">> Network/LAN:  http://{lan_ip}:{port}")
    print("=" * 65)

    if is_prod:
        from waitress import serve
        serve(app, host=host, port=port, threads=8)
    else:
        app.run(host=host, port=port, debug=debug_mode)
