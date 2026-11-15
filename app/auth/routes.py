"""
Authentication routes for CampusQuery.
Handles student registration, user login, logout, and profile inspection.
"""
from flask import render_template, request, redirect, url_for, flash, session, jsonify
from app.auth import auth_bp
from app.auth.utils import (
    record_failed_login,
    is_rate_limited,
    clear_failed_logins,
    login_required,
    get_current_user,
    LOCKOUT_MINUTES
)
from app.models.user import User
from app.database import db


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """
    Student registration endpoint.
    Strictly restricted to 'student' role. Public registration of 'admin' accounts is rejected.
    """
    if session.get("user_id"):
        return redirect(url_for("student.dashboard"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        roll_number = request.form.get("roll_number", "").strip().upper()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Server-side validation
        errors = []
        if not full_name:
            errors.append("Full name is required.")
        if not email or "@" not in email:
            errors.append("A valid email address is required.")
        if not roll_number:
            errors.append("Roll number is required for student registration.")
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long.")
        if password != confirm_password:
            errors.append("Passwords do not match.")

        # Check for existing email
        if User.query.filter_by(email=email).first():
            errors.append("An account with this email address already exists.")

        # Check for existing roll number
        if roll_number and User.query.filter_by(roll_number=roll_number).first():
            errors.append("An account with this roll number already exists.")

        # Explicit Security Rule: Ignore any client-sent 'role' field and enforce 'student'
        if request.form.get("role") and request.form.get("role").lower() != "student":
            errors.append("Public registration for administrative accounts is strictly prohibited.")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template(
                "auth/register.html",
                full_name=full_name,
                email=email,
                roll_number=roll_number
            ), 400

        # Create new student user
        new_student = User(
            full_name=full_name,
            email=email,
            roll_number=roll_number,
            role="student",
            is_active=True
        )
        new_student.set_password(password)

        try:
            db.session.add(new_student)
            db.session.commit()
            flash("Registration successful! You can now sign in with your credentials.", "success")
            return redirect(url_for("auth.login"))
        except Exception as e:
            db.session.rollback()
            flash("A database error occurred during registration. Please try again.", "danger")
            return render_template("auth/register.html"), 500

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """
    User login endpoint for students and administrators.
    Enforces password verification, account-status checks, and rate limiting.
    """
    if session.get("user_id"):
        if session.get("user_role") == "admin":
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("student.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        ip_addr = request.remote_addr or "127.0.0.1"

        # Rate Limiting Check (Task 13)
        rate_key = f"{ip_addr}:{email}"
        if is_rate_limited(rate_key) or is_rate_limited(ip_addr):
            flash(f"Too many failed login attempts. Please wait {LOCKOUT_MINUTES} minutes before trying again.", "danger")
            return render_template("auth/login.html", email=email), 429

        if not email or not password:
            flash("Please enter both email and password.", "danger")
            return render_template("auth/login.html", email=email), 400

        # Lookup user safely
        try:
            user = User.query.filter_by(email=email).first()
        except Exception as e:
            current_app.logger.error("Database connection failure in login: %s", e)
            flash("Database service is currently unreachable. Please verify your MySQL server connection.", "danger")
            return render_template("auth/login.html", email=email), 503

        # Validate credentials safely (Rule E: do not reveal whether account exists)
        if not user or not user.check_password(password):
            record_failed_login(rate_key)
            record_failed_login(ip_addr)
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html", email=email), 401

        # Account Status Check (Task 12)
        if not user.is_active:
            flash("Your account has been deactivated. Please contact the college administrator.", "danger")
            return render_template("auth/login.html", email=email), 403

        # Clear failed login attempts upon success
        clear_failed_logins(rate_key)
        clear_failed_logins(ip_addr)

        # Session Fixation Protection & Initialization (Tasks 4 & 5)
        session.clear()
        session["user_id"] = user.id
        session["user_email"] = user.email
        session["user_name"] = user.full_name
        session["user_role"] = user.role
        session.permanent = True

        flash(f"Welcome back, {user.full_name}!", "success")

        # Redirect to intended URL or role dashboard
        next_url = request.args.get("next")
        if next_url and next_url.startswith("/"):
            return redirect(next_url)

        if user.role == "admin":
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("student.dashboard"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    """Logs out the user and invalidates the session."""
    session.clear()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/profile")
@login_required
def profile():
    """Displays the authenticated user profile."""
    user = get_current_user()
    return jsonify(user.to_dict()), 200
