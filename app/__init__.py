"""Application factory for MP-Gateway."""

from .engine import port
from .branding import APP_LEGACY_NAME, APP_NAME, APP_SUBTITLE


def _register_blueprints(app):
    from .routes.api import bp as api_bp
    from .routes.backup import bp as backup_bp
    from .routes.config import bp as config_bp
    from .routes.dashboard import bp as dashboard_bp
    from .routes.events import bp as events_bp
    from .routes.influx import bp as influx_bp
    from .routes.knx import bp as knx_bp
    from .routes.loxone import bp as loxone_bp
    from .routes.mqtt import bp as mqtt_bp
    from .routes.objects import bp as objects_bp
    from .routes.objects_v33 import bp as objects_v33_bp
    from .routes.system import bp as system_bp
    from .routes.udp import bp as udp_bp
    from .routes.update import bp as update_bp

    blueprints = (
        dashboard_bp,
        config_bp,
        backup_bp,
        objects_bp,
        objects_v33_bp,
        mqtt_bp,
        udp_bp,
        loxone_bp,
        influx_bp,
        api_bp,
        events_bp,
        knx_bp,
        system_bp,
        update_bp,
    )
    for blueprint in blueprints:
        if blueprint.name not in app.blueprints:
            app.register_blueprint(blueprint)


def create_app():
    """Create the Flask application."""
    port.configure_paths()
    port.run_startup_check()

    from . import core

    core.APP_VERSION = port.APP_VERSION
    core.LOXWEBSOCKET_AVAILABLE = port.LOXWEBSOCKET_AVAILABLE
    core.LOXWEBSOCKET_STATUS = port.LOXWEBSOCKET_STATUS

    if not port.LOXWEBSOCKET_AVAILABLE:
        try:
            core.runtime_context.bridge.status = port.LOXWEBSOCKET_STATUS
        except Exception:
            pass
        try:
            core.add_log_entry(port.LOXWEBSOCKET_STATUS)
        except Exception:
            pass

    app = core.app
    app.config["APP_VERSION"] = port.APP_VERSION
    app.config["APP_NAME"] = APP_NAME
    app.config["APP_SUBTITLE"] = APP_SUBTITLE
    app.config["APP_LEGACY_NAME"] = APP_LEGACY_NAME
    app.config["PORT_MODE"] = "v32"
    app.config["LOXWEBSOCKET_AVAILABLE"] = port.LOXWEBSOCKET_AVAILABLE
    app.config["STARTUP_STATUS"] = port.startup_status()
    app.config["JSON_AS_ASCII"] = False
    if hasattr(app, "json"):
        app.json.ensure_ascii = False

    app.extensions["app_core"] = core
    app.extensions["runtime_context"] = core.runtime_context

    _register_blueprints(app)

    @app.context_processor
    def inject_app_identity():
        return {
            "app_name": APP_NAME,
            "app_subtitle": APP_SUBTITLE,
            "app_legacy_name": APP_LEGACY_NAME,
            "app_version": port.current_app_version(),
        }

    if "startup_status_route" not in app.view_functions:
        @app.route("/startup_status")
        def startup_status_route():
            return port.startup_status()

    return app
