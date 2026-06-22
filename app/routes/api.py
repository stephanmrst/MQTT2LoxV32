"""API, search, and conflict routes.

These routes delegate to the app core handlers during the migration.
"""

from flask import Blueprint, current_app


bp = Blueprint("api", __name__)


def _core():
    return current_app.extensions["app_core"]


@bp.route("/global_search")
def global_search():
    return _core().global_search()


@bp.route("/global_search_page")
def global_search_page():
    return _core().global_search_page()


@bp.route("/conflicts")
def conflicts():
    return _core().conflicts()


@bp.route("/conflicts_page")
def conflicts_page():
    return _core().conflicts_page()
