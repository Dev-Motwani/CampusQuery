"""
Application Factory for CampusQuery.
Configures logging, error handlers, database extensions, and modular blueprints.
"""
import os
import logging
from flask import Flask, render_template, jsonify, request
from flask_wtf.csrf import CSRFProtect, CSRFError
from app.config import config_by_name, Config
from app.database import db as sqlalchemy_db

csrf = CSRFProtect()


def configure_logging(app):
    """Configures structured development logging without leaking secrets."""
    log_level = logging.DEBUG if app.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="[%(asctime)s] %(levelname)s in %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    app.logger.setLevel(log_level)
    app.logger.info("Logging initialized at %s level", logging.getLevelName(log_level))


def register_error_handlers(app):
    """Registers safe error handlers supporting both JSON APIs and HTML browser views."""

    def is_api_request():
        return (
            request.path.startswith("/api/")
            or request.path in ("/health", "/api/health")
            or request.accept_mimetypes.best == "application/json"
        )

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        if is_api_request():
            return jsonify({"error": "Bad Request", "message": f"CSRF verification failed: {e.description}"}), 400
        return render_template("errors/400.html", title="CSRF Verification Failed", error=f"CSRF verification failed: {e.description}"), 400

    @app.errorhandler(400)
    def bad_request(e):
        if is_api_request():
            return jsonify({"error": "Bad Request", "message": str(e.description if hasattr(e, 'description') else e)}), 400
        return render_template("errors/400.html", title="Bad Request", error=str(e.description if hasattr(e, 'description') else e)), 400

    @app.errorhandler(403)
    def forbidden(e):
        if is_api_request():
            return jsonify({"error": "Forbidden", "message": "Access denied"}), 403
        return render_template("errors/403.html", title="Access Denied", error="You do not have permission to access this administrative resource."), 403

    @app.errorhandler(404)
    def page_not_found(e):
        if is_api_request():
            return jsonify({"error": "Not Found", "message": "The requested resource was not found"}), 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def request_entity_too_large(e):
        msg = "Uploaded file exceeds the maximum permitted size limit (16 MB)."
        if is_api_request():
            return jsonify({"error": "Payload Too Large", "message": msg}), 413
        return render_template("errors/400.html", title="File Too Large", error=msg), 413

    @app.errorhandler(500)
    def internal_server_error(e):
        app.logger.error("Internal Server Error: %s", str(e), exc_info=True)
        if is_api_request():
            return jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred"}), 500
        return render_template("errors/500.html"), 500


def create_app(config_name="default"):
    """
    Flask Application Factory.
    Args:
        config_name (str): Configuration environment ('development', 'testing', 'production')
    Returns:
        Flask: Configured application instance
    """
    app = Flask(__name__)

    # Load configuration
    app_config = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(app_config)

    # Validate configuration (Task 6)
    validation = app_config.validate(env_name=config_name)
    if validation["warnings"]:
        for warning in validation["warnings"]:
            logging.getLogger("campusquery.config").warning("Config warning: %s", warning)

    # Initialize Logging
    configure_logging(app)

    # Ensure upload directories exist
    os.makedirs(app.config["DOCUMENTS_UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["FLOWCHARTS_UPLOAD_FOLDER"], exist_ok=True)

    # Initialize extensions
    sqlalchemy_db.init_app(app)
    csrf.init_app(app)

    # Context Processor for current_user
    from app.auth.utils import get_current_user

    @app.context_processor
    def inject_template_globals():
        user = get_current_user()
        unread_notifications_count = 0
        if user and getattr(user, "role", None) == "student":
            try:
                from app.models.notification import Notification
                unread_notifications_count = Notification.query.filter_by(user_id=user.id, is_read=False).count()
            except Exception:
                unread_notifications_count = 0
        return {
            "current_user": user,
            "unread_notifications_count": unread_notifications_count
        }

    # Register Blueprints
    from app.student import student_bp
    from app.auth import auth_bp
    from app.admin import admin_bp
    from app.assistant import assistant_bp
    from app.documents import documents_bp
    from app.flowcharts import flowcharts_bp

    app.register_blueprint(student_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(assistant_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(flowcharts_bp)

    # Register Error Handlers
    register_error_handlers(app)

    return app
