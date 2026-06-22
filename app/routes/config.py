"""Config routes.

These routes delegate to the existing legacy handlers during the migration.
"""

from flask import Blueprint, current_app


bp = Blueprint("config", __name__)


def _legacy():
    return current_app.extensions["legacy_module"]


@bp.route("/settings")
def settings_page():
    return _legacy().settings_page()


@bp.route("/settings_embed")
def settings_embed():
    return _legacy().settings_embed()


@bp.route("/core_settings_embed")
def core_settings_embed():
    return _legacy().core_settings_embed()


@bp.route("/mqtt_settings_embed")
def mqtt_settings_embed():
    return _legacy().mqtt_settings_embed()


@bp.route("/influx_settings_embed")
def influx_settings_embed():
    return _legacy().influx_settings_embed()


@bp.route("/save", methods=["POST"])
def save():
    return _legacy().save()


@bp.route("/save_core", methods=["POST"])
def save_core():
    return _legacy().save_core()


@bp.route("/save_mqtt", methods=["POST"])
def save_mqtt():
    return _legacy().save_mqtt()


@bp.route("/save_influx", methods=["POST"])
def save_influx():
    return _legacy().save_influx()


@bp.route("/sidebar_links/save", methods=["POST"])
def sidebar_links_save():
    return _legacy().sidebar_links_save()


@bp.route("/plugins")
def plugins_page():
    return _legacy().plugins_page()


@bp.route("/plugins/save", methods=["POST"])
def save_plugins():
    return _legacy().save_plugins()
