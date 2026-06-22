"""Object manager routes.

These routes delegate to the existing legacy handlers during the migration.
"""

from flask import Blueprint, current_app


bp = Blueprint("objects", __name__)


def _legacy():
    return current_app.extensions["legacy_module"]


@bp.route("/objects")
def objects():
    return _legacy().objects()


@bp.route("/objects/edit/<object_id>")
def objects_edit(object_id):
    return _legacy().objects_edit(object_id)


@bp.route("/objects/sync_from_mappings", methods=["POST"])
def objects_sync_from_mappings():
    return _legacy().objects_sync_from_mappings()


@bp.route("/objects/rebuild_mappings", methods=["POST"])
def objects_rebuild_mappings():
    return _legacy().objects_rebuild_mappings()


@bp.route("/objects/save", methods=["POST"])
def objects_save():
    return _legacy().objects_save()


@bp.route("/objects/delete", methods=["POST"])
def objects_delete():
    return _legacy().objects_delete()


@bp.route("/objects/delete_all", methods=["POST"])
def objects_delete_all():
    return _legacy().objects_delete_all()
