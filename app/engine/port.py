import importlib.util
import os
import sys
import types
from pathlib import Path
from platform import python_version

try:
    from app.branding import APP_LEGACY_NAME, APP_NAME, APP_SUBTITLE
except ModuleNotFoundError:
    from branding import APP_LEGACY_NAME, APP_NAME, APP_SUBTITLE

APP_VERSION = "33.2.8a"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = PROJECT_ROOT
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
BACKUP_DIR = PROJECT_ROOT / "backups"
DEPENDENCIES = {}
LOXWEBSOCKET_AVAILABLE = False
LOXWEBSOCKET_STATUS = "Loxone: Bibliothek nicht installiert"


class OptionalDependencyError(RuntimeError):
    pass


def configure_paths():
    os.environ["MQTT2LOX_APP_ROOT"] = str(APP_ROOT)
    os.environ["MQTT2LOX_CONFIG_DIR"] = str(CONFIG_DIR)
    os.environ["MQTT2LOX_DATA_DIR"] = str(DATA_DIR)
    os.environ["MQTT2LOX_BACKUP_DIR"] = str(BACKUP_DIR)
    for path in (CONFIG_DIR, DATA_DIR, BACKUP_DIR):
        path.mkdir(parents=True, exist_ok=True)


def _forced_missing(key):
    env_key = f"MQTT2LOX_FORCE_{key.upper()}_MISSING"
    return os.environ.get(env_key) == "1"


def _module_available(name, key):
    if _forced_missing(key):
        return False
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:
        return False


def _mark_dependency(key, label, module_name, required=False):
    available = _module_available(module_name, key)
    DEPENDENCIES[key] = {
        "label": label,
        "module": module_name,
        "available": available,
        "required": required,
        "status": f"{label}: Bibliothek installiert" if available else f"{label}: Bibliothek nicht installiert",
    }
    return available


def _install_requests_stub():
    if "requests" in sys.modules:
        return
    module = types.ModuleType("requests")

    class Response:
        status_code = 503
        text = ""
        content = b""

        def json(self):
            raise OptionalDependencyError("Requests: Bibliothek nicht installiert")

        def raise_for_status(self):
            raise OptionalDependencyError("Requests: Bibliothek nicht installiert")

    def _missing(*args, **kwargs):
        raise OptionalDependencyError("Requests: Bibliothek nicht installiert")

    module.get = _missing
    module.post = _missing
    module.put = _missing
    module.delete = _missing
    module.request = _missing
    module.Response = Response
    module.RequestException = OptionalDependencyError
    module.exceptions = types.SimpleNamespace(RequestException=OptionalDependencyError)
    sys.modules["requests"] = module


def _install_paho_stub():
    if "paho.mqtt.client" in sys.modules:
        return
    paho = types.ModuleType("paho")
    mqtt_package = types.ModuleType("paho.mqtt")
    client_module = types.ModuleType("paho.mqtt.client")

    class Client:
        def __init__(self, *args, **kwargs):
            self.on_message = None

        def username_pw_set(self, *args, **kwargs):
            return None

        def connect(self, *args, **kwargs):
            raise OptionalDependencyError("MQTT: Bibliothek nicht installiert")

        def disconnect(self, *args, **kwargs):
            return None

        def subscribe(self, *args, **kwargs):
            raise OptionalDependencyError("MQTT: Bibliothek nicht installiert")

        def publish(self, *args, **kwargs):
            raise OptionalDependencyError("MQTT: Bibliothek nicht installiert")

        def loop_start(self, *args, **kwargs):
            return None

        def loop_stop(self, *args, **kwargs):
            return None

    client_module.Client = Client
    mqtt_package.client = client_module
    paho.mqtt = mqtt_package
    sys.modules.setdefault("paho", paho)
    sys.modules.setdefault("paho.mqtt", mqtt_package)
    sys.modules.setdefault("paho.mqtt.client", client_module)


def _install_loxwebsocket_stub():
    if "loxwebsocket.lox_ws_api" in sys.modules:
        return
    package = types.ModuleType("loxwebsocket")
    module = types.ModuleType("loxwebsocket.lox_ws_api")

    class LoxWs:
        def __init__(self, *args, **kwargs):
            raise OptionalDependencyError(LOXWEBSOCKET_STATUS)

    module.LoxWs = LoxWs
    package.lox_ws_api = module
    sys.modules.setdefault("loxwebsocket", package)
    sys.modules.setdefault("loxwebsocket.lox_ws_api", module)


def run_startup_check():
    global LOXWEBSOCKET_AVAILABLE, LOXWEBSOCKET_STATUS
    DEPENDENCIES.clear()
    DEPENDENCIES["python"] = {
        "label": "Python",
        "module": "python",
        "available": True,
        "required": True,
        "version": python_version(),
        "status": f"Python: {python_version()}",
    }
    _mark_dependency("flask", "Flask", "flask", required=True)
    mqtt_available = _mark_dependency("mqtt", "MQTT", "paho.mqtt.client")
    loxone_available = _mark_dependency("loxwebsocket", "Loxone", "loxwebsocket.lox_ws_api")
    requests_available = _mark_dependency("requests", "Requests", "requests")
    _mark_dependency("knx", "KNX", "xknx")
    _mark_dependency("influxdb_client", "InfluxDB Client", "influxdb_client")

    LOXWEBSOCKET_AVAILABLE = loxone_available
    LOXWEBSOCKET_STATUS = DEPENDENCIES["loxwebsocket"]["status"]

    if not mqtt_available:
        _install_paho_stub()
    if not loxone_available:
        _install_loxwebsocket_stub()
    if not requests_available:
        _install_requests_stub()
    return startup_status()


def startup_status():
    return {
        "ok": True,
        "app_name": APP_NAME,
        "app_subtitle": APP_SUBTITLE,
        "app_legacy_name": APP_LEGACY_NAME,
        "version": APP_VERSION,
        "python_version": python_version(),
        "checks": DEPENDENCIES,
        "missing_optional": [
            item["label"]
            for item in DEPENDENCIES.values()
            if not item.get("available") and not item.get("required")
        ],
        "missing_required": [
            item["label"]
            for item in DEPENDENCIES.values()
            if not item.get("available") and item.get("required")
        ],
    }



