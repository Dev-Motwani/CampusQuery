"""
Student and public portal routes.
"""
from datetime import datetime
from flask import Blueprint, render_template, jsonify, current_app

student_bp = Blueprint("student", __name__)


@student_bp.route("/")
def index():
    """Main landing page for CampusQueri."""
    return render_template("student/index.html")


@student_bp.route("/api/health")
def healthcheck():
    """System health check endpoint for testing and diagnostics."""
    return jsonify({
        "status": "healthy",
        "app": "CampusQueri",
        "version": "1.0.0",
        "environment": current_app.config.get("ENV", "development"),
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })
