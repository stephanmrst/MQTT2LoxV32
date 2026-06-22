"""KNX routes.

These routes delegate to the app core handlers during the migration.
"""

from flask import Blueprint, current_app


bp = Blueprint("knx", __name__)


def _core():
    return current_app.extensions["app_core"]


@bp.route("/knx")
def knx_hub():
    return _core().knx_hub()


@bp.route("/knx_settings_embed")
def knx_settings_embed():
    return _core().knx_settings_embed()


@bp.route("/knx/save", methods=["POST"])
def knx_save():
    return _core().knx_save()


@bp.route("/knx/test", methods=["POST"])
def knx_test():
    return _core().knx_test()


@bp.route("/mqtt2knx")
def mqtt2knx():
    return _core().mqtt2knx()


@bp.route("/mqtt2knx/save", methods=["POST"])
def mqtt2knx_save():
    return _core().mqtt2knx_save()


@bp.route("/mqtt2knx/test/<int:index>", methods=["POST"])
def mqtt2knx_test(index):
    return _core().mqtt2knx_test(index)


@bp.route("/mqtt2knx_data")
def mqtt2knx_data():
    return _core().mqtt2knx_data()


@bp.route("/udp2knx")
def udp2knx():
    return _core().udp2knx()


@bp.route("/udp2knx/save", methods=["POST"])
def udp2knx_save():
    return _core().udp2knx_save()


@bp.route("/udp2knx/test/<int:index>", methods=["POST"])
def udp2knx_test(index):
    return _core().udp2knx_test(index)


@bp.route("/udp2knx_data")
def udp2knx_data():
    return _core().udp2knx_data()


@bp.route("/knx2mqtt")
def knx2mqtt():
    return _core().knx2mqtt()


@bp.route("/knx2mqtt/save", methods=["POST"])
def knx2mqtt_save():
    return _core().knx2mqtt_save()


@bp.route("/knx2mqtt_data")
def knx2mqtt_data():
    return _core().knx2mqtt_data()


@bp.route("/knx2lox")
def knx2lox():
    return _core().knx2lox()


@bp.route("/knx2lox/save", methods=["POST"])
def knx2lox_save():
    return _core().knx2lox_save()


@bp.route("/knx2lox_data")
def knx2lox_data():
    return _core().knx2lox_data()


@bp.route("/knx_monitor")
def knx_monitor():
    return _core().knx_monitor()


@bp.route("/knx_monitor_data")
def knx_monitor_data():
    return _core().knx_monitor_data()


@bp.route("/knx_monitor/influx", methods=["POST"])
def knx_monitor_influx():
    return _core().knx_monitor_influx()


@bp.route("/knx_monitor/influx_type", methods=["POST"])
def knx_monitor_influx_type():
    return _core().knx_monitor_influx_type()


@bp.route("/knx_monitor/influx_topic", methods=["POST"])
def knx_monitor_influx_topic():
    return _core().knx_monitor_influx_topic()


@bp.route("/knx_listener_start", methods=["POST"])
def knx_listener_start():
    return _core().knx_listener_start()
