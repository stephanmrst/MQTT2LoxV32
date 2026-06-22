"""UDP routes.

These routes delegate to the app core handlers during the migration.
"""

from flask import Blueprint, current_app


bp = Blueprint("udp", __name__)


def _core():
    return current_app.extensions["app_core"]


@bp.route("/mqtt2udp")
def mqtt2udp():
    return _core().mqtt2udp()


@bp.route("/mqtt2udp/save", methods=["POST"])
def mqtt2udp_save():
    return _core().mqtt2udp_save()


@bp.route("/mqtt2udp/test/<int:index>", methods=["POST"])
def mqtt2udp_test(index):
    return _core().mqtt2udp_test(index)


@bp.route("/mqtt2udp_data")
def mqtt2udp_data():
    return _core().mqtt2udp_data()


@bp.route("/mqtt2udp/copy/<int:index>", methods=["POST"])
def mqtt2udp_copy(index):
    return _core().mqtt2udp_copy(index)


@bp.route("/udp_presets")
def udp_presets():
    return _core().udp_presets()


@bp.route("/udp_presets/save", methods=["POST"])
def udp_presets_save():
    return _core().udp_presets_save()


@bp.route("/udp2mqtt")
def udp2mqtt():
    return _core().udp2mqtt()


@bp.route("/udp2mqtt/save", methods=["POST"])
def udp2mqtt_save():
    return _core().udp2mqtt_save()


@bp.route("/udp2mqtt/test/<int:index>", methods=["POST"])
def udp2mqtt_test(index):
    return _core().udp2mqtt_test(index)


@bp.route("/udp2mqtt_data")
def udp2mqtt_data():
    return _core().udp2mqtt_data()


@bp.route("/udp_input")
def udp_input_page():
    return _core().udp_input_page()


@bp.route("/udp_input/save", methods=["POST"])
def udp_input_save():
    return _core().udp_input_save()


@bp.route("/udp_input/test", methods=["POST"])
def udp_input_test():
    return _core().udp_input_test()


@bp.route("/udp_input_data")
def udp_input_data():
    return _core().udp_input_data()


@bp.route("/udp_discovery_status")
def udp_discovery_status():
    return _core().udp_discovery_status()


@bp.route("/udp_discovery_toggle", methods=["POST"])
def udp_discovery_toggle():
    return _core().udp_discovery_toggle()
