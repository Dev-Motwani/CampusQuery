"""
Authentication utilities, security decorators, and rate limiting.
"""
from functools import wraps
from datetime import datetime, timedelta
from flask import session, redirect, url_for, flash, request, abort, jsonify
from app.database import db
from app.models.user import User

# In-memory login attempt tracker for rate limiting: key: ip_or_email -> list of timestamps
_FAILED_LOGIN_ATTEMPTS = {}
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def record_failed_login(identifier: str):
    """Records a failed login attempt for the given identifier (IP or email)."""
    now = datetime.utcnow()
    attempts = _FAILED_LOGIN_ATTEMPTS.get(identifier, [])
    # Filter out attempts older than LOCKOUT_MINUTES
    cutoff = now - timedelta(minutes=LOCKOUT_MINUTES)
    attempts = [t for t in attempts if t > cutoff]
    attempts.append(now)
    _FAILED_LOGIN_ATTEMPTS[identifier] = attempts


def is_rate_limited(identifier: str) -> bool:
    """Checks if the identifier has exceeded the maximum allowed failed attempts."""
    now = datetime.utcnow()
    attempts = _FAILED_LOGIN_ATTEMPTS.get(identifier, [])
    cutoff = now - timedelta(minutes=LOCKOUT_MINUTES)
    valid_attempts = [t for t in attempts if t > cutoff]
    _FAILED_LOGIN_ATTEMPTS[identifier] = valid_attempts
    return len(valid_attempts) >= MAX_FAILED_ATTEMPTS


def clear_failed_logins(identifier: str):
    """Clears failed login attempts upon successful login."""
    if identifier in _FAILED_LOGIN_ATTEMPTS:
        del _FAILED_LOGIN_ATTEMPTS[identifier]


def get_current_user():
    """Fetches the current authenticated User object from session, or returns None."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    user = db.session.get(User, user_id)
    if not user or not user.is_active:
        session.clear()
        return None
    return user


def login_required(f):
    """Decorator ensuring that a route requires an authenticated user."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            if request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json":
                return jsonify({"error": "Unauthorized", "message": "Authentication required."}), 401
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for("auth.login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator ensuring that a route requires an authenticated administrator."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            if request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json":
                return jsonify({"error": "Unauthorized", "message": "Authentication required."}), 401
            flash("Administrator sign-in required.", "warning")
            return redirect(url_for("auth.login", next=request.url))

        if session.get("user_role") != "admin":
            if request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json":
                return jsonify({"error": "Forbidden", "message": "Administrator privileges required."}), 403
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
