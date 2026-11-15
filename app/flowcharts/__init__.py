"""
Flowchart builder package.
"""
from flask import Blueprint

flowcharts_bp = Blueprint("flowcharts", __name__, url_prefix="/flowcharts")

from app.flowcharts import routes  # noqa: E402, F401
