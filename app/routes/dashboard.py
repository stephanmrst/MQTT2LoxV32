"""Dashboard routes.

These routes delegate to the existing legacy handlers during the migration.
"""

from flask import Blueprint, current_app


bp = Blueprint("dashboard", __name__)


def _legacy():
    return current_app.extensions["legacy_module"]


@bp.route("/")
def index():
    return _legacy().index()


@bp.route("/dashboard_embed")
def dashboard_embed():
    return _legacy().dashboard_embed()


@bp.route("/shell_status")
def shell_status():
    return _legacy().shell_status()


@bp.route("/live_log")
def live_log_console():
    return _legacy().live_log_console()


@bp.route("/live_log_page")
def live_log_page():
    return _legacy().live_log_page()


@bp.route("/live_log_data")
def live_log_data():
    return _legacy().live_log_data()


@bp.route("/clear_log")
def clear_log():
    return _legacy().clear_log()


@bp.route("/clear_monitor")
def clear_monitor():
    return _legacy().clear_monitor()
