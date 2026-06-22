"""Backup routes.

These routes delegate to the existing legacy handlers during the migration.
"""

from flask import Blueprint, current_app


bp = Blueprint("backup", __name__)


def _legacy():
    return current_app.extensions["legacy_module"]


@bp.route("/backup")
def backup_config():
    return _legacy().backup_config()


@bp.route("/restore", methods=["POST"])
def restore_config():
    return _legacy().restore_config()
