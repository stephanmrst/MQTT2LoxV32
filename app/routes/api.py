"""API, search, and conflict routes.

These routes delegate to the app core handlers during the migration.
"""

from flask import Blueprint, current_app, jsonify, request

try:
    from app.services import object_service
except ModuleNotFoundError:
    from services import object_service


bp = Blueprint("api", __name__)


def _core():
    return current_app.extensions["app_core"]


def _reload_object_routes():
    core = _core()
    if hasattr(core, "reload_object_routes"):
        core.reload_object_routes()


def _sync_object_live_from_core():
    try:
        core = _core()
    except Exception:
        return
    try:
        for info in getattr(core, "get_mqtt_monitor_values", lambda: {})().values():
            if isinstance(info, dict):
                object_service.record_live_value("mqtt", info.get("payload"), topic=info.get("topic", ""), timestamp=info.get("timestamp", info.get("time", "")))
    except Exception:
        current_app.logger.exception("Object live MQTT sync failed")
    try:
        for ga, info in getattr(core, "get_knx_monitor_values", lambda: {})().items():
            if isinstance(info, dict):
                object_service.record_live_value("knx", info.get("value"), group_address=info.get("ga", ga), timestamp=info.get("timestamp", info.get("time", "")))
    except Exception:
        current_app.logger.exception("Object live KNX sync failed")
    try:
        for topic, info in getattr(core, "get_udp_last_seen", lambda kind: {})("udp2mqtt").items():
            if isinstance(info, dict):
                object_service.record_live_value("udp", info.get("value"), udp_topic=topic, timestamp=info.get("timestamp", info.get("time", "")))
    except Exception:
        current_app.logger.exception("Object live UDP sync failed")


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


@bp.route("/api/objects")
def api_objects_list():
    objects = [object_service.serialize_object(item) for item in object_service.list_objects()]
    return jsonify({"objects": objects})


@bp.route("/api/objects/<object_id>")
def api_objects_get(object_id):
    item = object_service.get_object(object_id)
    if item is None:
        return jsonify({"success": False, "error": "object_not_found"}), 404
    return jsonify(object_service.serialize_object(item))


@bp.route("/api/objects/live")
def api_objects_live():
    _sync_object_live_from_core()
    return jsonify({"objects": object_service.list_object_live_status()})


@bp.route("/api/objects/<object_id>/live")
def api_objects_live_get(object_id):
    _sync_object_live_from_core()
    live = object_service.get_object_live_status(object_id)
    if live is None:
        return jsonify({"success": False, "error": "object_not_found"}), 404
    return jsonify(live)


@bp.route("/api/objects", methods=["POST"])
def api_objects_create():
    try:
        payload = request.get_json(silent=True) or request.form.to_dict()
        item = object_service.create_object(payload)
        _reload_object_routes()
        return jsonify({"success": True, "object": object_service.serialize_object(item)}), 201
    except Exception as exc:
        current_app.logger.exception("Object create failed: %s", exc)
        return jsonify({"success": False, "error": "object_create_failed"}), 500


@bp.route("/api/objects/<object_id>", methods=["PUT"])
def api_objects_update(object_id):
    try:
        payload = request.get_json(silent=True) or request.form.to_dict()
        item = object_service.update_object(object_id, payload)
        if item is None:
            return jsonify({"success": False, "error": "object_not_found"}), 404
        _reload_object_routes()
        return jsonify({"success": True, "object": object_service.serialize_object(item)})
    except Exception as exc:
        current_app.logger.exception("Object update failed: %s", exc)
        return jsonify({"success": False, "error": "object_update_failed"}), 500


@bp.route("/api/objects/<object_id>", methods=["DELETE"])
def api_objects_delete(object_id):
    try:
        deleted = object_service.delete_object(object_id)
        if not deleted:
            return jsonify({"success": False, "error": "object_not_found"}), 404
        _reload_object_routes()
        return jsonify({"success": True})
    except Exception as exc:
        current_app.logger.exception("Object delete failed: %s", exc)
        return jsonify({"success": False, "error": "object_delete_failed"}), 500


@bp.route("/api/objects/<object_id>/toggle", methods=["POST"])
def api_objects_toggle(object_id):
    try:
        payload = request.get_json(silent=True) or request.form.to_dict()
        enabled = payload.get("enabled", True)
        if isinstance(enabled, str):
            enabled = enabled.lower() in {"1", "true", "yes", "on"}
        item = object_service.toggle_object(object_id, bool(enabled))
        if item is None:
            return jsonify({"success": False, "error": "object_not_found"}), 404
        _reload_object_routes()
        return jsonify({"success": True, "object": object_service.serialize_object(item)})
    except Exception as exc:
        current_app.logger.exception("Object toggle failed: %s", exc)
        return jsonify({"success": False, "error": "object_toggle_failed"}), 500
