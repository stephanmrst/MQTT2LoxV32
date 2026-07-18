"""Config routes.

These routes delegate to the app core handlers during the migration.
"""

from flask import Blueprint, current_app


bp = Blueprint("config", __name__)


def _core():
    return current_app.extensions["app_core"]


@bp.route("/settings")
def settings_page():
    return _core().settings_page()


@bp.route("/settings_embed")
def settings_embed():
    return _core().settings_embed()


@bp.route("/core_settings_embed")
def core_settings_embed():
    return _core().core_settings_embed()


@bp.route("/mqtt_settings_embed")
def mqtt_settings_embed():
    return _core().mqtt_settings_embed()


@bp.route("/influx_settings_embed")
def influx_settings_embed():
    return _core().influx_settings_embed()


@bp.route("/save", methods=["POST"])
def save():
    return _core().save()


@bp.route("/save_core", methods=["POST"])
def save_core():
    return _core().save_core()


@bp.route("/save_mqtt", methods=["POST"])
def save_mqtt():
    return _core().save_mqtt()


@bp.route("/save_influx", methods=["POST"])
def save_influx():
    return _core().save_influx()


@bp.route("/sidebar_links/save", methods=["POST"])
def sidebar_links_save():
    return _core().sidebar_links_save()


@bp.route("/plugins")
def plugins_page():
    return _core().plugins_page()


@bp.route("/plugins/save", methods=["POST"])
def save_plugins():
    return _core().save_plugins()
