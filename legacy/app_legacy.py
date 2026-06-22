# === MQTT2Lox Sidebar Shell Layout Legacy UI Cleanup Objektmanager - 2026-06-17 ===
import asyncio
import json
import os
import re
import threading
import time
import requests
import socket
import subprocess
import shutil
import paho.mqtt.client as mqtt
import zipfile
import io
from flask import Flask, request, render_template_string, redirect, send_file, Response, stream_with_context
from markupsafe import escape
from loxwebsocket.lox_ws_api import LoxWs
from collections import deque
from urllib.parse import quote
from urllib.parse import quote
from services import config
from services import mqtt as mqtt_module
from services import udp
from services import object as object_service
from services import loxone as loxone_service
from services import knx as knx_service
from services import influx as influx_service
from services import runtime as runtime_service
from services import backup as backup_service
from services import template as template_service
try:
    from app.runtime.context import create_runtime_context
except ModuleNotFoundError:
    from runtime.context import create_runtime_context

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# -----------------------------------------------------------------------------
# Docker-/Standalone-Pfade
# -----------------------------------------------------------------------------
# Im Docker-Container liegen persistente Dateien getrennt in:
#   /app/config   -> JSON-Konfigurationen / Mappings
#   /app/data     -> Laufzeitdaten, Mosquitto-Daten
#   /app/backups  -> spätere Backup-Ablage / Mountpoint
# Lokal unter Windows/Linux ohne Docker bleibt alles wie bisher im Script-Ordner.
APP_ROOT = os.environ.get("MQTT2LOX_APP_ROOT", "/app" if os.path.isdir("/app") else BASE_DIR)
CONFIG_DIR = os.environ.get("MQTT2LOX_CONFIG_DIR", os.path.join(APP_ROOT, "config") if os.path.isdir("/app") else BASE_DIR)
DATA_DIR = os.environ.get("MQTT2LOX_DATA_DIR", os.path.join(APP_ROOT, "data") if os.path.isdir("/app") else BASE_DIR)
BACKUP_DIR = os.environ.get("MQTT2LOX_BACKUP_DIR", os.path.join(APP_ROOT, "backups") if os.path.isdir("/app") else BASE_DIR)

for _dir in (DATA_DIR, CONFIG_DIR, BACKUP_DIR):
    os.makedirs(_dir, exist_ok=True)

CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
TOPIC_CONFIG_FILE = os.path.join(CONFIG_DIR, "topic_config.json")
MQTT2LOX_FILE = os.path.join(CONFIG_DIR, "mqtt2lox.json")
MQTT2UDP_FILE = os.path.join(CONFIG_DIR, "mqtt2udp_config.json")
UDP2MQTT_FILE = os.path.join(CONFIG_DIR, "udp2mqtt.json")
UDP_PRESETS_FILE = os.path.join(CONFIG_DIR, "udp_presets.json")
MQTT_BROKERS_FILE = os.path.join(CONFIG_DIR, "mqtt_brokers.json")
MONITOR_SETTINGS_FILE = os.path.join(CONFIG_DIR, "monitor_settings.json")
PLUGIN_CONFIG_FILE = os.path.join(CONFIG_DIR, "plugins.json")
KNX_CONFIG_FILE = os.path.join(CONFIG_DIR, "knx_config.json")
MQTT2KNX_FILE = os.path.join(CONFIG_DIR, "mqtt2knx.json")
KNX2MQTT_FILE = os.path.join(CONFIG_DIR, "knx2mqtt.json")
UDP2KNX_FILE = os.path.join(CONFIG_DIR, "udp2knx.json")
KNX2LOX_FILE = os.path.join(CONFIG_DIR, "knx2lox.json")
SIDEBAR_LINKS_FILE = os.path.join(CONFIG_DIR, "sidebar_links.json")
INTERNAL_BROKER_FILE = os.path.join(CONFIG_DIR, "internal_broker.json")
OBJECTS_FILE = os.path.join(CONFIG_DIR, "objects.json")

_json_file_lock = threading.RLock()

def safe_load_json_file(path, default_value):
    """JSON stabil lesen. Verhindert sporadische 500er bei parallelem Lesen/Schreiben."""
    with _json_file_lock:
        try:
            if not os.path.exists(path):
                return default_value
            with open(path, "r", encoding="utf-8") as f:
                raw = f.read().strip()
            if not raw:
                return default_value
            return json.loads(raw)
        except json.JSONDecodeError as e:
            add_log_entry(f"JSON Lesefehler {os.path.basename(path)}: {e}")
            return default_value
        except Exception as e:
            add_log_entry(f"JSON Lesefehler {os.path.basename(path)}: {e}")
            return default_value

def safe_save_json_file(path, data, indent=2):
    """JSON atomar schreiben. Erst temp-Datei, dann os.replace()."""
    with _json_file_lock:
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        tmp_path = f"{path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)


runtime_context = create_runtime_context()
knx_monitor_log = deque(maxlen=15)
knx_monitor_values = {}

def knx_influx_topic(group_address):
    """Stabiler Influx-/Config-Key für KNX Gruppenadressen."""
    ga = knx_service.normalize_knx_ga(group_address)
    return f"knx/{ga}" if ga else ""

def get_knx_influx_output_topic(group_address, settings=None):
    """Influx-Zieltopic für KNX. Optionaler Alias aus topic_config, sonst knx/<GA>."""
    default_topic = knx_influx_topic(group_address)
    if not settings:
        return default_topic
    alias = str(settings.get("influx_topic", "") or "").strip().strip("/")
    return alias or default_topic


def write_knx_monitor_influx(group_address, value, dpt="", direction="RX"):
    """KNX Monitor/Explorer -> Influx. Aktivierung liegt in topic_config.json unter knx/<GA>."""
    try:
        config_key = knx_influx_topic(group_address)
        if not config_key:
            return
        settings = load_topic_config().get(config_key, {})
        if not isinstance(settings, dict) or not settings.get("influx", False):
            return
        value_type = settings.get("influx_value_type", "auto")
        output_topic = get_knx_influx_output_topic(group_address, settings)
        # Field bleibt bewusst immer value. Der optionale Alias betrifft nur das Influx-Topic.
        influx_service.write_to_influx_field(output_topic, "value", value, load_config, add_log_entry, value_type=value_type)
    except Exception as e:
        try:
            add_log_entry(f"KNX Influx Fehler {group_address}: {e}")
        except Exception:
            pass

# V22: kleine Versionszähler für Live-Push per Server-Sent Events (SSE).
# Sobald sich Daten ändern, bekommen die offenen Browser direkt ein Event.
sse_versions = {"log": 0, "mqtt": 0, "status": 0}

def bump_sse(name):
    if name == "knx":
        with runtime_context.knx.lock:
            runtime_context.knx.monitor_version += 1
        return
    try:
        sse_versions[name] = int(sse_versions.get(name, 0)) + 1
    except Exception:
        sse_versions[name] = 1


def add_log_entry(text):
    with runtime_context.live_log.lock:
        runtime_service.add_log(runtime_context.live_log.entries, bump_sse, text)
        runtime_context.live_log.version += 1


def get_mqtt_monitor_values():
    with runtime_context.mqtt.lock:
        return dict(runtime_context.mqtt.mqtt_monitor_values)


def set_mqtt_monitor_value(monitor_key, value):
    with runtime_context.mqtt.lock:
        runtime_context.mqtt.mqtt_monitor_values[monitor_key] = dict(value or {})
        runtime_context.mqtt.monitor_version += 1
        return runtime_context.mqtt.mqtt_monitor_values[monitor_key]


def clear_mqtt_monitor():
    with runtime_context.mqtt.lock:
        runtime_context.mqtt.mqtt_monitor_values.clear()
        runtime_context.mqtt.monitor_version += 1


def _udp_state_bucket(kind):
    buckets = {
        "mqtt2udp": runtime_context.udp.mqtt2udp_last_seen,
        "udp2mqtt": runtime_context.udp.udp2mqtt_last_seen,
        "udp2knx": runtime_context.udp.udp2knx_last_seen,
        "udp_input": runtime_context.udp.udp_input_last_seen,
    }
    return buckets.get(kind)


def get_udp_last_seen(kind, key=None):
    with runtime_context.udp.lock:
        bucket = _udp_state_bucket(kind)
        if bucket is None:
            return {}
        if key is None:
            if bucket:
                return dict(bucket)
        else:
            if key in bucket:
                return dict(bucket.get(key, {}))
    legacy_buckets = {
        "mqtt2udp": mqtt2udp_last_seen,
        "udp2mqtt": udp2mqtt_last_seen,
        "udp2knx": udp2knx_last_seen,
        "udp_input": udp_input_last_seen,
    }
    legacy_bucket = legacy_buckets.get(kind, {})
    if key is None:
        return dict(legacy_bucket)
    return dict(legacy_bucket.get(key, {}))


def update_udp_last_seen(kind, key, value):
    with runtime_context.udp.lock:
        bucket = _udp_state_bucket(kind)
        if bucket is None:
            return {}
        bucket[key] = dict(value or {})
        return bucket[key]


def clear_udp_last_seen(kind=None):
    with runtime_context.udp.lock:
        if kind is None:
            runtime_context.udp.mqtt2udp_last_seen.clear()
            runtime_context.udp.udp2mqtt_last_seen.clear()
            runtime_context.udp.udp2knx_last_seen.clear()
            runtime_context.udp.udp_input_last_seen.clear()
            return
        bucket = _udp_state_bucket(kind)
        if bucket is not None:
            bucket.clear()


def get_broker_process():
    with runtime_context.broker.lock:
        return runtime_context.broker.process


def set_broker_process(process):
    with runtime_context.broker.lock:
        runtime_context.broker.process = process
        return runtime_context.broker.process


def update_broker_state(status=None, running=None, start_requested=None, stop_requested=None, restart_requested=None):
    with runtime_context.broker.lock:
        if status is not None:
            runtime_context.broker.status = status
        if running is not None:
            runtime_context.broker.running = bool(running)
        if start_requested is not None:
            runtime_context.broker.start_requested = bool(start_requested)
        if stop_requested is not None:
            runtime_context.broker.stop_requested = bool(stop_requested)
        if restart_requested is not None:
            runtime_context.broker.restart_requested = bool(restart_requested)


def get_broker_state():
    with runtime_context.broker.lock:
        return {
            "process": runtime_context.broker.process,
            "running": runtime_context.broker.running,
            "status": runtime_context.broker.status,
            "start_requested": runtime_context.broker.start_requested,
            "stop_requested": runtime_context.broker.stop_requested,
            "restart_requested": runtime_context.broker.restart_requested,
        }


def _knx_state_bucket(kind):
    buckets = {
        "mqtt2knx": runtime_context.knx.mqtt2knx_last_seen,
        "knx2mqtt": runtime_context.knx.knx2mqtt_last_seen,
        "knx2lox": runtime_context.knx.knx2lox_last_seen,
    }
    return buckets.get(kind)


def get_knx_last_seen(kind, key=None):
    with runtime_context.knx.lock:
        bucket = _knx_state_bucket(kind)
        if bucket is None:
            return {}
        if key is None:
            if bucket:
                return dict(bucket)
        else:
            if key in bucket:
                return dict(bucket.get(key, {}))
    legacy_buckets = {
        "mqtt2knx": mqtt2knx_last_seen,
        "knx2mqtt": knx2mqtt_last_seen,
        "knx2lox": knx2lox_last_seen,
    }
    legacy_bucket = legacy_buckets.get(kind, {})
    if key is None:
        return dict(legacy_bucket)
    return dict(legacy_bucket.get(key, {}))


def update_knx_last_seen(kind, key, value):
    with runtime_context.knx.lock:
        bucket = _knx_state_bucket(kind)
        if bucket is None:
            return {}
        bucket[key] = dict(value or {})
        return bucket[key]


def clear_knx_last_seen(kind=None):
    with runtime_context.knx.lock:
        if kind is None:
            runtime_context.knx.mqtt2knx_last_seen.clear()
            runtime_context.knx.knx2mqtt_last_seen.clear()
            runtime_context.knx.knx2lox_last_seen.clear()
            return
        bucket = _knx_state_bucket(kind)
        if bucket is not None:
            bucket.clear()


def get_knx_monitor_values():
    values = dict(knx_monitor_values)
    with runtime_context.knx.lock:
        values.update(runtime_context.knx.monitor_values)
    return values


def set_knx_monitor_value(ga, value_data):
    with runtime_context.knx.lock:
        runtime_context.knx.monitor_values[ga] = dict(value_data or {})
        return runtime_context.knx.monitor_values[ga]


def clear_knx_monitor_values():
    with runtime_context.knx.lock:
        runtime_context.knx.monitor_values.clear()


def get_knx_monitor_log():
    with runtime_context.knx.lock:
        if runtime_context.knx.monitor_log:
            return list(runtime_context.knx.monitor_log)[:15]
    return list(knx_monitor_log)[:15]


def add_knx_monitor_log_entry(entry):
    with runtime_context.knx.lock:
        runtime_context.knx.monitor_log.appendleft(dict(entry or {}))


def clear_knx_monitor_log():
    with runtime_context.knx.lock:
        runtime_context.knx.monitor_log.clear()


def get_knx_monitor_version():
    with runtime_context.knx.lock:
        return int(runtime_context.knx.monitor_version)


def get_knx_listener():
    with runtime_context.knx.lock:
        return runtime_context.knx.listener_thread


def set_knx_listener(thread):
    with runtime_context.knx.lock:
        runtime_context.knx.listener_thread = thread
        return runtime_context.knx.listener_thread


def is_knx_listener_running():
    with runtime_context.knx.lock:
        thread = runtime_context.knx.listener_thread
        running = bool(thread and thread.is_alive())
        runtime_context.knx.listener_running = running
        return running


def set_knx_listener_running(running):
    with runtime_context.knx.lock:
        runtime_context.knx.listener_running = bool(running)
        return runtime_context.knx.listener_running


def request_knx_start():
    with runtime_context.knx.lock:
        runtime_context.knx.start_requested = True
        runtime_context.knx.stop_requested = False


def request_knx_stop():
    with runtime_context.knx.lock:
        runtime_context.knx.stop_requested = True
        runtime_context.knx.start_requested = False


def add_knx_monitor_entry(group_address, value, direction="RX", dpt=""):
    """Add a KNX telegram to the live KNX monitor."""
    global knx_monitor_log, knx_monitor_values

    from datetime import datetime

    ga = knx_service.normalize_knx_ga(group_address)
    if not ga:
        ga = str(group_address or "").strip()

    entry = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "ga": ga,
        "value": str(value),
        "direction": str(direction or "RX").upper(),
        "dpt": str(dpt or "")
    }

    print("[KNX MONITOR ADD]", entry)
    knx_monitor_log.appendleft(entry)
    add_knx_monitor_log_entry(entry)
    if ga:
        knx_monitor_values[ga] = entry
        set_knx_monitor_value(ga, entry)
        write_knx_monitor_influx(ga, entry.get("value", value), entry.get("dpt", dpt), entry.get("direction", direction))
    bump_sse("knx")

def load_topic_config():
    if not os.path.exists(TOPIC_CONFIG_FILE):
        with open(TOPIC_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
        return {}

    with open(TOPIC_CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_topic_config(data):
    with open(TOPIC_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_mqtt2lox_config():
    if not os.path.exists(MQTT2LOX_FILE):
        save_mqtt2lox_config([])
        return []

    with open(MQTT2LOX_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # neue Defaults für alte Configs ergänzen
    for m in data:
        m.setdefault("payload_mode", "raw")
        m.setdefault("json_key", "")
        m.setdefault("output_mode", "single")
        m.setdefault("group", "")
        m.setdefault("set_name", "")
        m.setdefault("mapping_alias", "")

    return data


def save_mqtt2lox_config(data):
    with open(MQTT2LOX_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_mqtt2udp_config():
    if not os.path.exists(MQTT2UDP_FILE):
        save_mqtt2udp_config([])
        return []

    with open(MQTT2UDP_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        data = []

    for m in data:
        if isinstance(m, dict):
            m.setdefault("enabled", True)
            m.setdefault("group", "")
            m.setdefault("set_name", "")
            m.setdefault("mapping_alias", "")
            m.setdefault("source_topic", "")
            m.setdefault("udp_topic", "")
            m.setdefault("udp_ip", "")
            m.setdefault("udp_port", "7000")
            m.setdefault("udp_format", "topic_value")
            m.setdefault("payload_mode", "raw")
            m.setdefault("json_key", "")
            m.setdefault("test_value", "123")

    return data


def save_mqtt2udp_config(data):
    with open(MQTT2UDP_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_udp2mqtt_config():
    if not os.path.exists(UDP2MQTT_FILE):
        save_udp2mqtt_config([])
        return []
    try:
        with open(UDP2MQTT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = []
    if not isinstance(data, list):
        data = []
    for m in data:
        if isinstance(m, dict):
            m.setdefault("enabled", True)
            m.setdefault("udp_topic", "")
            m.setdefault("mqtt_topic", "")
            m.setdefault("retain", False)
            m.setdefault("test_value", "123")
            m.setdefault("group", "")
            m.setdefault("set_name", "")
            m.setdefault("mapping_alias", "")
    return data


def save_udp2mqtt_config(data):
    with open(UDP2MQTT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)




def load_mqtt_brokers():
    data = safe_load_json_file(MQTT_BROKERS_FILE, [])
    if not isinstance(data, list):
        data = []
    if not os.path.exists(MQTT_BROKERS_FILE):
        save_mqtt_brokers(data)
    return data


def save_mqtt_brokers(data):
    safe_save_json_file(MQTT_BROKERS_FILE, data if isinstance(data, list) else [], indent=2)



def load_monitor_settings():
    if not os.path.exists(MONITOR_SETTINGS_FILE):
        data = {
            "favorites": [],
            "aliases": {}
        }
        save_monitor_settings(data)
        return data

    with open(MONITOR_SETTINGS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_monitor_settings(data):
    with open(MONITOR_SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)        


DEFAULT_PLUGINS = [
    {"id": "mqtt", "name": "MQTT", "enabled": True, "status": "aktiv", "description": "Hauptbroker und zusätzliche Broker", "route": "/mqtt_settings_embed"},
    {"id": "loxone", "name": "Loxone", "enabled": True, "status": "aktiv", "description": "Loxone Websocket, HTTP und Mapping", "route": "/settings_embed"},
    {"id": "udp", "name": "UDP", "enabled": True, "status": "aktiv", "description": "MQTT → UDP und UDP → MQTT", "route": "/mqtt2udp"},
    {"id": "influx", "name": "InfluxDB", "enabled": True, "status": "aktiv", "description": "Zeitreihen-Ausgabe", "route": "/influx_settings_embed"},
    {"id": "zigbee", "name": "Zigbee", "enabled": False, "status": "vorbereitet", "description": "Reserviert für Zigbee2MQTT Links und Mapping", "route": ""},
    {"id": "knx", "name": "KNX", "enabled": False, "status": "Foundation", "description": "KNX Gateway, MQTT → KNX und KNX → MQTT", "route": "/mqtt2knx"}
]


def load_plugins_config():
    if not os.path.exists(PLUGIN_CONFIG_FILE):
        save_plugins_config(DEFAULT_PLUGINS)
        return [dict(x) for x in DEFAULT_PLUGINS]

    try:
        with open(PLUGIN_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = []

    known = {item.get("id"): item for item in data if isinstance(item, dict)}
    merged = []
    for default in DEFAULT_PLUGINS:
        item = dict(default)
        item.update(known.get(default["id"], {}))
        merged.append(item)

    save_plugins_config(merged)
    return merged


def save_plugins_config(data):
    with open(PLUGIN_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_sidebar_links():
    if not os.path.exists(SIDEBAR_LINKS_FILE):
        save_sidebar_links([])
        return []

    try:
        with open(SIDEBAR_LINKS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = []

    if not isinstance(data, list):
        data = []

    cleaned = []
    for item in data:
        if not isinstance(item, dict):
            continue
        cleaned.append({
            "enabled": bool(item.get("enabled", True)),
            "label": str(item.get("label", "")).strip(),
            "url": str(item.get("url", "")).strip(),
            "new_tab": bool(item.get("new_tab", True))
        })

    save_sidebar_links(cleaned)
    return cleaned


def save_sidebar_links(data):
    with open(SIDEBAR_LINKS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ---------- Legacy Objektverwaltung / Smart-Home Datenpunkt-Zentrale ----------
def load_objects_config():
    data = safe_load_json_file(OBJECTS_FILE, [])
    if isinstance(data, dict) and isinstance(data.get("objects"), list):
        data = data.get("objects", [])
    if not isinstance(data, list):
        data = []
    cleaned = []
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            continue
        mqtt_cfg = item.get("mqtt") if isinstance(item.get("mqtt"), dict) else {}
        loxone_cfg = item.get("loxone") if isinstance(item.get("loxone"), dict) else {}
        knx_cfg = item.get("knx") if isinstance(item.get("knx"), dict) else {}
        udp_cfg = item.get("udp") if isinstance(item.get("udp"), dict) else {}
        influx_cfg = item.get("influx") if isinstance(item.get("influx"), dict) else {}
        cleaned.append({
            "id": str(item.get("id") or f"obj_{idx+1}"),
            "enabled": bool(item.get("enabled", True)),
            "name": str(item.get("name", "") or "").strip(),
            "room": str(item.get("room", "") or "").strip(),
            "type": str(item.get("type") or item.get("datatype", "") or "").strip(),
            "mqtt_topic": str(item.get("mqtt_topic") or mqtt_cfg.get("topic", "") or "").strip(),
            "mqtt_json_key": str(item.get("mqtt_json_key", "") or "").strip(),
            "loxone_topic": str(item.get("loxone_topic") or loxone_cfg.get("uuid", "") or "").strip(),
            "knx_ga": knx_service.normalize_knx_ga(item.get("knx_ga") or knx_cfg.get("group_address", "")),
            "udp_topic": str(item.get("udp_topic") or udp_cfg.get("template", "") or "").strip(),
            "influx_topic": str(item.get("influx_topic") or influx_cfg.get("measurement", "") or "").strip(),
            "notes": str(item.get("notes", "") or "").strip(),
        })
    if not os.path.exists(OBJECTS_FILE):
        save_objects_config(cleaned)
    return cleaned


def save_objects_config(data):
    current = safe_load_json_file(OBJECTS_FILE, [])
    payload = data if isinstance(data, list) else []
    if isinstance(current, dict) and "objects" in current:
        current["objects"] = payload
        safe_save_json_file(OBJECTS_FILE, current, indent=2)
    else:
        safe_save_json_file(OBJECTS_FILE, payload, indent=2)




DEFAULT_INTERNAL_BROKER_CONFIG = {
    "enabled": False,
    "use_as_main": False,
    "host": "0.0.0.0",
    "connect_host": "127.0.0.1",
    "port": 1883,
    "allow_anonymous": True,
    "user": "",
    "password": "",
    "persistence": True,
    "mosquitto_path": "mosquitto"
}


def load_internal_broker_config():
    data = safe_load_json_file(INTERNAL_BROKER_FILE, {})
    if not isinstance(data, dict):
        data = {}

    cfg = dict(DEFAULT_INTERNAL_BROKER_CONFIG)
    cfg.update(data)

    try:
        cfg["port"] = int(cfg.get("port", 1883))
    except Exception:
        cfg["port"] = 1883

    if not os.path.exists(INTERNAL_BROKER_FILE):
        save_internal_broker_config(cfg)
    return cfg


def save_internal_broker_config(data):
    cfg = dict(DEFAULT_INTERNAL_BROKER_CONFIG)
    if isinstance(data, dict):
        cfg.update(data)
    try:
        cfg["port"] = int(cfg.get("port", 1883))
    except Exception:
        cfg["port"] = 1883
    safe_save_json_file(INTERNAL_BROKER_FILE, cfg, indent=2)


def get_backup_files():
    return backup_service.get_backup_files(CONFIG_DIR, DATA_DIR, BASE_DIR, add_log_entry)


def is_tcp_port_open(host, port, timeout=0.4):
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except Exception:
        return False


def get_internal_broker_status():
    status = runtime_service.get_internal_broker_status(load_internal_broker_config, get_broker_process())
    update_broker_state(
        status=status.get("state", "gestoppt"),
        running=bool(status.get("running", False)),
    )
    return status


def build_mosquitto_config_file(cfg):
    return runtime_service.build_mosquitto_config_file(cfg, CONFIG_DIR, DATA_DIR, add_log_entry)


def start_internal_broker_process():
    update_broker_state(start_requested=True, stop_requested=False, status="startet")
    ok, msg, process = runtime_service.start_internal_broker(
        load_internal_broker_config,
        get_internal_broker_status,
        build_mosquitto_config_file,
        add_log_entry,
        BASE_DIR,
    )
    if process is not None:
        set_broker_process(process)
    status = get_internal_broker_status()
    update_broker_state(
        status=status.get("state", msg),
        running=bool(status.get("running", ok)),
        start_requested=False,
    )
    return ok, msg


def stop_internal_broker_process():
    update_broker_state(stop_requested=True, start_requested=False, status="Stop angefordert")
    ok, msg, process = runtime_service.stop_internal_broker(get_broker_process(), add_log_entry)
    set_broker_process(process)
    status = get_internal_broker_status()
    update_broker_state(
        status=status.get("state", msg),
        running=bool(status.get("running", False)),
        stop_requested=False,
    )
    return ok, msg


def get_effective_mqtt_config(config):
    return mqtt_module.get_effective_mqtt_config(config, load_internal_broker_config)


def build_sidebar_links_html():
    links = [x for x in load_sidebar_links() if x.get("enabled") and x.get("label") and x.get("url")]
    if not links:
        return ""

    html = '<span class="spacer external-spacer"></span>'
    for item in links:
        label = escape(str(item.get("label", "")))
        url = escape(str(item.get("url", "")))
        if item.get("new_tab", True):
            html += f'<a href="{url}" target="_blank" rel="noopener" onclick="setActive(this)">{label}</a>'
        else:
            html += f'<a href="{url}" target="contentFrame" onclick="setActive(this)">{label}</a>'
    return html


DEFAULT_KNX_CONFIG = {
    "enabled": False,
    "gateway_ip": "192.168.2.10",
    "gateway_port": 3671,
    "connection_type": "tunneling",
    "local_ip": "",
    "physical_address": "1.1.250"
}


def load_knx_config():
    """KNX Gateway Config laden, ohne vorhandene Werte versehentlich zu überschreiben."""
    data = safe_load_json_file(KNX_CONFIG_FILE, None)

    if not isinstance(data, dict):
        cfg = dict(DEFAULT_KNX_CONFIG)
        if not os.path.exists(KNX_CONFIG_FILE):
            save_knx_config(cfg)
        return cfg

    cfg = dict(DEFAULT_KNX_CONFIG)
    cfg.update(data)

    try:
        cfg["gateway_port"] = int(cfg.get("gateway_port", 3671))
    except Exception:
        cfg["gateway_port"] = 3671

    return cfg


def save_knx_config(data):
    """KNX Gateway Config atomar speichern."""
    cfg = dict(DEFAULT_KNX_CONFIG)

    if isinstance(data, dict):
        cfg.update(data)

    cfg["enabled"] = bool(cfg.get("enabled", False))
    cfg["gateway_ip"] = str(cfg.get("gateway_ip", DEFAULT_KNX_CONFIG["gateway_ip"]) or "").strip() or DEFAULT_KNX_CONFIG["gateway_ip"]

    try:
        cfg["gateway_port"] = int(cfg.get("gateway_port", 3671))
    except Exception:
        cfg["gateway_port"] = 3671

    cfg["connection_type"] = str(cfg.get("connection_type", "tunneling") or "tunneling").strip()
    if cfg["connection_type"] not in ["tunneling", "routing"]:
        cfg["connection_type"] = "tunneling"

    cfg["local_ip"] = str(cfg.get("local_ip", "") or "").strip()
    cfg["physical_address"] = str(cfg.get("physical_address", "1.1.250") or "1.1.250").strip()

    safe_save_json_file(KNX_CONFIG_FILE, cfg, indent=2)



def load_mqtt2knx_config():
    if not os.path.exists(MQTT2KNX_FILE):
        save_mqtt2knx_config([])
        return []
    try:
        with open(MQTT2KNX_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = []
    if not isinstance(data, list):
        data = []
    for m in data:
        if isinstance(m, dict):
            m.setdefault("enabled", True)
            m.setdefault("source_topic", "")
            m.setdefault("payload_mode", "raw")
            m.setdefault("json_key", "")
            m.setdefault("group_address", "")
            m.setdefault("dpt", "1.001")
            m.setdefault("invert", False)
            m.setdefault("test_value", "1")
    return data


def save_mqtt2knx_config(data):
    with open(MQTT2KNX_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_knx2mqtt_config():
    if not os.path.exists(KNX2MQTT_FILE):
        save_knx2mqtt_config([])
        return []
    try:
        with open(KNX2MQTT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = []
    if not isinstance(data, list):
        data = []
    for m in data:
        if isinstance(m, dict):
            m.setdefault("enabled", True)
            m.setdefault("group_address", "")
            m.setdefault("mqtt_topic", "")
            m.setdefault("dpt", "1.001")
            m.setdefault("retain", True)
            m.setdefault("invert", False)
    return data


def save_knx2mqtt_config(data):
    with open(KNX2MQTT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_udp2knx_config():
    if not os.path.exists(UDP2KNX_FILE):
        save_udp2knx_config([])
        return []
    try:
        with open(UDP2KNX_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = []
    if not isinstance(data, list):
        data = []
    for m in data:
        if isinstance(m, dict):
            m.setdefault("enabled", True)
            m.setdefault("source_topic", "")
            m.setdefault("group_address", "")
            m.setdefault("dpt", "1.001")
            m.setdefault("invert", False)
            m.setdefault("test_value", "1")
    return data


def save_udp2knx_config(data):
    with open(UDP2KNX_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_knx2lox_config():
    if not os.path.exists(KNX2LOX_FILE):
        save_knx2lox_config([])
        return []
    try:
        with open(KNX2LOX_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = []
    if not isinstance(data, list):
        data = []
    for m in data:
        if isinstance(m, dict):
            m.setdefault("enabled", True)
            m.setdefault("group_address", "")
            m.setdefault("loxone_io", "")
            m.setdefault("dpt", "1.001")
            m.setdefault("invert", False)
    return data


def save_knx2lox_config(data):
    with open(KNX2LOX_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


config.set_log_handler(add_log_entry)
APP_ROOT = config.APP_ROOT
CONFIG_DIR = config.CONFIG_DIR
DATA_DIR = config.DATA_DIR
BACKUP_DIR = config.BACKUP_DIR
CONFIG_FILE = config.CONFIG_FILE
TOPIC_CONFIG_FILE = config.TOPIC_CONFIG_FILE
MQTT2LOX_FILE = config.MQTT2LOX_FILE
MQTT2UDP_FILE = config.MQTT2UDP_FILE
UDP2MQTT_FILE = config.UDP2MQTT_FILE
MQTT_BROKERS_FILE = config.MQTT_BROKERS_FILE
MONITOR_SETTINGS_FILE = config.MONITOR_SETTINGS_FILE
PLUGIN_CONFIG_FILE = config.PLUGIN_CONFIG_FILE
KNX_CONFIG_FILE = config.KNX_CONFIG_FILE
MQTT2KNX_FILE = config.MQTT2KNX_FILE
KNX2MQTT_FILE = config.KNX2MQTT_FILE
UDP2KNX_FILE = config.UDP2KNX_FILE
KNX2LOX_FILE = config.KNX2LOX_FILE
SIDEBAR_LINKS_FILE = config.SIDEBAR_LINKS_FILE
INTERNAL_BROKER_FILE = config.INTERNAL_BROKER_FILE
OBJECTS_FILE = config.OBJECTS_FILE
safe_load_json_file = config.safe_load_json_file
safe_save_json_file = config.safe_save_json_file
load_config = config.load_config
save_config = config.save_config
load_topic_config = config.load_topic_config
save_topic_config = config.save_topic_config
load_mqtt2lox_config = config.load_mqtt2lox_config
save_mqtt2lox_config = config.save_mqtt2lox_config
load_mqtt2udp_config = config.load_mqtt2udp_config
save_mqtt2udp_config = config.save_mqtt2udp_config
load_udp2mqtt_config = config.load_udp2mqtt_config
save_udp2mqtt_config = config.save_udp2mqtt_config
load_mqtt_brokers = config.load_mqtt_brokers
save_mqtt_brokers = config.save_mqtt_brokers
load_monitor_settings = config.load_monitor_settings
save_monitor_settings = config.save_monitor_settings
load_plugins_config = config.load_plugins_config
save_plugins_config = config.save_plugins_config
load_sidebar_links = config.load_sidebar_links
save_sidebar_links = config.save_sidebar_links
load_objects_config = config.load_objects_config
save_objects_config = config.save_objects_config
load_internal_broker_config = config.load_internal_broker_config
save_internal_broker_config = config.save_internal_broker_config
load_knx_config = config.load_knx_config
save_knx_config = config.save_knx_config
load_mqtt2knx_config = config.load_mqtt2knx_config
save_mqtt2knx_config = config.save_mqtt2knx_config
load_knx2mqtt_config = config.load_knx2mqtt_config
save_knx2mqtt_config = config.save_knx2mqtt_config
load_udp2knx_config = config.load_udp2knx_config
save_udp2knx_config = config.save_udp2knx_config
load_knx2lox_config = config.load_knx2lox_config
save_knx2lox_config = config.save_knx2lox_config


# ---------- V19.3 Mapping Templates / Import-Export ----------
# Wichtig: als Funktion, damit Python keine Loader referenziert,
# bevor sie weiter unten im File definiert sind.
def get_template_export_sections():
    return {
        "mqtt2lox": {"label": "MQTT → Loxone", "file": MQTT2LOX_FILE, "load": load_mqtt2lox_config, "save": save_mqtt2lox_config, "kind": "list"},
        "mqtt2udp": {"label": "MQTT → UDP", "file": MQTT2UDP_FILE, "load": load_mqtt2udp_config, "save": save_mqtt2udp_config, "kind": "list"},
        "udp2mqtt": {"label": "UDP → MQTT", "file": UDP2MQTT_FILE, "load": load_udp2mqtt_config, "save": save_udp2mqtt_config, "kind": "list"},
        "mqtt2knx": {"label": "MQTT → KNX", "file": MQTT2KNX_FILE, "load": load_mqtt2knx_config, "save": save_mqtt2knx_config, "kind": "list"},
        "knx2mqtt": {"label": "KNX → MQTT", "file": KNX2MQTT_FILE, "load": load_knx2mqtt_config, "save": save_knx2mqtt_config, "kind": "list"},
        "udp2knx": {"label": "UDP → KNX", "file": UDP2KNX_FILE, "load": load_udp2knx_config, "save": save_udp2knx_config, "kind": "list"},
        "knx2lox": {"label": "KNX → Loxone", "file": KNX2LOX_FILE, "load": load_knx2lox_config, "save": save_knx2lox_config, "kind": "list"},
        "topic_config": {"label": "Topic Einstellungen", "file": TOPIC_CONFIG_FILE, "load": load_topic_config, "save": save_topic_config, "kind": "dict"},
        "mqtt_brokers": {"label": "Zusätzliche MQTT Broker", "file": MQTT_BROKERS_FILE, "load": load_mqtt_brokers, "save": save_mqtt_brokers, "kind": "list"},
        "udp_presets": {"label": "UDP Presets", "file": UDP_PRESETS_FILE, "load": load_udp_presets, "save": save_udp_presets, "kind": "list"},
    }


def make_template_package(name, selected_sections):
    from datetime import datetime
    data = {}
    includes = {}
    for section_id in selected_sections:
        spec = get_template_export_sections().get(section_id)
        if not spec:
            continue
        try:
            data[section_id] = spec["load"]()
            includes[section_id] = True
        except Exception as e:
            add_log_entry(f"Template Export Fehler {section_id}: {e}")
    return {
        "type": "mqtt2lox_mapping_template",
        "app": "MQTT2Lox",
        "version": "20",
        "name": str(name or "Mapping Template").strip() or "Mapping Template",
        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "includes": includes,
        "data": data,
    }


def merge_template_section(section_id, incoming, mode="append"):
    spec = get_template_export_sections().get(section_id)
    if not spec:
        return False, f"Unbekannter Bereich: {section_id}"
    kind = spec.get("kind")
    if kind == "list":
        if not isinstance(incoming, list):
            return False, f"{section_id}: keine Liste"
        if mode == "replace":
            new_data = incoming
        else:
            current = spec["load"]()
            if not isinstance(current, list):
                current = []
            new_data = current + incoming
        spec["save"](new_data)
        return True, f"{section_id}: {len(incoming)} Einträge importiert"
    if kind == "dict":
        if not isinstance(incoming, dict):
            return False, f"{section_id}: kein Objekt"
        if mode == "replace":
            new_data = incoming
        else:
            current = spec["load"]()
            if not isinstance(current, dict):
                current = {}
            new_data = dict(current)
            new_data.update(incoming)
        spec["save"](new_data)
        return True, f"{section_id}: {len(incoming)} Schlüssel importiert"
    return False, f"{section_id}: Typ nicht unterstützt"


def import_template_package(package, mode="append"):
    if not isinstance(package, dict):
        return False, ["Template ist kein gültiges JSON Objekt"]
    if package.get("type") not in ["mqtt2lox_mapping_template", "mapping_pack", "mqtt2lox_template"]:
        return False, ["Datei ist kein MQTT2Lox Mapping Template"]
    data = package.get("data", {})
    if not isinstance(data, dict):
        return False, ["Template enthält keinen data-Bereich"]
    messages = []
    imported_any = False
    for section_id, incoming in data.items():
        ok, msg = merge_template_section(section_id, incoming, mode=mode)
        messages.append(msg)
        imported_any = imported_any or ok
    return imported_any, messages


def mapping_templates_content(notice=""):
    rows = ""
    for section_id, spec in get_template_export_sections().items():
        count = "-"
        try:
            data = spec["load"]()
            count = len(data) if hasattr(data, "__len__") else "-"
        except Exception:
            count = "Fehler"
        rows += f"""
<tr>
    <td><input type=\"checkbox\" name=\"section_{escape(section_id)}\" checked></td>
    <td><b>{escape(spec.get('label', section_id))}</b><br><span class=\"small\">{escape(os.path.basename(spec.get('file','')))}</span></td>
    <td>{escape(str(count))}</td>
</tr>"""
    return f"""
{notice or ""}
<div class=\"card compact-card\">
    <h2 class=\"section-title\">Mapping Templates</h2>
    <p class=\"small\">V19: gezielte Export-/Import-Pakete für Integrationen. Kein komplettes Backup, sondern wiederverwendbare Vorlagen.</p>
</div>

<div class=\"card\">
    <h2 class=\"section-title\">Template exportieren</h2>
    <form method=\"post\" action=\"/templates/export\">
        <label>Name des Templates</label>
        <input name=\"template_name\" value=\"MQTT2Lox Mapping Template\">
        <table style=\"margin-top:14px;\">
            <tr><th>Export</th><th>Bereich</th><th>Einträge</th></tr>
            {rows}
        </table>
        <div class=\"button-row\" style=\"margin-top:14px;\">
            <button type=\"submit\">Template herunterladen</button>
        </div>
    </form>
</div>

<div class=\"card\">
    <h2 class=\"section-title\">Template importieren</h2>
    <form method=\"post\" action=\"/templates/import\" enctype=\"multipart/form-data\" class=\"restore-form\">
        <input type=\"file\" name=\"template_file\" accept=\".json\" required class=\"file-upload\">
        <select name=\"mode\" style=\"width:auto; min-width:180px;\">
            <option value=\"append\">Anhängen / ergänzen</option>
            <option value=\"replace\">Bereiche ersetzen</option>
        </select>
        <button type=\"submit\">Template importieren</button>
    </form>
    <p class=\"small\">Anhängen lässt bestehende Mappings stehen. Ersetzen überschreibt nur die Bereiche, die im Template enthalten sind.</p>
</div>
"""


def extract_mqtt_mapping_value(mapping, mqtt_payload):
    payload_mode = mapping.get("payload_mode", "raw")
    json_key = mapping.get("json_key", "").strip()
    if isinstance(mqtt_payload, bytes):
        mqtt_payload = mqtt_payload.decode("utf-8", errors="ignore")
    if payload_mode == "raw":
        return mqtt_payload
    try:
        data = json.loads(mqtt_payload) if isinstance(mqtt_payload, str) else mqtt_payload
    except Exception as e:
        add_log_entry(f"MQTT2KNX JSON Fehler: {e}")
        return None
    if payload_mode == "json_key":
        if not json_key:
            return None
        return get_nested_value(data, json_key)
    return mqtt_payload



def _send_knx_service_value(group_address, dpt, value):
    return knx_service.send_knx_value(
        group_address,
        dpt,
        value,
        load_knx_config,
        add_log_entry,
        add_monitor_entry=add_knx_monitor_entry,
    )


def _handle_mqtt_to_knx_service(topic, payload):
    return knx_service.handle_mqtt_to_knx(
        topic,
        payload,
        load_mqtt2knx_config,
        extract_mqtt_mapping_value,
        mqtt2knx_last_seen,
        _send_knx_service_value,
        add_log_entry,
        update_knx_last_seen,
    )


def _handle_udp_to_knx_service(topic, value):
    handled = knx_service.handle_udp_to_knx(
        topic,
        value,
        load_udp2knx_config,
        udp2knx_last_seen,
        _send_knx_service_value,
        add_log_entry,
    )
    for key, info in udp2knx_last_seen.items():
        update_udp_last_seen("udp2knx", key, info)
    return handled

def handle_udp_to_mqtt(raw_topic, value, default_prefix="", default_retain=False, legacy_fallback=False):
    """Map UDP topic/value to MQTT. Optional legacy fallback publishes all UDP telegrams for discovery."""
    global mqtt_client, udp2mqtt_last_seen
    publish_func = None
    if mqtt_client:
        publish_func = lambda topic, payload, retain=False: mqtt_client.publish(topic, payload, retain=bool(retain))
    return udp.handle_udp_to_mqtt(
        raw_topic,
        value,
        load_udp2mqtt_config,
        publish_func,
        add_log_entry,
        default_prefix,
        default_retain,
        legacy_fallback,
        update_udp_last_seen,
    )



async def _knx_listener_async(knx_cfg):
    try:
        from xknx import XKNX
        from xknx.io import ConnectionConfig, ConnectionType
    except Exception as e:
        add_log_entry(f"KNX Listener Fehler: xknx fehlt oder lädt nicht ({e})")
        add_log_entry("KNX Hinweis: pip install xknx")
        return
    connection_type = ConnectionType.TUNNELING
    if str(knx_cfg.get("connection_type", "tunneling")).lower() == "routing":
        connection_type = ConnectionType.ROUTING
    kwargs = {"connection_type": connection_type, "gateway_ip": knx_cfg.get("gateway_ip", ""), "gateway_port": int(knx_cfg.get("gateway_port", 3671))}
    local_ip = str(knx_cfg.get("local_ip", "")).strip()
    if local_ip:
        kwargs["local_ip"] = local_ip
    xknx = XKNX(connection_config=ConnectionConfig(**kwargs))
    def telegram_received_cb(telegram):
        try:
            ga = str(getattr(telegram, "destination_address", ""))
            payload = getattr(telegram, "payload", None)
            if ga:
                detected_dpt = knx_service.infer_knx_dpt(
                    ga,
                    "",
                    load_knx2mqtt_config,
                    load_knx2lox_config,
                    load_mqtt2knx_config,
                    load_udp2knx_config,
                )
                value_text = knx_service.parse_knx_payload_value(payload, detected_dpt)

                monitor_dpt = detected_dpt
                if not monitor_dpt:
                    try:
                        _auto_value, _auto_dpt = knx_service.auto_decode_value(knx_service.payload_to_bytes(payload))
                        if _auto_dpt:
                            monitor_dpt = _auto_dpt
                    except Exception:
                        monitor_dpt = ""

                add_knx_monitor_entry(ga, value_text, "RX", monitor_dpt)
                knx_service.publish_knx_to_mqtt(ga, payload, load_knx2mqtt_config, lambda: mqtt_client, knx2mqtt_last_seen, add_log_entry, update_knx_last_seen)
                knx_service.publish_knx_to_loxone(ga, payload, load_knx2lox_config, load_config, knx2lox_last_seen, add_log_entry, requests, update_knx_last_seen)
        except Exception as e:
            add_log_entry(f"KNX Listener Telegramm Fehler: {e}")
    try:
        if hasattr(xknx, "telegram_queue") and hasattr(xknx.telegram_queue, "register_telegram_received_cb"):
            xknx.telegram_queue.register_telegram_received_cb(telegram_received_cb)
        elif hasattr(xknx, "telegram_queue") and hasattr(xknx.telegram_queue, "register_telegram_received_callback"):
            xknx.telegram_queue.register_telegram_received_callback(telegram_received_cb)
        else:
            add_log_entry("KNX Listener Fehler: keine passende xknx Callback-API gefunden")
            return
        await xknx.start()
        add_log_entry("KNX Listener gestartet")
        while not runtime_context.bridge.stop_requested:
            await asyncio.sleep(1)
    except Exception as e:
        add_log_entry(f"KNX Listener Fehler: {e}")
    finally:
        try:
            await xknx.stop()
        except Exception:
            pass
        add_log_entry("KNX Listener gestoppt")


def knx_listener_runner(config):
    knx_cfg = load_knx_config()
    if not knx_cfg.get("enabled", False):
        add_log_entry("KNX Listener nicht gestartet: KNX deaktiviert")
        return
    try:
        asyncio.run(_knx_listener_async(knx_cfg))
    except Exception as e:
        add_log_entry(f"KNX Listener Runtime Fehler: {e}")


def ensure_knx_listener_started(reason=""):
    """Startet den KNX Listener nur bei Bedarf und nur wenn KNX aktiviert ist."""
    try:
        if not load_knx_config().get("enabled", False):
            add_log_entry("KNX Listener Auto-Start übersprungen: KNX deaktiviert")
            set_knx_listener_running(False)
            return False

        if is_knx_listener_running():
            return True

        config = load_config()
        thread = threading.Thread(
            target=knx_listener_runner,
            args=(config,),
            daemon=True
        )
        set_knx_listener(thread)
        request_knx_start()
        thread.start()
        set_knx_listener_running(True)

        suffix = f" ({reason})" if reason else ""
        add_log_entry(f"KNX Listener Auto-Start{suffix}")
        return True

    except Exception as e:
        set_knx_listener_running(False)
        add_log_entry(f"KNX Listener Auto-Start Fehler: {e}")
        return False


def build_udp_message(udp_topic, value, udp_format):
    return udp.build_udp_message(udp_topic, value, udp_format)

def send_mqtt2udp(ip_list, port, udp_topic, value, udp_format="topic_value"):
    return udp.send_mqtt2udp(ip_list, port, udp_topic, value, udp_format, add_log_entry)
    

def load_udp_presets():
    return udp.load_udp_presets()

def save_udp_presets(data):
    return udp.save_udp_presets(data)

def get_udp_port_presets():
    return udp.get_udp_port_presets(load_mqtt2udp_config)



def get_nested_value(data, key_path):
    try:
        value = data
        for part in key_path.split("."):
            if isinstance(value, dict):
                value = value[part]
            else:
                return None
        return value
    except Exception:
        return None


def flatten_json(data, prefix=""):
    result = {}

    if isinstance(data, dict):
        for key, value in data.items():
            new_key = f"{prefix}.{key}" if prefix else key
            result.update(flatten_json(value, new_key))
    else:
        result[prefix] = data

    return result




def restart_bridge_async():
    def worker():
        try:
            add_log_entry("Bridge Neustart angefordert")

            runtime_context.bridge.stop_requested = True

            if runtime_context.bridge.thread and runtime_context.bridge.thread.is_alive():
                runtime_context.bridge.thread.join(timeout=5)

            runtime_context.bridge.stop_requested = False

            config = load_config()

            runtime_context.bridge.thread = threading.Thread(
                target=bridge_runner,
                args=(config,),
                daemon=True
            )
            runtime_context.bridge.thread.start()

            add_log_entry("Bridge wurde neu gestartet")

        except Exception as e:
            add_log_entry(f"Bridge Neustart Fehler: {e}")

    threading.Thread(target=worker, daemon=True).start()






def udp_input_listener(config):
    global mqtt_client, udp_input_last_seen
    return udp.udp_input_listener(
        config,
        load_config,
        _handle_udp_to_knx_service,
        handle_udp_to_mqtt,
        add_log_entry,
        update_udp_last_seen,
    )


DEFAULT_CONFIG = {
    "loxone": {"host": "172.16.12.212", "user": "admin", "password": ""},
    "mqtt": {"host": "172.16.12.17", "port": 1883, "user": "", "password": "", "prefix": "loxone"},
    "udp_input": {
        "enabled": True,
        "port": 7002,
        "prefix": "",
        "retain": False,
        "legacy_fallback": False
    },
    "influx": {
        "enabled": False,
        "version": "2",
        "host": "172.16.12.122",
        "port": 8086,
        "database": "",
        "bucket": "loxone",
        "org": "home",
        "token": "",
        "user": "",
        "password": "",
        "measurement": "loxone"
    },
    
    "bridge": {"pulse_time": 0.5, "round_digits": 4, "retain": True, "change_only": True}
}

def handle_mqtt_to_udp(topic, payload):
    return udp.handle_mqtt_to_udp(
        topic,
        payload,
        load_mqtt2udp_config,
        extract_mqtt_mapping_value,
        add_log_entry,
        update_last_seen=update_udp_last_seen,
    )


app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False
if hasattr(app, "json"):
    app.json.ensure_ascii = False


@app.after_request
def force_utf8_response(response):
    if response.content_type.startswith("text/html"):
        response.headers["Content-Type"] = "text/html; charset=utf-8"
    elif response.content_type.startswith("text/event-stream"):
        response.headers["Content-Type"] = "text/event-stream; charset=utf-8"
    elif response.content_type.startswith("application/json"):
        response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response

app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024
app.config["MAX_FORM_MEMORY_SIZE"] = 20 * 1024 * 1024
app.config["MAX_FORM_PARTS"] = 5000

ws = None
main_loop = None
mqtt_client = None
mqtt_clients = mqtt_module.mqtt_clients
state_mapping = {}
control_mapping = {}

# Für Change-Only Publish
last_values = {}

# Für Anzeige im Topic Manager
display_values = {}

mqtt2lox_last_seen = {}
mqtt2udp_last_seen = udp.mqtt2udp_last_seen
udp2mqtt_last_seen = udp.udp2mqtt_last_seen
mqtt2knx_last_seen = {}
knx2mqtt_last_seen = {}
udp2knx_last_seen = {}
knx2lox_last_seen = {}
udp_input_last_seen = udp.udp_input_last_seen
mqtt_monitor_values = mqtt_module.mqtt_monitor_values


def clean_topic(text):
    text = str(text).lower()
    text = text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    text = text.replace("/", "_").replace(" ", "_")
    text = re.sub(r"[^a-z0-9_]", "", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")


def merge_defaults(config, defaults):
    for key, value in defaults.items():
        if key not in config:
            config[key] = value
        elif isinstance(value, dict) and isinstance(config.get(key), dict):
            merge_defaults(config[key], value)
    return config


def load_config():
    config = safe_load_json_file(CONFIG_FILE, dict(DEFAULT_CONFIG))
    if not isinstance(config, dict):
        config = dict(DEFAULT_CONFIG)
    config = merge_defaults(config, DEFAULT_CONFIG)
    if not os.path.exists(CONFIG_FILE):
        save_config(config)
    return config


def save_config(config):
    safe_save_json_file(CONFIG_FILE, config, indent=2)


load_config = config.load_config
save_config = config.save_config


def normalize_value(value, digits):
    if isinstance(value, bytes):
        try:
            value = value.decode("utf-8")
        except Exception:
            value = str(value)
    try:
        return str(round(float(value), int(digits)))
    except Exception:
        return str(value)


def load_mapping(config):
    global state_mapping, control_mapping

    url = f"http://{config['loxone']['host']}/data/LoxAPP3.json"
    r = requests.get(
        url,
        auth=(config["loxone"]["user"], config["loxone"]["password"]),
        timeout=20
    )
    r.raise_for_status()

    data = r.json()

    states = {}
    controls = {}

    def walk_controls(ctrls):
        for uuid, ctrl in ctrls.items():
            name = ctrl.get("name", uuid)
            controls[clean_topic(name)] = uuid

            for state_name, state_uuid in ctrl.get("states", {}).items():
                states[str(state_uuid)] = f"{name}/{state_name}"

            sub = ctrl.get("subControls", {})
            if sub:
                walk_controls(sub)

    walk_controls(data.get("controls", {}))

    state_mapping = states
    control_mapping = controls

    return data


def build_state_topic(prefix, name):
    parts = str(name).split("/")
    if len(parts) >= 2:
        return f"{prefix}/{clean_topic(parts[0])}/{clean_topic('_'.join(parts[1:]))}"
    return f"{prefix}/{clean_topic(name)}"



def build_datalist_html(datalist_id, options):
    return template_service.build_datalist_html(datalist_id, options)


def publish_value(config, name, value):
    global last_values, display_values, mqtt_client

    topic_settings = load_topic_config()

    default_topic = build_state_topic(config["mqtt"]["prefix"], name)
    settings = topic_settings.get(default_topic, {})

    custom_name = settings.get("custom_name", "").strip()
    final_topic = custom_name if custom_name else default_topic

    retain = config["bridge"]["retain"]
    change_only = config["bridge"]["change_only"]
    digits = config["bridge"]["round_digits"]

    payload = normalize_value(value, digits)

    # Nur Anzeige merken, unabhängig vom Aktiv-Haken
    display_values[default_topic] = payload
    if custom_name:
        display_values[custom_name] = payload

    # MQTT/Influx nur wenn aktiv
    if settings.get("enabled", True) is False:
        return

    # Change-only nur für echtes Senden
    if change_only and last_values.get(final_topic) == payload:
        return

    last_values[final_topic] = payload

    mqtt_client.publish(
        final_topic,
        payload,
        retain=retain
    )

    influx_service.write_to_influx(final_topic, payload, load_config, load_topic_config, add_log_entry)

    add_log_entry(f"MQTT -> {final_topic} = {payload}")
    

def get_influx_form_config(base_config=None):
    """Influx Config aus Formular übernehmen, ohne gespeicherte Tokens versehentlich zu löschen."""
    config = base_config or load_config()
    current = config.get("influx", {}).copy()

    try:
        port = int(request.form.get("influx_port", current.get("port", 8086)))
    except Exception:
        port = 8086

    token_from_form = request.form.get("influx_token", "")
    password_from_form = request.form.get("influx_password", "")

    # Schutz gegen Browser/Password-Manager-Mätzchen: leeres Feld löscht vorhandenen Token nicht automatisch.
    # Will man wirklich löschen, kann man den Token in der config.json entfernen oder neu überschreiben.
    if not token_from_form and current.get("token"):
        token_from_form = current.get("token", "")
    if not password_from_form and current.get("password"):
        password_from_form = current.get("password", "")

    return {
        "enabled": "influx_enabled" in request.form,
        "version": str(request.form.get("influx_version", current.get("version", "2")) or "2"),
        "host": str(request.form.get("influx_host", current.get("host", "")) or "").strip(),
        "port": port,
        "database": str(request.form.get("influx_database", current.get("database", "")) or "").strip(),
        "bucket": str(request.form.get("influx_bucket", current.get("bucket", "")) or "").strip(),
        "org": str(request.form.get("influx_org", current.get("org", "")) or "").strip(),
        "token": str(token_from_form or "").strip(),
        "user": str(request.form.get("influx_user", current.get("user", "")) or "").strip(),
        "password": str(password_from_form or ""),
        "measurement": str(request.form.get("influx_measurement", current.get("measurement", "loxone")) or "loxone").strip() or "loxone"
    }



def handle_mqtt_command(config, topic, payload):
    global ws, main_loop

    prefix = config["mqtt"]["prefix"]
    pulse_time = float(config["bridge"]["pulse_time"])

    parts = topic.split("/")

    if len(parts) < 3:
        return

    if parts[-1] != "set":
        return

    incoming_base_topic = "/".join(parts[:-1])
    topic_settings = load_topic_config()

    # Standard: loxone/bwm_1/set -> bwm_1
    control_name = clean_topic("_".join(parts[1:-1]))

    # Custom-Topic Rückwärts-Mapping
    for original_topic, settings in topic_settings.items():
        custom_topic = settings.get("custom_name", "").strip()

        if not custom_topic:
            continue

        # Variante A:
        # custom = loxone/grid1
        # write  = loxone/grid1/set
        if incoming_base_topic == custom_topic:
            original_parts = original_topic.split("/")
            if len(original_parts) >= 2:
                control_name = clean_topic(original_parts[1])
                print(f"Custom Write erkannt A: {incoming_base_topic} -> {control_name}")
                break

        # Variante B:
        # custom = loxone/grid1/value
        # write  = loxone/grid1/set
        custom_base = "/".join(custom_topic.split("/")[:-1])
        if incoming_base_topic == custom_base:
            original_parts = original_topic.split("/")
            if len(original_parts) >= 2:
                control_name = clean_topic(original_parts[1])
                print(f"Custom Write erkannt B: {incoming_base_topic} -> {control_name}")
                break

    control_uuid = control_mapping.get(control_name)

    if not control_uuid:
        print(f"Control nicht gefunden: {control_name}")
        return

    control_base_topic = f"{prefix}/{control_name}"

    writable_allowed = False

    # Schreibrecht direkt auf Control-Basis
    direct_settings = topic_settings.get(control_base_topic, {})
    if direct_settings.get("writable", False):
        writable_allowed = True

    # Schreibrecht über Original-State oder Custom-State prüfen
    for original_topic, settings in topic_settings.items():
        custom_topic = settings.get("custom_name", "").strip()

        if original_topic.startswith(control_base_topic + "/") and settings.get("writable", False):
            writable_allowed = True
            break

        if custom_topic:
            # custom = loxone/grid1
            if incoming_base_topic == custom_topic and settings.get("writable", False):
                writable_allowed = True
                break

            # custom = loxone/grid1/value
            custom_base = "/".join(custom_topic.split("/")[:-1])
            if incoming_base_topic == custom_base and settings.get("writable", False):
                writable_allowed = True
                break

    if not writable_allowed:
        print(f"Schreibzugriff blockiert: {topic} -> {control_name}")
        return

    if ws is None or main_loop is None:
        print("Bridge noch nicht bereit")
        return

    async def send_command():
        try:
            normalized = payload.lower()

            if normalized == "pulse":
                await ws.send_websocket_command(control_uuid, "1")
                await asyncio.sleep(pulse_time)
                await ws.send_websocket_command(control_uuid, "0")

            elif normalized in ["true", "on"]:
                await ws.send_websocket_command(control_uuid, "1")

            elif normalized in ["false", "off"]:
                await ws.send_websocket_command(control_uuid, "0")

            else:
                await ws.send_websocket_command(control_uuid, payload)

            add_log_entry(f"CMD -> {control_name} = {payload}")

        except Exception as e:
            print(f"Sendefehler: {e}")

    main_loop.call_soon_threadsafe(
        lambda: asyncio.create_task(send_command())
    )




def parse_udp_input_message(text):
    return udp.parse_udp_input_message(text)



async def bridge_async(config):
    global ws, main_loop, mqtt_client
    global last_values, display_values

    if not globals().get("LOXWEBSOCKET_AVAILABLE", True):
        runtime_context.bridge.status = globals().get("LOXWEBSOCKET_STATUS", "Loxone: Bibliothek nicht installiert")
        add_log_entry(runtime_context.bridge.status)
        return

    last_values = {}
    display_values = {}

    runtime_context.bridge.status = "lade Mapping"

    load_mapping(config)

    runtime_context.bridge.status = "verbinde MQTT"

    global mqtt_clients

    mqtt_clients = mqtt_module.mqtt_clients

    # Hauptbroker aus config oder interner Broker
    effective_mqtt = get_effective_mqtt_config(config)
    all_brokers = [
        {
            "name": "Hauptbroker",
            "host": effective_mqtt.get("host", config["mqtt"].get("host", "127.0.0.1")),
            "port": effective_mqtt.get("port", config["mqtt"].get("port", 1883)),
            "user": effective_mqtt.get("user", ""),
            "password": effective_mqtt.get("password", ""),
            "enabled": True,
            "is_main": True
        }
    ]

    # Zusätzliche Broker laden
    for broker in load_mqtt_brokers():
        if broker.get("enabled", True):
            broker["is_main"] = False
            all_brokers.append(broker)


    def on_mqtt_message(client, userdata, msg):
        try:
            payload = msg.payload.decode("utf-8", errors="ignore").strip()

            broker_name = (
                userdata.get("broker", "unbekannt")
                if isinstance(userdata, dict)
                else "unbekannt"
            )

            add_log_entry(f"MQTT RX [{broker_name}] -> {msg.topic} = {payload}")

            monitor_entry = mqtt_module.record_mqtt_message(broker_name, msg.topic, payload)
            set_mqtt_monitor_value(f"{broker_name}::{msg.topic}", monitor_entry)
            bump_sse("mqtt")

            # MQTT Explorer -> Influx: direkte Topics und aktivierte JSON-Keys schreiben.
            influx_service.write_mqtt_explorer_influx(msg.topic, payload, load_topic_config, get_nested_value, lambda t, v: influx_service.write_to_influx(t, v, load_config, load_topic_config, add_log_entry), lambda t, f, v, value_type="auto": influx_service.write_to_influx_field(t, f, v, load_config, add_log_entry, value_type=value_type), add_log_entry)

            # MQTT -> UDP Weiterleitung
            handle_mqtt_to_udp(msg.topic, payload)

            # MQTT -> KNX Weiterleitung
            if _handle_mqtt_to_knx_service(msg.topic, payload):
                return

            # Externe MQTT-Topics -> Loxone virtuelle Eingänge
            if loxone_service.handle_mqtt_to_loxone(config, msg.topic, payload, load_mqtt2lox_config, mqtt2lox_last_seen, add_log_entry, requests, get_nested_value, flatten_json):
                return

            # Normale Loxone-Set-Topics
            handle_mqtt_command(config, msg.topic, payload)

        except Exception as e:
            add_log_entry(f"MQTT Fehler: {e}")

    mqtt_client, mqtt_clients = mqtt_module.connect_brokers(
        config,
        mqtt,
        load_mqtt_brokers,
        load_internal_broker_config,
        on_mqtt_message,
        add_log_entry,
    )
    with runtime_context.mqtt.lock:
        runtime_context.mqtt.mqtt_client = mqtt_client
        runtime_context.mqtt.mqtt_clients = mqtt_clients
    all_brokers = []

    for broker in all_brokers:
        try:
            client = mqtt.Client(userdata={"broker": broker["name"]})

            user = broker.get("user", "")
            password = broker.get("password", "")

            if user:
                client.username_pw_set(user, password)

            client.on_message = on_mqtt_message

            client.connect(
                broker["host"],
                int(broker["port"]),
                60
            )

            client.subscribe("#")
            client.loop_start()

            mqtt_clients[broker["name"]] = client

            # Hauptbroker merken für publish
            if broker.get("is_main"):
                mqtt_client = client
                with runtime_context.mqtt.lock:
                    runtime_context.mqtt.mqtt_client = mqtt_client

            add_log_entry(
                f"MQTT verbunden: {broker['name']} "
                f"({broker['host']}:{broker['port']})"
            )

        except Exception as e:
            add_log_entry(
                f"MQTT Broker Fehler {broker.get('name')}: {e}"
            )

    add_log_entry("Starte UDP Input Thread")

    udp_thread = threading.Thread(
        target=udp_input_listener,
        args=(config,),
        daemon=True
    )
    udp_thread.start()

    try:
        ensure_knx_listener_started("Bridge Start")
    except Exception as e:
        add_log_entry(f"KNX Listener Start Fehler: {e}")

    runtime_context.bridge.status = "verbinde Loxone"

    main_loop = asyncio.get_running_loop()
    ws = LoxWs()

    async def message_callback(data, msg_type):
        if not isinstance(data, dict):
            return

        if msg_type != 2:
            return

        for uuid_bytes, value in data.items():
            try:
                uuid_str = uuid_bytes.decode("utf-8")
            except Exception:
                uuid_str = str(uuid_bytes)

            # Nur bekannte States publishen
            if uuid_str not in state_mapping:
                continue

            name = state_mapping[uuid_str]
            publish_value(config, name, value)

    ws.add_message_callback(message_callback, [2, 3])

    await ws.connect(
        config["loxone"]["user"],
        config["loxone"]["password"],
        f"http://{config['loxone']['host']}",
        receive_updates=True
    )

    runtime_context.bridge.running = True
    runtime_context.bridge.status = "läuft"

    print("✅ Bridge läuft")

    while not runtime_context.bridge.stop_requested:
        await asyncio.sleep(1)

    runtime_context.bridge.status = "stoppe"

    try:
        if ws:
            await ws.stop()
    except Exception:
        pass

    try:
        for name, client in mqtt_clients.items():
            try:
                client.loop_stop()
                client.disconnect()
                add_log_entry(f"MQTT getrennt: {name}")
            except Exception as e:
                add_log_entry(f"MQTT Disconnect Fehler {name}: {e}")


    except Exception:
        pass

    runtime_context.bridge.running = False
    runtime_context.bridge.status = "gestoppt"
    print("Bridge gestoppt")


def bridge_runner(config):
    try:
        asyncio.run(bridge_async(config))
    except Exception as e:
        runtime_context.bridge.running = False
        runtime_context.bridge.status = f"Fehler: {e}"
        print("Bridge Fehler:", e)



APP_LAYOUT = """
<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title }} · MQTT2Lox</title>
<style>
:root {
    --bg:#0f1115;
    --panel:#171a21;
    --panel2:#1d212b;
    --border:#2b3040;
    --text:#eef2ff;
    --muted:#9aa4b2;
    --blue:#5b7cfa;
    --blue2:#3f63e8;
    --red:#c23b3b;
    --green:#54d37d;
}
* { box-sizing:border-box; }
body {
    margin:0;
    font-family: Arial, sans-serif;
    background:var(--bg);
    color:var(--text);
}
a { color:inherit; }
.app-shell { display:flex; min-height:100vh; }
.sidebar {
    width:250px;
    position:fixed;
    inset:0 auto 0 0;
    background:#0b0d12;
    border-right:1px solid var(--border);
    padding:22px 16px;
    display:flex;
    flex-direction:column;
    gap:18px;
}
.brand {
    font-size:24px;
    font-weight:800;
    letter-spacing:.2px;
    display:flex;
    align-items:center;
    gap:10px;
    margin-bottom:8px;
}
.brand .bolt { color:#ffb86b; }
.nav-group-title {
    color:var(--muted);
    font-size:12px;
    text-transform:uppercase;
    letter-spacing:.12em;
    margin:10px 10px 6px;
}
.nav-link {
    display:flex;
    align-items:center;
    gap:10px;
    padding:11px 12px;
    border-radius:10px;
    text-decoration:none;
    color:#cfd6e6;
    transition:.12s ease;
}
.nav-link:hover { background:var(--panel2); color:white; }
.nav-link.active { background:var(--blue); color:white; }
.sidebar-footer {
    margin-top:auto;
    color:var(--muted);
    font-size:12px;
    padding:10px;
    border-top:1px solid var(--border);
}
.main {
    margin-left:250px;
    width:calc(100% - 250px);
    min-height:100vh;
    padding:28px;
}
.topbar {
    display:flex;
    align-items:flex-start;
    justify-content:space-between;
    gap:20px;
    margin-bottom:22px;
}
h1 { margin:0; font-size:30px; }
.subtitle { color:var(--muted); margin-top:6px; }
.card {
    background:var(--panel);
    border:1px solid var(--border);
    border-radius:16px;
    padding:20px;
    margin-bottom:18px;
    box-shadow:0 12px 35px rgba(0,0,0,.18);
}
.grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:16px; }
.stat-value { font-size:24px; font-weight:800; margin-top:8px; }
.muted { color:var(--muted); }
.ok { color:var(--green); }
.bad { color:#ff7b7b; }
.small { color:var(--muted); font-size:13px; }
button, .button-link {
    display:inline-flex;
    align-items:center;
    justify-content:center;
    min-height:40px;
    padding:0 16px;
    border:0;
    border-radius:10px;
    background:var(--blue);
    color:white;
    cursor:pointer;
    text-decoration:none;
    font-family:Arial, sans-serif;
    font-size:14px;
}
button:hover, .button-link:hover { background:var(--blue2); }
.stop { background:var(--red); }
.stop:hover { background:#a92e2e; }
.button-row { display:flex; gap:10px; flex-wrap:wrap; align-items:center; }
input, select {
    width:100%;
    padding:9px;
    border-radius:8px;
    border:1px solid #485063;
    background:#10131a;
    color:#fff;
}
input[type=checkbox] { width:auto; }
label { display:block; margin-top:12px; margin-bottom:5px; color:#e8edf7; }
table { width:100%; border-collapse:collapse; background:#11151d; }
th, td { border:1px solid var(--border); padding:8px; }
th { background:#202534; }
.file-upload { width:auto; max-width:300px; }
.restore-form { display:inline-flex; align-items:center; gap:8px; flex-wrap:wrap; }
.message {
    border:1px solid var(--border);
    background:#132015;
    border-radius:12px;
    padding:12px 14px;
    margin-bottom:18px;
}
.section-title { margin:0 0 12px; }
@media(max-width:850px) {
    .sidebar { position:relative; width:100%; inset:auto; }
    .app-shell { flex-direction:column; }
    .main { margin-left:0; width:100%; padding:18px; }
}
</style>
</head>
<body>
<div class="app-shell">
    <aside class="sidebar">
        <div class="brand"><span class="bolt">⚡</span><span>MQTT2Lox</span></div>

        <div>
            <div class="nav-group-title">Hauptmenü</div>
            <a class="nav-link {{ 'active' if active == 'dashboard' else '' }}" href="/">Dashboard</a>
            <a class="nav-link {{ 'active' if active == 'monitor' else '' }}" href="/monitor">MQTT Monitor</a>
            <a class="nav-link {{ 'active' if active == 'mqtt_hub' else '' }}" href="/mqtt">MQTT Hub</a>
            <a class="nav-link {{ 'active' if active == 'influx_explorer' else '' }}" href="/influx_explorer">Influx Explorer</a>
            <a class="nav-link {{ 'active' if active == 'objects' else '' }}" href="/objects">Objektmanager</a>
        </div>

        <div>
            <div class="nav-group-title">Werkzeuge</div>
            <a class="nav-link {{ 'active' if active == 'global_search' else '' }}" href="/global_search_page">Suche</a>
            <a class="nav-link {{ 'active' if active == 'conflict_scanner' else '' }}" href="/conflicts_page">Konfig prüfen</a>
        </div>

        <div>
            <div class="nav-group-title">Extras</div>
            <a class="nav-link" href="#" onclick="return false;">Externe Links</a>
            <a class="nav-link" href="#" onclick="return false;">Zigbee</a>
            <a class="nav-link" href="#" onclick="return false;">KNX</a>
        </div>

        <div>
            <div class="nav-group-title">System</div>
            <a class="nav-link {{ 'active' if active == 'settings' else '' }}" href="/settings">Einstellungen</a>
        </div>

        <div class="sidebar-footer">
            Bridge: <b>{{ status }}</b><br>
            MQTT2Lox 32.4.6
        </div>
    </aside>

    <main class="main">
        <div class="topbar">
            <div>
                <h1>{{ title }}</h1>
                {% if subtitle %}<div class="subtitle">{{ subtitle }}</div>{% endif %}
            </div>
        </div>

        {% if message %}<div class="message">{{ message|safe }}</div>{% endif %}

        {{ content|safe }}
    </main>
</div>
</body>
</html>
"""


def nav_active(name, active):
    return "active" if name == active else ""


def render_layout(title, content, active="dashboard", subtitle="", message=""):
    return template_service.render_layout(render_template_string, APP_LAYOUT, runtime_context.bridge.status, title, content, active, subtitle, message)




def _global_search_add(results, section, title, haystack, link="#", meta=""):
    text = " ".join(str(x or "") for x in haystack)
    results.append({
        "section": str(section),
        "title": str(title or ""),
        "text": text,
        "link": str(link or "#"),
        "meta": str(meta or "")
    })


def collect_global_search_items():
    """Collect searchable entries from all MQTT2Lox configuration areas."""
    results = []

    try:
        for idx, item in enumerate(load_mqtt2lox_config()):
            if not isinstance(item, dict):
                continue
            _global_search_add(
                results,
                "MQTT → Loxone",
                item.get("source_topic") or item.get("custom_topic") or item.get("loxone_io") or f"Mapping {idx + 1}",
                [
                    item.get("source_topic"), item.get("custom_topic"), item.get("loxone_io"),
                    item.get("payload_mode"), item.get("json_key"), item.get("output_mode"),
                    "aktiv" if item.get("enabled", True) else "deaktiviert"
                ],
                "/mqtt2lox",
                f"Loxone IO: {item.get('loxone_io', '')}"
            )
    except Exception as e:
        add_log_entry(f"Globale Suche MQTT2Lox Fehler: {e}")

    try:
        for idx, item in enumerate(load_mqtt2udp_config()):
            if not isinstance(item, dict):
                continue
            _global_search_add(
                results,
                "MQTT → UDP",
                item.get("source_topic") or item.get("udp_topic") or f"Mapping {idx + 1}",
                [
                    item.get("source_topic"), item.get("udp_topic"), item.get("udp_ip"),
                    item.get("udp_port"), item.get("udp_format"),
                    "aktiv" if item.get("enabled", True) else "deaktiviert"
                ],
                "/mqtt2udp",
                f"Ziel: {item.get('udp_ip', '')}:{item.get('udp_port', '')}"
            )
    except Exception as e:
        add_log_entry(f"Globale Suche MQTT2UDP Fehler: {e}")

    try:
        for idx, item in enumerate(load_mqtt2knx_config()):
            if not isinstance(item, dict):
                continue
            _global_search_add(
                results,
                "MQTT → KNX",
                item.get("source_topic") or item.get("group_address") or f"Mapping {idx + 1}",
                [
                    item.get("source_topic"), item.get("group_address"), item.get("dpt"),
                    item.get("payload_mode"), item.get("json_key"), item.get("test_value"),
                    "invert" if item.get("invert", False) else "", "aktiv" if item.get("enabled", True) else "deaktiviert"
                ],
                "/mqtt2knx",
                f"GA: {item.get('group_address', '')} · DPT: {item.get('dpt', '')}"
            )
    except Exception as e:
        add_log_entry(f"Globale Suche MQTT2KNX Fehler: {e}")

    try:
        for idx, item in enumerate(load_knx2mqtt_config()):
            if not isinstance(item, dict):
                continue
            _global_search_add(
                results,
                "KNX → MQTT",
                item.get("group_address") or item.get("mqtt_topic") or f"Mapping {idx + 1}",
                [
                    item.get("group_address"), item.get("mqtt_topic"), item.get("dpt"),
                    "retain" if item.get("retain", True) else "no-retain",
                    "invert" if item.get("invert", False) else "", "aktiv" if item.get("enabled", True) else "deaktiviert"
                ],
                "/knx2mqtt",
                f"Topic: {item.get('mqtt_topic', '')}"
            )
    except Exception as e:
        add_log_entry(f"Globale Suche KNX2MQTT Fehler: {e}")

    try:
        for topic, settings in load_topic_config().items():
            if not isinstance(settings, dict):
                settings = {}
            _global_search_add(
                results,
                "Topic Manager",
                topic,
                [
                    topic, settings.get("custom_name"),
                    "aktiv" if settings.get("enabled", True) else "deaktiviert",
                    "schreibbar" if settings.get("writable", False) else "",
                    "influx" if settings.get("influx", False) else ""
                ],
                "/topics",
                f"Custom: {settings.get('custom_name', '')}" if settings.get("custom_name") else ""
            )
    except Exception as e:
        add_log_entry(f"Globale Suche Topic Config Fehler: {e}")

    try:
        cfg = load_config()
        mqtt_cfg = get_effective_mqtt_config(cfg)
        _global_search_add(
            results,
            "MQTT Broker",
            "Hauptbroker",
            ["Hauptbroker", mqtt_cfg.get("host"), mqtt_cfg.get("port"), mqtt_cfg.get("user"), cfg.get("mqtt", {}).get("prefix")],
            "/mqtt_settings_embed",
            f"{mqtt_cfg.get('host', '')}:{mqtt_cfg.get('port', '')}"
        )
        for idx, broker in enumerate(load_mqtt_brokers()):
            if not isinstance(broker, dict):
                continue
            _global_search_add(
                results,
                "MQTT Broker",
                broker.get("name") or f"Zusatzbroker {idx + 1}",
                [broker.get("name"), broker.get("host"), broker.get("port"), broker.get("user"), "aktiv" if broker.get("enabled", True) else "deaktiviert"],
                "/mqtt_brokers",
                f"{broker.get('host', '')}:{broker.get('port', '')}"
            )
    except Exception as e:
        add_log_entry(f"Globale Suche Broker Fehler: {e}")

    try:
        ib = load_internal_broker_config()
        _global_search_add(
            results,
            "Interner Broker",
            "Interner MQTT Broker",
            [ib.get("host"), ib.get("connect_host"), ib.get("port"), ib.get("user"), ib.get("mosquitto_path"), "aktiv" if ib.get("enabled") else "deaktiviert"],
            "/settings_embed",
            f"{ib.get('connect_host', '')}:{ib.get('port', '')}"
        )
    except Exception as e:
        add_log_entry(f"Globale Suche Interner Broker Fehler: {e}")

    try:
        for idx, item in enumerate(load_udp_presets()):
            if not isinstance(item, dict):
                continue
            _global_search_add(
                results,
                "UDP Presets",
                item.get("label") or item.get("port") or f"Preset {idx + 1}",
                [item.get("label"), item.get("port")],
                "/udp_presets",
                f"Port: {item.get('port', '')}"
            )
    except Exception as e:
        add_log_entry(f"Globale Suche UDP Presets Fehler: {e}")

    try:
        for idx, item in enumerate(load_sidebar_links()):
            if not isinstance(item, dict):
                continue
            _global_search_add(
                results,
                "Sidebar Links",
                item.get("label") or item.get("url") or f"Link {idx + 1}",
                [item.get("label"), item.get("url"), "neuer Tab" if item.get("new_tab", True) else "im Content", "aktiv" if item.get("enabled", True) else "deaktiviert"],
                "/settings_embed",
                item.get("url", "")
            )
    except Exception as e:
        add_log_entry(f"Globale Suche Sidebar Links Fehler: {e}")

    return results


def global_search_content(query=""):
    q = str(query or "").strip()
    terms = [x.lower() for x in q.split() if x.strip()]
    all_items = collect_global_search_items()

    if terms:
        matches = [item for item in all_items if all(term in (item.get("section", "") + " " + item.get("title", "") + " " + item.get("text", "") + " " + item.get("meta", "")).lower() for term in terms)]
    else:
        matches = []

    grouped = {}
    for item in matches:
        grouped.setdefault(item["section"], []).append(item)

    sections_html = ""
    if q and not matches:
        sections_html = '<div class="card"><b>Keine Treffer.</b><br><span class="small">Nix gefunden — das Topic versteckt sich besser als ein loses WAGO-Kabel im Kabelkanal.</span></div>'
    elif not q:
        sections_html = '<div class="card"><b>Suchbegriff eingeben.</b><br><span class="small">Durchsucht Mappings, Topics, Broker, KNX-Gruppenadressen, UDP-Ziele und Sidebar-Links.</span></div>'
    else:
        for section in sorted(grouped.keys(), key=lambda x: x.lower()):
            rows = ""
            for item in sorted(grouped[section], key=lambda x: (x.get("title", "").lower(), x.get("meta", "").lower())):
                title = escape(item.get("title", ""))
                text = escape(item.get("text", ""))
                meta = escape(item.get("meta", ""))
                link = escape(item.get("link", "#"))
                rows += f"""
<tr>
    <td><b>{title}</b><br><span class=\"small\">{meta}</span></td>
    <td class=\"search-text\">{text}</td>
    <td><a class=\"button-link\" href=\"{link}\">Öffnen</a></td>
</tr>"""
            sections_html += f"""
<div class=\"card\">
    <h2 class=\"section-title\">{escape(section)} <span class=\"small\">({len(grouped[section])})</span></h2>
    <table class="knx-monitor-table">
        <tr><th style=\"width:30%;\">Treffer</th><th>Details</th><th style=\"width:110px;\">Aktion</th></tr>
        {rows}
    </table>
</div>"""

    return f"""
<style>
.search-hero {{ display:flex; gap:10px; align-items:center; flex-wrap:wrap; }}
.search-hero input {{ max-width:520px; font-size:16px; }}
.search-text {{ word-break:break-word; color:#d7e0ea; }}
.search-stats {{ margin-top:8px; }}
</style>
<div class=\"card compact-card\">
    <h1>Globale Suche</h1>
    <p class=\"small\">Ein Suchfeld für alles: MQTT, Loxone, UDP, KNX, Broker und Config-Kram. Endlich kein Versteckspiel mehr.</p>
    <form class=\"search-hero\" method=\"get\" action=\"/global_search\">
        <input name=\"q\" value=\"{escape(q)}\" placeholder=\"Topic, IO, Gruppenadresse, IP, Port, Broker...\" autofocus>
        <button type=\"submit\">Suchen</button>
        <a class=\"button-link\" href=\"/global_search\">Leeren</a>
    </form>
    <div class=\"small search-stats\">Index: {len(all_items)} Einträge · Treffer: {len(matches) if q else 0}</div>
</div>
{sections_html}
"""


# ---------- V21.4 Konfliktscanner mit Sprunglinks ----------
def _conflict_area_link(area, title="", key="", ref=""):
    area = str(area or "")
    key = str(key or "").strip()
    ref = str(ref or "").strip()
    row = ""
    m = re.search(r"Zeile\s+(\d+)", ref)
    if m:
        try:
            row = str(max(0, int(m.group(1)) - 1))
        except Exception:
            row = ""
    base = "/global_search"
    if area == "MQTT → Loxone":
        base = "/mqtt2lox"
    elif area == "MQTT → UDP":
        base = "/mqtt2udp"
    elif area == "MQTT → KNX":
        base = "/mqtt2knx"
    elif area == "KNX → MQTT":
        base = "/knx2mqtt"
    elif area == "Topic Manager":
        base = "/topics"
    elif area in ["MQTT Broker", "Interner Broker", "UDP Presets", "Sidebar Links"]:
        base = "/settings_embed"
    elif area == "UDP":
        base = "/mqtt2udp"
    if base == "/global_search" and key:
        from urllib.parse import quote
        return f"/global_search?q={quote(key)}"
    if row and base in ["/mqtt2lox", "/mqtt2udp", "/mqtt2knx", "/knx2mqtt"]:
        return f"{base}#row_{row}"
    if key and base in ["/mqtt2lox", "/mqtt2udp", "/mqtt2knx", "/knx2mqtt", "/topics"]:
        from urllib.parse import quote
        param = "group_address" if area in ["KNX", "KNX → MQTT"] else "source_topic"
        return f"{base}?{param}={quote(key)}"
    return base


def _issue(issues, level, area, title, details="", items=None, link=None):
    issues.append({
        "level": str(level or "warn"),
        "area": str(area or "Allgemein"),
        "title": str(title or ""),
        "details": str(details or ""),
        "items": list(items or []),
        "link": str(link or _conflict_area_link(area, title, "", details))
    })


def _track_seen(seen, key, label, ref):
    key = str(key or "").strip()
    if not key:
        return
    seen.setdefault(key, []).append({"label": str(label or key), "ref": str(ref or "")})


def _add_duplicate_issues(issues, seen, area, title_prefix, details_prefix=""):
    for key, refs in sorted(seen.items(), key=lambda x: x[0].lower()):
        if len(refs) > 1:
            items = []
            first_link = _conflict_area_link(area, title_prefix, key, "")
            for r in refs:
                label = r.get('label', '')
                ref = r.get('ref', '')
                item_text = f"{label} {ref}`".replace(' `','').strip()
                item_link = _conflict_area_link(label, title_prefix, key, ref)
                items.append({"text": item_text, "link": item_link})
            _issue(
                issues,
                "warn",
                area,
                f"{title_prefix}: {key}",
                f"{details_prefix}Kommt {len(refs)}x vor.",
                items,
                link=first_link
            )


def _valid_port(value):
    try:
        p = int(str(value).strip())
        return 1 <= p <= 65535
    except Exception:
        return False


def collect_config_conflicts():
    issues = []

    mqtt_sources = {}
    custom_topics = {}
    knx_ga_tx = {}
    knx_ga_rx = {}
    mqtt_targets = {}
    udp_targets = {}
    broker_names = {}
    sidebar_labels = {}
    sidebar_urls = {}

    # MQTT -> Loxone
    try:
        for idx, item in enumerate(load_mqtt2lox_config()):
            if not isinstance(item, dict):
                continue
            ref = f"Zeile {idx + 1}"
            enabled = item.get("enabled", True)
            source = str(item.get("source_topic", "") or "").strip()
            custom = str(item.get("custom_topic", "") or "").strip()
            lox = str(item.get("loxone_io", "") or "").strip()
            if enabled and not (source or custom or lox):
                _issue(issues, "info", "MQTT → Loxone", f"Leere aktive Mapping-Zeile", ref)
            if enabled and (source or custom) and not lox:
                _issue(issues, "warn", "MQTT → Loxone", "Ziel Loxone IO fehlt", f"{ref}: {source or custom}")
            if source:
                _track_seen(mqtt_sources, source, "MQTT → Loxone", ref)
            if custom:
                _track_seen(custom_topics, custom, "MQTT → Loxone", ref)
    except Exception as e:
        _issue(issues, "error", "MQTT → Loxone", "Prüfung fehlgeschlagen", str(e))

    # MQTT -> UDP
    try:
        for idx, item in enumerate(load_mqtt2udp_config()):
            if not isinstance(item, dict):
                continue
            ref = f"Zeile {idx + 1}"
            enabled = item.get("enabled", True)
            source = str(item.get("source_topic", "") or "").strip()
            udp_topic = str(item.get("udp_topic", "") or "").strip()
            udp_ip = str(item.get("udp_ip", "") or "").strip()
            udp_port = str(item.get("udp_port", "") or "").strip()
            if enabled and not (source or udp_topic or udp_ip or udp_port):
                _issue(issues, "info", "MQTT → UDP", "Leere aktive Mapping-Zeile", ref)
            if enabled and source and not (udp_topic and udp_ip and udp_port):
                _issue(issues, "warn", "MQTT → UDP", "UDP Ziel unvollständig", f"{ref}: {source}")
            if udp_port and not _valid_port(udp_port):
                _issue(issues, "warn", "MQTT → UDP", "Ungültiger UDP Port", f"{ref}: {udp_port}")
            if source:
                _track_seen(mqtt_sources, source, "MQTT → UDP", ref)
            if udp_ip and udp_port and udp_topic:
                _track_seen(udp_targets, f"{udp_ip}:{udp_port}/{udp_topic}", "MQTT → UDP", ref)
    except Exception as e:
        _issue(issues, "error", "MQTT → UDP", "Prüfung fehlgeschlagen", str(e))

    # MQTT -> KNX
    try:
        for idx, item in enumerate(load_mqtt2knx_config()):
            if not isinstance(item, dict):
                continue
            ref = f"Zeile {idx + 1}"
            enabled = item.get("enabled", True)
            source = str(item.get("source_topic", "") or "").strip()
            ga = knx_service.normalize_knx_ga(item.get("group_address", ""))
            if enabled and not (source or ga):
                _issue(issues, "info", "MQTT → KNX", "Leere aktive Mapping-Zeile", ref)
            if enabled and source and not ga:
                _issue(issues, "warn", "MQTT → KNX", "KNX Gruppenadresse fehlt", f"{ref}: {source}")
            if source:
                _track_seen(mqtt_sources, source, "MQTT → KNX", ref)
            if ga:
                _track_seen(knx_ga_tx, ga, "MQTT → KNX", ref)
    except Exception as e:
        _issue(issues, "error", "MQTT → KNX", "Prüfung fehlgeschlagen", str(e))

    # KNX -> MQTT
    try:
        for idx, item in enumerate(load_knx2mqtt_config()):
            if not isinstance(item, dict):
                continue
            ref = f"Zeile {idx + 1}"
            enabled = item.get("enabled", True)
            ga = knx_service.normalize_knx_ga(item.get("group_address", ""))
            topic = str(item.get("mqtt_topic", "") or "").strip()
            if enabled and not (ga or topic):
                _issue(issues, "info", "KNX → MQTT", "Leere aktive Mapping-Zeile", ref)
            if enabled and ga and not topic:
                _issue(issues, "warn", "KNX → MQTT", "MQTT Topic fehlt", f"{ref}: {ga}")
            if ga:
                _track_seen(knx_ga_rx, ga, "KNX → MQTT", ref)
            if topic:
                _track_seen(mqtt_targets, topic, "KNX → MQTT", ref)
    except Exception as e:
        _issue(issues, "error", "KNX → MQTT", "Prüfung fehlgeschlagen", str(e))

    # Topic Manager / Custom Topics
    try:
        for topic, settings in load_topic_config().items():
            if not isinstance(settings, dict):
                settings = {}
            custom = str(settings.get("custom_name", "") or "").strip()
            if custom:
                _track_seen(custom_topics, custom, "Topic Manager", str(topic))
            if topic:
                _track_seen(mqtt_targets, topic, "Topic Manager", "Original")
    except Exception as e:
        _issue(issues, "error", "Topic Manager", "Prüfung fehlgeschlagen", str(e))

    # Broker
    try:
        cfg = load_config()
        main_name = "Hauptbroker"
        _track_seen(broker_names, main_name.lower(), main_name, f"{cfg.get('mqtt',{}).get('host','')}:{cfg.get('mqtt',{}).get('port','')}")
        port = cfg.get("mqtt", {}).get("port", "")
        if port and not _valid_port(port):
            _issue(issues, "warn", "MQTT Broker", "Ungültiger Hauptbroker-Port", str(port))
        for idx, broker in enumerate(load_mqtt_brokers()):
            if not isinstance(broker, dict):
                continue
            name = str(broker.get("name", "") or "").strip()
            host = str(broker.get("host", "") or "").strip()
            port = str(broker.get("port", "") or "").strip()
            ref = f"Zusatzbroker {idx + 1}"
            if name:
                _track_seen(broker_names, name.lower(), name, ref)
            if broker.get("enabled", True) and not (name and host and port):
                _issue(issues, "warn", "MQTT Broker", "Broker unvollständig", f"{ref}: {name or '-'}")
            if port and not _valid_port(port):
                _issue(issues, "warn", "MQTT Broker", "Ungültiger Broker-Port", f"{ref}: {port}")
    except Exception as e:
        _issue(issues, "error", "MQTT Broker", "Prüfung fehlgeschlagen", str(e))

    # Interner Broker
    try:
        ib = load_internal_broker_config()
        port = ib.get("port", "")
        if port and not _valid_port(port):
            _issue(issues, "warn", "Interner Broker", "Ungültiger interner Broker-Port", str(port))
    except Exception as e:
        _issue(issues, "error", "Interner Broker", "Prüfung fehlgeschlagen", str(e))

    # UDP Presets
    try:
        preset_ports = {}
        for idx, item in enumerate(load_udp_presets()):
            if not isinstance(item, dict):
                continue
            port = str(item.get("port", "") or "").strip()
            label = str(item.get("label", "") or "").strip()
            ref = f"Preset {idx + 1}"
            if port:
                _track_seen(preset_ports, port, label or "UDP Preset", ref)
                if not _valid_port(port):
                    _issue(issues, "warn", "UDP Presets", "Ungültiger Preset-Port", f"{ref}: {port}")
        _add_duplicate_issues(issues, preset_ports, "UDP Presets", "Doppelter UDP Preset-Port")
    except Exception as e:
        _issue(issues, "error", "UDP Presets", "Prüfung fehlgeschlagen", str(e))

    # Sidebar Links
    try:
        for idx, item in enumerate(load_sidebar_links()):
            if not isinstance(item, dict):
                continue
            label = str(item.get("label", "") or "").strip()
            url = str(item.get("url", "") or "").strip()
            ref = f"Link {idx + 1}"
            if item.get("enabled", True) and not (label and url):
                _issue(issues, "info", "Sidebar Links", "Aktiver Link unvollständig", ref)
            if label:
                _track_seen(sidebar_labels, label.lower(), label, ref)
            if url:
                _track_seen(sidebar_urls, url.lower(), url, ref)
    except Exception as e:
        _issue(issues, "error", "Sidebar Links", "Prüfung fehlgeschlagen", str(e))

    # Duplicates after collection
    _add_duplicate_issues(issues, mqtt_sources, "MQTT", "Doppeltes MQTT Source Topic", "Mehrere aktive/konfigurierte Mappings hören auf dasselbe Topic. ")
    _add_duplicate_issues(issues, custom_topics, "MQTT", "Doppeltes Custom Topic", "Custom Topics sollten eindeutig bleiben. ")
    _add_duplicate_issues(issues, knx_ga_tx, "KNX", "Doppelte KNX Sende-Gruppenadresse", "Mehrere MQTT→KNX Mappings schreiben auf dieselbe GA. ")
    _add_duplicate_issues(issues, knx_ga_rx, "KNX", "Doppelte KNX Empfangs-Gruppenadresse", "Mehrere KNX→MQTT Mappings lesen dieselbe GA. ")
    _add_duplicate_issues(issues, mqtt_targets, "MQTT", "Doppeltes MQTT Ziel/Topic", "Mehrere Bereiche können dasselbe MQTT Topic erzeugen oder verwalten. ")
    _add_duplicate_issues(issues, udp_targets, "UDP", "Doppeltes UDP Ziel", "Gleiche IP/Port/Topic-Kombination mehrfach vorhanden. ")
    _add_duplicate_issues(issues, broker_names, "MQTT Broker", "Doppelter Brokername")
    _add_duplicate_issues(issues, sidebar_labels, "Sidebar Links", "Doppelter Link-Name")
    _add_duplicate_issues(issues, sidebar_urls, "Sidebar Links", "Doppelte Link-URL")

    level_order = {"error": 0, "warn": 1, "info": 2}
    return sorted(issues, key=lambda x: (level_order.get(x.get("level"), 9), x.get("area", ""), x.get("title", "")))


def conflict_scanner_content():
    issues = collect_config_conflicts()
    errors = len([x for x in issues if x.get("level") == "error"])
    warnings = len([x for x in issues if x.get("level") == "warn"])
    infos = len([x for x in issues if x.get("level") == "info"])

    if not issues:
        body = """
<div class=\"card ok-card\">
    <h2>🟢 Keine Konflikte gefunden</h2>
    <p class=\"small\">Alles sauber. Kein doppeltes Topic-Gulasch, keine KNX-Geisteradresse, kein UDP-Kabelsalat. TÜV-Plakette virtuell erteilt.</p>
</div>"""
    else:
        rows = ""
        icon_map = {"error": "🔴", "warn": "⚠️", "info": "ℹ️"}
        label_map = {"error": "Fehler", "warn": "Warnung", "info": "Hinweis"}
        for item in issues:
            level = item.get("level", "warn")
            items = item.get("items", []) or []
            details = escape(item.get("details", ""))
            if items:
                rendered_items = []
                for x in items:
                    if isinstance(x, dict):
                        rendered_items.append(f"<span class='small'>• <a class='issue-jump' href='{escape(str(x.get('link', '#')))}'>{escape(str(x.get('text', '')))}</a></span>")
                    else:
                        rendered_items.append(f"<span class='small'>• {escape(str(x))}</span>")
                details += "<br>" + "<br>".join(rendered_items)
            jump = escape(item.get("link", "#"))
            rows += f"""
<tr class="issue-{escape(level)} clickable-issue" onclick="window.location.href='{jump}'" title="Zur Problemstelle springen">
    <td style="width:90px;"><b>{icon_map.get(level, '⚠️')} {escape(label_map.get(level, level))}</b></td>
    <td style="width:150px;">{escape(item.get('area', ''))}</td>
    <td><b>{escape(item.get('title', ''))}</b><br><span class="small">{details}</span><br><a class="jump-link" href="{jump}" onclick="event.stopPropagation()">↪ Zur Stelle springen</a></td>
</tr>"""
        body = f"""
<div class=\"card\">
    <h2 class=\"section-title\">Gefundene Punkte</h2>
    <table>
        <tr><th>Typ</th><th>Bereich</th><th>Details</th></tr>
        {rows}
    </table>
</div>"""

    return f"""
<style>
.check-grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(170px, 1fr)); gap:14px; }}
.check-stat {{ background:#11151d; border:1px solid var(--border); border-radius:14px; padding:14px; }}
.check-stat b {{ font-size:24px; display:block; margin-top:6px; }}
.ok-card {{ border-color:rgba(84,211,125,.45); background:#122017; }}
.issue-error td {{ background:rgba(194,59,59,.08); }}
.issue-warn td {{ background:rgba(255,184,107,.06); }}
.issue-info td {{ background:rgba(91,124,250,.05); }}
.clickable-issue {{ cursor:pointer; }}
.clickable-issue:hover td {{ background:rgba(91,124,250,.13); }}
.jump-link, .issue-jump {{ color:#8fb0ff; text-decoration:none; font-weight:700; }}
.jump-link:hover, .issue-jump:hover {{ text-decoration:underline; }}
</style>
<div class=\"card compact-card\">
    <h1>Konfig prüfen</h1>
    <p class=\"small\">Der Konfliktscanner prüft deine Mappings auf doppelte Topics, KNX-Gruppenadressen, UDP-Ziele, Broker-Namen, leere Zeilen und kleine Stolperfallen.</p>
    <div class=\"check-grid\">
        <div class=\"check-stat\"><span class=\"small\">Fehler</span><b>{errors}</b></div>
        <div class=\"check-stat\"><span class=\"small\">Warnungen</span><b>{warnings}</b></div>
        <div class=\"check-stat\"><span class=\"small\">Hinweise</span><b>{infos}</b></div>
        <div class=\"check-stat\"><span class=\"small\">Gesamt</span><b>{len(issues)}</b></div>
    </div>
</div>
{body}
"""



def sse_response(event_name, payload_func, version_name, interval=0.2):
    """Simple SSE stream: initial payload immediately, then only on data changes.

    EventSource reconnects automatically in the browser if the connection drops.
    """
    def event_stream():
        last_version = None
        last_heartbeat = 0
        while True:
            try:
                if version_name == "knx":
                    version = get_knx_monitor_version()
                else:
                    version = int(sse_versions.get(version_name, 0))
                now = time.time()

                if last_version is None or version != last_version:
                    data = payload_func()
                    yield f"event: {event_name}\n"
                    yield "data: " + json.dumps(data, ensure_ascii=False, default=str) + "\n\n"
                    last_version = version
                    last_heartbeat = now
                elif now - last_heartbeat > 15:
                    yield ": keepalive\n\n"
                    last_heartbeat = now

                time.sleep(interval)
            except GeneratorExit:
                break
            except Exception as e:
                yield f"event: error\ndata: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
                time.sleep(2)

    return Response(stream_with_context(event_stream()), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no"
    })


def live_log_payload(limit=12):
    with runtime_context.live_log.lock:
        return runtime_service.live_log_payload(runtime_context.live_log.entries, limit)


def live_log_full_payload(limit=100):
    with runtime_context.live_log.lock:
        return {"logs": runtime_service.get_live_log_entries(runtime_context.live_log.entries, limit)}


def shell_status_payload():
    return runtime_service.build_status_payload(runtime_context.bridge.status)


def status_sse_response():
    return runtime_service.status_sse_response(Response, stream_with_context, shell_status_payload, lambda: runtime_context.bridge.status)


def knx_monitor_payload():
    return {
        "log": get_knx_monitor_log(),
        "last": get_knx_monitor_values(),
        "enabled": bool(load_knx_config().get("enabled", False)),
    }



def dashboard_content():
    config = load_config()
    loxone_explorer_count = loxone_service.get_loxone_explorer_count(load_config, load_mapping, add_log_entry, load_topic_config, lambda: state_mapping, build_state_topic)
    mqtt2lox_count = len(load_mqtt2lox_config())
    mqtt2udp_count = len(load_mqtt2udp_config())
    udp2mqtt_count = len(load_udp2mqtt_config())
    mqtt2knx_count = len(load_mqtt2knx_config())
    knx2mqtt_count = len(load_knx2mqtt_config())
    udp2knx_count = len(load_udp2knx_config())
    knx2lox_count = len(load_knx2lox_config())
    broker_count = len(load_mqtt_brokers())
    udp_cfg = config.get("udp_input", {})
    udp_state = "aktiv" if udp_cfg.get("enabled", False) else "aus"
    plugin_count = len([p for p in load_plugins_config() if p.get("enabled")])
    with runtime_context.live_log.lock:
        logs = list(runtime_context.live_log.entries)[:8]

    log_html = "".join(f"<div class='small'>{escape(str(x))}</div>" for x in logs) or "<div class='small'>Noch keine Logeinträge.</div>"

    return f"""
<div class="card compact-card">
    <h2 class="section-title">System</h2>
    <div class="system-grid">
        <div><div class="muted">Loxone</div><b>{escape(str(config.get('loxone', {}).get('host', '-')))}</b></div>
        <div><div class="muted">MQTT Hauptbroker</div><b>{escape(str(config.get('mqtt', {}).get('host', '-')))}:{escape(str(config.get('mqtt', {}).get('port', '-')))}</b></div>
        <div><div class="muted">Zusätzliche Broker</div><b>{broker_count}</b></div>
        <div><div class="muted">Interner Broker</div><b>{escape(str(get_internal_broker_status().get('state','-')))}</b></div>
        <div><div class="muted">Influx</div><b>{'aktiv' if config.get('influx', {}).get('enabled') else 'aus'}</b></div>
        <div><div class="muted">Plugins aktiv</div><b>{plugin_count}</b></div>
    </div>
</div>

<div class="grid dashboard-grid">
    <a class="card dashboard-tile" href="/mqtt2lox">
        <div class="muted">MQTT → Loxone</div>
        <div class="stat-value">{mqtt2lox_count}</div>
        <div class="small">Mappings</div>
    </a>
    <a class="card dashboard-tile" href="/mqtt2udp">
        <div class="muted">MQTT → UDP</div>
        <div class="stat-value">{mqtt2udp_count}</div>
        <div class="small">Mappings</div>
    </a>
    <a class="card dashboard-tile" href="/mqtt2knx">
        <div class="muted">MQTT → KNX</div>
        <div class="stat-value">{mqtt2knx_count}</div>
        <div class="small">Mappings</div>
    </a>
    <a class="card dashboard-tile" href="/knx">
        <div class="muted">KNX Hub</div>
        <div class="stat-value">{mqtt2knx_count + knx2mqtt_count + udp2knx_count + knx2lox_count}</div>
        <div class="small">KNX Mappings gesamt</div>
    </a>
    <a class="card dashboard-tile" href="/mqtt">
        <div class="muted">MQTT Hub</div>
        <div class="stat-value">{mqtt2lox_count + mqtt2udp_count + udp2mqtt_count + mqtt2knx_count + knx2mqtt_count}</div>
        <div class="small">MQTT Mappings gesamt</div>
    </a>

</div>

<div class="card compact-card">
    <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;">
        <h2 class="section-title">Live Log</h2>
        <div class="button-row">
            <button type="button" id="dashboardLogPauseBtn" onclick="toggleDashboardLogPause()">Pause</button>
            <a class="button-link" href="/live_log">Log-Konsole</a>
        </div>
    </div>
    <div id="liveLogEntries">{log_html}</div>
</div>

<script>
let dashboardLogPaused = false;
let dashboardLastLogData = null;

function dashboardEsc(str) {{
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}}

function renderLiveLog(data) {{
    dashboardLastLogData = data || dashboardLastLogData;
    if (dashboardLogPaused) return;

    const box = document.getElementById("liveLogEntries");
    if (!box) return;

    const logs = (data && data.logs) || [];
    if (!logs.length) {{
        box.innerHTML = '<div class="small">Noch keine Logeinträge.</div>';
        return;
    }}

    box.innerHTML = logs.map(x => '<div class="small">' + dashboardEsc(x) + '</div>').join("");
}}

function toggleDashboardLogPause() {{
    dashboardLogPaused = !dashboardLogPaused;
    const btn = document.getElementById("dashboardLogPauseBtn");
    if (btn) btn.textContent = dashboardLogPaused ? "Weiter" : "Pause";
    if (!dashboardLogPaused && dashboardLastLogData) renderLiveLog(dashboardLastLogData);
}}

function startLiveLogStream() {{
    if (!window.EventSource) {{
        return;
    }}
    const es = new EventSource("/events/live_log");
    es.addEventListener("live_log", ev => renderLiveLog(JSON.parse(ev.data || "{{}}")));
    es.onerror = () => console.log("LiveLog SSE reconnect...");
}}

startLiveLogStream();
</script>
"""


def live_log_console_content():
    with runtime_context.live_log.lock:
        logs = list(runtime_context.live_log.entries)[:100]
    log_html = "".join(f"<div class='log-line'>{escape(str(x))}</div>" for x in logs) or "<div class='small'>Noch keine Logeinträge.</div>"
    return f"""
<h1>Live-Log</h1>
<div class="card compact-card">
    <div class="button-row">
        <button type="button" id="pauseBtn" onclick="togglePause()">Pause</button>
        <button type="button" id="autoBtn" onclick="toggleAutoScroll()">Auto-Scroll: an</button>
        <button type="button" onclick="clearView()">Ansicht leeren</button>
        <a class="button-link" href="/clear_log" onclick="return confirm('Live-Log wirklich komplett leeren?')">Server-Log leeren</a>
    </div>
    <label>Suche / Filter</label>
    <input id="logSearch" placeholder="z.B. MQTT2LOX, Fehler, KNX, Topic..." oninput="renderLog()">
    <div class="small" id="logSummary" style="margin-top:8px;">Live per SSE · Anzeige pausierbar</div>
</div>

<div class="card">
    <div id="logConsole" class="log-console">{log_html}</div>
</div>

<style>
.log-console {{
    height:calc(100vh - 235px);
    min-height:360px;
    overflow:auto;
    background:#0d1217;
    border:1px solid #303b45;
    border-radius:6px;
    padding:10px;
    font-family:Consolas, 'Courier New', monospace;
    font-size:13px;
    line-height:1.35;
}}
.log-line {{
    white-space:pre-wrap;
    border-bottom:1px solid rgba(255,255,255,.05);
    padding:3px 0;
    color:#dce6ef;
}}
.log-line.hit {{ background:rgba(255,255,255,.08); }}
</style>

<script>
let paused = false;
let autoScroll = true;
let allLogs = {json.dumps([str(x) for x in logs], ensure_ascii=False)};
let visibleCleared = false;

function escLog(str) {{
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}}

function togglePause() {{
    paused = !paused;
    document.getElementById("pauseBtn").textContent = paused ? "Weiter" : "Pause";
    if (!paused) renderLog();
}}

function toggleAutoScroll() {{
    autoScroll = !autoScroll;
    document.getElementById("autoBtn").textContent = "Auto-Scroll: " + (autoScroll ? "an" : "aus");
}}

function clearView() {{
    visibleCleared = true;
    allLogs = [];
    renderLog();
}}

function renderLog() {{
    const box = document.getElementById("logConsole");
    const summary = document.getElementById("logSummary");
    const q = (document.getElementById("logSearch").value || "").toLowerCase();
    let rows = allLogs || [];
    if (q) rows = rows.filter(x => String(x).toLowerCase().includes(q));

    if (!rows.length) {{
        box.innerHTML = '<div class="small">Keine Logeinträge in dieser Ansicht.</div>';
    }} else {{
        box.innerHTML = rows.map(x => '<div class="log-line' + (q ? ' hit' : '') + '">' + escLog(x) + '</div>').join("");
    }}

    summary.textContent = `${{rows.length}} angezeigt · ${{allLogs.length}} im Speicher · ` + (paused ? "Anzeige pausiert" : "Live") + " · Auto-Scroll " + (autoScroll ? "an" : "aus");
    if (autoScroll && !paused) box.scrollTop = 0;
}}

function startLogConsoleStream() {{
    if (!window.EventSource) return;
    const es = new EventSource("/events/live_log_full");
    es.addEventListener("live_log", ev => {{
        if (paused) return;
        visibleCleared = false;
        const data = JSON.parse(ev.data || "{{}}");
        allLogs = data.logs || [];
        renderLog();
    }});
    es.onerror = () => console.log("LiveLog Console SSE reconnect...");
}}

renderLog();
startLogConsoleStream();
</script>
"""


def core_settings_content(config, notice=""):
    def checked(value):
        return "checked" if value else ""

    lox = config.get("loxone", {})
    bridge = config.get("bridge", {})
    notice_html = notice or ""

    return f'''
{notice_html}
<form method="post" action="/save_core">
    <div class="card">
        <h2 class="section-title">Loxone Miniserver</h2>
        <label>IP / Host</label>
        <input name="loxone_host" value="{escape(str(lox.get('host', '')))}">
        <label>Benutzer</label>
        <input name="loxone_user" value="{escape(str(lox.get('user', '')))}">
        <label>Passwort</label>
        <input name="loxone_password" type="password" value="{escape(str(lox.get('password', '')))}">

        <div class="button-row" style="margin-top:14px;">
            <button type="submit">Speichern</button>
            <button type="submit" formaction="/test/loxone" formmethod="post">Loxone testen</button>
        </div>
    </div>

    <div class="card">
        <h2 class="section-title">Bridge Einstellungen</h2>
        <label>Pulse Zeit Sekunden</label>
        <input name="pulse_time" value="{escape(str(bridge.get('pulse_time', 0.5)))}">
        <label>Rundung Nachkommastellen</label>
        <input name="round_digits" value="{escape(str(bridge.get('round_digits', 4)))}">
        <label><input type="checkbox" name="retain" {checked(bridge.get('retain'))}> Letzten Wert speichern</label>
        <label><input type="checkbox" name="change_only" {checked(bridge.get('change_only'))}> Nur bei Änderung senden</label>

        <div class="button-row" style="margin-top:14px;">
            <button type="submit">Speichern</button>
        </div>
    </div>
</form>
'''


def sidebar_links_settings_content():
    links = load_sidebar_links()
    new_i = len(links)
    rows = ""

    for i, item in enumerate(links):
        enabled = "checked" if item.get("enabled", True) else ""
        new_tab = "checked" if item.get("new_tab", True) else ""
        rows += f"""
            <tr>
                <td style="text-align:center;"><input type="checkbox" name="enabled_{i}" {enabled}></td>
                <td><input type="text" name="label_{i}" value="{escape(str(item.get('label', '')))}" placeholder="z.B. Node-RED"></td>
                <td><input type="text" name="url_{i}" value="{escape(str(item.get('url', '')))}" placeholder="http://172.16.12.223:1880"></td>
                <td style="text-align:center;"><input type="checkbox" name="new_tab_{i}" {new_tab}></td>
                <td style="text-align:center;"><input type="checkbox" name="delete_{i}"></td>
            </tr>
        """

    rows += f"""
            <tr>
                <td style="text-align:center;"><input type="checkbox" name="enabled_{new_i}" checked></td>
                <td><input type="text" name="label_{new_i}" placeholder="z.B. Zigbee2MQTT"></td>
                <td><input type="text" name="url_{new_i}" placeholder="http://172.16.12.223:8080"></td>
                <td style="text-align:center;"><input type="checkbox" name="new_tab_{new_i}" checked></td>
                <td>-</td>
            </tr>
    """

    return f"""
<form method="post" action="/sidebar_links/save">
    <div class="card">
        <h2 class="section-title">Sidebar Buttons</h2>
        <p class="small">Hier kannst du eigene Verknüpfungen in der linken Seitenleiste anlegen, z.B. Node-RED, Zigbee2MQTT, InfluxDB oder ioBroker.</p>
        <table>
            <tr>
                <th>Aktiv</th>
                <th>Name</th>
                <th>URL</th>
                <th>Neuer Tab</th>
                <th>Löschen</th>
            </tr>
            {rows}
        </table>
        <input type="hidden" name="count" value="{len(links)+1}">
        <div class="button-row" style="margin-top:14px;">
            <button type="submit">Sidebar Buttons speichern</button>
        </div>
    </div>
</form>
"""


def settings_content(config, notice=""):
    knx_cfg = load_knx_config()
    udp_cfg = config.get("udp_input", {})
    influx = config.get("influx", {})
    mqtt = config.get("mqtt", {})
    lox = config.get("loxone", {})

    modules = [
        {"name": "Bridge / Loxone", "status": runtime_context.bridge.status, "desc": f"Miniserver {lox.get('host', '-')}, Bridge-Basiswerte", "route": "/core_settings_embed"},
        {"name": "MQTT Broker", "status": f"{mqtt.get('host', '-')}:{mqtt.get('port', '-')}", "desc": "Hauptbroker, zusätzliche Broker und Prefix", "route": "/mqtt_settings_embed"},
        {"name": "UDP", "status": "aktiv" if udp_cfg.get("enabled") else "aus", "desc": f"UDP → MQTT Eingang auf Port {udp_cfg.get('port', '-')}; MQTT → UDP Mappings bleiben links unter Mappings", "route": "/udp_input"},
        {"name": "InfluxDB", "status": "aktiv" if influx.get("enabled") else "aus", "desc": "Zeitreihen-Ausgabe / Logging", "route": "/influx_settings_embed"},
        {"name": "KNX", "status": "aktiv" if knx_cfg.get("enabled") else "aus", "desc": f"Gateway {knx_cfg.get('gateway_ip', '-')}:{knx_cfg.get('gateway_port', '-')}; Mappings liegen im KNX Hub", "route": "/knx_settings_embed"}
    ]

    rows = ""
    for m in modules:
        rows += f'''
<tr>
    <td><b>{escape(str(m["name"]))}</b></td>
    <td>{escape(str(m["status"]))}</td>
    <td>{escape(str(m["desc"]))}</td>
    <td><a class="button-link" href="{escape(str(m["route"]))}">Öffnen</a></td>
</tr>'''

    return f'''
{notice or ""}
<div class="card compact-card">
    <h2 class="section-title">Einstellungen</h2>
    <p class="small">Zentrale Modul-Übersicht. Die Sidebar bleibt für Dashboard, Monitor und die Mapping-Seiten frei.</p>
</div>

<div class="card">
    <table>
        <tr>
            <th>Modul</th>
            <th>Status</th>
            <th>Beschreibung</th>
            <th class="actions">Aktion</th>
        </tr>
        {rows}
    </table>
</div>

{sidebar_links_settings_content()}

<div class="card">
    <h2 class="section-title">Template Export / Import</h2>
    <p class="small">Gezielte Mapping-Pakete für einzelne Integrationen exportieren oder importieren. Das ist unabhängig vom kompletten Backup.</p>
    <div class="button-row">
        <a href="/templates" class="button-link">Template exportieren / importieren</a>
    </div>
</div>

<div class="card">
    <h2 class="section-title">Backup / Restore</h2>
    <p class="small">Backup sichert automatisch alle JSON-Konfigurationsdateien plus interne Mosquitto-Konfiguration.</p>
    <div class="button-row">
        <a href="/backup" class="button-link">Backup herunterladen</a>
        <form method="post" action="/restore" enctype="multipart/form-data" class="restore-form">
            <input type="file" name="backup_file" accept=".zip" required class="file-upload">
            <button type="submit">Backup wiederherstellen</button>
        </form>
    </div>
</div>
'''



def internal_broker_settings_block(notice=""):
    cfg = load_internal_broker_config()
    status = get_internal_broker_status()
    def checked(value):
        return "checked" if value else ""
    state_class = "ok" if status.get("running") else "bad"
    state_text = escape(str(status.get("state", "-")))
    exe_hint = "" if status.get("exe_found") else '<div class="small bad">Mosquitto wurde nicht gefunden. Pfad unten eintragen oder PATH prüfen.</div>'
    return f"""
<form method="post" action="/internal_broker/save">
    <div class="card">
        <h2 class="section-title">Interner MQTT Broker</h2>
        <p class="small">Startet einen lokalen Mosquitto Broker aus der Bridge heraus. Wenn aktiv, kann die Bridge diesen Broker als Hauptbroker verwenden.</p>
        <div class="grid">
            <div><div class="muted">Status</div><div class="stat-value {state_class}">{state_text}</div></div>
            <div><div class="muted">Port</div><div class="stat-value">{escape(str(status.get('port','-')))}</div></div>
            <div><div class="muted">Als Hauptbroker</div><div class="stat-value">{'ja' if status.get('use_as_main') else 'nein'}</div></div>
        </div>
        {exe_hint}
        <label><input type="checkbox" name="internal_enabled" {checked(cfg.get('enabled'))}> Internen Broker aktivieren</label>
        <label><input type="checkbox" name="internal_use_as_main" {checked(cfg.get('use_as_main'))}> Internen Broker als Hauptbroker der Bridge verwenden</label>
        <label>Listener Host</label><input name="internal_host" value="{escape(str(cfg.get('host','0.0.0.0')))}">
        <label>Connect Host für Bridge</label><input name="internal_connect_host" value="{escape(str(cfg.get('connect_host','127.0.0.1')))}">
        <label>Port</label><input name="internal_port" value="{escape(str(cfg.get('port',1883)))}">
        <label>Mosquitto Pfad</label><input name="internal_mosquitto_path" value="{escape(str(cfg.get('mosquitto_path','mosquitto')))}">
        <label><input type="checkbox" name="internal_allow_anonymous" {checked(cfg.get('allow_anonymous'))}> Anonyme Anmeldung erlauben</label>
        <label>Benutzer optional</label><input name="internal_user" value="{escape(str(cfg.get('user','')))}">
        <label>Passwort optional</label><input name="internal_password" type="password" value="{escape(str(cfg.get('password','')))}">
        <label><input type="checkbox" name="internal_persistence" {checked(cfg.get('persistence'))}> Persistenz aktivieren</label>
        <div class="button-row" style="margin-top:14px;">
            <button type="submit">Internen Broker speichern</button>
            <button type="submit" formaction="/internal_broker/start" formmethod="post">Starten</button>
            <button type="submit" formaction="/internal_broker/stop" formmethod="post">Stoppen</button>
        </div>
    </div>
</form>
"""

def mqtt_settings_content(config, notice=""):
    def checked(value):
        return "checked" if value else ""

    mq = config.get("mqtt", {})
    brokers = load_mqtt_brokers()
    new_i = len(brokers)
    notice_html = notice or ""

    html = f"""
{notice_html}
<form method="post" action="/save_mqtt">
    <div class="card">
        <h2 class="section-title">MQTT Hauptbroker</h2>
        <label>Host</label>
        <input name="mqtt_host" value="{escape(str(mq.get('host', '')))}">
        <label>Port</label>
        <input name="mqtt_port" value="{escape(str(mq.get('port', 1883)))}">
        <label>Benutzer optional</label>
        <input name="mqtt_user" value="{escape(str(mq.get('user', '')))}">
        <label>Passwort optional</label>
        <input name="mqtt_password" type="password" value="{escape(str(mq.get('password', '')))}">
        <label>Prefix</label>
        <input name="mqtt_prefix" value="{escape(str(mq.get('prefix', 'loxone')))}">

        <div class="button-row" style="margin-top:14px;">
            <button type="submit">MQTT speichern</button>
            <button type="submit" formaction="/test/mqtt" formmethod="post">MQTT testen</button>
        </div>
    </div>
</form>

{internal_broker_settings_block()}

<form method="post" action="/mqtt_brokers/save">
    <div class="card">
        <h2 class="section-title">Zusätzliche MQTT Broker</h2>
        <p class="small">Diese Broker werden zusätzlich abonniert. Der Hauptbroker bleibt der Broker, auf den die Bridge aktiv publisht.</p>
        <table>
            <tr>
                <th>Aktiv</th>
                <th>Name</th>
                <th>Host</th>
                <th>Port</th>
                <th>User</th>
                <th>Passwort</th>
                <th>Test</th>
                <th>Löschen</th>
            </tr>
"""

    for i, item in enumerate(brokers):
        enabled = item.get("enabled", True)
        checked_state = "checked" if enabled else ""
        html += f"""
            <tr>
                <td><input type="checkbox" name="enabled_{i}" {checked_state}></td>
                <td><input type="text" name="name_{i}" value="{escape(item.get('name', ''))}"></td>
                <td><input type="text" name="host_{i}" value="{escape(item.get('host', ''))}"></td>
                <td><input type="text" name="port_{i}" value="{escape(str(item.get('port', 1883)))}"></td>
                <td><input type="text" name="user_{i}" value="{escape(item.get('user', ''))}"></td>
                <td><input type="password" name="password_{i}" value="{escape(item.get('password', ''))}"></td>
                <td><button type="submit" formaction="/test/mqtt_broker/{i}" formmethod="post">Test</button></td>
                <td class="checkbox-col"><input type="checkbox" name="delete_{i}"></td>
            </tr>
"""

    html += f"""
            <tr>
                <td class="checkbox-col"><input type="checkbox" name="enabled_{new_i}" checked></td>
                <td><input type="text" name="name_{new_i}"></td>
                <td><input type="text" name="host_{new_i}"></td>
                <td><input type="text" name="port_{new_i}" value="1883"></td>
                <td><input type="text" name="user_{new_i}"></td>
                <td><input type="password" name="password_{new_i}"></td>
                <td>-</td>
                <td>-</td>
            </tr>
        </table>
        <input type="hidden" name="count" value="{len(brokers)+1}">
        <div class="button-row" style="margin-top:14px;">
            <button type="submit">Zusätzliche Broker speichern</button>
        </div>
    </div>
</form>
"""
    return html


def influx_settings_content(config, notice=""):
    def checked(value):
        return "checked" if value else ""

    influx = config.get("influx", {})
    notice_html = notice or ""

    return f"""
{notice_html}
<form method="post" action="/save_influx">
    <div class="card">
        <h2 class="section-title">InfluxDB Einstellungen</h2>
        <label><input type="checkbox" name="influx_enabled" {checked(influx.get('enabled'))}> InfluxDB aktivieren</label>
        <label>Version</label>
        <select name="influx_version">
            <option value="1" {'selected' if str(influx.get('version')) == '1' else ''}>InfluxDB 1.x</option>
            <option value="2" {'selected' if str(influx.get('version')) == '2' else ''}>InfluxDB 2.x</option>
        </select>
        <label>Host</label><input name="influx_host" value="{escape(str(influx.get('host', '')))}">
        <label>Port</label><input name="influx_port" value="{escape(str(influx.get('port', 8086)))}">
        <label>Datenbank Influx 1.x</label><input name="influx_database" value="{escape(str(influx.get('database', '')))}">
        <label>Bucket Influx 2.x</label><input name="influx_bucket" value="{escape(str(influx.get('bucket', '')))}">
        <label>Organisation Influx 2.x</label><input name="influx_org" value="{escape(str(influx.get('org', '')))}">
        <label>Token Influx 2.x</label><input name="influx_token" type="password" value="{escape(str(influx.get('token', '')))}">
        <label>Benutzer optional</label><input name="influx_user" value="{escape(str(influx.get('user', '')))}">
        <label>Passwort optional</label><input name="influx_password" type="password" value="{escape(str(influx.get('password', '')))}">
        <label>Standard Measurement</label><input name="influx_measurement" value="{escape(str(influx.get('measurement', 'loxone')))}">

        <div class="button-row" style="margin-top:14px;">
            <button type="submit">Influx speichern</button>
            <button type="submit" formaction="/test/influx" formmethod="post">Influx testen</button>
        </div>
    </div>
</form>
"""


SHELL_LAYOUT = """
<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MQTT2Lox</title>
<style>
:root {
    --bg:#1e252c;
    --side:#171d23;
    --side2:#151a20;
    --content:#202830;
    --text:#f4f7fb;
    --muted:#b8c1cc;
    --green:#7CFF75;
    --button:#5f686f;
    --button-hover:#727d85;
    --active:#5f686f;
    --border:#2a333c;
}
* { box-sizing:border-box; }
html, body {
    margin:0;
    width:100%;
    height:100%;
    background:var(--bg);
    color:var(--text);
    font-family:Arial, sans-serif;
    overflow:hidden;
}
.shell {
    display:grid;
    grid-template-columns:185px 1fr;
    grid-template-rows:92px 1fr;
    height:100vh;
    width:100vw;
}
.header {
    grid-column:1 / 3;
    grid-row:1;
    display:flex;
    align-items:center;
    padding:0 14px;
    background:var(--side2);
}
.brand {
    display:flex;
    align-items:center;
    gap:14px;
    min-width:185px;
}
.brand h1 {
    margin:0;
    font-size:24px;
    line-height:1;
    color:var(--green);
    font-weight:800;
}
.status {
    font-size:11px;
    font-weight:700;
    color:#fff;
}
.status b { color:var(--green); }
.header-search {
    display:flex;
    align-items:center;
    gap:8px;
    margin-left:24px;
    min-width:340px;
    max-width:560px;
    flex:1;
}
.header-search input {
    height:30px;
    border:1px solid #3b4652;
    border-radius:4px;
    background:#10151b;
    color:#fff;
    padding:0 10px;
    font-size:13px;
    width:100%;
}
.header-search button {
    width:auto;
    min-width:74px;
    height:30px;
    border:none;
    border-radius:4px;
    background:var(--button);
    color:white;
    font-size:13px;
    font-weight:700;
    cursor:pointer;
}
.header-search button:hover { background:var(--button-hover); }
.top-actions {
    margin-left:auto;
    display:flex;
    gap:8px;
}
.top-actions button {
    width:116px;
    height:24px;
    border:none;
    border-radius:3px;
    background:var(--button);
    color:white;
    font-size:13px;
    font-weight:700;
    cursor:pointer;
}
.top-actions button:hover { background:var(--button-hover); }
.sidebar {
    grid-column:1;
    grid-row:2;
    background:var(--side);
    padding-top:16px;
}
.nav {
    display:flex;
    flex-direction:column;
    align-items:center;
    gap:15px;
}
.nav a {
    min-width:116px;
    text-align:center;
    color:white;
    text-decoration:none;
    font-weight:700;
    font-size:14px;
    padding:6px 10px;
    border-radius:4px;
}
.nav a.active,
.nav a:hover {
    background:var(--active);
}
.nav .spacer { height:26px; }
.nav .external-spacer { height:8px; }
.settings-submenu { display:none; flex-direction:column; align-items:center; gap:9px; margin-top:-6px; }
.settings-submenu a { min-width:116px; font-size:12px; opacity:.92; padding:4px 8px; }
.settings-submenu.open { display:flex; }
.content-wrap {
    grid-column:2;
    grid-row:2;
    background:var(--content);
    overflow:hidden;
    position:relative;
}
#contentFrame {
    width:100%;
    height:100%;
    border:0;
    background:var(--content);
}
@media(max-width:850px) {
    html, body { overflow:auto; }
    .shell {
        display:block;
        height:auto;
    }
    .header {
        height:auto;
        padding:14px;
        flex-wrap:wrap;
        gap:12px;
    }
    .brand { min-width:0; }
    .header-search {
        margin-left:0;
        min-width:100%;
        max-width:none;
        width:100%;
    }
    .top-actions {
        margin-left:0;
        width:100%;
    }
    .top-actions button { flex:1; }
    .sidebar {
        padding:10px;
    }
    .nav {
        flex-direction:row;
        align-items:flex-start;
        justify-content:flex-start;
        flex-wrap:wrap;
        gap:8px;
    }
    .nav .spacer { display:none; }
    .content-wrap {
        height:calc(100vh - 145px);
        min-height:600px;
    }
}
</style>
</head>
<body>
<div class="shell">
    <header class="header">
        <div class="brand">
            <h1>Loxone Bridge</h1>
            <div class="status">Status: <b id="bridgeStatus">{{ status }}</b></div>
        </div>


        <div class="top-actions">
            <button onclick="bridgeControl('/start')">Start</button>
            <button onclick="bridgeControl('/stop')">Stopp</button>
        </div>
    </header>

    <aside class="sidebar">
                <nav class="nav">
            <a class="active" href="/dashboard_embed" target="contentFrame" onclick="setActive(this)">Dashboard</a>
            <a href="/monitor" target="contentFrame" onclick="setActive(this)">MQTT Monitor</a>
<a href="/topics2" target="contentFrame" onclick="setActive(this)">Loxone Monitor</a>
            <a href="/mqtt" target="contentFrame" onclick="setActive(this)">MQTT Hub</a>
            <a href="/influx_explorer" target="contentFrame" onclick="setActive(this)">Influx Explorer</a>
            <a href="/objects" target="contentFrame" onclick="setActive(this)">Objektmanager</a>
            <a href="/knx" target="contentFrame" onclick="setActive(this)">KNX</a>
            <a href="/knx_monitor" target="contentFrame" onclick="setActive(this)">KNX Monitor</a>
            <a href="/global_search" target="contentFrame" onclick="setActive(this)">Suche</a>
            <a href="/conflicts" target="contentFrame" onclick="setActive(this)">Konfig prüfen</a>
            <span class="spacer"></span>
            {{ sidebar_links_html|safe }}
            <a href="/settings_embed" target="contentFrame" onclick="setActive(this)">Einstellungen</a>
        </nav>
    </aside>

    <main class="content-wrap">
        <iframe id="contentFrame" name="contentFrame" src="/dashboard_embed"></iframe>
    </main>
</div>

<script>
function setActive(el) {
    document.querySelectorAll(".nav a").forEach(a => a.classList.remove("active"));
    el.classList.add("active");
}

function activateSearchNav() {
    const links = document.querySelectorAll(".nav a");
    links.forEach(a => a.classList.remove("active"));
    links.forEach(a => {
        const href = a.getAttribute("href") || "";
        if (href === "/global_search" || href === "/conflicts") {
            a.classList.add("active");
        }
    });
}

function toggleSettingsMenu(el) {
    const menu = document.getElementById("settingsSubmenu");
    if (!menu) return;
    menu.classList.toggle("open");
}

function bridgeControl(url) {
    fetch(url, {method:"POST"})
        .then(() => {
            const frame = document.getElementById("contentFrame");
            try {
                if (frame.contentWindow && frame.contentWindow.location.pathname === "/dashboard_embed") {
                    frame.contentWindow.location.reload();
                }
            } catch(e) {}
        })
        .catch(err => console.log(err));
}

function setBridgeStatus(data) {
    document.getElementById("bridgeStatus").innerText = (data && data.status) || "-";
}

function startStatusStream() {
    if (!window.EventSource) {
        fetch("/shell_status?t=" + Date.now(), {cache:"no-store"})
            .then(r => r.json())
            .then(setBridgeStatus)
            .catch(err => console.log(err));
        return;
    }
    const es = new EventSource("/events/status");
    es.addEventListener("status", ev => setBridgeStatus(JSON.parse(ev.data || "{}")));
    es.onerror = () => console.log("Status SSE reconnect...");
}

startStatusStream();
</script>
</body>
</html>
"""


def embedded_page(title, content):
    return template_service.embedded_page(title, content)




@app.route("/dashboard_embed")
def dashboard_embed():
    return embedded_page("Dashboard", dashboard_content())


@app.route("/live_log")
def live_log_console():
    return embedded_page("Live-Log", live_log_console_content())


@app.route("/live_log_page")
def live_log_page():
    return render_layout("Live-Log", live_log_console_content(), active="live_log", subtitle="Log-Konsole mit Pause, Filter und Auto-Scroll")


@app.route("/settings_embed")
def settings_embed():
    return embedded_page("Einstellungen", settings_content(load_config()))


@app.route("/core_settings_embed")
def core_settings_embed():
    return embedded_page("Bridge / Loxone", core_settings_content(load_config()))


@app.route("/mqtt_settings_embed")
def mqtt_settings_embed():
    return embedded_page("MQTT Broker", mqtt_settings_content(load_config()))


@app.route("/influx_settings_embed")
def influx_settings_embed():
    return embedded_page("InfluxDB", influx_settings_content(load_config()))


@app.route("/global_search")
def global_search():
    return embedded_page("Globale Suche", global_search_content(request.args.get("q", "")))


@app.route("/conflicts")
def conflicts():
    return embedded_page("Konfig prüfen", conflict_scanner_content())


@app.route("/conflicts_page")
def conflicts_page():
    return render_layout("Konfig prüfen", conflict_scanner_content(), active="conflict_scanner", subtitle="Konfliktscanner für Mappings und Einstellungen")


@app.route("/global_search_page")
def global_search_page():
    return render_layout("Globale Suche", global_search_content(request.args.get("q", "")), active="global_search", subtitle="Suche über alle Mappings und Einstellungen")


def plugins_content(notice=""):
    plugins = load_plugins_config()
    rows = []

    for item in plugins:
        raw_pid = str(item.get("id", ""))
        pid = escape(raw_pid)
        name = escape(str(item.get("name", "")))
        status = escape(str(item.get("status", "")))
        desc = escape(str(item.get("description", "")))
        route = str(item.get("route", "")).strip()
        checked_state = "checked" if item.get("enabled") else ""
        if route:
            route_html = f'<a class="button-link" href="{escape(route)}">Öffnen</a>'
        else:
            route_html = '<span class="small">noch kein Modul</span>'

        rows.append(
            f'<tr id="{pid}">'
            f'<td><input type="checkbox" name="enabled_{pid}" {checked_state}></td>'
            f'<td><b>{name}</b><br><span class="small">{pid}</span></td>'
            f'<td>{status}</td>'
            f'<td>{desc}</td>'
            f'<td>{route_html}</td>'
            f'</tr>'
        )

    rows_html = "".join(rows)

    return f'''
{notice or ""}
<div class="card compact-card">
    <h2 class="section-title">Plugins</h2>
    <p class="small">V13 erweitert KNX: MQTT → KNX und KNX → MQTT. Zigbee bleibt vorbereitet.</p>
</div>

<form method="post" action="/plugins/save">
    <div class="card">
        <table>
            <tr>
                <th>Aktiv</th>
                <th>Plugin</th>
                <th>Status</th>
                <th>Beschreibung</th>
                <th>Seite</th>
            </tr>
            {rows_html}
        </table>
        <div class="button-row" style="margin-top:14px;">
            <button type="submit">Plugins speichern</button>
        </div>
    </div>
</form>
'''


@app.route("/plugins")
def plugins_page():
    return redirect('/settings_embed')




@app.route("/sidebar_links/save", methods=["POST"])
def sidebar_links_save():
    try:
        count = int(request.form.get("count", 0))
    except Exception:
        count = 0

    links = []

    for i in range(count):
        if request.form.get(f"delete_{i}"):
            continue

        label = request.form.get(f"label_{i}", "").strip()
        url = request.form.get(f"url_{i}", "").strip()

        # Leere neue Zeile ignorieren
        if not label and not url:
            continue

        links.append({
            "enabled": f"enabled_{i}" in request.form,
            "label": label,
            "url": url,
            "new_tab": f"new_tab_{i}" in request.form
        })

    save_sidebar_links(links)
    add_log_entry("Sidebar Buttons gespeichert")

    # Die Sidebar sitzt im Parent-Shell. Nach dem Speichern muss die Hauptseite neu laden,
    # sonst sieht man neue/geänderte Buttons erst nach manuellem Refresh.
    return """
<!doctype html>
<html lang="de">
<head><meta charset="utf-8"><title>Sidebar Buttons gespeichert</title></head>
<body style="background:#202830;color:#f4f7fb;font-family:Arial,sans-serif;padding:22px;">
    Sidebar Buttons gespeichert. Oberfläche wird neu geladen...
    <script>
        setTimeout(function() {
            try {
                window.parent.location.reload();
            } catch(e) {
                window.location.href = "/";
            }
        }, 250);
    </script>
</body>
</html>
"""


@app.route("/plugins/save", methods=["POST"])
def save_plugins():
    plugins = load_plugins_config()
    for item in plugins:
        pid = str(item.get("id", ""))
        item["enabled"] = f"enabled_{pid}" in request.form

    save_plugins_config(plugins)
    add_log_entry("Plugin-Konfiguration gespeichert")
    notice = '<div class="card ok">✅ Plugins gespeichert</div>'
    return embedded_page("Plugins", plugins_content(notice))


@app.route("/shell_status")
def shell_status():
    return shell_status_payload()


@app.route("/live_log_data")
def live_log_data():
    return live_log_payload()


@app.route("/")
def index(message=""):
    return render_template_string(SHELL_LAYOUT, status=runtime_context.bridge.status, sidebar_links_html=build_sidebar_links_html())


@app.route("/settings")
def settings_page(message=""):
    return render_layout("Einstellungen", settings_content(load_config()), active="settings", subtitle="Modul-Übersicht und Grundeinstellungen", message=message)


@app.route("/save", methods=["POST"])
def save():
    return save_core()


@app.route("/save_core", methods=["POST"])
def save_core():
    config = load_config()

    config["loxone"] = {
        "host": request.form.get("loxone_host", config.get("loxone", {}).get("host", "")),
        "user": request.form.get("loxone_user", config.get("loxone", {}).get("user", "")),
        "password": request.form.get("loxone_password", config.get("loxone", {}).get("password", ""))
    }

    config["bridge"] = {
        "pulse_time": float(request.form.get("pulse_time", config.get("bridge", {}).get("pulse_time", 0.5))),
        "round_digits": int(request.form.get("round_digits", config.get("bridge", {}).get("round_digits", 4))),
        "retain": "retain" in request.form,
        "change_only": "change_only" in request.form
    }

    save_config(config)
    add_log_entry("Loxone/Bridge-Konfiguration gespeichert")
    restart_bridge_async()

    return redirect('/core_settings_embed')



@app.route("/internal_broker/save", methods=["POST"])
def internal_broker_save():
    cfg = load_internal_broker_config()
    try:
        cfg.update({
            "enabled": "internal_enabled" in request.form,
            "use_as_main": "internal_use_as_main" in request.form,
            "host": request.form.get("internal_host", cfg.get("host", "0.0.0.0")).strip() or "0.0.0.0",
            "connect_host": request.form.get("internal_connect_host", cfg.get("connect_host", "127.0.0.1")).strip() or "127.0.0.1",
            "port": int(request.form.get("internal_port", cfg.get("port", 1883))),
            "mosquitto_path": request.form.get("internal_mosquitto_path", cfg.get("mosquitto_path", "mosquitto")).strip() or "mosquitto",
            "allow_anonymous": "internal_allow_anonymous" in request.form,
            "user": request.form.get("internal_user", cfg.get("user", "")).strip(),
            "password": request.form.get("internal_password", cfg.get("password", "")),
            "persistence": "internal_persistence" in request.form
        })
        save_internal_broker_config(cfg)
        add_log_entry("Interner MQTT Broker gespeichert")
        if cfg.get("use_as_main"):
            restart_bridge_async()
    except Exception as e:
        add_log_entry(f"Interner Broker Speichern Fehler: {e}")
    return redirect('/mqtt_settings_embed')


@app.route("/internal_broker/start", methods=["POST"])
def internal_broker_start():
    internal_broker_save_values_from_form()
    ok, msg = start_internal_broker_process()
    add_log_entry(f"Interner Broker Start: {msg}")
    return redirect('/mqtt_settings_embed')


@app.route("/internal_broker/stop", methods=["POST"])
def internal_broker_stop():
    ok, msg = stop_internal_broker_process()
    add_log_entry(f"Interner Broker Stop: {msg}")
    return redirect('/mqtt_settings_embed')


def internal_broker_save_values_from_form():
    cfg = load_internal_broker_config()
    try:
        cfg.update({
            "enabled": "internal_enabled" in request.form,
            "use_as_main": "internal_use_as_main" in request.form,
            "host": request.form.get("internal_host", cfg.get("host", "0.0.0.0")).strip() or "0.0.0.0",
            "connect_host": request.form.get("internal_connect_host", cfg.get("connect_host", "127.0.0.1")).strip() or "127.0.0.1",
            "port": int(request.form.get("internal_port", cfg.get("port", 1883))),
            "mosquitto_path": request.form.get("internal_mosquitto_path", cfg.get("mosquitto_path", "mosquitto")).strip() or "mosquitto",
            "allow_anonymous": "internal_allow_anonymous" in request.form,
            "user": request.form.get("internal_user", cfg.get("user", "")).strip(),
            "password": request.form.get("internal_password", cfg.get("password", "")),
            "persistence": "internal_persistence" in request.form
        })
        save_internal_broker_config(cfg)
    except Exception as e:
        add_log_entry(f"Interner Broker Formular Fehler: {e}")


@app.route("/internal_broker/status")
def internal_broker_status_route():
    return get_internal_broker_status()

@app.route("/save_mqtt", methods=["POST"])
def save_mqtt():
    config = load_config()

    config["mqtt"] = {
        "host": request.form.get("mqtt_host", config.get("mqtt", {}).get("host", "")),
        "port": int(request.form.get("mqtt_port", config.get("mqtt", {}).get("port", 1883))),
        "user": request.form.get("mqtt_user", config.get("mqtt", {}).get("user", "")),
        "password": request.form.get("mqtt_password", config.get("mqtt", {}).get("password", "")),
        "prefix": request.form.get("mqtt_prefix", config.get("mqtt", {}).get("prefix", "loxone"))
    }

    save_config(config)
    add_log_entry("MQTT Hauptbroker gespeichert")
    restart_bridge_async()

    return redirect('/mqtt_settings_embed')


@app.route("/save_influx", methods=["POST"])
def save_influx():
    config = load_config()
    config["influx"] = get_influx_form_config(config)

    save_config(config)

    missing = []
    influx = config.get("influx", {})
    if influx.get("enabled"):
        if not influx.get("host"):
            missing.append("Host")
        if str(influx.get("version", "2")) == "2":
            if not influx.get("bucket"):
                missing.append("Bucket")
            if not influx.get("org"):
                missing.append("Organisation")
            if not influx.get("token"):
                missing.append("Token")
        elif not influx.get("database"):
            missing.append("Datenbank")

    if missing:
        add_log_entry("InfluxDB-Konfiguration gespeichert, aber es fehlt: " + ", ".join(missing))
    else:
        add_log_entry("InfluxDB-Konfiguration gespeichert")

    return redirect('/influx_settings_embed')

@app.route("/test/loxone", methods=["POST"])
def test_loxone():
    try:
        # Mit aktuellen Formularwerten testen, ohne vorher speichern zu müssen
        cfg = load_config()
        cfg["loxone"] = {
            "host": request.form.get("loxone_host", cfg.get("loxone", {}).get("host", "")),
            "user": request.form.get("loxone_user", cfg.get("loxone", {}).get("user", "")),
            "password": request.form.get("loxone_password", cfg.get("loxone", {}).get("password", ""))
        }
        data = load_mapping(cfg)
        project = data.get("msInfo", {}).get("projectName", "unbekannt")
        controls = len(data.get("controls", {}))
        notice = f'<div class="card ok">✅ Loxone OK<br>Projekt: {escape(str(project))}<br>Controls: {controls}</div>'
        return embedded_page('Bridge / Loxone', core_settings_content(load_config(), notice))
    except Exception as e:
        notice = f'<div class="card bad">❌ Loxone Fehler: {escape(str(e))}</div>'
        return embedded_page('Bridge / Loxone', core_settings_content(load_config(), notice))


@app.route("/test/mqtt", methods=["POST"])
def test_mqtt():
    try:
        cfg = load_config()
        mqtt_cfg = {
            "host": request.form.get("mqtt_host", cfg.get("mqtt", {}).get("host", "")),
            "port": int(request.form.get("mqtt_port", cfg.get("mqtt", {}).get("port", 1883))),
            "user": request.form.get("mqtt_user", cfg.get("mqtt", {}).get("user", "")),
            "password": request.form.get("mqtt_password", cfg.get("mqtt", {}).get("password", "")),
            "prefix": request.form.get("mqtt_prefix", cfg.get("mqtt", {}).get("prefix", "loxone"))
        }
        mqtt_module.test_connection(
            mqtt,
            mqtt_cfg["host"],
            int(mqtt_cfg["port"]),
            mqtt_cfg.get("user", ""),
            mqtt_cfg.get("password", ""),
            5,
        )
        notice = '<div class="card ok">✅ MQTT Hauptbroker erreichbar</div>'
        return embedded_page('MQTT Broker', mqtt_settings_content(load_config(), notice))
    except Exception as e:
        notice = f'<div class="card bad">❌ MQTT Fehler: {escape(str(e))}</div>'
        return embedded_page('MQTT Broker', mqtt_settings_content(load_config(), notice))


@app.route("/start", methods=["POST"])
def start_bridge():
    if not globals().get("LOXWEBSOCKET_AVAILABLE", True):
        runtime_context.bridge.status = globals().get("LOXWEBSOCKET_STATUS", "Loxone: Bibliothek nicht installiert")
        add_log_entry(runtime_context.bridge.status)
        return redirect('/')

    if runtime_context.bridge.running or (runtime_context.bridge.thread and runtime_context.bridge.thread.is_alive()):
        return redirect('/')

    runtime_context.bridge.stop_requested = False
    runtime_context.bridge.status = "startet"

    cfg = load_config()
    runtime_context.bridge.thread = threading.Thread(target=bridge_runner, args=(cfg,), daemon=True)
    runtime_context.bridge.thread.start()

    time.sleep(0.5)
    return redirect('/')


@app.route("/stop", methods=["POST"])
def stop_bridge():
    runtime_context.bridge.stop_requested = True
    runtime_context.bridge.status = "Stop angefordert"
    return redirect('/')

def _topic_manager_2_collect_topics():
    """Collect Loxone state topics plus topic settings for Loxone Explorer."""
    config = load_config()

    try:
        load_mapping(config)
    except Exception as e:
        add_log_entry(f"Loxone Explorer Mapping Fehler: {e}")

    topic_settings = load_topic_config()
    topics = {}

    prefix = config.get("mqtt", {}).get("prefix", "loxone")

    for uuid, name in state_mapping.items():
        topic = build_state_topic(prefix, name)
        topics[topic] = {
            "topic": topic,
            "name": name,
            "uuid": uuid,
            "source": "loxone_state"
        }

    # Auch manuell konfigurierte Topics anzeigen, selbst wenn sie nicht mehr aus Loxone kommen.
    for topic in topic_settings.keys():
        topics.setdefault(topic, {
            "topic": topic,
            "name": topic,
            "uuid": "",
            "source": "topic_config"
        })

    result = []
    for topic in sorted(topics.keys(), key=lambda x: str(x).casefold()):
        item = topics[topic]
        settings = topic_settings.get(topic, {})
        if not isinstance(settings, dict):
            settings = {}

        custom_name = str(settings.get("custom_name", "") or "").strip()
        lookup_topic = custom_name if custom_name else topic

        value = display_values.get(lookup_topic, "")
        if value == "":
            value = last_values.get(lookup_topic, "")

        result.append({
            "topic": topic,
            "parts": [p for p in str(topic).split("/") if p],
            "name": item.get("name", ""),
            "uuid": item.get("uuid", ""),
            "source": item.get("source", ""),
            "value": str(value),
            "enabled": bool(settings.get("enabled", True)),
            "writable": bool(settings.get("writable", False)),
            "influx": bool(settings.get("influx", False)),
            "custom_name": custom_name
        })

    return result


@app.route("/topics2")
def topics2_page():
    return topics2_content()


def topics2_content():
    return """
<!doctype html>
<html>
<head>
    <title>Loxone Explorer</title>
<style>
body {
    margin:0;
    font-family: Arial, sans-serif;
    background:#202830;
    color:#f4f7fb;
}

header {
    background:#1b2229;
    padding:14px 20px;
    display:flex;
    align-items:center;
    gap:15px;
    border-bottom:1px solid #333;
    flex-wrap:nowrap;
}

header h1 {
    margin:0;
    font-size:22px;
    white-space:nowrap;
}

#tm2Search {
    flex:1;
    padding:10px;
    background:#111820;
    color:white;
    border:1px solid #4a5663;
    border-radius:8px;
    font-size:15px;
}

.layout {
    display:grid;
    grid-template-columns: 34% 66%;
    height: calc(100vh - 62px);
    min-width:720px;
}

.tree {
    overflow:auto;
    border-right:1px solid #333;
    padding:12px;
    background:#151515;
}

.details {
    overflow:auto;
    padding:16px;
    background:#101010;
}

.tm2-topline {
    display:flex;
    align-items:center;
    gap:12px;
    flex-wrap:wrap;
    margin-bottom:12px;
}

.tm2-filter {
    display:flex;
    gap:12px;
    flex-wrap:wrap;
    align-items:center;
    color:#dbe6f2;
    font-size:13px;
}

.tm2-filter label {
    display:inline-flex;
    align-items:center;
    gap:6px;
    margin:0;
}

.tm2-filter input {
    width:auto;
}

.tm2-count {
    color:#aeb8c4;
    font-size:13px;
    margin-bottom:10px;
}

.tm2-tree-inner {
    min-width:max-content;
}

.tm2-node {
    border-radius:6px;
    user-select:none;
    white-space:nowrap;
}

.tm2-node-row {
    padding:5px 8px;
    border-radius:6px;
    cursor:pointer;
    display:flex;
    align-items:center;
    gap:6px;
}

.tm2-node-row:hover {
    background:#2a333d;
}

.tm2-node-row.selected {
    background:#5b5ff0;
    color:white;
}

.tm2-node-children {
    margin-left:18px;
}

.tm2-caret {
    display:inline-block;
    width:22px;
    cursor:pointer;
    color:#ccc;
    text-align:center;
}

.tm2-leaf .tm2-caret {
    color:transparent;
}

.tm2-topic-label {
    cursor:pointer;
}

.tm2-badges {
    display:inline-flex;
    gap:5px;
    margin-left:10px;
}

.tm2-badge {
    font-size:11px;
    border:1px solid #3a4357;
    background:#1c2230;
    border-radius:999px;
    padding:2px 6px;
    color:#cfd6e6;
}

.tm2-badge.off { opacity:.45; }
.tm2-badge.green { border-color:#2d7d4f; color:#77e49b; }
.tm2-badge.blue { border-color:#4664d8; color:#9db0ff; }
.tm2-badge.orange { border-color:#9c6a25; color:#ffca7a; }

.button-link,
.action-btn {
    background:#5f686f;
    color:white;
    border:0;
    padding:9px 14px;
    text-decoration:none;
    border-radius:8px;
    cursor:pointer;
    font-size:14px;
    display:inline-flex;
    align-items:center;
    justify-content:center;
}

.button-link:hover,
.action-btn:hover {
    background:#727d85;
}

.tm2-value,
.payload-box {
    background:#1b2229;
    border:1px solid #303b45;
    border-radius:10px;
    padding:15px;
    white-space:pre-wrap;
    word-break:break-word;
    font-family:Consolas, monospace;
}

.meta {
    color:#aeb8c4;
    margin-bottom:15px;
}

.tm2-path {
    color:#aeb8c4;
    margin-bottom:15px;
    word-break:break-all;
}

.tm2-actions {
    margin:12px 0 18px 0;
    display:flex;
    gap:10px;
    flex-wrap:wrap;
}

.tm2-detail-grid {
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:12px;
}

.tm2-detail-grid .full {
    grid-column:1 / -1;
}

.tm2-detail-grid input {
    width:100%;
    background:#111820;
    color:white;
    border:1px solid #4a5663;
    border-radius:8px;
    padding:9px;
}

.tm2-switches {
    display:flex;
    gap:14px;
    flex-wrap:wrap;
    margin:8px 0;
}

.tm2-switches label {
    display:inline-flex;
    align-items:center;
    gap:7px;
    margin:0;
    color:#e8edf7;
}

.tm2-switches input {
    width:auto;
}

.tm2-save {
    background:#5f686f;
}



.tm2-save,
.tm2-actions button,
.tm2-actions .button-link {
    background:#5f686f !important;
    color:white !important;
    border:0 !important;
    padding:9px 14px !important;
    text-decoration:none !important;
    border-radius:8px !important;
    cursor:pointer !important;
    font-size:14px !important;
    min-height:36px !important;
    display:inline-flex !important;
    align-items:center !important;
    justify-content:center !important;
    font-family:Arial, sans-serif !important;
}

.tm2-save:hover,
.tm2-actions button:hover,
.tm2-actions .button-link:hover {
    background:#727d85 !important;
}

.object-main-btn {
    background:#2878d6 !important;
}

.object-main-btn:hover {
    background:#1e63b2 !important;
}

.expert-actions {
    margin:0 0 16px 0;
    border:1px solid #303b45;
    background:#121922;
    border-radius:10px;
    padding:10px 12px;
}

.expert-actions summary {
    cursor:pointer;
    color:#cfe0f5;
    font-size:13px;
    font-weight:bold;
    user-select:none;
}

.expert-actions-row {
    margin-top:10px;
    display:flex;
    gap:10px;
    flex-wrap:wrap;
}

.expert-actions-row button {
    background:#5f686f !important;
    color:white !important;
    border:0 !important;
    padding:9px 14px !important;
    border-radius:8px !important;
    cursor:pointer !important;
    font-size:14px !important;
}
</style>
</head>
<body>

<header>
    <h1>Loxone Explorer</h1>
    <input id="tm2Search" placeholder="Topic suchen...">
    <button type="button" class="action-btn" onclick="tm2ExpandAll()">Alles aufklappen</button>
    <button type="button" class="action-btn" onclick="tm2CollapseAll()">Alles einklappen</button>
    <button type="button" class="action-btn" onclick="tm2Reload()">Aktualisieren</button>
</header>

<div class="layout">
    <div class="tree">
        <div class="tm2-topline">
            <div class="tm2-filter">
                <label><input type="checkbox" id="tm2OnlyEnabled"> Aktiv</label>
                <label><input type="checkbox" id="tm2OnlyWritable"> Schreibbar</label>
                <label><input type="checkbox" id="tm2OnlyInflux"> Influx</label>
                <label><input type="checkbox" id="tm2OnlyCustom"> Custom</label>
            </div>
        </div>
        <div class="tm2-count" id="tm2Count">Lade Topics...</div>
        <div class="tm2-tree-inner" id="tm2Tree"></div>
    </div>

    <div class="details">
        <h2 id="tm2DetailTitle">Kein Topic gewählt</h2>

        <div class="meta" id="tm2DetailMeta">-</div>
        <div class="payload-box" id="tm2Detail">
            Links ein Topic auswählen.
        </div>
    </div>
</div>

<script>
let tm2Topics = [];
let tm2Selected = null;
let tm2Collapsed = {};
const TM2_COLLAPSE_STORAGE_KEY = "mqtt2lox_loxone_explorer_collapsed";

function tm2Esc(v) {
    return String(v ?? "").replace(/[&<>"']/g, s => ({
        "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"
    }[s]));
}

function tm2BuildTree(list) {
    const root = {children:{}, item:null, key:""};
    for (const item of list) {
        let node = root;
        const parts = item.parts && item.parts.length ? item.parts : String(item.topic).split("/");
        for (const part of parts) {
            if (!node.children[part]) node.children[part] = {children:{}, item:null, key:(node.key ? node.key + "/" : "") + part};
            node = node.children[part];
        }
        node.item = item;
    }
    return root;
}

function tm2PassFilter(item) {
    const q = document.getElementById("tm2Search").value.trim().toLowerCase();
    if (q) {
        const hay = [item.topic, item.custom_name, item.value, item.name].join(" ").toLowerCase();
        if (!hay.includes(q)) return false;
    }
    if (document.getElementById("tm2OnlyEnabled").checked && !item.enabled) return false;
    if (document.getElementById("tm2OnlyWritable").checked && !item.writable) return false;
    if (document.getElementById("tm2OnlyInflux").checked && !item.influx) return false;
    if (document.getElementById("tm2OnlyCustom").checked && !item.custom_name) return false;
    return true;
}

function tm2SubtreeHasVisible(node) {
    if (node.item && tm2PassFilter(node.item)) return true;
    return Object.values(node.children || {}).some(tm2SubtreeHasVisible);
}

function tm2Badges(item) {
    if (!item) return "";
    return `
        <span class="tm2-badge ${item.enabled ? "green" : "off"}">${item.enabled ? "aktiv" : "aus"}</span>
        ${item.writable ? '<span class="tm2-badge blue">write</span>' : ''}
        ${item.influx ? '<span class="tm2-badge orange">influx</span>' : ''}
        ${item.custom_name ? '<span class="tm2-badge">custom</span>' : ''}
    `;
}

function tm2RenderNode(name, node, depth=0) {
    if (!tm2SubtreeHasVisible(node)) return "";

    const hasChildren = Object.keys(node.children || {}).length > 0;
    const isLeaf = !!node.item;
    const collapsed = !!tm2Collapsed[node.key];
    const selected = tm2Selected && node.item && tm2Selected.topic === node.item.topic;
    const rowClass = "tm2-node-row" + (selected ? " selected" : "");
    const nodeClass = "tm2-node" + (isLeaf ? " tm2-leaf" : "");

    let html = `<div class="${nodeClass}">
        <div class="${rowClass}" onclick="${isLeaf ? `tm2Select('${encodeURIComponent(node.item.topic)}')` : `tm2Toggle('${tm2Esc(node.key)}')`}">
            <span class="tm2-caret">${hasChildren ? (collapsed ? "▸" : "▾") : "•"}</span>
            <span class="tm2-topic-label">${tm2Esc(name)}</span>
            <span class="tm2-badges">${tm2Badges(node.item)}</span>
        </div>`;

    if (hasChildren && !collapsed) {
        html += `<div class="tm2-node-children">`;
        const entries = Object.entries(node.children).sort((a,b) => a[0].localeCompare(b[0], undefined, {numeric:true}));
        for (const [childName, child] of entries) html += tm2RenderNode(childName, child, depth+1);
        html += `</div>`;
    }

    html += `</div>`;
    return html;
}

function tm2RenderTree() {
    const visibleCount = tm2Topics.filter(tm2PassFilter).length;
    document.getElementById("tm2Count").textContent = `${visibleCount} von ${tm2Topics.length} Topics`;
    const tree = tm2BuildTree(tm2Topics);
    let html = "";
    for (const [name, node] of Object.entries(tree.children).sort((a,b) => a[0].localeCompare(b[0], undefined, {numeric:true}))) {
        html += tm2RenderNode(name, node);
    }
    document.getElementById("tm2Tree").innerHTML = html || '<div class="small" style="padding:12px;">Keine passenden Topics.</div>';
}


function tm2CollectAllKeys() {
    const keys = new Set();

    for (const item of tm2Topics) {
        const parts = item.parts && item.parts.length ? item.parts : String(item.topic || "").split("/");
        let path = "";

        for (const part of parts) {
            if (!part) continue;
            path = path ? path + "/" + part : part;
            keys.add(path);
        }
    }

    return Array.from(keys);
}


function tm2SaveCollapseState() {
    try {
        localStorage.setItem(TM2_COLLAPSE_STORAGE_KEY, JSON.stringify(tm2Collapsed || {}));
    } catch (e) {}
}

function tm2LoadCollapseState() {
    try {
        const raw = localStorage.getItem(TM2_COLLAPSE_STORAGE_KEY);
        if (!raw) return;
        const saved = JSON.parse(raw);
        if (saved && typeof saved === "object") {
            tm2Collapsed = saved;
        }
    } catch (e) {
        tm2Collapsed = {};
    }
}

function tm2CollapseAll() {
    tm2Collapsed = {};
    tm2CollectAllKeys().forEach(key => {
        tm2Collapsed[key] = true;
    });
    tm2SaveCollapseState();
    tm2RenderTree();
}

function tm2ExpandAll() {
    tm2Collapsed = {};
    tm2SaveCollapseState();
    tm2RenderTree();
}

function tm2Toggle(key) {
    tm2Collapsed[key] = !tm2Collapsed[key];
    if (!tm2Collapsed[key]) {
        delete tm2Collapsed[key];
    }
    tm2SaveCollapseState();
    tm2RenderTree();
}

function tm2Find(topic) {
    return tm2Topics.find(x => x.topic === topic);
}

function tm2Select(encodedTopic) {
    const topic = decodeURIComponent(encodedTopic);
    const item = tm2Find(topic);
    if (!item) return;
    tm2Selected = item;
    tm2RenderTree();
    tm2RenderDetail(item);
}

function tm2EffectiveTopic(item) {
    const custom = (item && item.custom_name ? String(item.custom_name).trim() : "");
    return custom || item.topic;
}

function tm2RenderDetail(item) {
    const custom = item.custom_name || "";
    const effectiveTopic = tm2EffectiveTopic(item);
    const qTopic = encodeURIComponent(effectiveTopic);

    document.getElementById("tm2DetailTitle").textContent = "Topic bearbeiten";
    document.getElementById("tm2DetailMeta").innerHTML =
        custom
            ? "Original: " + tm2Esc(item.topic) + "<br>Alias: " + tm2Esc(custom)
            : tm2Esc(item.topic);

    document.getElementById("tm2Detail").className = "";
    document.getElementById("tm2Detail").innerHTML = `

        <div class="tm2-detail-grid" style="margin-top:14px;">
            <div class="full">
                <label>Letzter Wert</label>
                <div class="tm2-value" id="tm2DetailValue">${tm2Esc(item.value || "-")}</div>
            </div>

            <div class="full">
                <label>Custom Topic / Alias</label>
                <input id="tm2Custom" type="text" value="${tm2Esc(custom)}" placeholder="leer = Originaltopic verwenden">
            </div>

            <div class="full tm2-switches">
                <label><input type="checkbox" id="tm2Enabled" ${item.enabled ? "checked" : ""}> Aktiv</label>
                <label><input type="checkbox" id="tm2Writable" ${item.writable ? "checked" : ""}> Schreibbar</label>
                <label><input type="checkbox" id="tm2Influx" ${item.influx ? "checked" : ""}> Influx</label>
            </div>
        </div>

        <div class="tm2-actions">
            <button type="button" class="action-btn tm2-save" onclick="tm2SaveSelected()">Speichern</button>
            <button type="button" class="action-btn object-main-btn" onclick="tm2CreateObjectSelected()">Objekt erstellen / verknüpfen</button>
            <button type="button" class="action-btn" onclick="tm2CopySelected()">Topic kopieren</button>
        </div>

        <details class="expert-actions" style="margin-top:12px;">
            <summary>⚙ Expertenmapping anzeigen</summary>
            <div class="expert-actions-row">
                <button type="button" class="action-btn" onclick="tm2GoMapping('/mqtt2lox')">MQTT→Loxone</button>
                <button type="button" class="action-btn" onclick="tm2GoMapping('/mqtt2udp')">MQTT→UDP</button>
                <button type="button" class="action-btn" onclick="tm2GoMapping('/mqtt2knx')">MQTT→KNX</button>
            </div>
        </details>

        <div class="small" id="tm2SaveState" style="margin-top:12px;"></div>
    `;
}

function tm2CopyText(text) {
    text = String(text || "");

    function showCopyState(ok) {
        const box = document.getElementById("tm2SaveState");
        if (box) box.textContent = ok ? "Topic kopiert ✅" : "Kopieren fehlgeschlagen ❌";
    }

    if (!text) {
        showCopyState(false);
        return;
    }

    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text)
            .then(() => showCopyState(true))
            .catch(() => tm2CopyTextFallback(text, showCopyState));
    } else {
        tm2CopyTextFallback(text, showCopyState);
    }
}

function tm2CopyTextFallback(text, callback) {
    try {
        const ta = document.createElement("textarea");
        ta.value = text;
        ta.setAttribute("readonly", "");
        ta.style.position = "fixed";
        ta.style.left = "-9999px";
        ta.style.top = "-9999px";
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        const ok = document.execCommand("copy");
        document.body.removeChild(ta);
        if (callback) callback(ok);
    } catch (e) {
        if (callback) callback(false);
    }
}

function tm2Copy(encodedTopic) {
    const topic = decodeURIComponent(encodedTopic);
    tm2CopyText(topic);
}

function tm2CopySelected() {
    if (!tm2Selected) return;
    const input = document.getElementById("tm2Custom");
    const custom = input ? input.value.trim() : (tm2Selected.custom_name || "");
    const topic = custom || tm2Selected.topic;
    tm2CopyText(topic);
}

function tm2CurrentTopicForAction() {
    if (!tm2Selected) return "";
    const input = document.getElementById("tm2Custom");
    const custom = input ? input.value.trim() : (tm2Selected.custom_name || "");
    return custom || tm2Selected.topic;
}

function tm2GoMapping(baseUrl) {
    const topic = tm2CurrentTopicForAction();
    if (!topic) {
        window.location.href = baseUrl;
        return;
    }
    window.location.href = baseUrl + "?source_topic=" + encodeURIComponent(topic);
}

function tm2CreateObjectSelected() {
    const topic = tm2CurrentTopicForAction();
    if (!topic) return;
    let name = topic.split('/').filter(Boolean).slice(-2).join(' ');
    window.location.href = "/objects/edit/new?source=loxone&value=" + encodeURIComponent(topic) + "&name=" + encodeURIComponent(name);
}


function tm2SaveSelected() {
    if (!tm2Selected) return;

    const fd = new FormData();
    fd.append("topic", tm2Selected.topic);
    fd.append("enabled", document.getElementById("tm2Enabled").checked ? "1" : "0");
    fd.append("writable", document.getElementById("tm2Writable").checked ? "1" : "0");
    fd.append("influx", document.getElementById("tm2Influx").checked ? "1" : "0");
    fd.append("custom_name", document.getElementById("tm2Custom").value.trim());

    fetch("/topics2/save", {method:"POST", body:fd})
        .then(r => r.json())
        .then(data => {
            const box = document.getElementById("tm2SaveState");
            box.textContent = data.message || "Gespeichert ✅";

            tm2Selected.enabled = document.getElementById("tm2Enabled").checked;
            tm2Selected.writable = document.getElementById("tm2Writable").checked;
            tm2Selected.influx = document.getElementById("tm2Influx").checked;
            tm2Selected.custom_name = document.getElementById("tm2Custom").value.trim();

            const customInput = document.getElementById("tm2Custom");
            if (customInput) customInput.blur();

            tm2RenderTree();
            tm2RenderDetail(tm2Selected);
        })
        .catch(err => {
            document.getElementById("tm2SaveState").textContent = "Fehler beim Speichern ❌ " + err;
        });
}

function tm2Reload(keepSelection=true) {
    const currentTopic = tm2Selected ? tm2Selected.topic : null;
    const activeId = document.activeElement ? document.activeElement.id : "";
    const userIsEditing =
        activeId === "tm2Custom" ||
        activeId === "tm2Enabled" ||
        activeId === "tm2Writable" ||
        activeId === "tm2Influx";

    fetch("/topics2/data?t=" + Date.now(), {cache:"no-store"})
        .then(r => r.json())
        .then(data => {
            tm2Topics = data.topics || [];
            tm2LoadCollapseState();

            if (keepSelection && currentTopic) {
                const fresh = tm2Find(currentTopic);

                if (fresh) {
                    if (userIsEditing && tm2Selected) {
                        // Während der Eingabe nicht den Detailbereich neu zeichnen,
                        // sonst wird das Alias-Feld wieder überschrieben.
                        tm2Selected.value = fresh.value;
                        tm2Selected.enabled = fresh.enabled;
                        tm2Selected.writable = fresh.writable;
                        tm2Selected.influx = fresh.influx;

                        const valueBox = document.getElementById("tm2DetailValue");
                        if (valueBox) valueBox.textContent = fresh.value || "-";
                    } else {
                        tm2Selected = fresh;
                        tm2RenderDetail(tm2Selected);
                    }
                }
            }

            tm2RenderTree();
        })
        .catch(err => {
            document.getElementById("tm2Count").textContent = "Fehler beim Laden: " + err;
        });
}

["tm2Search","tm2OnlyEnabled","tm2OnlyWritable","tm2OnlyInflux","tm2OnlyCustom"].forEach(id => {
    document.getElementById(id).addEventListener("input", tm2RenderTree);
    document.getElementById(id).addEventListener("change", tm2RenderTree);
});

tm2Reload(false);
setInterval(() => tm2Reload(true), 5000);
</script>
</body>
</html>
"""


@app.route("/topics2/data")
def topics2_data():
    return {"topics": _topic_manager_2_collect_topics()}


@app.route("/topics2/save", methods=["POST"])
def topics2_save():
    topic = request.form.get("topic", "").strip()
    if not topic:
        return {"success": False, "message": "Topic fehlt ❌"}, 400

    topic_settings = load_topic_config()
    current = topic_settings.get(topic, {})
    if not isinstance(current, dict):
        current = {}

    current["enabled"] = request.form.get("enabled", "0") == "1"
    current["writable"] = request.form.get("writable", "0") == "1"
    current["influx"] = request.form.get("influx", "0") == "1"
    current["custom_name"] = request.form.get("custom_name", "").strip()

    topic_settings[topic] = current
    save_topic_config(topic_settings)

    return {"success": True, "message": "Topic gespeichert ✅"}



@app.route("/topics")
def topics():
    config = load_config()

    try:
        load_mapping(config)
    except Exception as e:
        return f"Fehler beim Laden der Topics: {e}"

    topic_settings = load_topic_config()

    html = """
<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>Topic Manager</title>

<style>
body { font-family: Arial, sans-serif; margin:30px; background:#202830; color:#f4f7fb; }
.toolbar { margin-bottom:20px; background:#1b2229; padding:15px; border-radius:10px; }
#searchInput { width:320px; padding:8px; background:#111820; color:#fff; border:1px solid #4a5663; border-radius:6px; }
label { margin-left:18px; }
table { width:100%; border-collapse:collapse; table-layout:fixed; background:#151c23; }
th, td { border:1px solid #303b45; padding:6px; vertical-align:middle; }
th { background:#2a333d; position:sticky; top:0; z-index:2; }
td.topic { width:45%; word-break:break-all; }
td.check { width:80px; text-align:center; }
td.custom input { width:100%; box-sizing:border-box; background:#111820; color:#fff; border:1px solid #4a5663; padding:5px; }
td.last-value { width:80px; text-align:right; font-family:monospace; color:#d7e0ea; word-break:break-all; }
tr.topic-row:hover { background:#2a333d; }

button, .button-link {
    display:inline-flex; align-items:center; justify-content:center;
    height:40px; padding:0 18px; border:0; border-radius:8px;
    background:#5f686f; color:white; cursor:pointer; text-decoration:none;
    box-sizing:border-box; font-family:Arial, sans-serif; font-size:14px;
}

#saveMessage {
    display:none; margin-bottom:15px; padding:10px; border-radius:8px;
    background:#1f7a3a; color:white;
}

.bulk-actions { margin-top:12px; display:flex; gap:8px; flex-wrap:wrap; }
.bulk-actions button { height:32px; padding:0 12px; font-size:13px; border-radius:6px; background:#5f686f; }
.bulk-actions button:hover { background:#5f686f; }
</style>
</head>

<body>

<h1>Topic Manager</h1>

<div id="saveMessage">Gespeichert ✅</div>

<div class="toolbar">
    <input type="text" id="searchInput" placeholder="Topic suchen...">

    <label><input type="checkbox" id="filterInflux"> Nur Influx</label>
    <label><input type="checkbox" id="filterWritable"> Nur Schreibbar</label>
    <label><input type="checkbox" id="filterEnabled"> Nur Aktivierte</label>
    <label><input type="checkbox" id="filterCustom"> Nur Custom</label>

    <div class="bulk-actions">
        <button type="button" onclick="setVisibleCheckboxes('enabled-box', true)">Aktiv +</button>
        <button type="button" onclick="setVisibleCheckboxes('enabled-box', false)">Aktiv -</button>
        <button type="button" onclick="setVisibleCheckboxes('writable-box', true)">Schreibbar +</button>
        <button type="button" onclick="setVisibleCheckboxes('writable-box', false)">Schreibbar -</button>
        <button type="button" onclick="setVisibleCheckboxes('influx-box', true)">Influx +</button>
        <button type="button" onclick="setVisibleCheckboxes('influx-box', false)">Influx -</button>
    </div>
</div>

<form id="topicsForm" method="post" action="/topics/save">

<table>
<thead>
<tr>
    <th>Topic</th>
    <th>Letzter Wert</th>
    <th>Aktiv</th>
    <th>Schreibbar</th>
    <th>Influx</th>
    <th>Custom Topic</th>
</tr>
</thead>
<tbody>
"""

    for idx, (uuid, name) in enumerate(state_mapping.items()):
        topic = build_state_topic(config["mqtt"]["prefix"], name)
        settings = topic_settings.get(topic, {})

        enabled = settings.get("enabled", True)
        writable = settings.get("writable", False)
        influx = settings.get("influx", False)
        custom_name = settings.get("custom_name", "")

        safe_key = topic.replace("/", "_")

        try:
            last_value = display_values.get(custom_name if custom_name else topic, "")
        except NameError:
            last_value = last_values.get(custom_name if custom_name else topic, "")

        html += f"""
<tr class="topic-row">
    <td class="topic">
        {topic}
        <input type="hidden" name="topic_{idx}" value="{topic}">
    </td>

    <td class="last-value" id="value_{safe_key}">{last_value}</td>

    <td class="check">
        <input type="checkbox" class="enabled-box" name="enabled_{idx}" {"checked" if enabled else ""}>
    </td>

    <td class="check">
        <input type="checkbox" class="writable-box" name="writable_{idx}" {"checked" if writable else ""}>
    </td>

    <td class="check">
        <input type="checkbox" class="influx-box" name="influx_{idx}" {"checked" if influx else ""}>
    </td>

    <td class="custom">
        <input type="text" name="custom_{idx}" value="{custom_name}">
    </td>
</tr>
"""

    html += f"""
</tbody>
</table>

<p>
    <button type="submit">Speichern</button>
</p>

<input type="hidden" name="topic_count" value="{len(state_mapping)}">
</form>

<p>
    
    
</p>

<script>
function filterTopics() {{
    let search = document.getElementById("searchInput").value.toLowerCase();
    let onlyInflux = document.getElementById("filterInflux").checked;
    let onlyWritable = document.getElementById("filterWritable").checked;
    let onlyEnabled = document.getElementById("filterEnabled").checked;
    let onlyCustom = document.getElementById("filterCustom").checked;

    document.querySelectorAll(".topic-row").forEach(row => {{
        let topicText = row.cells[0].innerText.toLowerCase();
        let enabled = row.querySelector(".enabled-box")?.checked;
        let writable = row.querySelector(".writable-box")?.checked;
        let influx = row.querySelector(".influx-box")?.checked;
        let customInput = row.querySelector("td.custom input");
        let hasCustom = customInput && customInput.value.trim() !== "";

        let visible = true;

        if (search && !topicText.includes(search)) visible = false;
        if (onlyInflux && !influx) visible = false;
        if (onlyWritable && !writable) visible = false;
        if (onlyEnabled && !enabled) visible = false;
        if (onlyCustom && !hasCustom) visible = false;

        row.style.display = visible ? "" : "none";
    }});
}}

function setVisibleCheckboxes(className, state) {{
    document.querySelectorAll(".topic-row").forEach(row => {{
        if (row.style.display !== "none") {{
            let checkbox = row.querySelector("." + className);
            if (checkbox) checkbox.checked = state;
        }}
    }});
}}

function refreshTopicValues() {{
    fetch("/topics_data")
        .then(response => response.json())
        .then(data => {{
            for (const key in data) {{
                const cell = document.getElementById("value_" + key);
                if (cell) cell.innerText = data[key];
            }}
        }})
        .catch(err => console.log(err));
}}

function saveTopics(event) {{
    event.preventDefault();

    const form = document.getElementById("topicsForm");
    const formData = new FormData(form);

    fetch("/topics/save", {{
        method: "POST",
        body: formData
    }})
    .then(response => response.json())
    .then(data => {{
        const msg = document.getElementById("saveMessage");
        msg.innerText = data.message || "Gespeichert ✅";
        msg.style.display = "block";

        setTimeout(() => {{
            msg.style.display = "none";
        }}, 2500);
    }})
    .catch(err => {{
        const msg = document.getElementById("saveMessage");
        msg.innerText = "Fehler beim Speichern ❌";
        msg.style.display = "block";
        console.log(err);
    }});

    return false;
}}

document.getElementById("searchInput").addEventListener("keyup", filterTopics);
document.getElementById("filterInflux").addEventListener("change", filterTopics);
document.getElementById("filterWritable").addEventListener("change", filterTopics);
document.getElementById("filterEnabled").addEventListener("change", filterTopics);
document.getElementById("filterCustom").addEventListener("change", filterTopics);
document.getElementById("topicsForm").addEventListener("submit", saveTopics);

setInterval(refreshTopicValues, 5000);
</script>

</body>
</html>
"""

    return html

@app.route("/topics/save", methods=["POST"])
def topics_save():
    count = int(request.form.get("topic_count", 0))

    topic_settings = {}

    for i in range(count):
        topic = request.form.get(f"topic_{i}", "").strip()

        if not topic:
            continue

        enabled = f"enabled_{i}" in request.form
        writable = f"writable_{i}" in request.form
        influx = f"influx_{i}" in request.form
        custom_name = request.form.get(f"custom_{i}", "").strip()

        topic_settings[topic] = {
            "enabled": enabled,
            "writable": writable,
            "influx": influx,
            "custom_name": custom_name
        }

    save_topic_config(topic_settings)

    return {
        "success": True,
        "message": "Topic Manager gespeichert ✅"
    }




# -----------------------------------------------------------------------------
# Legacy Shared Mapping Explorer Engine
# -----------------------------------------------------------------------------
def shared_mapping_explorer_script(
    namespace,
    tree_storage_key,
    subitem_storage_key,
    selected_storage_key,
    data_url,
    card_id_prefix,
    value_id_prefix,
    time_id_prefix,
    tree_value_id_prefix,
    current_value_id_prefix,
    current_time_id_prefix,
        extra_js=""
):
    """Gemeinsamer JS-Kern für Mapping-Explorer-Seiten.

    Wird aktuell von MQTT→Loxone und MQTT→UDP genutzt. Die Seiten behalten ihre
    eigenen IDs/Routes, aber Auf-/Zuklappen, Suche, Set-Auswahl, Löschen,
    Live-Werte und LocalStorage laufen nur noch über diese eine Engine.
    """
    template = """
<script>
const EXPLORER_ENGINE = {
    namespace: "__NAMESPACE__",
    treeStorageKey: "__TREE_STORAGE_KEY__",
    subitemStorageKey: "__SUBITEM_STORAGE_KEY__",
    selectedStorageKey: "__SELECTED_STORAGE_KEY__",
    dataUrl: "__DATA_URL__",
    cardIdPrefix: "__CARD_ID_PREFIX__",
    valueIdPrefix: "__VALUE_ID_PREFIX__",
    timeIdPrefix: "__TIME_ID_PREFIX__",
    treeValueIdPrefix: "__TREE_VALUE_ID_PREFIX__",
    currentValueIdPrefix: "__CURRENT_VALUE_ID_PREFIX__",
    currentTimeIdPrefix: "__CURRENT_TIME_ID_PREFIX__"
};

function cssEscapeSafe(value) {
    if (window.CSS && CSS.escape) return CSS.escape(value);
    return String(value).replace(/'/g, "\\'");
}

function engineLoadJson(key, fallback) {
    try { return JSON.parse(localStorage.getItem(key) || JSON.stringify(fallback)) || fallback; }
    catch(e) { return fallback; }
}

function engineSaveJson(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value || {})); }
    catch(e) {}
}

function getTreeState() { return engineLoadJson(EXPLORER_ENGINE.treeStorageKey, {}); }
function saveTreeState(state) { engineSaveJson(EXPLORER_ENGINE.treeStorageKey, state); }
function getSetSubitemState() { return engineLoadJson(EXPLORER_ENGINE.subitemStorageKey, {}); }
function saveSetSubitemState(state) { engineSaveJson(EXPLORER_ENGINE.subitemStorageKey, state); }

function applyTreeState() {
    const state = getTreeState();
    document.querySelectorAll("[data-tree-group]").forEach(group => {
        const key = group.getAttribute("data-tree-group");
        const body = document.getElementById("tree_body_" + key);
        const arrow = document.getElementById("tree_arrow_" + key);
        if (!body || !arrow) return;
        const collapsed = !!state[key];
        body.classList.toggle("collapsed", collapsed);
        arrow.textContent = collapsed ? "▸" : "▾";
    });
}

function applySetSubitemState() {
    const state = getSetSubitemState();
    document.querySelectorAll("[data-subitems-for]").forEach(box => {
        const key = box.getAttribute("data-subitems-for");
        const arrow = document.getElementById("set_arrow_" + key);
        const collapsed = !!state[key];
        box.classList.toggle("collapsed", collapsed);
        if (arrow) arrow.textContent = collapsed ? "▸" : "▾";
    });
}

function toggleTreeGroup(key) {
    const state = getTreeState();
    state[key] = !state[key];
    if (!state[key]) delete state[key];
    saveTreeState(state);
    applyTreeState();
}

function toggleSetSubitems(setKey) {
    const state = getSetSubitemState();
    state[setKey] = !state[setKey];
    if (!state[setKey]) delete state[setKey];
    saveSetSubitemState(state);
    applySetSubitemState();
}

function collapseAllTree() {
    const treeState = {};
    document.querySelectorAll("[data-tree-group]").forEach(group => {
        const key = group.getAttribute("data-tree-group");
        if (key) treeState[key] = true;
    });
    saveTreeState(treeState);
    applyTreeState();

    const subState = {};
    document.querySelectorAll("[data-subitems-for]").forEach(box => {
        const key = box.getAttribute("data-subitems-for");
        if (key) subState[key] = true;
    });
    saveSetSubitemState(subState);
    applySetSubitemState();
}

function expandAllTree() {
    saveTreeState({});
    applyTreeState();
    saveSetSubitemState({});
    applySetSubitemState();
}

function showSet(key) {
    document.querySelectorAll("[data-set-panel]").forEach(panel => {
        panel.classList.toggle("active", panel.getAttribute("data-set-panel") === key);
    });
    document.querySelectorAll("[data-set-link]").forEach(link => {
        link.classList.toggle("active", link.getAttribute("data-set-link") === key);
    });
    try { localStorage.setItem(EXPLORER_ENGINE.selectedStorageKey, key); } catch(e) {}
}

function selectTreeRow(setKey, rowIndex) {
    showSet(setKey);
    EXPLORER_ENGINE.selectedRowIndex = String(rowIndex);
    document.querySelectorAll(".tree-subitem").forEach(item => item.classList.remove("active-row"));
    const active = document.querySelector('[data-row-index="' + String(rowIndex).replace(/"/g, '\"') + '"]');
    if (active) active.classList.add("active-row");
}

function getSelectedRowPanel(fallbackPanel) {
    const idx = EXPLORER_ENGINE.selectedRowIndex;
    if (idx !== undefined && idx !== null && idx !== "") {
        const row = document.getElementById(EXPLORER_ENGINE.cardIdPrefix + idx);
        if (row) return row;
    }
    return fallbackPanel;
}

function restoreSelectedSet() {
    let key = "";
    try { key = localStorage.getItem(EXPLORER_ENGINE.selectedStorageKey) || ""; } catch(e) {}
    if (key && document.querySelector("[data-set-panel='" + cssEscapeSafe(key) + "']")) showSet(key);
}

function syncSetGroup(setKey, value) {
    document.querySelectorAll("[data-group-sync='" + cssEscapeSafe(setKey) + "']").forEach(el => el.value = value);
}

function syncSetName(setKey, value) {
    document.querySelectorAll("[data-set-sync='" + cssEscapeSafe(setKey) + "']").forEach(el => el.value = value);
}

function showExtraMapping(setKey) {
    const box = document.getElementById("extra_wrap_" + setKey);
    if (box) box.style.display = "block";
}

function markDeleteAndHide(index) {
    const cb = document.getElementById("delete_" + index);
    const card = document.getElementById(EXPLORER_ENGINE.cardIdPrefix + index);
    if (cb) cb.checked = true;
    if (card) card.style.display = "none";
}

function deleteWholeSet(setKey) {
    if (!confirm("Dieses komplette Set beim nächsten Speichern löschen?")) return;
    document.querySelectorAll("[data-set-panel='" + cssEscapeSafe(setKey) + "'] [id^='delete_']").forEach(cb => cb.checked = true);
    const panel = document.querySelector("[data-set-panel='" + cssEscapeSafe(setKey) + "']");
    if (panel) panel.style.opacity = "0.45";
}

function filterTree() {
    const input = document.getElementById("treeSearch");
    const q = ((input && input.value) || "").toLowerCase().trim();

    document.querySelectorAll(".tree-set, .tree-subitem").forEach(item => {
        const txt = (item.getAttribute("data-search") || "").toLowerCase();
        item.classList.toggle("hidden-by-search", !!q && !txt.includes(q));
    });

    document.querySelectorAll(".tree-group").forEach(group => {
        const groupTxt = (group.getAttribute("data-search") || "").toLowerCase();
        const visibleItem = group.querySelector(".tree-set:not(.hidden-by-search), .tree-subitem:not(.hidden-by-search)");
        group.classList.toggle("hidden-by-search", !!q && !groupTxt.includes(q) && !visibleItem);
    });

    document.querySelectorAll("[data-subitems-for]").forEach(box => { if (q) box.classList.remove("collapsed"); });
    if (!q) applySetSubitemState();
}

function setExplorerText(idPrefix, key, text) {
    if (!idPrefix) return null;
    const el = document.getElementById(idPrefix + key);
    if (el) el.innerText = text;
    return el;
}

function refreshMappingValues() {
    fetch(EXPLORER_ENGINE.dataUrl, { cache: "no-store" })
        .then(response => response.json())
        .then(data => {
            for (const key in data) {
                const rawVal = data[key] && data[key].value;
                const rawTime = data[key] && data[key].time;
                const val = (rawVal && rawVal !== "-") ? rawVal : "";
                const valDisplay = val || "-";
                const time = (rawTime && rawTime !== "-") ? rawTime : "-";

                setExplorerText(EXPLORER_ENGINE.valueIdPrefix, key, valDisplay);
                setExplorerText(EXPLORER_ENGINE.timeIdPrefix, key, time);

                const treeValue = setExplorerText(EXPLORER_ENGINE.treeValueIdPrefix, key, val);
                if (treeValue) treeValue.classList.toggle("empty", !val);

                const currentValue = setExplorerText(EXPLORER_ENGINE.currentValueIdPrefix, key, valDisplay);
                if (currentValue) currentValue.classList.toggle("empty", !val);

                setExplorerText(EXPLORER_ENGINE.currentTimeIdPrefix, key, "Zuletzt: " + time);
            }
        })
        .catch(err => console.log(err));
}

function initSharedExplorerEngine() {
    applyTreeState();
    applySetSubitemState();
    restoreSelectedSet();
    refreshMappingValues();
    setInterval(refreshMappingValues, 3000);
}

__EXTRA_JS__

initSharedExplorerEngine();
</script>
"""
    values = {
        "__NAMESPACE__": namespace,
        "__TREE_STORAGE_KEY__": tree_storage_key,
        "__SUBITEM_STORAGE_KEY__": subitem_storage_key,
        "__SELECTED_STORAGE_KEY__": selected_storage_key,
        "__DATA_URL__": data_url,
        "__CARD_ID_PREFIX__": card_id_prefix,
        "__VALUE_ID_PREFIX__": value_id_prefix,
        "__TIME_ID_PREFIX__": time_id_prefix,
        "__TREE_VALUE_ID_PREFIX__": tree_value_id_prefix,
        "__CURRENT_VALUE_ID_PREFIX__": current_value_id_prefix,
        "__CURRENT_TIME_ID_PREFIX__": current_time_id_prefix,
        "__EXTRA_JS__": extra_js or ""
    }
    for key, value in values.items():
        template = template.replace(key, str(value))
    return template


def mqtt2udp_explorer_extra_js():
    return """
function openPortPresets(input) {
    input.dataset.oldValue = input.value;
    input.value = "";
    setTimeout(() => { if (input.showPicker) input.showPicker(); }, 50);
}
function restorePortIfEmpty(input) {
    if (input.value.trim() === "" && input.dataset.oldValue) input.value = input.dataset.oldValue;
}
"""

@app.route("/mqtt2lox")
def mqtt2lox():
    config = load_config()
    mappings = load_mqtt2lox_config()

    prefill_source_topic = request.args.get("source_topic", "")
    prefill_json_key = request.args.get("json_key", "")
    prefill_payload_mode = request.args.get("payload_mode", "raw")
    prefill_group = request.args.get("group", "")
    prefill_set = request.args.get("set_name", "")

    def safe_key(text_value):
        return clean_topic(text_value) or "ohne_name"

    for m in mappings:
        m.setdefault("group", "")
        m.setdefault("set_name", "")

    tree = {}
    for i, item in enumerate(mappings):
        group_name = str(item.get("group", "") or "").strip() or "Ohne Gruppe"
        set_name = str(item.get("set_name", "") or "").strip() or str(item.get("loxone_io", "") or item.get("source_topic", "") or "Importiert").strip() or "Importiert"
        group_key = safe_key(group_name)
        set_key = safe_key(group_name + "__" + set_name)
        tree.setdefault(group_key, {"name": group_name, "sets": {}})
        tree[group_key]["sets"].setdefault(set_key, {"name": set_name, "rows": []})
        tree[group_key]["sets"][set_key]["rows"].append(i)

    first_set_key = "__new__"
    # Legacy: Kommt man direkt aus dem MQTT Explorer, soll sofort das neue
    # vorbefüllte MQTT→UDP Mapping geöffnet sein - nicht irgendein vorhandenes Set.
    if not prefill_source_topic:
        for gk in sorted(tree.keys(), key=lambda x: tree[x]["name"].casefold()):
            for sk in sorted(tree[gk]["sets"].keys(), key=lambda x: tree[gk]["sets"][x]["name"].casefold()):
                first_set_key = sk
                break
            if first_set_key != "__new__":
                break

    existing_count = len(mappings)
    next_index = existing_count

    html = """
<!doctype html>
<html>
<head>
    <title>MQTT → Loxone Mapping Explorer</title>
    <style>
        :root {
            --bg:#202830;
            --panel:#1b2229;
            --panel2:#111820;
            --panel3:#151c23;
            --border:#303b45;
            --muted:#aeb8c4;
            --text:#f4f7fb;
            --accent:#5f686f;
            --green:#1fa342;
            --danger:#b83b3b;
            --yellow:#f5d76e;
            --blue:#3b90e8;
        }

        * { box-sizing:border-box; }

        html, body { height:100%; overflow:hidden; }

        body {
            font-family: Arial, sans-serif;
            background:var(--bg);
            color:var(--text);
            margin:0;
        }

        header {
            height:76px;
            background:#1b2229;
            border-bottom:1px solid var(--border);
            display:flex;
            align-items:center;
            justify-content:space-between;
            gap:14px;
            padding:14px 20px;
            overflow:hidden;
        }

        h1 {
            margin:0;
            font-size:28px;
            white-space:nowrap;
            overflow:hidden;
            text-overflow:ellipsis;
        }

        .header-tools {
            display:flex;
            gap:8px;
            align-items:center;
            flex-wrap:wrap;
        }

        .page {
            display:grid;
            grid-template-columns:330px minmax(0, 1fr);
            height:calc(100vh - 76px);
            min-width:0;
            overflow:hidden;
        }

        .sidebar {
            background:#111820;
            border-right:1px solid var(--border);
            overflow:auto;
            padding:14px;
        }

        .editor {
            overflow-x:auto;
            overflow-y:auto;
            min-width:0;
            padding:18px;
            padding-bottom:18px;
        }

        .editor-inner {
            width:max(100%, 1050px);
            min-width:0;
            padding-right:18px;
        }

        button, a.button-link {
            background:var(--accent);
            color:white;
            padding:9px 13px;
            text-decoration:none;
            border:none;
            border-radius:8px;
            cursor:pointer;
            display:inline-block;
            font-size:14px;
            font-weight:700;
        }

        button:hover, a.button-link:hover { background:#737d86; }

        .save-bottom {
            background:var(--green);
            min-width:240px;
            font-size:16px;
            padding:13px 20px;
        }

        .save-bottom:hover { background:#27b54d; }

        .delete-btn {
            background:transparent;
            border:1px solid var(--danger);
            color:#ff6b6b;
            padding:7px 10px;
        }

        .delete-btn:hover { background:#3a1618; }

        input[type=text], select {
            width:100%;
            background:#0f1720;
            color:white;
            border:1px solid #4a5663;
            border-radius:6px;
            padding:9px;
            box-sizing:border-box;
            font-size:14px;
        }

        input[type=checkbox] {
            width:18px;
            height:18px;
            accent-color:#35c75a;
        }

        label {
            display:block;
            font-size:12px;
            color:var(--muted);
            margin-bottom:5px;
        }

        .small {
            font-size:12px;
            color:var(--muted);
            line-height:1.38;
        }

        .search-box {
            position:relative;
            margin-bottom:14px;
        }

        .search-box input {
            padding-left:34px;
        }

        .search-icon {
            position:absolute;
            left:11px;
            top:9px;
            opacity:.75;
        }

        .tree-group {
            margin-bottom:10px;
        }

        .tree-group-title {
            color:var(--yellow);
            font-weight:900;
            padding:8px;
            cursor:pointer;
            user-select:none;
            display:flex;
            justify-content:space-between;
            align-items:center;
            border-radius:7px;
        }

        .tree-group-title:hover { background:#202830; }

        .tree-set {
            margin-left:18px;
            padding:8px 9px;
            border-radius:8px;
            cursor:pointer;
            display:flex;
            justify-content:space-between;
            align-items:center;
            gap:8px;
            color:#e9edf5;
        }

        .tree-set:hover { background:#25303a; }
        .tree-set.active { background:#5f686f; color:white; }

        .tree-set-main {
            display:flex;
            align-items:center;
            gap:6px;
            min-width:0;
        }

        .tree-set-arrow {
            width:16px;
            display:inline-block;
            text-align:center;
            font-weight:900;
            opacity:.9;
            user-select:none;
        }

        .tree-set-name {
            overflow:hidden;
            text-overflow:ellipsis;
            white-space:nowrap;
        }

        .tree-subitems {
            margin-left:34px;
            margin-bottom:4px;
        }

        .tree-subitems.collapsed {
            display:none;
        }

        .tree-subitem {
            padding:5px 8px;
            border-radius:7px;
            color:#cfd8e6;
            font-size:13px;
            cursor:pointer;
            opacity:.9;
            display:flex;
            align-items:center;
            justify-content:space-between;
            gap:8px;
        }

        .tree-subitem:hover {
            background:#25303a;
            color:white;
        }

        .tree-subitem-name {
            overflow:hidden;
            text-overflow:ellipsis;
            white-space:nowrap;
            min-width:0;
        }

        .tree-live-value {
            color:#35d05b;
            background:rgba(35, 208, 91, .12);
            border:1px solid rgba(35, 208, 91, .22);
            border-radius:7px;
            padding:1px 5px;
            font-size:11px;
            font-weight:800;
            white-space:nowrap;
            max-width:92px;
            overflow:hidden;
            text-overflow:ellipsis;
        }

        .tree-live-value.empty {
            display:none;
        }

        .tree-set.active + .tree-subitems .tree-subitem {
            color:#ffffff;
        }

        .tree-subitem.hidden-by-search,
        .tree-set.hidden-by-search,
        .tree-group.hidden-by-search { display:none; }

        .badge {
            background:#26313d;
            border:1px solid #3c4856;
            color:#cfd8e6;
            border-radius:999px;
            font-size:11px;
            padding:2px 7px;
            white-space:nowrap;
        }

        .group-body.collapsed { display:none; }

        .new-set-link {
            margin-top:14px;
            border:1px dashed #596777;
            border-radius:10px;
            padding:12px;
            cursor:pointer;
            background:#111820;
        }

        .new-set-link:hover { background:#1b2530; }

        .set-panel { display:none; }
        .set-panel.active { display:block; }

        .card {
            background:var(--panel);
            border:1px solid var(--border);
            border-radius:12px;
            padding:16px;
            margin-bottom:16px;
            width:100%;
        }

        .set-head {
            display:grid;
            grid-template-columns:230px 280px 44px minmax(220px, 1fr) auto;
            gap:12px;
            align-items:end;
        }

        .mapping-header {
            display:flex;
            justify-content:space-between;
            align-items:center;
            gap:12px;
            flex-wrap:wrap;
            margin-bottom:14px;
        }

        .mapping-list {
            display:flex;
            flex-direction:column;
            gap:12px;
        }

        .mapping-card {
            background:#111820;
            border:1px solid var(--border);
            border-radius:12px;
            padding:14px;
        }

        .mapping-alias {
            display:grid;
            grid-template-columns:1fr auto;
            gap:12px;
            align-items:end;
            margin-bottom:12px;
            padding-bottom:12px;
            border-bottom:1px solid var(--border);
        }

        .mapping-alias-title {
            font-weight:900;
            color:#f5d76e;
            margin-bottom:4px;
        }


        .mapping-card-top {
            display:grid;
            grid-template-columns:240px 42px minmax(260px, 1.45fr) minmax(240px, 1.15fr) 100px;
            gap:12px;
            align-items:end;
            margin-bottom:12px;
        }

        .current-value-box {
            border:1px solid var(--border);
            border-radius:10px;
            background:rgba(255,255,255,.02);
            padding:10px 12px;
            min-height:82px;
            display:flex;
            flex-direction:column;
            justify-content:center;
        }

        .current-value-title {
            color:var(--muted);
            font-size:12px;
            margin-bottom:7px;
        }

        .current-value-main {
            color:#35d05b;
            font-size:22px;
            font-weight:900;
            line-height:1.1;
            white-space:nowrap;
            overflow:hidden;
            text-overflow:ellipsis;
        }

        .current-value-main.empty {
            color:var(--muted);
        }

        .current-value-time {
            color:var(--muted);
            font-size:12px;
            margin-top:8px;
            white-space:nowrap;
            overflow:hidden;
            text-overflow:ellipsis;
        }

        .mapping-card-bottom {
            display:grid;
            grid-template-columns:150px 200px 145px 110px 110px minmax(170px, 1fr);
            gap:12px;
            align-items:end;
        }

        .mapping-actions {
            display:flex;
            gap:8px;
            align-items:center;
            justify-content:flex-end;
        }

        .info-box {
            border:1px solid #30445d;
            background:#132033;
            border-radius:10px;
            padding:12px 14px;
            margin-top:14px;
        }

        .footer-actions {
            position:sticky;
            bottom:0;
            display:flex;
            justify-content:flex-end;
            gap:10px;
            z-index:20;
            padding:10px 0 0;
            margin-top:10px;
            background:linear-gradient(to top, var(--bg) 75%, rgba(32,40,48,0));
        }

        .separator {
            height:1px;
            background:var(--border);
            margin:12px 0;
        }

        @media(max-width:1200px) {
            .page {
                grid-template-columns:300px minmax(0, 1fr);
            }
            .editor-inner {
                width:max(100%, 1050px);
            }
        }
    </style>
</head>
<body>

<header>
    <h1>MQTT → Loxone Mapping Explorer</h1>
    <div class="header-tools">
        <a class="button-link" href="/mqtt">← Zurück zum MQTT Hub</a>
        <button type="button" onclick="expandAllTree()">Alles aufklappen</button>
        <button type="button" onclick="collapseAllTree()">Alles einklappen</button>
    </div>
</header>

<form method="post" action="/mqtt2lox/save" id="mappingForm">
<div class="page">
    <aside class="sidebar">
        <div class="search-box">
            <span class="search-icon">🔎</span>
            <input id="treeSearch" type="text" placeholder="Suchen..." oninput="filterTree()">
        </div>

        <button type="button" style="width:100%; margin:0 0 12px 0; justify-content:center;" onclick="showSet('__new__')">＋ Neues Set erstellen</button>

        <div class="small" style="margin-bottom:12px;">
            Links Gruppen und Sets. Rechts bearbeitest du das gewählte Gerät/Objekt mit mehreren Topics.
        </div>
"""

    for group_key in sorted(tree.keys(), key=lambda x: tree[x]["name"].casefold()):
        group = tree[group_key]
        html += f"""
        <div class="tree-group" data-tree-group="{escape(group_key)}" data-search="{escape(group["name"].lower())}">
            <div class="tree-group-title" onclick="toggleTreeGroup('{escape(group_key)}')">
                <span><span id="tree_arrow_{escape(group_key)}">▾</span> {escape(group["name"])}</span>
                <span class="badge">{len(group["sets"])} Set(s)</span>
            </div>
            <div class="group-body" id="tree_body_{escape(group_key)}">
"""
        for set_key in sorted(group["sets"].keys(), key=lambda x: group["sets"][x]["name"].casefold()):
            set_obj = group["sets"][set_key]
            active_cls = " active" if set_key == first_set_key else ""
            alias_names = []
            for row_index in set_obj["rows"]:
                row_item = mappings[row_index]
                alias = str(row_item.get("mapping_alias", "") or "").strip()
                if not alias:
                    alias = str(row_item.get("loxone_io", "") or row_item.get("source_topic", "") or f"Mapping {row_index + 1}").strip()
                alias_names.append(alias)

            search_text = f"{group['name']} {set_obj['name']} {' '.join(alias_names)}".lower()
            html += f"""
                <div class="tree-set{active_cls}" data-set-link="{escape(set_key)}" data-search="{escape(search_text)}" onclick="showSet('{escape(set_key)}')">
                    <span class="tree-set-main">
                        <span class="tree-set-arrow" id="set_arrow_{escape(set_key)}" onclick="event.stopPropagation(); toggleSetSubitems('{escape(set_key)}')">▾</span>
                        <span class="tree-set-name">{escape(set_obj["name"])}</span>
                    </span>
                    <span class="badge">{len(set_obj["rows"])}</span>
                </div>
                <div class="tree-subitems" id="subitems_{escape(set_key)}" data-subitems-for="{escape(set_key)}">
"""
            for row_index, alias in zip(set_obj["rows"], alias_names):
                row_item = mappings[row_index]
                source_topic = str(row_item.get("source_topic", "") or "").strip()
                last_info = mqtt2lox_last_seen.get(source_topic, {})
                live_value = str(last_info.get("value", "") or "").strip()
                live_cls = "" if live_value and live_value != "-" else " empty"
                html += f"""
                    <div class="tree-subitem" data-set-link="{escape(set_key)}" data-search="{escape((group['name'] + ' ' + set_obj['name'] + ' ' + alias).lower())}" onclick="showSet('{escape(set_key)}')">
                        <span class="tree-subitem-name">↳ {escape(alias)}</span>
                        <span class="tree-live-value{live_cls}" id="tree_value_{row_index}">{escape(live_value if live_value != "-" else "")}</span>
                    </div>
"""
            html += """
                </div>
"""
        html += """
            </div>
        </div>
"""

    html += """
    </aside>

    <main class="editor">
        <div class="editor-inner">
"""

    rendered_sets = set()
    extra_index = existing_count

    def payload_mode_options(selected):
        return f"""
                                    <option value="raw" {"selected" if selected == "raw" else ""}>RAW / kompletter Payload</option>
                                    <option value="json_key" {"selected" if selected == "json_key" else ""}>JSON-Key</option>
"""

    def render_mapping_card(i, item, set_key, is_new=False, group_name="", set_name=""):
        enabled = item.get("enabled", True)
        mapping_alias = item.get("mapping_alias", "")
        source_topic = item.get("source_topic", "")
        loxone_io = item.get("loxone_io", "")
        test_value = item.get("test_value", "123")
        payload_mode = item.get("payload_mode", "raw")
        json_key = item.get("json_key", "")
        output_mode = item.get("output_mode", "single")
        last_info = mqtt2lox_last_seen.get(source_topic, {})
        last_payload = last_info.get("value", "-")
        last_time = last_info.get("time", "-")
        checked = "checked" if enabled else ""
        group_hidden = f'<input type="hidden" name="group_{i}" value="{escape(group_name)}" data-group-sync="{escape(set_key)}">'
        set_hidden = f'<input type="hidden" name="set_name_{i}" value="{escape(set_name)}" data-set-sync="{escape(set_key)}">'
        test_button = "-" if is_new else f'<button class="testbtn" type="submit" formaction="/mqtt2lox/test/{i}" formmethod="post">Test</button>'
        delete_cell = "-" if is_new else f'<button type="button" class="delete-btn" onclick="markDeleteAndHide({i})">🗑</button><input type="checkbox" name="delete_{i}" id="delete_{i}" style="display:none;">'

        return f"""
                    <div class="mapping-card" id="mapping_card_{i}">
                        {group_hidden}
                        {set_hidden}
                        <div class="mapping-alias">
                            <div>
                                <label>Datenpunkt / Alias</label>
                                <input type="text" name="mapping_alias_{i}" value="{escape(str(mapping_alias))}" placeholder="z.B. Schaltzustand, Batteriestand, Temperatur">
                            </div>
                            <div class="small">Name erscheint links unter dem Set</div>
                        </div>
                        <div class="mapping-card-top">
                            <div class="current-value-box">
                                <div class="current-value-title">Aktueller Wert</div>
                                <div class="current-value-main {'empty' if not last_payload or str(last_payload) == '-' else ''}" id="current_value_{i}">{escape(str(last_payload if last_payload != '-' else '-'))}</div>
                                <div class="current-value-time" id="current_time_{i}">Zuletzt: {escape(str(last_time))}</div>
                            </div>
                            <div>
                                <label>Aktiv</label>
                                <input type="checkbox" name="enabled_{i}" {checked}>
                            </div>
                            <div>
                                <label>MQTT Topic</label>
                                <input type="text" name="source_topic_{i}" value="{escape(str(source_topic))}" placeholder="z.B. zigbee2mqtt/kueche">
                            </div>
                            <div>
                                <label>Loxone Eingang</label>
                                <input type="text" name="loxone_io_{i}" value="{escape(str(loxone_io))}" list="loxoneInputs" onfocus="this.select()" placeholder="z.B. kueche_temp">
                            </div>
                            <div class="mapping-actions">
                                {test_button}
                                {delete_cell}
                            </div>
                        </div>

                        <div class="mapping-card-bottom">
                            <div>
                                <label>Payload</label>
                                <select name="payload_mode_{i}">
                                    <option value="raw" {"selected" if payload_mode == "raw" else ""}>RAW</option>
                                    <option value="json_all" {"selected" if payload_mode == "json_all" else ""}>JSON alle</option>
                                    <option value="json_key" {"selected" if payload_mode == "json_key" else ""}>JSON Key</option>
                                </select>
                            </div>
                            <div>
                                <label>JSON Key optional</label>
                                <input type="text" name="json_key_{i}" value="{escape(str(json_key))}" placeholder="z.B. em.apower">
                            </div>
                            <div>
                                <label>Ausgabe</label>
                                <select name="output_mode_{i}">
                                    <option value="single" {"selected" if output_mode == "single" else ""}>Sammeln</option>
                                    <option value="split" {"selected" if output_mode == "split" else ""}>Einzeln</option>
                                </select>
                            </div>
                            <div>
                                <label>Letzter Wert</label>
                                <div class="small" id="mqtt2lox_value_{i}">{escape(str(last_payload))}</div>
                            </div>
                            <div>
                                <label>Zuletzt</label>
                                <div class="small" id="mqtt2lox_time_{i}">{escape(str(last_time))}</div>
                            </div>
                            <div>
                                <label>Testwert</label>
                                <input type="text" name="test_value_{i}" value="{escape(str(test_value))}">
                            </div>
                        </div>
                    </div>
"""

    for group_key in sorted(tree.keys(), key=lambda x: tree[x]["name"].casefold()):
        group = tree[group_key]
        for set_key in sorted(group["sets"].keys(), key=lambda x: group["sets"][x]["name"].casefold()):
            if set_key in rendered_sets:
                continue
            rendered_sets.add(set_key)
            set_obj = group["sets"][set_key]
            active_cls = " active" if set_key == first_set_key else ""

            html += f"""
        <section class="set-panel{active_cls}" data-set-panel="{escape(set_key)}">
            <div class="card">
                <div class="set-head">
                    <div>
                        <label>Gruppe</label>
                        <input type="text" value="{escape(group["name"] if group["name"] != "Ohne Gruppe" else "")}" oninput="syncSetGroup('{escape(set_key)}', this.value)" list="mappingGroups">
                    </div>
                    <div>
                        <label>Name / Pseudonym</label>
                        <input type="text" value="{escape(set_obj["name"])}" oninput="syncSetName('{escape(set_key)}', this.value)">
                    </div>
                    <div>
                        <button type="button" title="Nur Name/Gruppe ändern">✎</button>
                    </div>
                    <div class="small">
                        Ein Set kann mehrere Datenpunkte eines Gerätes enthalten, z.B. Temperatur, Luftfeuchte und Batterie.
                    </div>
                    <div>
                        <button type="button" class="delete-btn" onclick="deleteWholeSet('{escape(set_key)}')">Set löschen</button>
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="mapping-header">
                    <div>
                        <h2 style="margin:0;">Mappings in diesem Set</h2>
                        <div class="small">{len(set_obj["rows"])} gespeicherte Mapping(s)</div>
                    </div>
                    <button type="button" onclick="showExtraMapping('{escape(set_key)}')">＋ Topic / Mapping hinzufügen</button>
                </div>

                <div class="mapping-list">
"""
            for i in set_obj["rows"]:
                item = mappings[i]
                group_name = str(item.get("group", "") or "").strip()
                set_name = str(item.get("set_name", "") or "").strip() or set_obj["name"]
                html += render_mapping_card(i, item, set_key, False, group_name, set_name)

            # Eine vorbereitete neue Zeile pro Set
            html += f"""
                    <div id="extra_wrap_{escape(set_key)}" style="display:none;">
"""
            html += render_mapping_card(extra_index, {
                "enabled": True,
                "mapping_alias": "",
                "source_topic": "",
                "loxone_io": "",
                "test_value": "123",
                "payload_mode": "raw",
                "json_key": "",
                "output_mode": "single",
            }, set_key, True, group["name"] if group["name"] != "Ohne Gruppe" else "", set_obj["name"])
            html += """
                    </div>
                </div>

                <div class="info-box small">
                    Payload RAW = Wert direkt senden · JSON alle = alle Felder aus Payload verwenden · JSON Key = einzelnes Feld, z.B. <b>em.apower</b> · Sammeln = eine UDP-Zeile · Einzeln = mehrere UDP-Zeilen
                </div>
            </div>
        </section>
"""
            extra_index += 1

    # Neues Set
    html += f"""
        <section class="set-panel{' active' if first_set_key == '__new__' else ''}" data-set-panel="__new__">
            <div class="card">
                <div class="set-head">
                    <div>
                        <label>Gruppe</label>
                        <input type="text" name="group_{extra_index}" value="{escape(prefill_group)}" list="mappingGroups" placeholder="z.B. Temperatur">
                    </div>
                    <div>
                        <label>Name / Pseudonym</label>
                        <input type="text" name="set_name_{extra_index}" value="{escape(prefill_set)}" placeholder="z.B. Sensor Küche">
                    </div>
                    <div></div>
                    <div class="small">
                        Neues Gerät/Objekt anlegen. Danach erscheint es links im Explorer.
                    </div>
                    <div></div>
                </div>
            </div>

            <div class="card">
                <div class="mapping-header">
                    <div>
                        <h2 style="margin:0;">Erstes Mapping</h2>
                        <div class="small">Nach dem Speichern kannst du weitere Topics im Set ergänzen.</div>
                    </div>
                </div>
                <div class="mapping-list">
"""
    html += render_mapping_card(extra_index, {
        "enabled": True,
        "mapping_alias": "",
        "source_topic": prefill_source_topic,
        "loxone_io": "",
        "test_value": "123",
        "payload_mode": prefill_payload_mode,
        "json_key": prefill_json_key,
        "output_mode": "single",
    }, "__new__", True, prefill_group, prefill_set)
    html += f"""
                </div>
            </div>
        </section>

        <input type="hidden" name="count" value="{extra_index + 1}">

        <div class="footer-actions">
            <button type="submit" class="save-bottom">💾 Speichern</button>
        </div>
        </div>
    </main>
</div>
"""

    html += """
<datalist id="mappingGroups">
"""
    known_groups = sorted({str(item.get("group", "") or "").strip() for item in mappings if str(item.get("group", "") or "").strip()}, key=lambda x: x.casefold())
    for group_name in known_groups:
        html += f'    <option value="{escape(group_name)}">\n'

    html += """
</datalist>

<datalist id="loxoneInputs">
"""

    try:
        load_mapping(config)
        sorted_inputs = sorted(control_mapping.keys(), key=lambda x: str(x).casefold())
        for input_name in sorted_inputs:
            html += f'    <option value="{escape(str(input_name))}">\n'
    except Exception as e:
        print(f"Datalist Fehler: {e}")

    html += """
</datalist>
</form>

"""
    html += shared_mapping_explorer_script(
        namespace="mqtt2lox",
        tree_storage_key="mqtt2lox_mapping_explorer_tree_collapsed",
        subitem_storage_key="mqtt2lox_mapping_explorer_set_subitems_collapsed",
        selected_storage_key="mqtt2lox_mapping_explorer_selected_set",
        data_url="/mqtt2lox_data",
        card_id_prefix="mapping_card_",
        value_id_prefix="mqtt2lox_value_",
        time_id_prefix="mqtt2lox_time_",
        tree_value_id_prefix="tree_value_",
        current_value_id_prefix="current_value_",
        current_time_id_prefix="current_time_"
    )
    html += """

</body>
</html>
"""

    return html


@app.route("/mqtt2lox/save", methods=["POST"])
def mqtt2lox_save():
    count = int(request.form.get("count", 0))
    new_data = []

    for i in range(count):
        if f"delete_{i}" in request.form:
            continue
        if request.form.get(f"save_row_{i}", "1") == "0":
            continue

        group = request.form.get(f"group_{i}", "").strip()
        set_name = request.form.get(f"set_name_{i}", "").strip()
        mapping_alias = request.form.get(f"mapping_alias_{i}", "").strip()
        source_topic = request.form.get(f"source_topic_{i}", "").strip()
        loxone_io = request.form.get(f"loxone_io_{i}", "").strip()
        test_value = request.form.get(f"test_value_{i}", "123").strip()

        payload_mode = request.form.get(f"payload_mode_{i}", "raw").strip()
        json_key = request.form.get(f"json_key_{i}", "").strip()
        output_mode = request.form.get(f"output_mode_{i}", "single").strip()

        enabled = f"enabled_{i}" in request.form

        # Legacy: Versteckte/angefangene Extra-Zeilen dürfen nicht als leere technische Mappings gespeichert werden.
        # Gruppe/Set allein ist nur UI-Struktur und kein echtes MQTT→Loxone Mapping.
        # Sonst entsteht bei jedem Speichern wieder ein leeres Mapping-Goblinchen.
        has_real_mapping = bool(source_topic or loxone_io)
        if not has_real_mapping:
            continue

        if not set_name:
            set_name = loxone_io or source_topic or mapping_alias or "Neues Set"

        new_data.append({
            "enabled": enabled,
            "group": group,
            "set_name": set_name,
            "mapping_alias": mapping_alias,
            "source_topic": source_topic,
            "loxone_io": loxone_io,
            "test_value": test_value,
            "payload_mode": payload_mode,
            "json_key": json_key,
            "output_mode": output_mode
        })

    save_mqtt2lox_config(new_data)
    # Legacy: Kein automatischer Objekt-Sync beim Speichern technischer Mappings.
    # Sonst entstehen aus Alt-/Test-Mappings plötzlich hunderte Objekte.
    return redirect("/mqtt2lox")


@app.route("/mqtt2lox/test/<int:index>", methods=["POST"])
def mqtt2lox_test(index):
    mappings = load_mqtt2lox_config()
    config = load_config()

    if index < 0 or index >= len(mappings):
        return redirect("/mqtt2lox")

    item = mappings[index]

    loxone_io = item.get("loxone_io", "").strip()
    test_value = request.form.get(f"test_value_{index}", "123").strip()
    group = request.form.get(f"group_{index}", item.get("group", "")).strip()
    set_name = request.form.get(f"set_name_{index}", item.get("set_name", "")).strip()
    mapping_alias = request.form.get(f"mapping_alias_{index}", item.get("mapping_alias", "")).strip()

    mappings[index]["test_value"] = test_value
    mappings[index]["group"] = group
    mappings[index]["set_name"] = set_name
    mappings[index]["mapping_alias"] = mapping_alias
    save_mqtt2lox_config(mappings)

    if not loxone_io:
        return redirect("/mqtt2lox")

    try:
        url = f"http://{config['loxone']['host']}/dev/sps/io/{loxone_io}/{test_value}"

        r = requests.get(
            url,
            auth=(config["loxone"]["user"], config["loxone"]["password"]),
            timeout=5
        )

        if r.status_code == 200:
            add_log_entry(f"MQTT2LOX TEST -> {loxone_io} = {test_value}")
        else:
            add_log_entry(f"MQTT2LOX TEST Fehler {r.status_code}: {r.text}")

    except Exception as e:
        add_log_entry(f"MQTT2LOX TEST Fehler: {e}")

    return redirect("/mqtt2lox")


@app.route("/mqtt2lox_data")
def mqtt2lox_data():
    mappings = load_mqtt2lox_config()
    data = {}

    for i, item in enumerate(mappings):
        source_topic = item.get("source_topic", "").strip()
        info = mqtt2lox_last_seen.get(source_topic, {})

        data[str(i)] = {
            "value": str(info.get("value", "-")),
            "time": str(info.get("time", "-"))
        }

    return data


@app.route("/mqtt2udp")
def mqtt2udp():
    mappings = load_mqtt2udp_config()

    prefill_source_topic = request.args.get("source_topic", "").strip()
    prefill_payload_mode = request.args.get("payload_mode", "raw").strip() or "raw"
    prefill_json_key = request.args.get("json_key", "").strip()
    prefill_group = request.args.get("group", "").strip()
    prefill_set = request.args.get("set_name", "").strip()
    prefill_alias = request.args.get("mapping_alias", "").strip()

    if prefill_payload_mode not in ["raw", "json_key"]:
        prefill_payload_mode = "raw"
    if prefill_json_key and not prefill_alias:
        prefill_alias = prefill_json_key

    def safe_key(text_value):
        return clean_topic(text_value) or "ohne_name"

    tree = {}
    for i, item in enumerate(mappings):
        group_name = str(item.get("group", "") or "").strip() or "Ohne Gruppe"
        set_name = str(item.get("set_name", "") or "").strip() or str(item.get("udp_topic", "") or item.get("source_topic", "") or "Importiert").strip() or "Importiert"
        group_key = safe_key(group_name)
        set_key = safe_key(group_name + "__" + set_name)
        tree.setdefault(group_key, {"name": group_name, "sets": {}})
        tree[group_key]["sets"].setdefault(set_key, {"name": set_name, "rows": []})
        tree[group_key]["sets"][set_key]["rows"].append(i)

    first_set_key = "__new__"
    for gk in sorted(tree.keys(), key=lambda x: tree[x]["name"].casefold()):
        for sk in sorted(tree[gk]["sets"].keys(), key=lambda x: tree[gk]["sets"][x]["name"].casefold()):
            first_set_key = sk
            break
        if first_set_key != "__new__":
            break

    existing_count = len(mappings)
    extra_index = existing_count

    html = """
<!doctype html>
<html>
<head>
    <title>MQTT → UDP Explorer</title>
    <style>
        :root {
            --bg:#202830; --panel:#1b2229; --panel2:#111820; --border:#303b45;
            --muted:#aeb8c4; --text:#f4f7fb; --accent:#5f686f; --green:#1fa342;
            --danger:#b83b3b; --yellow:#f5d76e;
        }
        * { box-sizing:border-box; }
        html, body { height:100%; overflow:hidden; }
        body { font-family:Arial,sans-serif; background:var(--bg); color:var(--text); margin:0; }
        header { height:76px; background:#1b2229; border-bottom:1px solid var(--border); display:flex; align-items:center; justify-content:space-between; gap:14px; padding:14px 20px; overflow:hidden; }
        h1 { margin:0; font-size:28px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
        .header-tools { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
        .page { display:grid; grid-template-columns:330px minmax(0,1fr); height:calc(100vh - 76px); min-width:0; overflow:hidden; }
        .sidebar { background:#111820; border-right:1px solid var(--border); overflow:auto; padding:14px; }
        .editor { overflow-x:auto; overflow-y:auto; min-width:0; padding:18px; padding-bottom:18px; }
        .editor-inner { width:max(100%, 1050px); min-width:0; padding-right:18px; }
        button, a.button-link, a { background:var(--accent); color:white; padding:9px 13px; text-decoration:none; border:none; border-radius:8px; cursor:pointer; display:inline-block; font-size:14px; font-weight:700; }
        button:hover, a:hover { background:#737d86; }
        .save-bottom { background:var(--green); min-width:240px; font-size:16px; padding:13px 20px; }
        .save-bottom:hover { background:#27b54d; }
        .delete-btn { background:transparent; border:1px solid var(--danger); color:#ff6b6b; padding:7px 10px; }
        .delete-btn:hover { background:#3a1618; }
        input[type=text], select { width:100%; background:#0f1720; color:white; border:1px solid #4a5663; border-radius:6px; padding:9px; box-sizing:border-box; font-size:14px; }
        input[type=checkbox] { width:18px; height:18px; accent-color:#35c75a; }
        label { display:block; font-size:12px; color:var(--muted); margin-bottom:5px; }
        .small { font-size:12px; color:var(--muted); line-height:1.38; }
        .search-box { position:relative; margin-bottom:14px; }
        .search-box input { padding-left:34px; }
        .search-icon { position:absolute; left:11px; top:9px; opacity:.75; }
        .tree-group { margin-bottom:10px; }
        .tree-group-title { color:var(--yellow); font-weight:900; padding:8px; cursor:pointer; user-select:none; display:flex; justify-content:space-between; align-items:center; border-radius:7px; }
        .tree-group-title:hover { background:#202830; }
        .tree-set { margin-left:18px; padding:8px 9px; border-radius:8px; cursor:pointer; display:flex; justify-content:space-between; align-items:center; gap:8px; color:#e9edf5; }
        .tree-set:hover { background:#25303a; }
        .tree-set.active { background:#5f686f; color:white; }
        .tree-set-main { display:flex; align-items:center; gap:6px; min-width:0; }
        .tree-set-arrow { width:16px; display:inline-block; text-align:center; font-weight:900; opacity:.9; user-select:none; }
        .tree-set-name { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
        .tree-subitems { margin-left:34px; margin-bottom:4px; }
        .tree-subitems.collapsed { display:none; }
        .tree-subitem { padding:5px 8px; border-radius:7px; color:#cfd8e6; font-size:13px; cursor:pointer; opacity:.9; display:flex; align-items:center; justify-content:space-between; gap:8px; }
        .tree-subitem:hover { background:#25303a; color:white; }
        .tree-subitem-name { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; min-width:0; }
        .tree-live-value { color:#35d05b; background:rgba(35,208,91,.12); border:1px solid rgba(35,208,91,.22); border-radius:7px; padding:1px 5px; font-size:11px; font-weight:800; white-space:nowrap; max-width:92px; overflow:hidden; text-overflow:ellipsis; }
        .tree-live-value.empty { display:none; }
        .tree-subitem.hidden-by-search, .tree-set.hidden-by-search, .tree-group.hidden-by-search { display:none; }
        .badge { background:#26313d; border:1px solid #3c4856; color:#cfd8e6; border-radius:999px; font-size:11px; padding:2px 7px; white-space:nowrap; }
        .group-body.collapsed { display:none; }
        .new-set-link { margin-top:14px; border:1px dashed #596777; border-radius:10px; padding:12px; cursor:pointer; background:#111820; }
        .new-set-link:hover { background:#1b2530; }
        .set-panel { display:none; }
        .set-panel.active { display:block; }
        .card { background:var(--panel); border:1px solid var(--border); border-radius:12px; padding:16px; margin-bottom:16px; width:100%; }
        .set-head { display:grid; grid-template-columns:230px 280px minmax(220px,1fr) auto; gap:12px; align-items:end; }
        .mapping-header { display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap; margin-bottom:14px; }
        .mapping-list { display:flex; flex-direction:column; gap:12px; }
        .mapping-card { background:#111820; border:1px solid var(--border); border-radius:12px; padding:14px; }
        .mapping-alias { display:grid; grid-template-columns:1fr auto; gap:12px; align-items:end; margin-bottom:12px; padding-bottom:12px; border-bottom:1px solid var(--border); }
        .mapping-card-top { display:grid; grid-template-columns:240px 42px minmax(260px,1.45fr) minmax(240px,1.15fr) 110px; gap:12px; align-items:end; margin-bottom:12px; }
        .mapping-card-bottom { display:grid; grid-template-columns:220px 120px 150px 150px 180px 120px 120px minmax(170px,1fr); gap:12px; align-items:end; }
        .current-value-box { border:1px solid var(--border); border-radius:10px; background:rgba(255,255,255,.02); padding:10px 12px; min-height:82px; display:flex; flex-direction:column; justify-content:center; }
        .current-value-title { color:var(--muted); font-size:12px; margin-bottom:7px; }
        .current-value-main { color:#35d05b; font-size:22px; font-weight:900; line-height:1.1; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
        .current-value-main.empty { color:var(--muted); }
        .current-value-time { color:var(--muted); font-size:12px; margin-top:8px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
        .mapping-actions { display:flex; gap:8px; align-items:center; justify-content:flex-end; }
        .info-box { border:1px solid #30445d; background:#132033; border-radius:10px; padding:12px 14px; margin-top:14px; }
        .footer-actions { position:sticky; bottom:0; display:flex; justify-content:flex-end; gap:10px; z-index:20; padding:10px 0 0; margin-top:10px; background:linear-gradient(to top, var(--bg) 75%, rgba(32,40,48,0)); }
        @media(max-width:1200px) { .page { grid-template-columns:300px minmax(0,1fr); } .editor-inner { width:max(100%,1050px); } }
    </style>
</head>
<body>
<header>
    <h1>MQTT → UDP Explorer</h1>
    <div class="header-tools">
        <a class="button-link" href="/mqtt">← Zurück zum MQTT Hub</a>
        <button type="button" onclick="expandAllTree()">Alles aufklappen</button>
        <button type="button" onclick="collapseAllTree()">Alles einklappen</button>
    </div>
</header>

<form method="post" action="/mqtt2udp/save" id="mappingForm">
<div class="page">
    <aside class="sidebar">
        <div class="search-box"><span class="search-icon">🔎</span><input id="treeSearch" type="text" placeholder="Suchen..." oninput="filterTree()"></div>
        <button type="button" style="width:100%; margin:0 0 12px 0; justify-content:center;" onclick="showSet('__new__')">＋ Neues Set erstellen</button>
        <div class="small" style="margin-bottom:12px;">Links Gruppen und UDP-Sets. Rechts bearbeitest du das gewählte Objekt mit mehreren MQTT → UDP Zuordnungen.</div>
"""

    for group_key in sorted(tree.keys(), key=lambda x: tree[x]["name"].casefold()):
        group = tree[group_key]
        html += f"""
        <div class="tree-group" data-tree-group="{escape(group_key)}" data-search="{escape(group["name"].lower())}">
            <div class="tree-group-title" onclick="toggleTreeGroup('{escape(group_key)}')">
                <span><span id="tree_arrow_{escape(group_key)}">▾</span> {escape(group["name"])}</span>
                <span class="badge">{len(group["sets"])} Set(s)</span>
            </div>
            <div class="group-body" id="tree_body_{escape(group_key)}">
"""
        for set_key in sorted(group["sets"].keys(), key=lambda x: group["sets"][x]["name"].casefold()):
            set_obj = group["sets"][set_key]
            active_cls = " active" if set_key == first_set_key else ""
            alias_names = []
            for row_index in set_obj["rows"]:
                row_item = mappings[row_index]
                alias = str(row_item.get("mapping_alias", "") or "").strip()
                if not alias:
                    alias = str(row_item.get("udp_topic", "") or row_item.get("source_topic", "") or f"Mapping {row_index + 1}").strip()
                alias_names.append(alias)

            search_text = f"{group['name']} {set_obj['name']} {' '.join(alias_names)}".lower()
            html += f"""
                <div class="tree-set{active_cls}" data-set-link="{escape(set_key)}" data-search="{escape(search_text)}" onclick="showSet('{escape(set_key)}')">
                    <span class="tree-set-main">
                        <span class="tree-set-arrow" id="set_arrow_{escape(set_key)}" onclick="event.stopPropagation(); toggleSetSubitems('{escape(set_key)}')">▾</span>
                        <span class="tree-set-name">{escape(set_obj["name"])}</span>
                    </span>
                    <span class="badge">{len(set_obj["rows"])}</span>
                </div>
                <div class="tree-subitems" id="subitems_{escape(set_key)}" data-subitems-for="{escape(set_key)}">
"""
            for row_index, alias in zip(set_obj["rows"], alias_names):
                source_topic = str(mappings[row_index].get("source_topic", "") or "").strip()
                last_info = get_udp_last_seen("mqtt2udp", source_topic)
                live_value = str(last_info.get("value", "") or "").strip()
                live_cls = "" if live_value and live_value != "-" else " empty"
                html += f"""
                    <div class="tree-subitem" data-set-link="{escape(set_key)}" data-search="{escape((group['name'] + ' ' + set_obj['name'] + ' ' + alias).lower())}" onclick="showSet('{escape(set_key)}')">
                        <span class="tree-subitem-name">↳ {escape(alias)}</span>
                        <span class="tree-live-value{live_cls}" id="mqtt2udp_tree_value_{row_index}">{escape(live_value if live_value != "-" else "")}</span>
                    </div>
"""
            html += """
                </div>
"""
        html += """
            </div>
        </div>
"""

    html += """
    </aside>
    <main class="editor"><div class="editor-inner">
"""

    rendered_sets = set()

    def format_options(selected):
        return f"""
                                    <option value="topic_value" {"selected" if selected == "topic_value" else ""}>topic:value</option>
                                    <option value="json" {"selected" if selected == "json" else ""}>JSON Text</option>
                                    <option value="json_number" {"selected" if selected == "json_number" else ""}>JSON Zahl</option>
                                    <option value="value_only" {"selected" if selected == "value_only" else ""}>Nur Wert</option>
"""

    def payload_mode_options(selected):
        return f"""
                                    <option value="raw" {"selected" if selected == "raw" else ""}>RAW / kompletter Payload</option>
                                    <option value="json_key" {"selected" if selected == "json_key" else ""}>JSON-Key</option>
"""

    def render_mapping_card(i, item, set_key, is_new=False, group_name="", set_name=""):
        enabled = item.get("enabled", True)
        mapping_alias = item.get("mapping_alias", "")
        source_topic = item.get("source_topic", "")
        udp_topic = item.get("udp_topic", "")
        udp_ip = item.get("udp_ip", "")
        udp_port = item.get("udp_port", "7000")
        udp_format = item.get("udp_format", "topic_value")
        payload_mode = item.get("payload_mode", "raw")
        json_key = item.get("json_key", "")
        test_value = item.get("test_value", "123")
        last_info = get_udp_last_seen("mqtt2udp", source_topic)
        last_payload = last_info.get("value", "-")
        last_time = last_info.get("time", "-")
        checked = "checked" if enabled else ""
        group_hidden = f'<input type="hidden" name="group_{i}" value="{escape(group_name)}" data-group-sync="{escape(set_key)}">'
        set_hidden = f'<input type="hidden" name="set_name_{i}" value="{escape(set_name)}" data-set-sync="{escape(set_key)}">'
        test_button = "-" if is_new else f'<button class="testbtn" type="submit" formaction="/mqtt2udp/test/{i}" formmethod="post">Test</button>'
        copy_button = "-" if is_new else f'<button class="testbtn" type="submit" formaction="/mqtt2udp/copy/{i}" formmethod="post">Kopie</button>'
        delete_cell = "-" if is_new else f'<button type="button" class="delete-btn" onclick="markDeleteAndHide({i})">🗑</button><input type="checkbox" name="delete_{i}" id="delete_{i}" style="display:none;">'
        return f"""
                    <div class="mapping-card" id="mqtt2udp_mapping_card_{i}">
                        {group_hidden}
                        {set_hidden}
                        <div class="mapping-alias">
                            <div>
                                <label>Datenpunkt / Alias</label>
                                <input type="text" name="mapping_alias_{i}" value="{escape(str(mapping_alias))}" placeholder="z.B. Leistung, Status, Temperatur">
                            </div>
                            <div class="small">Name erscheint links unter dem Set</div>
                        </div>

                        <div class="mapping-card-top">
                            <div class="current-value-box">
                                <div class="current-value-title">Aktueller Wert</div>
                                <div class="current-value-main {'empty' if not last_payload or str(last_payload) == '-' else ''}" id="mqtt2udp_current_value_{i}">{escape(str(last_payload if last_payload != '-' else '-'))}</div>
                                <div class="current-value-time" id="mqtt2udp_current_time_{i}">Zuletzt: {escape(str(last_time))}</div>
                            </div>
                            <div>
                                <label>Aktiv</label>
                                <input type="checkbox" name="enabled_{i}" {checked}>
                            </div>
                            <div>
                                <label>MQTT Topic</label>
                                <input type="text" name="source_topic_{i}" value="{escape(str(source_topic))}" placeholder="z.B. solar/wr/power">
                            </div>
                            <div>
                                <label>UDP Topic</label>
                                <input type="text" name="udp_topic_{i}" value="{escape(str(udp_topic))}" placeholder="z.B. wr_leistung">
                            </div>
                            <div class="mapping-actions">
                                {test_button}
                                {copy_button}
                                {delete_cell}
                            </div>
                        </div>

                        <div class="mapping-card-bottom">
                            <div>
                                <label>UDP IP / Ziele</label>
                                <input type="text" name="udp_ip_{i}" value="{escape(str(udp_ip))}" placeholder="192.168.1.50,192.168.1.60">
                            </div>
                            <div>
                                <label>UDP Port</label>
                                <input type="text" name="udp_port_{i}" value="{escape(str(udp_port))}" placeholder="7000" list="udpPortPresets" onmousedown="openPortPresets(this)" onblur="restorePortIfEmpty(this)">
                            </div>
                            <div>
                                <label>Format</label>
                                <select name="udp_format_{i}">
                                    {format_options(udp_format)}
                                </select>
                            </div>
                            <div>
                                <label>Payload</label>
                                <select name="payload_mode_{i}">
                                    {payload_mode_options(payload_mode)}
                                </select>
                            </div>
                            <div>
                                <label>JSON-Key</label>
                                <input type="text" name="json_key_{i}" value="{escape(str(json_key))}" placeholder="z.B. power.total">
                            </div>
                            <div>
                                <label>Letzter Wert</label>
                                <div class="small" id="mqtt2udp_value_{i}">{escape(str(last_payload))}</div>
                            </div>
                            <div>
                                <label>Zuletzt</label>
                                <div class="small" id="mqtt2udp_time_{i}">{escape(str(last_time))}</div>
                            </div>
                            <div>
                                <label>Testwert</label>
                                <input type="text" name="test_value_{i}" value="{escape(str(test_value))}">
                            </div>
                        </div>
                    </div>
"""

    for group_key in sorted(tree.keys(), key=lambda x: tree[x]["name"].casefold()):
        group = tree[group_key]
        for set_key in sorted(group["sets"].keys(), key=lambda x: group["sets"][x]["name"].casefold()):
            if set_key in rendered_sets:
                continue
            rendered_sets.add(set_key)
            set_obj = group["sets"][set_key]
            active_cls = " active" if set_key == first_set_key else ""
            html += f"""
        <section class="set-panel{active_cls}" data-set-panel="{escape(set_key)}">
            <div class="card">
                <div class="set-head">
                    <div>
                        <label>Gruppe</label>
                        <input type="text" value="{escape(group["name"] if group["name"] != "Ohne Gruppe" else "")}" oninput="syncSetGroup('{escape(set_key)}', this.value)" list="mappingGroups">
                    </div>
                    <div>
                        <label>Name / Pseudonym</label>
                        <input type="text" value="{escape(set_obj["name"])}" oninput="syncSetName('{escape(set_key)}', this.value)">
                    </div>
                    <div class="small">Ein UDP-Set kann mehrere MQTT Topics an UDP/Loxone senden.</div>
                    <div><button type="button" class="delete-btn" onclick="deleteWholeSet('{escape(set_key)}')">Set löschen</button></div>
                </div>
            </div>
            <div class="card">
                <div class="mapping-header">
                    <div>
                        <h2 style="margin:0;">MQTT → UDP Mappings</h2>
                        <div class="small">{len(set_obj["rows"])} Mapping(s) in diesem Set</div>
                    </div>
                    <button type="button" onclick="showExtraMapping('{escape(set_key)}')">＋ Topic / UDP Mapping hinzufügen</button>
                </div>
                <div class="mapping-list">
"""
            for i in set_obj["rows"]:
                item = mappings[i]
                group_name = str(item.get("group", "") or "").strip()
                set_name = str(item.get("set_name", "") or "").strip() or set_obj["name"]
                html += render_mapping_card(i, item, set_key, False, group_name, set_name)

            html += f"""                    <div id="extra_wrap_{escape(set_key)}" style="display:none;">
"""
            html += render_mapping_card(extra_index, {
                "enabled": True, "mapping_alias": "", "source_topic": "", "udp_topic": "",
                "udp_ip": "", "udp_port": "7000", "udp_format": "topic_value", "payload_mode": "raw", "json_key": "", "test_value": "123"
            }, set_key, True, group["name"] if group["name"] != "Ohne Gruppe" else "", set_obj["name"])
            html += """
                    </div>
                </div>
                <div class="info-box small">UDP Format: <b>topic:value</b> für Loxone, JSON Text/Zahl oder nur Wert. Mehrere Ziel-IPs kommasepariert eintragen.</div>
            </div>
        </section>
"""
            extra_index += 1

    html += f"""
        <section class="set-panel{' active' if first_set_key == '__new__' else ''}" data-set-panel="__new__">
            <div class="card">
                <div class="set-head">
                    <div><label>Gruppe</label><input type="text" name="group_{extra_index}" value="{escape(prefill_group)}" list="mappingGroups" placeholder="z.B. Loxone UDP"></div>
                    <div><label>Name / Pseudonym</label><input type="text" name="set_name_{extra_index}" value="{escape(prefill_set)}" placeholder="z.B. Stromzähler"></div>
                    <div class="small">Neues UDP-Set anlegen. Danach erscheint es links im Explorer.</div>
                    <div></div>
                </div>
            </div>
            <div class="card">
                <div class="mapping-header"><div><h2 style="margin:0;">Erstes UDP Mapping</h2><div class="small">Nach dem Speichern kannst du weitere Topics ergänzen.</div></div></div>
                <div class="mapping-list">
"""
    html += render_mapping_card(extra_index, {
        "enabled": True, "mapping_alias": prefill_alias, "source_topic": prefill_source_topic,
        "udp_topic": prefill_source_topic, "udp_ip": "", "udp_port": "7000",
        "udp_format": "topic_value", "payload_mode": prefill_payload_mode, "json_key": prefill_json_key, "test_value": "123"
    }, "__new__", True, prefill_group, prefill_set)
    html += f"""
                </div>
            </div>
        </section>

        <input type="hidden" name="count" value="{extra_index + 1}">

        <div class="footer-actions"><button type="submit" class="save-bottom">💾 Speichern</button></div>
    </div></main>
</div>
"""

    html += """
<datalist id="mappingGroups">
"""
    known_groups = sorted({str(item.get("group", "") or "").strip() for item in mappings if str(item.get("group", "") or "").strip()}, key=lambda x: x.casefold())
    for group_name in known_groups:
        html += f'    <option value="{escape(group_name)}">\n'
    html += """
</datalist>

<datalist id="udpPortPresets">
"""
    for preset in get_udp_port_presets():
        html += f"""    <option value="{escape(str(preset['port']))}" label="{escape(str(preset['label']))}">\n"""
    html += """
</datalist>
</form>

"""
    html += shared_mapping_explorer_script(
        namespace="mqtt2udp",
        tree_storage_key="mqtt2udp_explorer_tree_collapsed",
        subitem_storage_key="mqtt2udp_explorer_set_subitems_collapsed",
        selected_storage_key="mqtt2udp_explorer_selected_set",
        data_url="/mqtt2udp_data",
        card_id_prefix="mqtt2udp_mapping_card_",
        value_id_prefix="mqtt2udp_value_",
        time_id_prefix="mqtt2udp_time_",
        tree_value_id_prefix="mqtt2udp_tree_value_",
        current_value_id_prefix="mqtt2udp_current_value_",
        current_time_id_prefix="mqtt2udp_current_time_",
        extra_js=mqtt2udp_explorer_extra_js()
    )
    html += """
</body>
</html>
"""
    return html


@app.route("/mqtt2udp/save", methods=["POST"])
def mqtt2udp_save():
    count = int(request.form.get("count", 0))
    new_data = []

    for i in range(count):
        if f"delete_{i}" in request.form:
            continue
        if request.form.get(f"save_row_{i}", "1") == "0":
            continue

        group = request.form.get(f"group_{i}", "").strip()
        set_name = request.form.get(f"set_name_{i}", "").strip()
        mapping_alias = request.form.get(f"mapping_alias_{i}", "").strip()
        source_topic = request.form.get(f"source_topic_{i}", "").strip()
        udp_topic = request.form.get(f"udp_topic_{i}", "").strip()
        udp_ip = request.form.get(f"udp_ip_{i}", "").strip()
        udp_port = request.form.get(f"udp_port_{i}", "7000").strip()
        udp_format = request.form.get(f"udp_format_{i}", "topic_value").strip()
        payload_mode = request.form.get(f"payload_mode_{i}", "raw").strip() or "raw"
        json_key = request.form.get(f"json_key_{i}", "").strip()
        if payload_mode not in ["raw", "json_key"]:
            payload_mode = "raw"
        test_value = request.form.get(f"test_value_{i}", "123").strip()
        enabled = f"enabled_{i}" in request.form

        # Legacy: Keine leeren Draft-/UI-Zeilen als technische MQTT→UDP Mappings speichern.
        # Gruppe/Set/Alias alleine ist nur Struktur und darf kein neues Mapping erzeugen.
        # Ein echtes Mapping braucht mindestens Quelle + Zielname oder Ziel-IP.
        has_real_mapping = bool(source_topic or udp_topic or udp_ip)
        if not has_real_mapping:
            continue

        if not set_name:
            set_name = udp_topic or source_topic or mapping_alias or "Neues Set"

        new_data.append({
            "enabled": enabled,
            "group": group,
            "set_name": set_name,
            "mapping_alias": mapping_alias,
            "source_topic": source_topic,
            "udp_topic": udp_topic,
            "udp_ip": udp_ip,
            "udp_port": udp_port,
            "udp_format": udp_format,
            "payload_mode": payload_mode,
            "json_key": json_key,
            "test_value": test_value
        })

    save_mqtt2udp_config(new_data)
    # Legacy: Kein automatischer Objekt-Sync beim Speichern technischer Mappings.
    return redirect("/mqtt2udp")


@app.route("/mqtt2udp/test/<int:index>", methods=["POST"])
def mqtt2udp_test(index):
    mappings = load_mqtt2udp_config()

    if index < 0 or index >= len(mappings):
        return redirect("/mqtt2udp")

    item = mappings[index]
    item["test_value"] = request.form.get(f"test_value_{index}", item.get("test_value", "123")).strip()
    item["group"] = request.form.get(f"group_{index}", item.get("group", "")).strip()
    item["set_name"] = request.form.get(f"set_name_{index}", item.get("set_name", "")).strip()
    item["mapping_alias"] = request.form.get(f"mapping_alias_{index}", item.get("mapping_alias", "")).strip()
    save_mqtt2udp_config(mappings)

    udp_topic = item.get("udp_topic", "").strip()
    udp_ip = item.get("udp_ip", "").strip()
    udp_port = item.get("udp_port", "7000").strip()
    udp_format = item.get("udp_format", "topic_value").strip()
    test_value = item.get("test_value", "123")

    if udp_topic and udp_ip and udp_port:
        send_mqtt2udp(udp_ip, udp_port, udp_topic, test_value, udp_format)

    return redirect("/mqtt2udp")


@app.route("/mqtt2udp_data")
def mqtt2udp_data():
    mappings = load_mqtt2udp_config()
    data = {}

    for i, item in enumerate(mappings):
        source_topic = item.get("source_topic", "").strip()
        info = get_udp_last_seen("mqtt2udp", source_topic)

        data[str(i)] = {
            "value": str(info.get("value", "-")),
            "time": str(info.get("time", "-"))
        }

    return data


@app.route("/udp_presets")
def udp_presets():
    presets = load_udp_presets()
    new_i = len(presets)

    html = """
<!doctype html>
<html>
<head>
<title>UDP Port Presets</title>
<style>
body { font-family:Arial; background:#202830; color:#f4f7fb; margin:30px; }
table { width:100%; border-collapse:collapse; background:#151c23; }
th,td { border:1px solid #303b45; padding:8px; }
input[type=text] { width:100%; background:#111820; color:white; border:1px solid #4a5663; padding:6px; box-sizing:border-box; }
button,a { background:#5f686f; color:white; padding:10px 15px; text-decoration:none; border:none; border-radius:8px; cursor:pointer; display:inline-block; font-size:14px; }
</style>
</head>
<body>

<h1>UDP Port Presets</h1>

<form method="post" action="/udp_presets/save">

<table>
<tr>
    <th>Port</th>
    <th>Bezeichnung</th>
    <th>Löschen</th>
</tr>
"""

    for i, item in enumerate(presets):
        port = item.get("port", "")
        label = item.get("label", "")

        html += f"""
<tr>
    <td><input type="text" name="port_{i}" value="{escape(str(port))}"></td>
    <td><input type="text" name="label_{i}" value="{escape(str(label))}"></td>
    <td class="checkbox-col"><input type="checkbox" name="delete_{i}"></td>
</tr>
"""

    html += f"""
<tr>
    <td><input type="text" name="port_{new_i}" placeholder="0815"></td>
    <td><input type="text" name="label_{new_i}" placeholder="Mein UDP Port"></td>
    <td>-</td>
</tr>
</table>

<br>

<input type="hidden" name="count" value="{len(presets) + 1}">

<button type="submit">Speichern</button>




</form>

</body>
</html>
"""

    return html


@app.route("/udp_presets/save", methods=["POST"])
def udp_presets_save():
    count = int(request.form.get("count", 0))
    data = []

    for i in range(count):
        if f"delete_{i}" in request.form:
            continue

        port = request.form.get(f"port_{i}", "").strip()
        label = request.form.get(f"label_{i}", "").strip()

        if not port:
            continue

        data.append({
            "port": port,
            "label": label
        })

    save_udp_presets(data)

    return redirect("/udp_presets")


@app.route("/mqtt2udp/copy/<int:index>", methods=["POST"])
def mqtt2udp_copy(index):
    mappings = load_mqtt2udp_config()

    if index < 0 or index >= len(mappings):
        return redirect("/mqtt2udp")

    item = mappings[index].copy()

    # optional Testwert zurücksetzen
    item["test_value"] = item.get("test_value", "123")

    # direkt unter Original einfügen
    mappings.insert(index + 1, item)

    save_mqtt2udp_config(mappings)

    add_log_entry(
        f"MQTT2UDP Mapping kopiert: {item.get('source_topic', '')}"
    )

    return redirect("/mqtt2udp")




@app.route("/test/influx", methods=["POST"])
def test_influx():
    config = load_config()
    influx = config.get("influx", {}).copy()

    # Mit aktuellen Formularwerten testen, ohne vorher speichern zu müssen
    if request.form:
        influx = get_influx_form_config(config)

    try:
        host = str(influx.get("host", "")).strip()
        port = int(influx.get("port", 8086))
        version = str(influx.get("version", "2"))

        if not host:
            notice = '<div class="card bad">❌ Influx Fehler: Host fehlt</div>'
            return embedded_page('InfluxDB', influx_settings_content(load_config(), notice))

        if version == "1":
            ping_url = f"http://{host}:{port}/ping"
            r = requests.get(ping_url, timeout=5)
            if r.status_code not in [200, 204]:
                notice = f'<div class="card bad">❌ InfluxDB 1.x nicht erreichbar: HTTP {r.status_code}</div>'
                return embedded_page('InfluxDB', influx_settings_content(load_config(), notice))

            # Schreibtest für 1.x
            test_cfg = dict(influx)
            if not test_cfg.get("database"):
                notice = '<div class="card bad">❌ InfluxDB 1.x: Datenbank fehlt</div>'
                return embedded_page('InfluxDB', influx_settings_content(load_config(), notice))

            line = f"{influx_service.influx_escape_measurement(test_cfg.get('measurement', 'loxone'))},topic=mqtt2lox_influx_test value=1"
            url = f"http://{host}:{port}/write?db={quote(str(test_cfg.get('database')), safe='')}&precision=s"
            auth = (test_cfg.get("user", ""), test_cfg.get("password", "")) if test_cfg.get("user") or test_cfg.get("password") else None
            wr = requests.post(url, data=line.encode("utf-8"), auth=auth, timeout=5)
            if wr.status_code == 204:
                notice = '<div class="card ok">✅ InfluxDB 1.x erreichbar und Testwert geschrieben</div>'
            else:
                notice = f'<div class="card bad">❌ InfluxDB 1.x Schreibtest Fehler: HTTP {wr.status_code} {escape(wr.text)}</div>'

        else:
            # Health zeigt nur, ob Influx lebt. Der echte Test ist danach der Write mit Token/Bucket/Org.
            health_url = f"http://{host}:{port}/health"
            hr = requests.get(health_url, timeout=5)
            if hr.status_code != 200:
                notice = f'<div class="card bad">❌ InfluxDB 2.x nicht erreichbar: HTTP {hr.status_code}</div>'
                return embedded_page('InfluxDB', influx_settings_content(load_config(), notice))

            ok, msg = influx_service.influx_v2_write(influx, "mqtt2lox_influx_test", 1, test=True)
            if ok:
                notice = '<div class="card ok">✅ InfluxDB 2.x erreichbar, Token/Bucket/Org OK, Testwert geschrieben</div>'
                add_log_entry("Influx Test OK: Testwert geschrieben")
            else:
                notice = f'<div class="card bad">❌ InfluxDB 2.x Schreibtest Fehler: {escape(msg)}</div>'
                add_log_entry(f"Influx Test Fehler: {msg}")

        return embedded_page('InfluxDB', influx_settings_content(load_config(), notice))

    except Exception as e:
        notice = f'<div class="card bad">❌ Influx Fehler: {escape(str(e))}</div>'
        add_log_entry(f"Influx Test Exception: {e}")
        return embedded_page('InfluxDB', influx_settings_content(load_config(), notice))


@app.route("/monitor")
def monitor():
    html = """
<!doctype html>
<html>
<head>
    <title>MQTT Explorer Monitor</title>
    <style>
        body {
            margin:0;
            font-family: Arial, sans-serif;
            background:#202830;
            color:#f4f7fb;
        }

        header {
            background:#1b2229;
            padding:14px 20px;
            display:flex;
            align-items:center;
            gap:15px;
            border-bottom:1px solid #333;
        }

        header h1 {
            margin:0;
            font-size:22px;
        }

        #search {
            flex:1;
            padding:10px;
            background:#111820;
            color:white;
            border:1px solid #4a5663;
            border-radius:8px;
            font-size:15px;
        }

        .layout {
            display:grid;
            grid-template-columns: 42% 58%;
            height: calc(100vh - 62px);
        }

        .tree {
            overflow:auto;
            border-right:1px solid #333;
            padding:15px;
            background:#151515;
        }

        .details {
            overflow:auto;
            padding:20px;
            background:#101010;
        }

        .node {
            padding:5px 8px;
            border-radius:6px;
            user-select:none;
            white-space:nowrap;
            display:flex;
            align-items:center;
            gap:4px;
            min-height:24px;
        }

        .node:hover,
        .node.selected {
            background:#2a333d;
        }

        .node.topic {
            cursor:pointer;
        }

        .node.topic {
            color:#d7e0ea;
        }

        .toggle {
            display:inline-flex;
            width:22px;
            min-width:22px;
            cursor:pointer;
            color:#ccc;
            align-items:center;
            justify-content:center;
        }

        .name {
            cursor:pointer;
            flex:0 1 auto;
        }

        .badge {
            margin-left:auto;
            pointer-events:none;
        }

        .children {
            margin-left:18px;
        }

        .payload-box {
            background:#1b2229;
            border:1px solid #303b45;
            border-radius:10px;
            padding:15px;
            white-space:pre-wrap;
            word-break:break-word;
            font-family:Consolas, monospace;
        }

        .meta {
            color:#aeb8c4;
            margin-bottom:15px;
        }

        .button-link,
        .action-btn,
        .json-key-btn {
            background:#5f686f;
            color:white;
            border:0;
            padding:9px 14px;
            text-decoration:none;
            border-radius:8px;
            cursor:pointer;
            font-size:14px;
        }

        .button-link:hover,
        .action-btn:hover,
        .json-key-btn:hover {
            background:#727d85;
        }

        .action-btn.active {
            background:#1f9d55;
            color:white;
            box-shadow:0 0 0 1px rgba(47, 214, 111, .45) inset;
        }

        .action-btn.active:hover {
            background:#168347;
        }

        .json-key-btn {
            padding:6px 10px;
            margin:4px;
            font-size:13px;
        }

        .json-map-row {
            display:flex;
            align-items:center;
            justify-content:space-between;
            gap:10px;
            padding:7px 0;
            border-bottom:1px solid #2d3742;
        }

        .json-map-row:last-child {
            border-bottom:0;
        }

        .json-map-key {
            min-width:0;
            word-break:break-word;
        }

        .json-map-select {
            min-width:170px;
            max-width:190px;
            background:#111820;
            color:white;
            border:1px solid #4a5663;
            border-radius:6px;
            padding:6px;
        }

        .badge {
            color:#aeb8c4;
            font-size:12px;
            margin-left:10px;
        }

        .broker {
            color:#ffd479;
            font-weight:bold;
        }

        .json-box {
            margin-top:15px;
            background:#181818;
            border:1px solid #333;
            border-radius:10px;
            padding:12px;
        }

        .json-box h3 {
            margin:0 0 10px 0;
            font-size:16px;
        }

        .json-path {
            color:#aeb8c4;
            font-size:12px;
            margin-left:6px;
        }

        .json-influx-btn {
            background:#5f686f;
            color:white;
            border:0;
            padding:7px 10px;
            border-radius:8px;
            cursor:pointer;
            font-size:13px;
            margin-left:8px;
        }

        .json-influx-btn:hover {
            background:#727d85;
        }

        .json-influx-btn.active {
            background:#1f9d55;
            color:white;
            box-shadow:0 0 0 1px rgba(47, 214, 111, .45) inset;
        }

        .json-influx-btn.active:hover {
            background:#168347;
        }

        .json-influx-btn.inactive {
            opacity:.82;
        }

        .json-influx-state {
            color:#2fd66f;
            font-size:12px;
            margin-left:6px;
            font-weight:bold;
        }

        .object-primary-actions {
            margin:12px 0 18px 0;
            display:flex;
            gap:10px;
            flex-wrap:wrap;
            align-items:center;
        }

        .expert-actions {
            margin:0 0 16px 0;
            border:1px solid #303b45;
            background:#121922;
            border-radius:10px;
            padding:10px 12px;
        }

        .expert-actions summary {
            cursor:pointer;
            color:#cfe0f5;
            font-size:13px;
            font-weight:bold;
            user-select:none;
        }

        .expert-actions-row {
            margin-top:10px;
            display:flex;
            gap:10px;
            flex-wrap:wrap;
        }

        .object-main-btn {
            background:#2878d6;
        }

        .object-main-btn:hover {
            background:#1e63b2;
        }

        .discovery-toggle {
            display:flex;
            align-items:center;
            gap:8px;
            background:#111820;
            border:1px solid #4a5663;
            border-radius:999px;
            padding:7px 10px;
            color:#dbe6f2;
            font-size:13px;
            white-space:nowrap;
        }

        .discovery-toggle input {
            width:auto;
        }

        .discovery-state {
            color:#aeb8c4;
            font-size:12px;
        }
    </style>
</head>
<body>

<header>
    <h1>MQTT Explorer</h1>
    <input id="search" placeholder="Topic oder Payload suchen...">
    <button type="button" class="action-btn" onclick="expandAllExplorerNodes()">Alles aufklappen</button>
    <button type="button" class="action-btn" onclick="collapseAllExplorerNodes()">Alles einklappen</button>
    <label class="discovery-toggle" title="Legacy UDP→MQTT Discovery: unbekannte UDP Telegramme automatisch im MQTT Monitor sichtbar machen">
        <input type="checkbox" id="udpDiscoveryToggle" onchange="setUdpDiscovery(this.checked)">
        UDP Discovery
        <span id="udpDiscoveryState" class="discovery-state">lädt…</span>
    </label>
</header>

<div class="layout">
    <div class="tree" id="tree"></div>

    <div class="details">
        <h2 id="detailTopic">Kein Topic gewählt</h2>

        <div class="object-primary-actions">
            <button onclick="createObjectFromSelectedMqtt()" class="action-btn object-main-btn">Objekt erstellen / verknüpfen</button>
            <button onclick="copyTopic()" class="action-btn">Topic kopieren</button>
        </div>

        <details class="expert-actions">
            <summary>⚙ Expertenmapping anzeigen</summary>
            <div class="expert-actions-row">
                <button onclick="sendToMqtt2Lox()" class="action-btn">MQTT→Loxone</button>
                <button onclick="sendToMqtt2Udp()" class="action-btn">MQTT→UDP</button>
                <button onclick="sendToMqtt2Knx()" class="action-btn">MQTT→KNX</button>
                <button onclick="sendToUdp2Mqtt()" class="action-btn">UDP→MQTT</button>
            </div>
        </details>
        
        <div style="margin:0 0 15px 0; display:flex; gap:10px; flex-wrap:wrap;">
            <button onclick="toggleFavorite()" class="action-btn">⭐ Favorit</button>
            <button onclick="setAlias()" class="action-btn">🏷️ Alias</button>
            <button id="topicInfluxBtn" onclick="toggleSelectedTopicInflux()" class="action-btn inactive">📈 Topic → Influx</button>
        </div>

        <div id="favoritesBox" class="json-box" style="display:none;"></div>

        <div class="meta" id="detailMeta">-</div>
        <div class="payload-box" id="detailPayload">Links ein Topic auswählen.</div>
        <div id="jsonKeysBox"></div>
        <div id="historyBox" class="json-box" style="display:none;"></div>
    </div>
</div>

<script>
let latestData = {};
let selectedKey = null;
let collapsedNodes = {};
let firstLoad = true;
let pauseRenderUntil = 0;
let treeMouseInside = false;
let selectedPayloadCache = null;
let monitorSettings = { favorites: [], aliases: {} };
let topicConfig = {};
let knxAliasEditGa = "";
let knxAliasDraft = {};
let payloadHistory = {};
let historyLimit = 10;

function esc(str) {
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function pauseTreeRender(ms = 1500) {
    pauseRenderUntil = Date.now() + ms;
}

function jsData(value) {
    return encodeURIComponent(String(value ?? ""));
}

function fromJsData(value) {
    try {
        return decodeURIComponent(String(value || ""));
    } catch (e) {
        return String(value || "");
    }
}

function setupTreeEvents() {
    const treeEl = document.getElementById("tree");
    if (!treeEl || treeEl.dataset.eventsReady === "1") return;

    treeEl.dataset.eventsReady = "1";

    treeEl.addEventListener("mouseenter", () => {
        treeMouseInside = true;
        pauseTreeRender(2500);
    });

    treeEl.addEventListener("mousemove", () => {
        treeMouseInside = true;
        pauseTreeRender(900);
    });

    treeEl.addEventListener("mouseleave", () => {
        treeMouseInside = false;
    });

    treeEl.addEventListener("click", (event) => {
        const toggle = event.target.closest("[data-toggle-path]");
        if (toggle && treeEl.contains(toggle)) {
            event.preventDefault();
            event.stopPropagation();
            toggleNode(fromJsData(toggle.dataset.togglePath));
            return;
        }

        const row = event.target.closest(".node[data-topic-key]");
        if (row && treeEl.contains(row)) {
            event.preventDefault();
            selectTopic(fromJsData(row.dataset.topicKey));
        }
    });
}


function buildTree(data) {
    const root = {};

    for (const key in data) {
        const item = data[key];
        const broker = item.broker || "unbekannt";
        const topic = item.topic || key;

        if (!root[broker]) root[broker] = {};

        const parts = topic.split("/");
        let node = root[broker];

        for (const part of parts) {
            if (!node[part]) node[part] = {};
            node = node[part];
        }

        node.__key = key;
        node.__topic = topic;
    }

    return root;
}

function renderNode(name, node, path, search) {
    const fullPath = path ? path + "/" + name : name;
    const hasTopic = !!node.__key;

    const childrenKeys = Object.keys(node)
        .filter(k => k !== "__topic" && k !== "__key")
        .sort();

    let childHtml = "";

    for (const child of childrenKeys) {
        childHtml += renderNode(child, node[child], fullPath, search);
    }

    const item = hasTopic ? latestData[node.__key] : null;

    const ownMatch =
        !search ||
        fullPath.toLowerCase().includes(search) ||
        (
            item &&
            String(item.payload || "").toLowerCase().includes(search)
        );

    if (!ownMatch && !childHtml) {
        return "";
    }

    const hasChildren = childrenKeys.length > 0;
    const collapsed = collapsedNodes[fullPath] === true;
    const icon = hasChildren ? (collapsed ? "▶" : "▼") : "•";
    const cls = hasTopic ? "node topic" : "node";

    let valueText = "";

    if (item) {
        let val = String(item.payload ?? "");

        if (val.length > 45) {
            val = val.substring(0, 45) + "...";
        }

        valueText = `<span class="badge">${esc(val)}</span>`;
    }

    const brokerClass = path === "" ? " broker" : "";
    const selectedClass = hasTopic && selectedKey === node.__key ? " selected" : "";
    const topicKeyAttr = hasTopic ? ` data-topic-key="${jsData(node.__key)}"` : "";

    let html = `
        <div class="${cls}${selectedClass}"${topicKeyAttr}>
            <span class="toggle" data-toggle-path="${jsData(fullPath)}">${icon}</span>
            <span class="name${brokerClass}">${esc(name)}</span>
            ${valueText}
        </div>
    `;

    if (childHtml && !collapsed) {
        html += `<div class="children">${childHtml}</div>`;
    }

    return html;
}


function collectAllExplorerPaths() {
    const paths = new Set();

    for (const key in latestData) {
        const item = latestData[key] || {};
        const broker = item.broker || "unbekannt";
        const topic = item.topic || key;
        const parts = String(topic || "").split("/").filter(Boolean);

        let path = broker;
        paths.add(path);

        for (const part of parts) {
            path += "/" + part;
            paths.add(path);
        }
    }

    return Array.from(paths);
}

function collapseAllExplorerNodes() {
    pauseTreeRender(1500);
    collapsedNodes = {};
    collectAllExplorerPaths().forEach(path => {
        collapsedNodes[path] = true;
    });
    renderTree();
}

function expandAllExplorerNodes() {
    pauseTreeRender(1500);
    collapsedNodes = {};
    renderTree();
}

function toggleNode(path) {
    pauseTreeRender(1500);
    collapsedNodes[path] = !collapsedNodes[path];
    renderTree();
}

function renderTree() {
    setupTreeEvents();

    const treeEl = document.getElementById("tree");
    const scrollTop = treeEl ? treeEl.scrollTop : 0;
    const search = document.getElementById("search").value.toLowerCase();
    const tree = buildTree(latestData);
    let html = "";

    for (const key of Object.keys(tree).sort()) {
        html += renderNode(key, tree[key], "", search);
    }

    if (treeEl) {
        treeEl.innerHTML = html || "<p>Keine MQTT Daten.</p>";
        treeEl.scrollTop = scrollTop;
    }
}

function getTopicInfluxSettings(topic) {
    const cfg = topicConfig?.[topic] || {};
    return (cfg && typeof cfg === "object") ? cfg : {};
}

function isSelectedTopicInfluxActive() {
    const topic = getSelectedTopicSilent();
    if (!topic) return false;
    return !!getTopicInfluxSettings(topic).influx;
}

function isJsonKeyInfluxActive(jsonKey) {
    const topic = getSelectedTopicSilent();
    if (!topic || !jsonKey) return false;
    const keys = getTopicInfluxSettings(topic).influx_json_keys || [];
    return Array.isArray(keys) && keys.includes(jsonKey);
}

function getJsonKeyInfluxType(jsonKey) {
    const topic = getSelectedTopicSilent();
    if (!topic || !jsonKey) return "auto";
    const types = getTopicInfluxSettings(topic).influx_json_key_types || {};
    return types[jsonKey] || "auto";
}

function getSelectedTopicSilent() {
    if (!selectedKey || !latestData[selectedKey]) return null;
    return latestData[selectedKey].topic;
}

function updateSelectedTopicInfluxButton() {
    const btn = document.getElementById("topicInfluxBtn");
    if (!btn) return;

    const active = isSelectedTopicInfluxActive();
    btn.classList.toggle("active", active);
    btn.classList.toggle("inactive", !active);
    btn.innerText = active ? "✓ Topic → Influx" : "📈 Topic → Influx";
    btn.title = active ? "Ganzes Topic aus Influx entfernen" : "Ganzes Topic für Influx aktivieren";
}

function buildJsonKeyButtons(obj, prefix = "") {
    let html = "";

    for (const key in obj) {
        const value = obj[key];
        const path = prefix ? prefix + "." + key : key;

        if (
            typeof value === "object" &&
            value !== null &&
            !Array.isArray(value)
        ) {
            html += buildJsonKeyButtons(value, path);
        } else {
            let preview = String(value);

            if (preview.length > 30) {
                preview = preview.substring(0, 30) + "...";
            }

            const influxActive = isJsonKeyInfluxActive(path);
            const influxClass = influxActive ? "json-influx-btn active" : "json-influx-btn inactive";
            const influxLabel = influxActive ? "✓ Influx" : "Influx";
            const influxTitle = influxActive ? "Aus Influx entfernen" : "Für Influx aktivieren";
            const influxState = influxActive ? '<span class="json-influx-state">aktiv</span>' : '';
            const influxType = getJsonKeyInfluxType(path);

            html += `
                <div class="json-map-row" data-json-key="${esc(path)}">
                    <div class="json-map-key">
                        <b>${esc(path)}</b><span class="json-path"> = ${esc(preview)}</span>${influxState}
                    </div>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <button type="button" class="${influxClass}" title="${influxTitle}" data-json-influx-key="${encodeURIComponent(path)}" onclick="toggleJsonKeyInflux('${encodeURIComponent(path)}')">${influxLabel}</button>
                        <select class="json-map-select" title="Influx Wert-Typ" onchange="setJsonKeyInfluxType('${encodeURIComponent(path)}', this.value)">
                            <option value="auto" ${influxType === "auto" ? "selected" : ""}>Auto</option>
                            <option value="bool01" ${influxType === "bool01" ? "selected" : ""}>Bool 0/1</option>
                            <option value="number" ${influxType === "number" ? "selected" : ""}>Zahl</option>
                            <option value="text" ${influxType === "text" ? "selected" : ""}>Text</option>
                        </select>
                        <button type="button" class="json-influx-btn object-main-btn" onclick="sendJsonKeyToTarget('${encodeURIComponent(path)}', 'object')">+ Objekt</button>
                        <select class="json-map-select" title="Expertenmapping" onchange="sendJsonKeyToTarget('${encodeURIComponent(path)}', this.value); this.value='';">
                            <option value="">⚙ Mapping…</option>
                            <option value="lox">MQTT → Loxone</option>
                            <option value="udp">MQTT → UDP</option>
                            <option value="knx">MQTT → KNX</option>
                            <option value="udp2mqtt">UDP → MQTT</option>
                        </select>
                    </div>
                </div>
            `;
        }
    }

    return html;
}

function selectTopic(key, fromRefresh = false) {
    if (!key) return;

    if (!fromRefresh) {
        pauseTreeRender(1500);
        selectedPayloadCache = null;
    }

    selectedKey = key;

    document.querySelectorAll("#tree .node.selected").forEach(el => el.classList.remove("selected"));
    const selectedRow = document.querySelector(`#tree .node[data-topic-key="${jsData(key)}"]`);
    if (selectedRow) selectedRow.classList.add("selected");

    const item = latestData[key];

    if (!item) return;

    const payloadCache =
        String(item.topic || "") + "|" +
        String(item.time || "") + "|" +
        String(item.payload || "");

    if (fromRefresh && selectedPayloadCache === payloadCache) {
        return;
    }

    selectedPayloadCache = payloadCache;

    document.getElementById("detailTopic").innerText =
        "[" + (item.broker || "-") + "] " + getDisplayName(item);

    document.getElementById("detailMeta").innerText =
        "Letztes Update: " + (item.time || "-");

    updateSelectedTopicInfluxButton();

    let payload = item.payload;
    let jsonKeysHtml = "";

    try {
        const obj = JSON.parse(payload);
        payload = JSON.stringify(obj, null, 2);

        if (typeof obj === "object" && obj !== null && !Array.isArray(obj)) {
            const buttons = buildJsonKeyButtons(obj);

            if (buttons) {
                jsonKeysHtml = `
                    <div class="json-box">
                        <h3>JSON Keys → Mapping</h3>
                        ${buttons}
                    </div>
                `;
            }
        }
    } catch(e) {
        jsonKeysHtml = "";
    }

    addPayloadHistory(item);
    renderPayloadHistory(item.topic);
    document.getElementById("detailPayload").innerText = payload;
    document.getElementById("jsonKeysBox").innerHTML = jsonKeysHtml;
}

function getSelectedTopic() {
    if (!selectedKey || !latestData[selectedKey]) {
        alert("Bitte erst links ein Topic auswählen.");
        return null;
    }

    return latestData[selectedKey].topic;
}

function sendToMqtt2Lox() {
    const topic = getSelectedTopic();
    if (!topic) return;

    window.location.href = "/mqtt2lox?source_topic=" + encodeURIComponent(topic);
}

function sendToMqtt2Udp() {
    const topic = getSelectedTopic();
    if (!topic) return;

    window.location.href = "/mqtt2udp?source_topic=" + encodeURIComponent(topic);
}

function sendToMqtt2Knx() {
    const topic = getSelectedTopic();
    if (!topic) return;

    window.location.href = "/mqtt2knx?source_topic=" + encodeURIComponent(topic);
}

function sendToUdp2Mqtt() {
    const topic = getSelectedTopic();
    if (!topic) return;

    window.location.href = "/udp2mqtt?mqtt_topic=" + encodeURIComponent(topic);
}

function createObjectFromSelectedMqtt() {
    const topic = getSelectedTopic();
    if (!topic) return;
    let name = topic.split('/').filter(Boolean).slice(-2).join(' ');
    window.location.href = "/objects/edit/new?source=mqtt&value=" + encodeURIComponent(topic) + "&name=" + encodeURIComponent(name);
}

function sendJsonKeyToLox(jsonKey) {
    const topic = getSelectedTopic();
    if (!topic) return;

    window.location.href =
        "/mqtt2lox?source_topic=" + encodeURIComponent(topic) +
        "&payload_mode=json_key" +
        "&json_key=" + jsonKey;
}

function sendJsonKeyToKnx(jsonKey) {
    const topic = getSelectedTopic();
    if (!topic) return;

    window.location.href =
        "/mqtt2knx?source_topic=" + encodeURIComponent(topic) +
        "&payload_mode=json_key" +
        "&json_key=" + jsonKey;
}

function sendJsonKeyToUdp(jsonKey) {
    const topic = getSelectedTopic();
    if (!topic) return;

    window.location.href =
        "/mqtt2udp?source_topic=" + encodeURIComponent(topic) +
        "&payload_mode=json_key" +
        "&json_key=" + encodeURIComponent(jsonKey) +
        "&mapping_alias=" + encodeURIComponent(jsonKey);
}

function sendJsonKeyToTarget(jsonKey, target) {
    if (!target) return;

    if (target === "lox") {
        sendJsonKeyToLox(jsonKey);
    } else if (target === "udp") {
        sendJsonKeyToUdp(jsonKey);
    } else if (target === "knx") {
        sendJsonKeyToKnx(jsonKey);
    } else if (target === "udp2mqtt") {
        sendToUdp2Mqtt();
    }
}

function ensureTopicConfigEntry(topic) {
    if (!topicConfig[topic] || typeof topicConfig[topic] !== "object") {
        topicConfig[topic] = {};
    }
    return topicConfig[topic];
}

function toggleSelectedTopicInflux() {
    const topic = getSelectedTopic();
    if (!topic) return;

    const currentlyActive = isSelectedTopicInfluxActive();
    const nextState = !currentlyActive;

    const fd = new FormData();
    fd.append("topic", topic);
    fd.append("enabled", nextState ? "1" : "0");

    fetch("/monitor/influx_topic", { method:"POST", body:fd })
        .then(r => r.json())
        .then(data => {
            const cfg = ensureTopicConfigEntry(topic);
            cfg.influx = !!data.enabled;
            cfg.enabled = true;
            updateSelectedTopicInfluxButton();
            document.getElementById("detailMeta").innerText = data.message || (nextState ? "Topic für Influx aktiviert ✅" : "Topic für Influx deaktiviert ✅");
        })
        .catch(err => {
            document.getElementById("detailMeta").innerText = "Influx speichern fehlgeschlagen ❌ " + err;
        });
}

function toggleJsonKeyInflux(encodedJsonKey) {
    const topic = getSelectedTopic();
    if (!topic) return;

    const jsonKey = decodeURIComponent(encodedJsonKey || "");
    if (!jsonKey) return;

    const nextState = !isJsonKeyInfluxActive(jsonKey);

    const fd = new FormData();
    fd.append("topic", topic);
    fd.append("json_key", jsonKey);
    fd.append("enabled", nextState ? "1" : "0");

    fetch("/monitor/influx_json_key", { method:"POST", body:fd })
        .then(r => r.json())
        .then(data => {
            const cfg = ensureTopicConfigEntry(topic);
            cfg.influx_json_keys = data.keys || [];
            cfg.influx_json_key_types = data.types || cfg.influx_json_key_types || {};
            cfg.enabled = true;

            selectedPayloadCache = null;
            selectTopic(selectedKey, true);

            document.getElementById("detailMeta").innerText = data.message || (nextState ? "Influx Key aktiviert: " + jsonKey : "Influx Key deaktiviert: " + jsonKey);
        })
        .catch(err => {
            document.getElementById("detailMeta").innerText = "Influx Key Fehler ❌ " + err;
        });
}

function setJsonKeyInfluxType(encodedJsonKey, valueType) {
    const topic = getSelectedTopic();
    if (!topic) return;

    const jsonKey = decodeURIComponent(encodedJsonKey || "");
    if (!jsonKey) return;

    const fd = new FormData();
    fd.append("topic", topic);
    fd.append("json_key", jsonKey);
    fd.append("value_type", valueType || "auto");

    fetch("/monitor/influx_json_key_type", { method:"POST", body:fd })
        .then(r => r.json())
        .then(data => {
            const cfg = ensureTopicConfigEntry(topic);
            cfg.influx_json_key_types = data.types || {};
            cfg.enabled = true;
            document.getElementById("detailMeta").innerText = data.message || ("Influx Typ gespeichert: " + jsonKey);
        })
        .catch(err => {
            document.getElementById("detailMeta").innerText = "Influx Typ Fehler ❌ " + err;
        });
}

function copyTopic() {
    const topic = getSelectedTopic();
    if (!topic) return;

    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(topic).then(() => {
            document.getElementById("detailMeta").innerText =
                "Topic kopiert: " + topic;
        }).catch(() => {
            fallbackCopyTopic(topic);
        });
    } else {
        fallbackCopyTopic(topic);
    }
}

function fallbackCopyTopic(text) {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();

    try {
        document.execCommand("copy");
        document.getElementById("detailMeta").innerText =
            "Topic kopiert: " + text;
    } catch (e) {
        alert("Kopieren nicht möglich: " + text);
    }

    document.body.removeChild(textarea);
}

function refreshData() {
    fetch("/monitor_data?t=" + Date.now(), { cache: "no-store" })
        .then(r => r.json())
        .then(data => {
            latestData = data || {};
            for (const key in latestData) {
                addPayloadHistory(latestData[key]);
            }

            renderFavorites();

            if (firstLoad) {
                const tree = buildTree(latestData);

                function collapseBelowBroker(node, path, level) {
                    for (const key of Object.keys(node)) {
                        if (key === "__topic" || key === "__key") continue;

                        const fullPath = path ? path + "/" + key : key;

                        if (level >= 1) {
                            collapsedNodes[fullPath] = true;
                        }

                        collapseBelowBroker(node[key], fullPath, level + 1);
                    }
                }

                collapseBelowBroker(tree, "", 0);
                firstLoad = false;
            }

            if (Date.now() > pauseRenderUntil && !treeMouseInside) {
                renderTree();
            }

            if (selectedKey && latestData[selectedKey]) {
                selectTopic(selectedKey, true);
            }
        })
        .catch(err => console.log(err));
}


function getAlias(topic) {
    return monitorSettings.aliases?.[topic] || "";
}

function getDisplayName(item) {
    const alias = getAlias(item.topic);
    return alias ? alias + "  —  " + item.topic : item.topic;
}

function loadMonitorSettings() {
    fetch("/monitor_settings?t=" + Date.now(), { cache: "no-store" })
        .then(r => r.json())
        .then(data => {
            monitorSettings = data || { favorites: [], aliases: {} };
            renderFavorites();
            if (!treeMouseInside) {
                renderTree();
            }
        })
        .catch(err => console.log(err));
}

function loadTopicConfig() {
    fetch("/monitor_topic_config?t=" + Date.now(), { cache: "no-store" })
        .then(r => r.json())
        .then(data => {
            topicConfig = data || {};
            updateSelectedTopicInfluxButton();
            if (selectedKey && latestData[selectedKey]) {
                const keepCache = selectedPayloadCache;
                selectedPayloadCache = null;
                selectTopic(selectedKey, true);
                selectedPayloadCache = keepCache;
            }
        })
        .catch(err => console.log(err));
}

function renderFavorites() {
    const box = document.getElementById("favoritesBox");
    const favs = monitorSettings.favorites || [];

    if (!favs.length) {
        box.style.display = "none";
        box.innerHTML = "";
        return;
    }

    let html = "<h3>⭐ Favoriten</h3>";

    for (const topic of favs) {
        let foundKey = null;

        for (const key in latestData) {
            if (latestData[key].topic === topic) {
                foundKey = key;
                break;
            }
        }

        const alias = monitorSettings.aliases?.[topic] || topic;

        html += `
            <button class="json-key-btn"
                    onclick="selectTopic('${esc(foundKey || "")}')">
                ${esc(alias)}
            </button>
        `;
    }

    box.innerHTML = html;
    box.style.display = "block";
}

function toggleFavorite() {
    const topic = getSelectedTopic();
    if (!topic) return;

    const favs = monitorSettings.favorites || [];
    const isFav = favs.includes(topic);

    const form = new FormData();
    form.append("topic", topic);
    form.append("action", isFav ? "remove" : "add");

    fetch("/monitor/favorite", {
        method: "POST",
        body: form
    })
    .then(r => r.json())
    .then(data => {
        monitorSettings.favorites = data.favorites || [];
        renderFavorites();
        document.getElementById("detailMeta").innerText =
            isFav ? "Favorit entfernt: " + topic : "Favorit gespeichert: " + topic;
    });
}

function setAlias() {
    const topic = getSelectedTopic();
    if (!topic) return;

    const oldAlias = monitorSettings.aliases?.[topic] || "";
    const alias = prompt("Alias für dieses Topic:", oldAlias);

    if (alias === null) return;

    const form = new FormData();
    form.append("topic", topic);
    form.append("alias", alias);

    fetch("/monitor/alias", {
        method: "POST",
        body: form
    })
    .then(r => r.json())
    .then(data => {
        monitorSettings.aliases = data.aliases || {};
        renderFavorites();
        renderTree();

        if (selectedKey && latestData[selectedKey]) {
            selectTopic(selectedKey, true);
        }
    });
}

function addPayloadHistory(item) {
    if (!item || !item.topic) return;

    if (!payloadHistory[item.topic]) {
        payloadHistory[item.topic] = [];
    }

    const list = payloadHistory[item.topic];
    const last = list[list.length - 1];

    const value = String(item.payload ?? "");
    const time = item.time || new Date().toLocaleTimeString();

    if (last && last.value === value) return;

    list.push({ time, value });

    if (list.length > historyLimit) {
        list.shift();
    }
}

function renderPayloadHistory(topic) {
    const box = document.getElementById("historyBox");
    const list = payloadHistory[topic] || [];

    if (!list.length) {
        box.style.display = "none";
        box.innerHTML = "";
        return;
    }

    let html = "<h3>📈 Verlauf</h3>";

    for (const entry of list.slice().reverse()) {
        let value = entry.value;

        if (value.length > 120) {
            value = value.substring(0, 120) + "...";
        }

        html += `
            <div style="font-family:Consolas, monospace; font-size:13px; margin:4px 0;">
                <span style="color:#aeb8c4;">${esc(entry.time)}</span>
                → ${esc(value)}
            </div>
        `;
    }

    box.innerHTML = html;
    box.style.display = "block";
}



document.getElementById("search").addEventListener("keyup", renderTree);


function startMqttMonitorStream() {
    if (!window.EventSource) {
        refreshData();
        setInterval(refreshData, 1000);
        return;
    }

    const es = new EventSource("/events/mqtt_monitor");
    es.addEventListener("mqtt_monitor", ev => {
        try {
            const data = JSON.parse(ev.data || "{}");
            latestData = data || {};
            for (const key in latestData) {
                addPayloadHistory(latestData[key]);
            }

            renderFavorites();

            if (firstLoad) {
                const tree = buildTree(latestData);

                function collapseBelowBroker(node, path, level) {
                    for (const key of Object.keys(node)) {
                        if (key === "__topic" || key === "__key") continue;

                        const fullPath = path ? path + "/" + key : key;

                        if (level >= 1) {
                            collapsedNodes[fullPath] = true;
                        }

                        collapseBelowBroker(node[key], fullPath, level + 1);
                    }
                }

                collapseBelowBroker(tree, "", 0);
                firstLoad = false;
            }

            if (Date.now() > pauseRenderUntil && !treeMouseInside) {
                renderTree();
            }

            if (selectedKey && latestData[selectedKey]) {
                selectTopic(selectedKey, true);
            }
        } catch (e) {
            console.log(e);
        }
    });
    es.onerror = () => console.log("MQTT Monitor SSE reconnect...");
}

function loadUdpDiscoveryState() {
    fetch("/udp_discovery_status?t=" + Date.now(), { cache: "no-store" })
        .then(r => r.json())
        .then(data => {
            const on = !!data.legacy_fallback;
            const cb = document.getElementById("udpDiscoveryToggle");
            const label = document.getElementById("udpDiscoveryState");
            if (cb) cb.checked = on;
            if (label) label.textContent = on ? "an" : "aus";
        })
        .catch(() => {
            const label = document.getElementById("udpDiscoveryState");
            if (label) label.textContent = "Fehler";
        });
}

function setUdpDiscovery(enabled) {
    const label = document.getElementById("udpDiscoveryState");
    if (label) label.textContent = enabled ? "schalte an…" : "schalte aus…";

    const form = new FormData();
    form.append("legacy_fallback", enabled ? "1" : "0");

    fetch("/udp_discovery_toggle", { method: "POST", body: form })
        .then(r => r.json())
        .then(data => {
            const on = !!data.legacy_fallback;
            const cb = document.getElementById("udpDiscoveryToggle");
            if (cb) cb.checked = on;
            if (label) label.textContent = on ? "an" : "aus";
            const meta = document.getElementById("detailMeta");
            if (meta) meta.innerText = on
                ? "UDP Discovery aktiv: unbekannte UDP Telegramme werden als MQTT Topics sichtbar."
                : "UDP Discovery aus: nur explizite UDP→MQTT Mappings werden veröffentlicht.";
        })
        .catch(() => {
            if (label) label.textContent = "Fehler";
            loadUdpDiscoveryState();
        });
}

loadUdpDiscoveryState();
loadMonitorSettings();
loadTopicConfig();
startMqttMonitorStream();
</script>

</body>
</html>
"""
    return html


@app.route("/clear_monitor")
def clear_monitor():
    with runtime_context.live_log.lock:
        runtime_context.live_log.entries.clear()
        runtime_context.live_log.version += 1
    bump_sse("log")
    return redirect("/monitor")


@app.route("/clear_log")
def clear_log():
    with runtime_context.live_log.lock:
        runtime_context.live_log.entries.clear()
        runtime_context.live_log.version += 1
    bump_sse("log")
    return redirect("/live_log")




@app.route("/topics_data")
def topics_data():
    config = load_config()
    topic_settings = load_topic_config()

    data = {}

    for idx, (uuid, name) in enumerate(state_mapping.items()):
        topic = build_state_topic(config["mqtt"]["prefix"], name)
        settings = topic_settings.get(topic, {})

        custom_name = settings.get("custom_name", "").strip()

        lookup_topic = custom_name if custom_name else topic
        value = display_values.get(lookup_topic, "")

        safe_key = topic.replace("/", "_")
        data[safe_key] = str(value)

    return data





def mqtt_hub_content():
    config = load_config()
    mqtt = get_effective_mqtt_config(config)
    udp_cfg = config.get("udp_input", {})
    mqtt_monitor_snapshot = get_mqtt_monitor_values()
    cards = [
        ("Loxone Explorer", "/topics2", len(_topic_manager_2_collect_topics()), "Explorer-Ansicht für Loxone Topics: suchen, auswählen, Alias setzen, Influx/Writable schalten und direkt weiter mappen."),
        ("MQTT Monitor", "/monitor", len(mqtt_monitor_snapshot), "Live MQTT Topics ansehen, filtern und kopieren. Discovery kannst du direkt dort ein- und ausschalten."),
        ("MQTT → Loxone", "/mqtt2lox", len(load_mqtt2lox_config()), "MQTT Topics an Loxone Eingänge/Controls schicken."),
        ("MQTT → UDP", "/mqtt2udp", len(load_mqtt2udp_config()), "MQTT Topics als UDP Telegramme senden."),
        ("UDP → MQTT", "/udp2mqtt", len(load_udp2mqtt_config()), "UDP Telegramme als MQTT Topics veröffentlichen und gezielt mappen."),
        ("MQTT → KNX", "/mqtt2knx", len(load_mqtt2knx_config()), "MQTT Topics direkt auf KNX Gruppenadressen senden."),
        ("Influx Explorer", "/influx_explorer", "DB", "InfluxDB direkt aus MQTT2Lox verwalten: Topics finden, prüfen und gezielt löschen."),
        ("Objektmanager", "/objects", len(load_objects_config()), "Datenpunkte aus MQTT, Loxone, KNX, UDP und Influx zu einer Smart-Home-Objektansicht bündeln."),
    ]
    html_cards = ""
    for title, url, count, desc in cards:
        if title == "UDP → MQTT" and udp_cfg.get("enabled"):
            status = "aktiv"
        else:
            status = str(count)
        html_cards += f"""
        <a class="mqtt-card" href="{escape(url)}">
            <div class="mqtt-card-title">{escape(title)}</div>
            <div class="mqtt-card-count">{escape(status)}</div>
            <div class="small">{escape(desc)}</div>
        </a>"""
    return f"""
<!doctype html><html><head><title>MQTT Hub</title><style>
body {{ font-family:Arial; background:#202830; color:#f4f7fb; margin:30px; }}
a {{ color:inherit; text-decoration:none; }}
.card {{ background:#1b2229; border:1px solid #303b45; border-radius:12px; padding:18px; margin-bottom:16px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:14px; }}
.mqtt-card {{ background:#1b2229; border:1px solid #303b45; border-radius:12px; padding:18px; display:block; transition:.12s ease; }}
.mqtt-card:hover {{ background:#25303a; border-color:#5f686f; transform:translateY(-1px); }}
.mqtt-card-title {{ font-size:20px; font-weight:800; margin-bottom:10px; }}
.mqtt-card-count {{ font-size:30px; font-weight:900; margin-bottom:6px; color:#fff; }}
.small {{ color:#aeb8c4; font-size:13px; line-height:1.35; }} .mini-row {{ display:flex; gap:6px; align-items:center; }} .mini-row input {{ flex:1; }} .mini-btn {{ padding:9px 10px; white-space:nowrap; }}
.badge {{ display:inline-block; padding:4px 8px; border-radius:999px; background:#2a333d; color:#dbe6f2; font-size:12px; }}
</style></head><body>
<h1>MQTT Hub</h1>
<div class="card">
    <span class="badge">Broker: {escape(str(mqtt.get('host','-')))}:{escape(str(mqtt.get('port','-')))}</span>
    <span class="badge">UDP Eingang: {escape('aktiv' if udp_cfg.get('enabled') else 'aus')}</span>
    <p class="small">Alle MQTT-Brücken an einem Ort: Loxone, UDP, KNX, Objektmanager und Monitor. UDP Discovery schaltest du direkt im MQTT Monitor ein und aus.</p>
</div>
<div class="grid">{html_cards}</div>
</body></html>"""


@app.route('/mqtt')
def mqtt_hub():
    return mqtt_hub_content()


def knx_hub_content():
    knx_cfg = load_knx_config()
    monitor_values = get_knx_monitor_values()
    cards = [
        ("MQTT → KNX", "/mqtt2knx", len(load_mqtt2knx_config()), "MQTT Topics direkt auf KNX Gruppenadressen senden."),
        ("KNX → MQTT", "/knx2mqtt", len(load_knx2mqtt_config()), "KNX Telegramme als MQTT Topics veröffentlichen."),
        ("UDP → KNX", "/udp2knx", len(load_udp2knx_config()), "UDP Telegramme direkt auf KNX Gruppenadressen senden."),
        ("KNX → Loxone", "/knx2lox", len(load_knx2lox_config()), "KNX Telegramme direkt an Loxone Eingänge/Controls schicken."),
        ("KNX Gateway", "/knx_settings_embed", 1 if knx_cfg.get("enabled") else 0, "Gateway, Tunneling/Routing und lokale Schnittstelle einstellen."),
        ("KNX Monitor", "/knx_monitor", len(monitor_values), "Live Telegramme ansehen und debuggen."),
    ]
    html_cards = ""
    for title, url, count, desc in cards:
        status = "aktiv" if title == "KNX Gateway" and knx_cfg.get("enabled") else str(count)
        html_cards += f'''
        <a class="knx-card" href="{escape(url)}">
            <div class="knx-card-title">{escape(title)}</div>
            <div class="knx-card-count">{escape(status)}</div>
            <div class="small">{escape(desc)}</div>
        </a>'''
    return f'''
<!doctype html><html><head><title>KNX Hub</title><style>
body {{ font-family:Arial; background:#202830; color:#f4f7fb; margin:30px; }}
a {{ color:inherit; text-decoration:none; }}
.card {{ background:#1b2229; border:1px solid #303b45; border-radius:12px; padding:18px; margin-bottom:16px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:14px; }}
.knx-card {{ background:#1b2229; border:1px solid #303b45; border-radius:12px; padding:18px; display:block; transition:.12s ease; }}
.knx-card:hover {{ background:#25303a; border-color:#5f686f; transform:translateY(-1px); }}
.knx-card-title {{ font-size:20px; font-weight:800; margin-bottom:10px; }}
.knx-card-count {{ font-size:30px; font-weight:900; margin-bottom:6px; color:#fff; }}
.small {{ color:#aeb8c4; font-size:13px; line-height:1.35; }} .mini-row {{ display:flex; gap:6px; align-items:center; }} .mini-row input {{ flex:1; }} .mini-btn {{ padding:9px 10px; white-space:nowrap; }}
.badge {{ display:inline-block; padding:4px 8px; border-radius:999px; background:#2a333d; color:#dbe6f2; font-size:12px; }}
</style></head><body>
<h1>KNX Hub</h1>
<div class="card">
    <span class="badge">Gateway: {escape('aktiv' if knx_cfg.get('enabled') else 'aus')}</span>
    <p class="small">Alle KNX Brücken an einem Ort: MQTT, UDP, Loxone, Gateway und Monitor. Der KNX Monitor bleibt zusätzlich direkt in der Sidebar erreichbar.</p>
</div>
<div class="grid">{html_cards}</div>
</body></html>'''


@app.route('/knx')
def knx_hub():
    return knx_hub_content()


def mapping_page_style():
    return '''<style>
body { font-family:Arial; background:#202830; color:#f4f7fb; margin:30px; overflow:auto; }
a { color:inherit; } .card { background:#1b2229; border:1px solid #303b45; border-radius:8px; padding:18px; margin-bottom:16px; }
table { width:100%; min-width:1000px; border-collapse:collapse; background:#151c23; table-layout:fixed; }
th,td { border:1px solid #303b45; padding:7px; overflow-wrap:anywhere; } th { background:#2a333d; }
input[type=text], select { width:100%; background:#111820; color:white; border:1px solid #4a5663; padding:6px; box-sizing:border-box; }
input[type=checkbox] { width:16px; height:16px; } button, .button-link { background:#5f686f; color:white; padding:9px 14px; border:0; border-radius:8px; cursor:pointer; font-size:14px; text-decoration:none; display:inline-flex; align-items:center; }
button:hover, .button-link:hover { background:#727d85; } .small { color:#aeb8c4; font-size:13px; } .button-row { display:flex; gap:9px; flex-wrap:wrap; margin-top:14px; }
tr.problem-row:target td { background:rgba(255,184,107,.22); box-shadow:inset 4px 0 0 #ffb86b; }
</style>'''


def knx_ga_script():
    return r'''<script>
function formatKnxGroupAddress(value) { let v=String(value||"").trim().replace(/\s+/g,""); if(!v) return ""; if(v.includes("/")){let p=v.split("/").map(x=>x.trim()).filter(Boolean); if(p.length>=3)return p[0]+"/"+p[1]+"/"+p[2]; if(p.length===2){let t=p[1].replace(/\D/g,""); if(t.length>=2)return p[0]+"/"+t[0]+"/"+t.slice(1); return p[0]+"/"+p[1];} if(p.length===1)v=p[0];} let d=v.replace(/\D/g,""); if(d.length<=1)return d; if(d.length===2)return d[0]+"/"+d[1]; return d[0]+"/"+d[1]+"/"+d.slice(2); }
document.addEventListener("blur",e=>{ if(e.target.classList.contains("knx-ga-input")) e.target.value=formatKnxGroupAddress(e.target.value);},true);
document.addEventListener("submit",()=>{ document.querySelectorAll(".knx-ga-input").forEach(i=>i.value=formatKnxGroupAddress(i.value));},true);
</script>'''


# -----------------------------------------------------------------------------
# Legacy: Shared Explorer Layout auch für KNX/UDP Mapping-Seiten
# -----------------------------------------------------------------------------
def mapping_safe_key(value):
    return clean_topic(str(value or "")) or "ohne_name"


def mapping_dpt_select(name, selected="1.001"):
    selected = str(selected or "1.001")
    opts = [
        ("1.001", "1.001 Schalten"),
        ("1.002", "1.002 Bool"),
        ("5.001", "5.001 Prozent"),
        ("5.010", "5.010 0-255"),
        ("9.001", "9.001 Temperatur"),
    ]
    return template_service.build_select_html(name, opts, selected)


def mapping_payload_select(name, selected="raw"):
    selected = str(selected or "raw")
    opts = [("raw", "Raw Payload"), ("json_key", "JSON Key")]
    return template_service.build_select_html(name, opts, selected)


def get_mapping_group_set(item, fallback_set="Importiert"):
    group_name = str(item.get("group", "") or "").strip() or "Ohne Gruppe"
    set_name = str(item.get("set_name", "") or "").strip()
    if not set_name:
        set_name = str(fallback_set or "Importiert").strip() or "Importiert"
    group_key = mapping_safe_key(group_name)
    set_key = mapping_safe_key(group_name + "__" + set_name)
    return group_name, set_name, group_key, set_key



def render_shared_mapping_explorer_page(page_id, title, description, back_url, form_action, mappings, build_card_fn, build_new_card_fn, data_url, value_id_prefix, time_id_prefix, datalist_html="", extra_script=""):
    tree = {}
    known_groups = set()
    for i, item in enumerate(mappings):
        if not isinstance(item, dict): item = {}
        fallback = item.get("mapping_alias") or item.get("source_topic") or item.get("mqtt_topic") or item.get("loxone_io") or item.get("group_address") or f"Mapping {i+1}"
        group_name, set_name, group_key, set_key = get_mapping_group_set(item, fallback)
        alias = str(item.get("mapping_alias", "") or fallback or f"Mapping {i+1}").strip()
        known_groups.add(group_name)
        tree.setdefault(group_key, {"name": group_name, "sets": {}})
        tree[group_key]["sets"].setdefault(set_key, {"name": set_name, "rows": []})
        tree[group_key]["sets"][set_key]["rows"].append({"index": i, "alias": alias, "item": item})
    tree_html = ""
    for group_key in sorted(tree.keys(), key=lambda x: tree[x]["name"].casefold()):
        group = tree[group_key]
        total_rows = sum(len(st["rows"]) for st in group["sets"].values())
        tree_html += f"""<div class="tree-group" data-tree-group="{escape(group_key)}" data-search="{escape(group['name'])}">
    <div class="tree-group-title" onclick="toggleTreeGroup('{escape(group_key)}')"><span id="tree_arrow_{escape(group_key)}">▾</span><span>{escape(group['name'])}</span><span class="tree-count">{total_rows}</span></div>
    <div id="tree_body_{escape(group_key)}" class="tree-body">"""
        for set_key in sorted(group["sets"].keys(), key=lambda x: group["sets"][x]["name"].casefold()):
            st = group["sets"][set_key]
            rows = st["rows"]
            search = " ".join([group["name"], st["name"]] + [r["alias"] for r in rows])
            tree_html += f"""<div class="tree-set" data-set-link="{escape(set_key)}" data-search="{escape(search)}">
    <div class="tree-set-main" onclick="showSet('{escape(set_key)}')"><span>▸ {escape(st['name'])}</span><span class="tree-count">{len(rows)}</span></div>
    <div class="tree-subitems" data-subitems-for="{escape(set_key)}">"""
            for r in rows:
                tree_html += f"""<div class="tree-subitem" data-row-index="{r['index']}" data-search="{escape(search)}" onclick="selectTreeRow('{escape(set_key)}', {r['index']})">↳ {escape(r['alias'])}<span id="{escape(page_id)}_tree_value_{r['index']}" class="tree-value empty"></span></div>"""
            tree_html += "</div></div>"
        tree_html += "</div></div>"
    if not tree_html:
        tree_html = '<div class="empty-tree">Noch keine Mappings. Rechts ein neues Set anlegen und speichern.</div>'
    panels = ""
    next_index = len(mappings)
    first_panel = True
    for group_key in sorted(tree.keys(), key=lambda x: tree[x]["name"].casefold()):
        group = tree[group_key]
        for set_key in sorted(group["sets"].keys(), key=lambda x: group["sets"][x]["name"].casefold()):
            st = group["sets"][set_key]
            active = " active" if first_panel else ""
            first_panel = False
            rows_html = "".join(build_card_fn(r["index"], r["item"], group["name"], st["name"], set_key, r["alias"]) for r in st["rows"])
            rows_html += f'<div id="extra_wrap_{escape(set_key)}" style="display:none;">' + build_new_card_fn(next_index, group["name"], st["name"], set_key) + '</div>'
            panels += f"""
<section class="set-panel{active}" data-set-panel="{escape(set_key)}">
    <div class="card compact-card"><div class="set-head lox-style-head"><div><label>Gruppe</label><input type="text" data-set-header-group="{escape(set_key)}" value="{escape(group['name'] if group['name'] != 'Ohne Gruppe' else '')}" list="mappingGroups" oninput="syncPanelGroup('{escape(set_key)}', this.value)"></div><div><label>Name / Pseudonym</label><input type="text" data-set-header-name="{escape(set_key)}" value="{escape(st['name'])}" oninput="syncPanelSetName('{escape(set_key)}', this.value)"></div><div><button type="button" title="Name/Gruppe auf alle Mappings übernehmen" onclick="syncPanelHeader('{escape(set_key)}')">✎</button></div><div class="small">Ein Set kann mehrere Datenpunkte eines Gerätes enthalten, z.B. Schalten, Temperatur, Status oder Leistung.</div><div><button type="button" class="delete-btn" onclick="deleteWholeSet('{escape(set_key)}')">Set löschen</button></div></div></div>
    <div class="card"><div class="mapping-header"><div><h2 style="margin:0;">Mappings in diesem Set</h2><div class="small">{len(st['rows'])} gespeicherte Mapping(s)</div></div><button type="button" onclick="showExtraMapping('{escape(set_key)}')">＋ Topic / Mapping hinzufügen</button></div><div class="mapping-list">{rows_html}</div><div class="info-box small">Aktiv = Mapping aktiv · Letzter Wert/Zeit werden live aktualisiert · Gruppe und Name bilden links den Explorer-Baum.</div></div>
</section>"""
            next_index += 1
    new_active = " active" if first_panel else ""
    panels += f"""
<section class="set-panel{new_active}" data-set-panel="__new__"><div class="card compact-card"><div class="set-head lox-style-head"><div><label>Gruppe</label><input type="text" data-set-header-group="__new__" value="" list="mappingGroups" placeholder="z.B. Strom Zähler" oninput="syncPanelGroup('__new__', this.value)"></div><div><label>Name / Pseudonym</label><input type="text" data-set-header-name="__new__" value="Neues {escape(title)} Set" oninput="syncPanelSetName('__new__', this.value)"></div><div></div><div class="small">Neues Gerät/Objekt anlegen. Danach erscheint es links im Explorer.</div><div></div></div></div><div class="card"><div class="mapping-header"><div><h2 style="margin:0;">Erstes Mapping</h2><div class="small">Nach dem Speichern kannst du weitere Topics im Set ergänzen.</div></div></div><div class="mapping-list">{build_new_card_fn(next_index, '', f'Neues {title} Set', '__new__')}</div></div></section>"""
    mapping_groups_html = '<datalist id="mappingGroups">' + ''.join(f'<option value="{escape(g)}">' for g in sorted([g for g in known_groups if g and g != "Ohne Gruppe"], key=lambda x: x.casefold())) + '</datalist>'
    extra = (extra_script or "") + "\n" + knx_ga_script().replace("<script>", "").replace("</script>", "") + """
// Legacy: Gruppe/Set-Name robust speichern.
// Wichtig: nicht per CSS.escape in Attribut-Selektoren suchen, sondern per getAttribute vergleichen.
// Sonst greifen Sonderzeichen in Set-Namen wie '/', Leerzeichen usw. nicht zuverlässig.
function findByAttr(attr, value){
    return Array.from(document.querySelectorAll('[' + attr + ']')).filter(function(el){
        return el.getAttribute(attr) === String(value);
    });
}
function syncPanelGroup(k, val){
    findByAttr('data-group-sync', k).forEach(function(x){ x.value = val || ''; });
}
function syncPanelSetName(k, val){
    findByAttr('data-set-sync', k).forEach(function(x){ x.value = val || ''; });
}
function syncPanelHeader(k){
    var g = findByAttr('data-set-header-group', k)[0];
    var n = findByAttr('data-set-header-name', k)[0];
    syncPanelGroup(k, g ? g.value : '');
    syncPanelSetName(k, n ? n.value : '');
}
function syncAllPanelHeaders(){
    document.querySelectorAll('[data-set-panel]').forEach(function(p){
        syncPanelHeader(p.getAttribute('data-set-panel'));
    });
}

// Legacy: Neues Set aus dem aktuell angeklickten Explorer-Eintrag vorbereiten.
// Das kopiert gezielt die Quell-Adresse/Topic-Daten in das __new__ Panel,
// statt nur ein leeres neues Set zu öffnen.
function firstNamedInput(panel, baseName){
    if(!panel) return null;
    return Array.from(panel.querySelectorAll('input[name], select[name]')).find(function(el){
        return (el.getAttribute('name') || '').replace(/_\\d+$/, '') === baseName;
    }) || null;
}
function copyNamedValue(fromPanel, toPanel, baseName){
    var src = firstNamedInput(fromPanel, baseName);
    var dst = firstNamedInput(toPanel, baseName);
    if(src && dst && src.value !== undefined){ dst.value = src.value || ''; }
}
function createNewSetFromCurrentSelection(){
    var current = document.querySelector('[data-set-panel].active');
    var newPanel = findByAttr('data-set-panel', '__new__')[0];
    if(!newPanel){ showSet('__new__'); return; }

    if(current && current !== newPanel){
        var sourcePanel = getSelectedRowPanel(current);
        var currentKey = current.getAttribute('data-set-panel');
        var currentGroup = findByAttr('data-set-header-group', currentKey)[0];
        var newGroup = findByAttr('data-set-header-group', '__new__')[0];
        if(currentGroup && newGroup){
            newGroup.value = currentGroup.value || '';
            syncPanelGroup('__new__', newGroup.value);
        }

        ['source_topic','mqtt_topic','udp_topic','group_address','dpt','payload_mode','json_key'].forEach(function(name){
            copyNamedValue(sourcePanel, newPanel, name);
        });
    }

    // Legacy: URL-/Explorer-Übernahme immer anwenden, auch wenn gerade kein bestehendes Set aktiv ist.
    // Besonders wichtig für KNX→MQTT: /knx2mqtt?group_address=1/2/10 soll direkt das neue Mapping öffnen.
    try {
        var params = new URLSearchParams(window.location.search || '');
        ['group_address','source_topic','mqtt_topic','udp_topic','dpt','payload_mode','json_key'].forEach(function(name){
            var dst = firstNamedInput(newPanel, name);
            var v = params.get(name);
            if(dst && v){ dst.value = v; }
        });
    } catch(e) {}

    var setValue = '';
    var gaEl = firstNamedInput(newPanel, 'group_address');
    if(gaEl && gaEl.value && typeof formatKnxGroupAddress === 'function'){
        gaEl.value = formatKnxGroupAddress(gaEl.value);
    }
    ['group_address','source_topic','mqtt_topic','udp_topic'].some(function(name){
        var el = firstNamedInput(newPanel, name);
        if(el && el.value){ setValue = el.value; return true; }
        return false;
    });
    var newName = findByAttr('data-set-header-name', '__new__')[0];
    if(newName && setValue){
        newName.value = setValue;
        syncPanelSetName('__new__', setValue);
    }

    var alias = firstNamedInput(newPanel, 'mapping_alias');
    if(alias && !alias.value){ alias.value = 'Neues Mapping'; }

    markPanelRowsForSave(newPanel);
    showSet('__new__');
    setTimeout(function(){
        var focusEl = firstNamedInput(newPanel, 'mapping_alias') || firstNamedInput(newPanel, 'group_address') || firstNamedInput(newPanel, 'source_topic');
        if(focusEl){ focusEl.focus(); try{ focusEl.select(); }catch(e){} }
    }, 50);
}

function markPanelRowsForSave(panel){
    if(!panel) return;
    panel.querySelectorAll('input[name^=save_row_]').forEach(function(x){ x.value = '1'; });
}
function showExtraMapping(k){
    var e = document.getElementById('extra_wrap_' + k);
    if(e){
        e.style.display = 'block';
        markPanelRowsForSave(e);
    }
    syncPanelHeader(k);
}
function deleteWholeSet(k){
    findByAttr('data-set-panel', k).forEach(function(panel){
        panel.querySelectorAll('input[type=checkbox][name^=delete_]').forEach(function(x){ x.checked = true; });
        panel.style.display = 'none';
    });
}
document.addEventListener('DOMContentLoaded', function(){
    var f = document.getElementById('mappingForm');
    if(f){ f.addEventListener('submit', syncAllPanelHeaders, true); }
    document.querySelectorAll('button[type="submit"]').forEach(function(btn){
        btn.addEventListener('click', syncAllPanelHeaders, true);
    });
    syncAllPanelHeaders();
});
"""
    hub_label = "KNX Hub" if str(back_url).rstrip("/") == "/knx" else "MQTT Hub"
    script = shared_mapping_explorer_script(page_id, f"{page_id}_tree_collapsed_v32", f"{page_id}_subitems_collapsed_v32", f"{page_id}_selected_set_v32", data_url, f"{page_id}_card_", value_id_prefix, time_id_prefix, f"{page_id}_tree_value_", f"{page_id}_current_value_", f"{page_id}_current_time_", extra)
    return f"""<!doctype html><html><head><title>{escape(title)} Mapping Explorer</title><style>
:root {{ --bg:#202830; --panel:#1b2229; --border:#303b45; --muted:#aeb8c4; --text:#f4f7fb; --accent:#5f686f; --green:#1fa342; }}
* {{ box-sizing:border-box; }} html,body {{ height:100%; overflow:hidden; }} body {{ font-family:Arial,sans-serif; background:var(--bg); color:var(--text); margin:0; }} header {{ height:74px; background:#1b2229; border-bottom:1px solid var(--border); display:flex; align-items:center; justify-content:space-between; gap:14px; padding:14px 20px; }} h1 {{ margin:0; font-size:28px; }} .header-tools {{ display:flex; gap:8px; align-items:center; }} .page {{ display:grid; grid-template-columns:330px minmax(0,1fr); height:calc(100vh - 74px); overflow:hidden; }} .sidebar {{ background:#111820; border-right:1px solid var(--border); overflow:auto; padding:14px; }} .editor {{ overflow:auto; padding:18px; }} .editor-inner {{ width:max(100%, 1080px); padding-right:18px; }} button,a.button-link {{ background:var(--accent); color:white; padding:9px 13px; text-decoration:none; border:none; border-radius:8px; cursor:pointer; display:inline-block; font-size:14px; font-weight:700; }} button:hover,a.button-link:hover {{ background:#737d86; }} .save-bottom {{ background:var(--green); min-width:230px; font-size:16px; padding:13px 20px; }} .delete-btn {{ background:transparent; border:1px solid #e05050; color:#ff7777; }} input[type=text],select {{ width:100%; background:#0f1720; color:white; border:1px solid #4a5663; border-radius:6px; padding:8px; font-size:14px; }} input[type=checkbox] {{ width:18px; height:18px; accent-color:#35c75a; }} label {{ display:block; color:#cfe0f5; font-size:12px; margin-bottom:4px; }} .small {{ color:#cfe0f5; font-size:13px; line-height:1.35; }} .tree-tools {{ margin-bottom:12px; }} .tree-group-title {{ padding:8px 10px; cursor:pointer; font-weight:900; color:#ffe66a; display:flex; justify-content:space-between; gap:8px; align-items:center; }} .tree-body {{ padding-left:18px; }} .collapsed {{ display:none !important; }} .tree-set-main {{ padding:8px 10px; cursor:pointer; display:flex; justify-content:space-between; border-radius:8px; }} [data-set-link].active .tree-set-main {{ background:#6f7a81; color:#fff; }} .tree-count {{ background:#2f4156; color:#d8eaff; border-radius:999px; padding:2px 8px; font-size:12px; }} .tree-subitems {{ padding:2px 0 4px 22px; }} .tree-subitem {{ padding:5px 0; color:#dce6ef; font-size:12px; cursor:pointer; display:flex; justify-content:space-between; }} .tree-subitem.active-row {{ background:rgba(95,104,111,.35); border-radius:6px; padding-left:6px; }} .tree-value {{ color:#24e36d; background:#143b26; border-radius:6px; padding:1px 6px; font-family:Consolas,monospace; }} .tree-value.empty,.hidden-by-search {{ display:none !important; }} .empty-tree {{ color:var(--muted); padding:14px; }} .card {{ background:#1b2229; border:1px solid var(--border); border-radius:12px; padding:16px; margin-bottom:16px; }} .set-panel {{ display:none; }} .set-panel.active {{ display:block; }} .set-head.lox-style-head {{ display:grid; grid-template-columns:230px 280px 46px 1fr auto; gap:12px; align-items:end; }} .mapping-header {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; }} .mapping-list {{ display:grid; gap:14px; }} .mapping-row,.mapping-card {{ background:#121922; border:1px solid #303b45; border-radius:12px; padding:14px; }} .mapping-alias {{ display:grid; grid-template-columns:1fr auto; gap:12px; align-items:end; margin-bottom:12px; padding-bottom:12px; border-bottom:1px solid var(--border); }} .mapping-card-top.shared-live-card {{ display:grid; grid-template-columns:240px 42px repeat(4,minmax(150px,1fr)) auto; gap:12px; align-items:end; margin-bottom:12px; }} .current-value-box {{ border:1px solid var(--border); border-radius:10px; background:rgba(255,255,255,.02); padding:10px 12px; min-height:82px; display:flex; flex-direction:column; justify-content:center; }} .current-value-title {{ color:var(--muted); font-size:12px; margin-bottom:7px; }} .current-value-main {{ color:#35d05b; font-size:22px; font-weight:900; line-height:1.1; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }} .current-value-main.empty {{ color:var(--muted); }} .current-value-time {{ color:var(--muted); font-size:12px; margin-top:8px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }} .mapping-card-bottom.shared-live-bottom {{ display:grid; grid-template-columns:repeat(6,minmax(120px,1fr)); gap:12px; align-items:end; }} .mapping-actions {{ display:flex; gap:8px; align-items:center; justify-content:flex-end; }} .mapping-grid {{ display:grid; grid-template-columns:80px 1.5fr 1fr 1fr 1fr 90px 90px; gap:10px; align-items:end; }} .mapping-grid.wide {{ grid-template-columns:80px 1.4fr 1fr 1fr 1fr 1fr 90px 90px; }} .mapping-grid.mqtt-knx {{ grid-template-columns:70px 1.4fr 1fr .9fr 1fr 1fr 70px 105px 90px 130px; }} .live-pill {{ background:#101820; border:1px solid #31404f; border-radius:8px; padding:8px; min-height:37px; font-family:Consolas,monospace; }} .live-pill.empty {{ color:var(--muted); }} .info-box {{ margin-top:14px; border:1px solid #24456f; background:#12233b; border-radius:9px; padding:12px 14px; }} .form-bottom {{ position:sticky; bottom:0; background:rgba(32,40,48,.96); border-top:1px solid var(--border); padding:14px 0; display:flex; justify-content:flex-end; }} @media (max-width:1100px) {{ .page {{ grid-template-columns:1fr; }} .sidebar {{ display:none; }} html,body {{ overflow:auto; }} .editor {{ overflow:visible; }} .mapping-grid,.mapping-grid.wide,.mapping-grid.mqtt-knx,.mapping-card-top.shared-live-card,.mapping-card-bottom.shared-live-bottom,.set-head.lox-style-head,.mapping-alias {{ grid-template-columns:1fr; }} }}
</style></head><body><header><div><h1>{escape(title)} Mapping Explorer</h1><div class="small">{description}</div></div><div class="header-tools"><a class="button-link" href="{escape(back_url)}">← Zurück zum {escape(hub_label)}</a><button type="button" onclick="expandAllTree()">Alles aufklappen</button><button type="button" onclick="collapseAllTree()">Alles einklappen</button></div></header><div class="page"><aside class="sidebar"><div class="tree-tools"><input id="treeSearch" type="text" placeholder="Suchen..." oninput="filterTree()"><button type="button" style="width:100%; margin-top:9px; justify-content:center;" onclick="createNewSetFromCurrentSelection()">＋ Neues Set erstellen</button></div>{tree_html}</aside><main class="editor"><div class="editor-inner"><form id="mappingForm" method="post" action="{escape(form_action)}">{panels}<input type="hidden" name="count" value="{next_index+1}">{mapping_groups_html}{datalist_html}<div class="form-bottom"><button type="submit" class="save-bottom">💾 Speichern</button></div></form></div></main></div>{script}</body></html>"""





def render_shared_live_mapping_card(page_id, i, group_name, set_name, set_key, alias, enabled=True, current_value='-', current_time='-', top_html='', bottom_html='', actions_html='', is_new=False):
    """Shared Mapping-Card im MQTT→Loxone-Stil mit großem Live-Wert links."""
    checked = 'checked' if enabled else ''
    current_text = str(current_value if current_value not in [None, ''] else '-')
    time_text = str(current_time if current_time not in [None, ''] else '-')
    empty_cls = ' empty' if current_text == '-' else ''
    group_hidden = f'<input type="hidden" name="group_{i}" value="{escape(group_name if group_name != "Ohne Gruppe" else "")}" data-group-sync="{escape(set_key)}">'
    set_hidden = f'<input type="hidden" name="set_name_{i}" value="{escape(set_name)}" data-set-sync="{escape(set_key)}">'
    # Legacy: Neue/zusätzliche Mapping-Karten werden erst gespeichert, wenn sie wirklich geöffnet/benutzt wurden.
    # Sonst erzeugt jeder Speichern-Klick aus dem versteckten __new__-Panel wieder leere "Neues Mapping"-Einträge.
    save_marker = '0' if is_new else '1'
    save_hidden = f'<input type="hidden" name="save_row_{i}" value="{save_marker}" data-save-marker="{i}">'
    return f"""
<div class="mapping-card" id="{escape(page_id)}_card_{i}">
    {save_hidden}
    {group_hidden}
    {set_hidden}
    <div class="mapping-alias">
        <div>
            <label>Datenpunkt / Alias</label>
            <input type="text" name="mapping_alias_{i}" value="{escape(str(alias or ''))}" placeholder="z.B. Temperatur, Schaltzustand, Leistung">
        </div>
        <div class="small">Name erscheint links unter dem Set</div>
    </div>
    <div class="mapping-card-top shared-live-card">
        <div class="current-value-box">
            <div class="current-value-title">Aktueller Wert</div>
            <div class="current-value-main{empty_cls}" id="{escape(page_id)}_current_value_{i}">{escape(current_text)}</div>
            <div class="current-value-time" id="{escape(page_id)}_current_time_{i}">Zuletzt: {escape(time_text)}</div>
        </div>
        <div>
            <label>Aktiv</label>
            <input type="checkbox" name="enabled_{i}" {checked}>
        </div>
        {top_html}
        <div class="mapping-actions">{actions_html}</div>
    </div>
    <div class="mapping-card-bottom shared-live-bottom">
        {bottom_html}
    </div>
</div>
"""

def shared_mapping_set_header(i, group_name, set_name, set_key, alias):
    return f'''<div class="set-head"><div><h2 style="margin:0 0 4px 0;">{escape(set_name)}</h2><div class="small">{escape(alias)}</div></div><div><button type="button" class="delete-btn" onclick="markDeleteAndHide({i})">Mapping löschen</button></div></div>
<div class="set-grid">
    <div><label>Gruppe</label><input type="text" name="group_{i}" value="{escape(group_name)}" data-group-sync="{escape(set_key)}" oninput="syncSetGroup('{escape(set_key)}', this.value)"></div>
    <div><label>Set Name</label><input type="text" name="set_name_{i}" value="{escape(set_name)}" data-set-sync="{escape(set_key)}" oninput="syncSetName('{escape(set_key)}', this.value)"></div>
    <div><label>Anzeigename</label><input type="text" name="mapping_alias_{i}" value="{escape(alias)}" placeholder="optional"></div>
</div>
<input type="checkbox" id="delete_{i}" name="delete_{i}" style="display:none;">
'''



@app.route('/udp2knx')
def udp2knx():
    mappings = load_udp2knx_config()
    prefill_source_topic = request.args.get('source_topic', '')
    prefill_group_address = knx_service.normalize_knx_ga(request.args.get('group_address', ''))

    def card(i, item, group_name, set_name, set_key, alias):
        last = get_udp_last_seen("udp2knx", item.get('source_topic',''))
        top = f'''<div><label>UDP Topic</label><input type="text" name="source_topic_{i}" value="{escape(str(item.get('source_topic','')))}" placeholder="topic vor Doppelpunkt"></div><div><label>KNX GA</label><input class="knx-ga-input" type="text" name="group_address_{i}" value="{escape(str(item.get('group_address','')))}" placeholder="1/2/10"></div><div><label>DPT</label>{mapping_dpt_select(f'dpt_{i}', item.get('dpt','1.001'))}</div><div><label>Testwert</label><input type="text" name="test_value_{i}" value="{escape(str(item.get('test_value','1')))}"></div>'''
        bottom = f'''<div><label>Invert</label><input type="checkbox" name="invert_{i}" {'checked' if item.get('invert', False) else ''}></div><div><label>Letzter Wert</label><div class="small" id="udp2knx_value_{i}">{escape(str(last.get('value','-')))}</div></div><div><label>Zuletzt</label><div class="small" id="udp2knx_time_{i}">{escape(str(last.get('time','-')))}</div></div>'''
        actions = f'''<button type="submit" formaction="/udp2knx/test/{i}" formmethod="post">Test</button><button type="button" class="delete-btn" onclick="document.getElementById('delete_{i}').checked=true; this.closest('.mapping-card').style.display='none';">🗑</button><input type="checkbox" id="delete_{i}" name="delete_{i}" style="display:none;">'''
        return render_shared_live_mapping_card('udp2knx', i, group_name, set_name, set_key, alias, item.get('enabled', True), last.get('value','-'), last.get('time','-'), top, bottom, actions)

    def new_card(i, group_name='', set_name='', set_key='__new__'):
        top = f'''<div><label>UDP Topic</label><input type="text" name="source_topic_{i}" value="{escape(str(prefill_source_topic))}" placeholder="topic vor Doppelpunkt"></div><div><label>KNX GA</label><input class="knx-ga-input" type="text" name="group_address_{i}" value="{escape(str(prefill_group_address))}" placeholder="1/2/10"></div><div><label>DPT</label>{mapping_dpt_select(f'dpt_{i}', '1.001')}</div><div><label>Testwert</label><input type="text" name="test_value_{i}" value="1"></div>'''
        bottom = f'''<div><label>Invert</label><input type="checkbox" name="invert_{i}"></div><div><label>Letzter Wert</label><div class="small" id="udp2knx_value_{i}">-</div></div><div><label>Zuletzt</label><div class="small" id="udp2knx_time_{i}">-</div></div>'''
        return render_shared_live_mapping_card('udp2knx', i, group_name, set_name, set_key, 'Neues Mapping', True, '-', '-', top, bottom, '', is_new=True)

    return render_shared_mapping_explorer_page('udp2knx', 'UDP → KNX', 'UDP topic:value direkt auf KNX Gruppenadressen senden.', '/knx', '/udp2knx/save', mappings, card, new_card, '/udp2knx_data', 'udp2knx_value_', 'udp2knx_time_')

@app.route('/udp2knx_data')
def udp2knx_data():
    data={}
    for i,item in enumerate(load_udp2knx_config()):
        info = get_udp_last_seen("udp2knx", item.get('source_topic','').strip())
        data[str(i)] = {'value': str(info.get('value','-')), 'time': str(info.get('time','-'))}
    return data

@app.route('/udp2knx/save', methods=['POST'])
def udp2knx_save():
    count = int(request.form.get('count',0)); new_data=[]
    for i in range(count):
        if f'delete_{i}' in request.form: continue
        if request.form.get(f'save_row_{i}', '1') == '0': continue
        source_topic = request.form.get(f'source_topic_{i}','').strip(); group_address = knx_service.normalize_knx_ga(request.form.get(f'group_address_{i}','').strip())
        group = request.form.get(f'group_{i}','').strip(); set_name = request.form.get(f'set_name_{i}','').strip(); mapping_alias = request.form.get(f'mapping_alias_{i}','').strip()
        if not any([source_topic, group_address, group, set_name, mapping_alias]): continue
        if not set_name: set_name = source_topic or group_address or mapping_alias or 'Neues Set'
        new_data.append({'enabled': f'enabled_{i}' in request.form, 'source_topic': source_topic, 'group_address': group_address, 'dpt': request.form.get(f'dpt_{i}','1.001').strip(), 'invert': f'invert_{i}' in request.form, 'test_value': request.form.get(f'test_value_{i}','1').strip(), 'group': group, 'set_name': set_name, 'mapping_alias': mapping_alias})
    save_udp2knx_config(new_data); add_log_entry('UDP2KNX Mappings gespeichert'); restart_bridge_async(); return redirect('/udp2knx')


@app.route('/udp2knx/test/<int:index>', methods=['POST'])
def udp2knx_test(index):
    mappings = load_udp2knx_config()
    if index < 0 or index >= len(mappings): return redirect('/udp2knx')
    item = mappings[index]; test_value = request.form.get(f'test_value_{index}', item.get('test_value','1')).strip(); item['test_value']=test_value; save_udp2knx_config(mappings)
    try:
        value = knx_service.convert_knx_value(test_value, item.get('dpt','1.001'), bool(item.get('invert',False))); _send_knx_service_value(knx_service.normalize_knx_ga(item.get('group_address','')), item.get('dpt','1.001'), value)
    except Exception as e: add_log_entry(f'UDP2KNX Test Fehler: {e}')
    return redirect('/udp2knx')



@app.route('/knx2lox')
def knx2lox():
    config = load_config()
    mappings = load_knx2lox_config()
    prefill_group_address = knx_service.normalize_knx_ga(request.args.get('group_address', ''))
    lox_io_datalist = build_datalist_html('loxoneInputs', loxone_service.get_loxone_io_options(config, load_config, load_mapping, add_log_entry, lambda: control_mapping))

    def card(i, item, group_name, set_name, set_key, alias):
        last = get_knx_last_seen("knx2lox", knx_service.normalize_knx_ga(item.get('group_address','')))
        top = f'''<div><label>KNX GA</label><input class="knx-ga-input" type="text" name="group_address_{i}" value="{escape(str(item.get('group_address','')))}" placeholder="1/2/10"></div><div><label>Loxone IO</label><input type="text" name="loxone_io_{i}" value="{escape(str(item.get('loxone_io','')))}" list="loxoneInputs" placeholder="Virtueller Eingang / Control"></div><div><label>DPT</label>{mapping_dpt_select(f'dpt_{i}', item.get('dpt','1.001'))}</div>'''
        bottom = f'''<div><label>Invert</label><input type="checkbox" name="invert_{i}" {'checked' if item.get('invert', False) else ''}></div><div><label>Letzter Wert</label><div class="small" id="knx2lox_value_{i}">{escape(str(last.get('value','-')))}</div></div><div><label>Zuletzt</label><div class="small" id="knx2lox_time_{i}">{escape(str(last.get('time','-')))}</div></div>'''
        actions = f'''<button type="button" class="delete-btn" onclick="document.getElementById('delete_{i}').checked=true; this.closest('.mapping-card').style.display='none';">🗑</button><input type="checkbox" id="delete_{i}" name="delete_{i}" style="display:none;">'''
        return render_shared_live_mapping_card('knx2lox', i, group_name, set_name, set_key, alias, item.get('enabled', True), last.get('value','-'), last.get('time','-'), top, bottom, actions)

    def new_card(i, group_name='', set_name='', set_key='__new__'):
        top = f'''<div><label>KNX GA</label><input class="knx-ga-input" type="text" name="group_address_{i}" value="{escape(str(prefill_group_address))}" placeholder="1/2/10"></div><div><label>Loxone IO</label><input type="text" name="loxone_io_{i}" list="loxoneInputs" placeholder="Virtueller Eingang / Control"></div><div><label>DPT</label>{mapping_dpt_select(f'dpt_{i}', '1.001')}</div>'''
        bottom = f'''<div><label>Invert</label><input type="checkbox" name="invert_{i}"></div><div><label>Letzter Wert</label><div class="small" id="knx2lox_value_{i}">-</div></div><div><label>Zuletzt</label><div class="small" id="knx2lox_time_{i}">-</div></div>'''
        return render_shared_live_mapping_card('knx2lox', i, group_name, set_name, set_key, 'Neues Mapping', True, '-', '-', top, bottom, '', is_new=True)

    return render_shared_mapping_explorer_page('knx2lox', 'KNX → Loxone', 'KNX Telegramme direkt an Loxone Eingänge/Controls schicken.', '/knx', '/knx2lox/save', mappings, card, new_card, '/knx2lox_data', 'knx2lox_value_', 'knx2lox_time_', lox_io_datalist)

@app.route('/knx2lox_data')
def knx2lox_data():
    data={}
    for i,item in enumerate(load_knx2lox_config()):
        info = get_knx_last_seen("knx2lox", knx_service.normalize_knx_ga(item.get('group_address','')))
        data[str(i)] = {'value': str(info.get('value','-')), 'time': str(info.get('time','-'))}
    return data

@app.route('/knx2lox/save', methods=['POST'])
def knx2lox_save():
    count = int(request.form.get('count',0)); new_data=[]
    for i in range(count):
        if f'delete_{i}' in request.form: continue
        if request.form.get(f'save_row_{i}', '1') == '0': continue
        group_address = knx_service.normalize_knx_ga(request.form.get(f'group_address_{i}','').strip()); loxone_io = request.form.get(f'loxone_io_{i}','').strip()
        group = request.form.get(f'group_{i}','').strip(); set_name = request.form.get(f'set_name_{i}','').strip(); mapping_alias = request.form.get(f'mapping_alias_{i}','').strip()
        if not any([group_address, loxone_io, group, set_name, mapping_alias]): continue
        if not set_name: set_name = loxone_io or group_address or mapping_alias or 'Neues Set'
        new_data.append({'enabled': f'enabled_{i}' in request.form, 'group_address': group_address, 'loxone_io': loxone_io, 'dpt': request.form.get(f'dpt_{i}','1.001').strip(), 'invert': f'invert_{i}' in request.form, 'group': group, 'set_name': set_name, 'mapping_alias': mapping_alias})
    save_knx2lox_config(new_data); add_log_entry('KNX2LOX Mappings gespeichert'); restart_bridge_async(); return redirect('/knx2lox')

def knx_settings_content(notice=""):
    knx_cfg = load_knx_config()
    def checked(value):
        return 'checked' if value else ''
    return f'''
{notice or ""}
<form method="post" action="/knx/save">
    <input type="hidden" name="next" value="/knx_settings_embed">
    <div class="card">
        <h2 class="section-title">KNX Gateway</h2>
        <label><input type="checkbox" name="knx_enabled" {checked(knx_cfg.get('enabled'))}> KNX aktivieren</label>
        <label>Gateway IP</label>
        <input type="text" name="gateway_ip" value="{escape(str(knx_cfg.get('gateway_ip','')))}">
        <label>Gateway Port</label>
        <input type="text" name="gateway_port" value="{escape(str(knx_cfg.get('gateway_port',3671)))}">
        <label>Verbindung</label>
        <select name="connection_type">
            <option value="tunneling" {'selected' if knx_cfg.get('connection_type') == 'tunneling' else ''}>Tunneling / IP Interface</option>
            <option value="routing" {'selected' if knx_cfg.get('connection_type') == 'routing' else ''}>Routing / IP Router</option>
        </select>
        <label>Lokale IP optional</label>
        <input type="text" name="local_ip" value="{escape(str(knx_cfg.get('local_ip','')))}" placeholder="leer lassen, wenn automatisch">
        <label>Physikalische Adresse</label>
        <input type="text" name="physical_address" value="{escape(str(knx_cfg.get('physical_address','1.1.250')))}">
        <div class="button-row" style="margin-top:14px;">
            <button type="submit">KNX speichern</button>
            <button type="submit" formaction="/knx/test" formmethod="post">Gateway testen</button>
        </div>
        <p class="small">Die KNX Mapping-Seiten findest du im KNX Hub.</p>
    </div>
</form>
'''


@app.route('/knx_settings_embed')
def knx_settings_embed():
    return embedded_page('KNX Einstellungen', knx_settings_content())


@app.route('/mqtt2knx')
def mqtt2knx():
    mappings = load_mqtt2knx_config()
    prefill_source_topic = request.args.get('source_topic', '')
    prefill_json_key = request.args.get('json_key', '')
    prefill_payload_mode = request.args.get('payload_mode', 'raw')
    prefill_group_address = knx_service.normalize_knx_ga(request.args.get('group_address', ''))

    def card(i, item, group_name, set_name, set_key, alias):
        last = get_knx_last_seen("mqtt2knx", item.get('source_topic',''))
        top = f'''<div><label>MQTT Topic</label><input type="text" name="source_topic_{i}" value="{escape(str(item.get('source_topic','')))}"></div><div><label>KNX GA</label><input class="knx-ga-input" type="text" name="group_address_{i}" value="{escape(str(item.get('group_address','')))}" placeholder="1/2/10"></div><div><label>DPT</label>{mapping_dpt_select(f'dpt_{i}', item.get('dpt','1.001'))}</div><div><label>Testwert</label><input type="text" name="test_value_{i}" value="{escape(str(item.get('test_value','1')))}"></div>'''
        bottom = f'''<div><label>Payload</label>{mapping_payload_select(f'payload_mode_{i}', item.get('payload_mode','raw'))}</div><div><label>JSON Key optional</label><input type="text" name="json_key_{i}" value="{escape(str(item.get('json_key','')))}" placeholder="z.B. contact"></div><div><label>Invert</label><input type="checkbox" name="invert_{i}" {'checked' if item.get('invert', False) else ''}></div><div><label>Letzter Wert</label><div class="small" id="mqtt2knx_value_{i}">{escape(str(last.get('value','-')))}</div></div><div><label>Zuletzt</label><div class="small" id="mqtt2knx_time_{i}">{escape(str(last.get('time','-')))}</div></div>'''
        actions = f'''<button type="submit" formaction="/mqtt2knx/test/{i}" formmethod="post">Test</button><button type="button" class="delete-btn" onclick="document.getElementById('delete_{i}').checked=true; this.closest('.mapping-card').style.display='none';">🗑</button><input type="checkbox" id="delete_{i}" name="delete_{i}" style="display:none;">'''
        return render_shared_live_mapping_card('mqtt2knx', i, group_name, set_name, set_key, alias, item.get('enabled', True), last.get('value','-'), last.get('time','-'), top, bottom, actions)

    def new_card(i, group_name='', set_name='', set_key='__new__'):
        top = f'''<div><label>MQTT Topic</label><input type="text" name="source_topic_{i}" value="{escape(str(prefill_source_topic))}"></div><div><label>KNX GA</label><input class="knx-ga-input" type="text" name="group_address_{i}" value="{escape(str(prefill_group_address))}" placeholder="1/2/10"></div><div><label>DPT</label>{mapping_dpt_select(f'dpt_{i}', '1.001')}</div><div><label>Testwert</label><input type="text" name="test_value_{i}" value="1"></div>'''
        bottom = f'''<div><label>Payload</label>{mapping_payload_select(f'payload_mode_{i}', prefill_payload_mode)}</div><div><label>JSON Key optional</label><input type="text" name="json_key_{i}" value="{escape(str(prefill_json_key))}" placeholder="z.B. contact"></div><div><label>Invert</label><input type="checkbox" name="invert_{i}"></div><div><label>Letzter Wert</label><div class="small" id="mqtt2knx_value_{i}">-</div></div><div><label>Zuletzt</label><div class="small" id="mqtt2knx_time_{i}">-</div></div>'''
        return render_shared_live_mapping_card('mqtt2knx', i, group_name, set_name, set_key, 'Neues Mapping', True, '-', '-', top, bottom, '', is_new=True)

    return render_shared_mapping_explorer_page('mqtt2knx', 'MQTT → KNX', 'MQTT Topics direkt auf KNX Gruppenadressen senden.', '/knx', '/mqtt2knx/save', mappings, card, new_card, '/mqtt2knx_data', 'mqtt2knx_value_', 'mqtt2knx_time_')

@app.route('/knx/save', methods=['POST'])
def knx_save():
    try:
        cfg = {
            'enabled': 'knx_enabled' in request.form,
            'gateway_ip': request.form.get('gateway_ip','').strip(),
            'gateway_port': int(request.form.get('gateway_port','3671').strip() or 3671),
            'connection_type': request.form.get('connection_type','tunneling').strip(),
            'local_ip': request.form.get('local_ip','').strip(),
            'physical_address': request.form.get('physical_address','1.1.250').strip()
        }
        save_knx_config(cfg)
        saved = load_knx_config()
        add_log_entry(f"KNX Gateway gespeichert: {'aktiv' if saved.get('enabled') else 'aus'} {saved.get('gateway_ip')}:{saved.get('gateway_port')}")
    except Exception as e:
        add_log_entry(f"KNX Gateway Speicherfehler: {e}")
    return redirect(request.form.get('next') or '/knx_settings_embed')

@app.route('/knx/test', methods=['POST'])
def knx_test():
    cfg = {
        'enabled': 'knx_enabled' in request.form,
        'gateway_ip': request.form.get('gateway_ip','').strip(),
        'gateway_port': int(request.form.get('gateway_port','3671').strip() or 3671),
        'connection_type': request.form.get('connection_type','tunneling').strip(),
        'local_ip': request.form.get('local_ip','').strip(),
        'physical_address': request.form.get('physical_address','1.1.250').strip()
    }
    save_knx_config(cfg)
    cfg = load_knx_config()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); sock.settimeout(2)
        sock.sendto(b'\x06\x10\x02\x01\x00\x0e\x08\x01\x00\x00\x00\x00\x00\x00', (cfg['gateway_ip'], int(cfg['gateway_port'])))
        try:
            sock.recvfrom(1024); add_log_entry(f"KNX Gateway antwortet: {cfg['gateway_ip']}:{cfg['gateway_port']}")
        except socket.timeout:
            add_log_entry(f"KNX Test gesendet, keine Antwort innerhalb 2s: {cfg['gateway_ip']}:{cfg['gateway_port']}")
        finally: sock.close()
    except Exception as e: add_log_entry(f'KNX Test Fehler: {e}')
    return redirect(request.form.get('next') or '/mqtt2knx')

@app.route('/mqtt2knx/save', methods=['POST'])
def mqtt2knx_save():
    count = int(request.form.get('count',0)); new_data=[]
    for i in range(count):
        if f'delete_{i}' in request.form: continue
        if request.form.get(f'save_row_{i}', '1') == '0': continue
        source_topic = request.form.get(f'source_topic_{i}','').strip()
        group_address = knx_service.normalize_knx_ga(request.form.get(f'group_address_{i}','').strip())
        group = request.form.get(f'group_{i}','').strip(); set_name = request.form.get(f'set_name_{i}','').strip(); mapping_alias = request.form.get(f'mapping_alias_{i}','').strip()
        if not any([source_topic, group_address, group, set_name, mapping_alias]): continue
        if not set_name: set_name = source_topic or group_address or mapping_alias or 'Neues Set'
        new_data.append({'enabled': f'enabled_{i}' in request.form, 'source_topic': source_topic, 'payload_mode': request.form.get(f'payload_mode_{i}','raw').strip(), 'json_key': request.form.get(f'json_key_{i}','').strip(), 'group_address': group_address, 'dpt': request.form.get(f'dpt_{i}','1.001').strip(), 'invert': f'invert_{i}' in request.form, 'test_value': request.form.get(f'test_value_{i}','1').strip(), 'group': group, 'set_name': set_name, 'mapping_alias': mapping_alias})
    save_mqtt2knx_config(new_data); add_log_entry('MQTT2KNX Mappings gespeichert'); return redirect('/mqtt2knx')

@app.route('/mqtt2knx/test/<int:index>', methods=['POST'])
def mqtt2knx_test(index):
    mappings = load_mqtt2knx_config()
    if index < 0 or index >= len(mappings): return redirect('/mqtt2knx')
    item = mappings[index]; test_value = request.form.get(f'test_value_{index}', item.get('test_value','1')).strip(); item['test_value']=test_value; save_mqtt2knx_config(mappings)
    try:
        value = knx_service.convert_knx_value(test_value, item.get('dpt','1.001'), bool(item.get('invert',False))); _send_knx_service_value(knx_service.normalize_knx_ga(item.get('group_address','')), item.get('dpt','1.001'), value)
    except Exception as e: add_log_entry(f'MQTT2KNX Test Fehler: {e}')
    return redirect('/mqtt2knx')

@app.route('/mqtt2knx_data')
def mqtt2knx_data():
    data={}
    for i,item in enumerate(load_mqtt2knx_config()):
        info = get_knx_last_seen("mqtt2knx", item.get('source_topic','').strip())
        data[str(i)] = {'value': str(info.get('value','-')), 'time': str(info.get('time','-'))}
    return data



@app.route('/knx2mqtt')
def knx2mqtt():
    mappings = load_knx2mqtt_config()
    prefill_group_address = knx_service.normalize_knx_ga(request.args.get('group_address', ''))

    def card(i, item, group_name, set_name, set_key, alias):
        last = get_knx_last_seen("knx2mqtt", item.get('group_address',''))
        top = f'''<div><label>KNX GA</label><input class="knx-ga-input" type="text" name="group_address_{i}" value="{escape(str(item.get('group_address','')))}" placeholder="1/2/10"></div><div><label>MQTT Topic</label><input type="text" name="mqtt_topic_{i}" value="{escape(str(item.get('mqtt_topic','')))}" placeholder="knx/licht/flur"></div><div><label>DPT</label>{mapping_dpt_select(f'dpt_{i}', item.get('dpt','1.001'))}</div>'''
        bottom = f'''<div><label>Retain</label><input type="checkbox" name="retain_{i}" {'checked' if item.get('retain', True) else ''}></div><div><label>Invert</label><input type="checkbox" name="invert_{i}" {'checked' if item.get('invert', False) else ''}></div><div><label>Letzter Wert</label><div class="small" id="knx2mqtt_value_{i}">{escape(str(last.get('value','-')))}</div></div><div><label>Zuletzt</label><div class="small" id="knx2mqtt_time_{i}">{escape(str(last.get('time','-')))}</div></div>'''
        actions = f'''<button type="button" class="delete-btn" onclick="document.getElementById('delete_{i}').checked=true; this.closest('.mapping-card').style.display='none';">🗑</button><input type="checkbox" id="delete_{i}" name="delete_{i}" style="display:none;">'''
        return render_shared_live_mapping_card('knx2mqtt', i, group_name, set_name, set_key, alias, item.get('enabled', True), last.get('value','-'), last.get('time','-'), top, bottom, actions)

    def new_card(i, group_name='', set_name='', set_key='__new__'):
        top = f'''<div><label>KNX GA</label><input class="knx-ga-input" type="text" name="group_address_{i}" value="{escape(str(prefill_group_address))}" placeholder="1/2/10"></div><div><label>MQTT Topic</label><input type="text" name="mqtt_topic_{i}" placeholder="knx/licht/flur"></div><div><label>DPT</label>{mapping_dpt_select(f'dpt_{i}', '1.001')}</div>'''
        bottom = f'''<div><label>Retain</label><input type="checkbox" name="retain_{i}" checked></div><div><label>Invert</label><input type="checkbox" name="invert_{i}"></div><div><label>Letzter Wert</label><div class="small" id="knx2mqtt_value_{i}">-</div></div><div><label>Zuletzt</label><div class="small" id="knx2mqtt_time_{i}">-</div></div>'''
        return render_shared_live_mapping_card('knx2mqtt', i, group_name, set_name, set_key, 'Neues Mapping', True, '-', '-', top, bottom, '', is_new=True)

    return render_shared_mapping_explorer_page(
        'knx2mqtt',
        'KNX → MQTT',
        'KNX Telegramme als MQTT Topics veröffentlichen.',
        '/knx',
        '/knx2mqtt/save',
        mappings,
        card,
        new_card,
        '/knx2mqtt_data',
        'knx2mqtt_value_',
        'knx2mqtt_time_',
        extra_script="""
function autoOpenKnx2MqttNewMapping(){
    try {
        var params = new URLSearchParams(window.location.search || '');
        if(params.get('group_address') || params.get('ga')){
            var ga = params.get('group_address') || params.get('ga') || '';
            if(ga && !params.get('group_address')){
                // ga als Kurzalias unterstützen
                var newUrl = new URL(window.location.href);
                newUrl.searchParams.set('group_address', ga);
                history.replaceState(null, '', newUrl.toString());
            }
            createNewSetFromCurrentSelection();
        }
    } catch(e) {}
}
setTimeout(autoOpenKnx2MqttNewMapping, 0);
"""
    )

@app.route('/knx2mqtt/save', methods=['POST'])
def knx2mqtt_save():
    count = int(request.form.get('count',0)); new_data=[]
    for i in range(count):
        if f'delete_{i}' in request.form: continue
        if request.form.get(f'save_row_{i}', '1') == '0': continue
        group_address = knx_service.normalize_knx_ga(request.form.get(f'group_address_{i}','').strip()); mqtt_topic = request.form.get(f'mqtt_topic_{i}','').strip()
        group = request.form.get(f'group_{i}','').strip(); set_name = request.form.get(f'set_name_{i}','').strip(); mapping_alias = request.form.get(f'mapping_alias_{i}','').strip()
        if not any([group_address, mqtt_topic, group, set_name, mapping_alias]): continue
        if not set_name: set_name = mqtt_topic or group_address or mapping_alias or 'Neues Set'
        new_data.append({'enabled': f'enabled_{i}' in request.form, 'group_address': group_address, 'mqtt_topic': mqtt_topic, 'dpt': request.form.get(f'dpt_{i}','1.001').strip(), 'retain': f'retain_{i}' in request.form, 'invert': f'invert_{i}' in request.form, 'group': group, 'set_name': set_name, 'mapping_alias': mapping_alias})
    save_knx2mqtt_config(new_data); add_log_entry('KNX2MQTT Mappings gespeichert'); restart_bridge_async(); return redirect('/knx2mqtt')

@app.route('/knx2mqtt_data')
def knx2mqtt_data():
    data={}
    for i,item in enumerate(load_knx2mqtt_config()):
        info = get_knx_last_seen("knx2mqtt", item.get('group_address','').strip())
        data[str(i)] = {'value': str(info.get('value','-')), 'time': str(info.get('time','-'))}
    return data




@app.route("/knx_monitor")
def knx_monitor():
    ensure_knx_listener_started("Monitor geöffnet")
    return """
<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>KNX Monitor</title>
<style>
html, body { height:100%; overflow:hidden; }
body { font-family:Arial, sans-serif; background:#111; color:#eee; margin:0; }
.header { background:#161a22; border-bottom:1px solid #333; padding:14px 18px; z-index:2; }
h1 { margin:0 0 10px; font-size:26px; }
.toolbar { display:flex; gap:10px; align-items:center; flex-wrap:wrap; }
input, select, button { background:#10131a; color:#fff; border:1px solid #485063; border-radius:7px; padding:8px 10px; }
input { min-width:320px; }
button { background:#5f686f; cursor:pointer; border:0; font-weight:700; }
button:hover { background:#737d86; }
.wrap { display:grid; grid-template-columns:360px 1fr; height:calc(100vh - 148px); overflow:hidden; }
.tree { border-right:1px solid #333; padding:14px; overflow:auto; background:#101010; }
.content { padding:14px 18px; overflow:hidden; display:flex; flex-direction:column; min-height:0; }
.telegram-scroll { overflow:auto; flex:1; min-height:0; border:1px solid #303645; border-radius:8px; }
.group { margin:5px 0; }
.ga { cursor:pointer; padding:6px 8px; border-radius:5px; display:flex; justify-content:space-between; gap:8px; }
.ga:hover { background:#242a35; }
.ga.active { background:#5f686f; }
.ga-main { font-weight:700; color:#f5d76e; }
.ga-sub { color:#aeb8c4; font-size:12px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:150px; }
.card { background:#171a21; border:1px solid #333; border-radius:10px; padding:12px; margin-bottom:12px; }
table { width:100%; border-collapse:collapse; background:#11151d; }
th, td { border-bottom:1px solid #303645; padding:8px; text-align:left; vertical-align:top; }
th { background:#202534; position:sticky; top:0; z-index:1; }
.badge { display:inline-block; min-width:36px; text-align:center; border-radius:12px; padding:3px 8px; font-weight:700; }
.rx { background:#243e2e; color:#7dff9e; }
.tx { background:#263653; color:#7cb5ff; }
.small { color:#aeb8c4; font-size:12px; }
.value { font-family:Consolas, monospace; white-space:pre-wrap; word-break:break-word; }
.actions a, .actions button { font-size:12px; padding:6px 8px; margin-right:5px; text-decoration:none; color:white; border-radius:6px; background:#5f686f; display:inline-block; }
.influx-btn.active { background:#2ecc40 !important; color:white; }
.influx-btn.inactive { background:#5f686f; color:white; }
.influx-type-select { min-width:86px; padding:5px 7px; font-size:12px; }
.knx-influx-topic-input { width:145px; padding:5px 7px; font-size:12px; }
.knx-alias-save-btn { background:#2ecc40 !important; color:white !important; padding:5px 7px !important; margin-left:4px !important; }
.knx-alias-cancel-btn { background:#5f686f !important; color:white !important; padding:5px 7px !important; margin-left:3px !important; }
.expert-map-box summary { cursor:pointer; color:#cfe0f5; font-weight:700; font-size:12px; }
.expert-map-box[open] { background:#121722; border:1px solid #303645; border-radius:8px; padding:6px; }
@media(max-width:900px) { .wrap { grid-template-columns:1fr; height:calc(100vh - 170px); } .tree { border-right:0; border-bottom:1px solid #333; max-height:220px; } input { min-width:180px; width:100%; } }
</style>
</head>
<body>
<div class="header">
    <h1>KNX Monitor</h1>
    <div class="toolbar">
        <input id="search" placeholder="Gruppenadresse, Wert oder Richtung suchen...">
        <select id="direction">
            <option value="">Empfangen + Senden</option>
            <option value="RX">nur Empfangen</option>
            <option value="TX">nur Senden</option>
        </select>
        <button id="pauseBtn" onclick="togglePause()">Pause</button>
        <button onclick="clearView()">Ansicht leeren</button>
        <span id="copyHint" class="small"></span>
    </div>
</div>

<div class="wrap">
    <div class="tree">
        <div class="small">Gruppenadressen</div>
        <div id="treeBox"></div>
    </div>
    <div class="content">
        <div class="card">
            <b>Letzte Telegramme</b>
            <div class="small" id="summary">warte auf Daten...</div>
        </div>
        <div class="telegram-scroll">
        <table>
            <thead>
                <tr>
                    <th>Zeit</th>
                    <th>Richtung</th>
                    <th>Gruppenadresse</th>
                    <th>Wert</th>
                    <th>DPT</th>
                    <th class="actions">Aktion</th>
                </tr>
            </thead>
            <tbody id="rows"></tbody>
        </table>
        </div>
    </div>
</div>

<script>
let paused = false;
let selectedGa = "";
let localClearedAt = 0;
let topicConfig = {};
let knxAliasEditGa = "";
let knxAliasDraft = {};

function esc(s) {
    return String(s ?? "").replace(/[&<>"']/g, m => ({
        "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"
    }[m]));
}

function knxInfluxTopic(ga) {
    return "knx/" + String(ga || "").trim();
}

function getKnxInfluxSettings(ga) {
    const key = knxInfluxTopic(ga);
    const cfg = topicConfig?.[key] || {};
    return (cfg && typeof cfg === "object") ? cfg : {};
}

function isKnxInfluxActive(ga) {
    return !!getKnxInfluxSettings(ga).influx;
}

function getKnxInfluxType(ga) {
    return getKnxInfluxSettings(ga).influx_value_type || "auto";
}

function getKnxInfluxTopicAlias(ga) {
    return getKnxInfluxSettings(ga).influx_topic || "";
}

function startKnxAliasEdit(ga, currentValue) {
    knxAliasEditGa = String(ga || "");
    if (!(knxAliasEditGa in knxAliasDraft)) {
        knxAliasDraft[knxAliasEditGa] = currentValue || "";
    }
}

function setKnxAliasDraft(ga, value) {
    knxAliasEditGa = String(ga || "");
    knxAliasDraft[knxAliasEditGa] = value || "";
}

function cancelKnxAliasEdit(ga) {
    const key = String(ga || "");
    delete knxAliasDraft[key];
    if (knxAliasEditGa === key) knxAliasEditGa = "";
    renderLast(window.lastKnxData || {});
}

function saveKnxAliasEdit(ga) {
    const key = String(ga || "");
    const alias = (knxAliasDraft[key] ?? getKnxInfluxTopicAlias(key) ?? "");
    setKnxInfluxTopic(key, alias);
}

function setKnxInfluxTopic(ga, alias) {
    const key = String(ga || "");
    const fd = new FormData();
    fd.append("group_address", key);
    fd.append("influx_topic", alias || "");
    fetch("/knx_monitor/influx_topic", { method:"POST", body:fd })
        .then(r => r.json())
        .then(data => {
            const cfg = ensureKnxConfigEntry(key);
            cfg.influx_topic = data.influx_topic || "";
            cfg.enabled = true;
            delete knxAliasDraft[key];
            if (knxAliasEditGa === key) knxAliasEditGa = "";
            showCopyHint(data.message || "KNX Influx Topic gespeichert");
            renderLast(window.lastKnxData || {});
        })
        .catch(err => showCopyHint("Influx Topic Fehler: " + err));
}

function ensureKnxConfigEntry(ga) {
    const key = knxInfluxTopic(ga);
    if (!topicConfig[key] || typeof topicConfig[key] !== "object") topicConfig[key] = {};
    return topicConfig[key];
}

function toggleKnxInflux(ga) {
    const nextState = !isKnxInfluxActive(ga);
    const fd = new FormData();
    fd.append("group_address", ga);
    fd.append("enabled", nextState ? "1" : "0");
    fetch("/knx_monitor/influx", { method:"POST", body:fd })
        .then(r => r.json())
        .then(data => {
            const cfg = ensureKnxConfigEntry(ga);
            cfg.influx = !!data.enabled;
            cfg.enabled = true;
            renderLast(window.lastKnxData || {});
            showCopyHint(data.message || (nextState ? "KNX → Influx aktiviert" : "KNX → Influx deaktiviert"));
        })
        .catch(err => showCopyHint("Influx Fehler: " + err));
}

function setKnxInfluxType(ga, valueType) {
    const fd = new FormData();
    fd.append("group_address", ga);
    fd.append("value_type", valueType || "auto");
    fetch("/knx_monitor/influx_type", { method:"POST", body:fd })
        .then(r => r.json())
        .then(data => {
            const cfg = ensureKnxConfigEntry(ga);
            cfg.influx_value_type = data.value_type || valueType || "auto";
            cfg.enabled = true;
            showCopyHint(data.message || "KNX Influx Typ gespeichert");
        })
        .catch(err => showCopyHint("Influx Typ Fehler: " + err));
}

function copyText(t) {
    const text = String(t || "");
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(() => {
            showCopyHint("Kopiert: " + text);
        }).catch(() => fallbackCopyText(text));
    } else {
        fallbackCopyText(text);
    }
}

function fallbackCopyText(text) {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    try { document.execCommand("copy"); showCopyHint("Kopiert: " + text); }
    catch(e) { showCopyHint("Kopieren fehlgeschlagen"); }
    document.body.removeChild(ta);
}

function showCopyHint(text) {
    const el = document.getElementById("copyHint");
    if (!el) return;
    el.textContent = text;
    clearTimeout(window.copyHintTimer);
    window.copyHintTimer = setTimeout(() => { el.textContent = ""; }, 1800);
}

function directionLabel(direction) {
    return String(direction || "RX").toUpperCase() === "TX" ? "Senden" : "Empfangen";
}

function directionClass(direction) {
    return String(direction || "RX").toUpperCase() === "TX" ? "tx" : "rx";
}

function togglePause() {
    paused = !paused;
    document.getElementById("pauseBtn").textContent = paused ? "Weiter" : "Pause";
}

function clearView() {
    localClearedAt = Date.now();
    document.getElementById("rows").innerHTML = "";
    document.getElementById("summary").textContent = "Ansicht geleert – neue Daten laufen weiter ein.";
}

function selectGa(ga) {
    selectedGa = selectedGa === ga ? "" : ga;
    renderLast(window.lastKnxData || {});
}

function renderLast(data) {
    window.lastKnxData = data;

    // Legacy: Während ein KNX Influx Topic/Alias editiert wird, die Tabelle nicht
    // durch Live-Telegramme neu rendern. Sonst verliert das Eingabefeld den Fokus
    // und halbfertige Aliase landen versehentlich in der Config/Influx.
    const active = document.activeElement;
    if (knxAliasEditGa && active && active.classList && active.classList.contains("knx-influx-topic-input")) {
        return;
    }

    const search = document.getElementById("search").value.toLowerCase();
    const dir = document.getElementById("direction").value;

    const last = data.last || {};
    const log = data.log || [];

    let gas = Object.keys(last).sort((a,b) => {
        const pa = a.split("/").map(x => parseInt(x || "0", 10));
        const pb = b.split("/").map(x => parseInt(x || "0", 10));
        return (pa[0]-pb[0]) || (pa[1]-pb[1]) || (pa[2]-pb[2]);
    });

    const treeHtml = gas.map(ga => {
        const e = last[ga] || {};
        const match = !search || ga.toLowerCase().includes(search) || String(e.value || "").toLowerCase().includes(search);
        if (!match) return "";
        const alias = getKnxInfluxTopicAlias(ga);
        const aliasMark = alias ? ` → ${esc(alias)}` : '';
        const influxMark = isKnxInfluxActive(ga) ? `<span class="small" style="color:#7dff9e;font-weight:700;">Influx${aliasMark}</span><br>` : '';
        return `<div class="ga ${selectedGa===ga?'active':''}" onclick="selectGa('${esc(ga)}')">
            <span><span class="ga-main">${esc(ga)}</span><br>${influxMark}<span class="ga-sub">${esc(e.value || "")}</span></span>
            <span class="badge ${directionClass(e.direction)}">${esc(directionLabel(e.direction))}</span>
        </div>`;
    }).join("");

    document.getElementById("treeBox").innerHTML = treeHtml || '<div class="small">Noch keine KNX Telegramme.</div>';

    let filtered = log.filter(e => {
        if (dir && e.direction !== dir) return false;
        if (selectedGa && e.ga !== selectedGa) return false;
        if (search) {
            const hay = [e.time, e.ga, e.value, e.direction, directionLabel(e.direction), e.dpt].join(" ").toLowerCase();
            if (!hay.includes(search)) return false;
        }
        return true;
    });

    document.getElementById("summary").textContent =
        `${filtered.length} angezeigt · max. 15 im Verlauf · ${gas.length} Gruppenadressen`;

    document.getElementById("rows").innerHTML = filtered.map(e => {
        const qga = encodeURIComponent(e.ga || "");
        const gaJson = JSON.stringify(String(e.ga || ""));
        const influxActive = isKnxInfluxActive(e.ga);
        const influxClass = influxActive ? "influx-btn active" : "influx-btn inactive";
        const influxLabel = influxActive ? "✓ Influx" : "Influx";
        const influxType = getKnxInfluxType(e.ga);
        const influxTopicAlias = getKnxInfluxTopicAlias(e.ga);
        const aliasEditActive = knxAliasEditGa === String(e.ga || "");
        const aliasInputValue = aliasEditActive && (String(e.ga || "") in knxAliasDraft) ? knxAliasDraft[String(e.ga || "")] : influxTopicAlias;
        return `<tr>
            <td>${esc(e.time)}</td>
            <td><span class="badge ${directionClass(e.direction)}">${esc(directionLabel(e.direction))}</span></td>
            <td><b>${esc(e.ga)}</b></td>
            <td class="value">${esc(e.value)}</td>
            <td>${esc(e.dpt || "")}</td>
            <td class="actions" style="min-width:230px;width:230px;">
                <div style="display:flex; gap:6px; flex-wrap:wrap; margin-bottom:6px;">
                    <button onclick='copyText(${gaJson})'>GA kopieren</button>
                    <a class="object-main-btn" href="/objects/edit/new?source=knx&value=${qga}&influx_topic=${encodeURIComponent(influxTopicAlias || ('knx/' + (e.ga || '')))}&name=${qga}">+ Objekt</a>
                </div>
                <details class="expert-map-box">
                    <summary>⚙ Expertenmapping anzeigen</summary>
                    <table class="knx-action-table" style="margin-top:6px;">
                        <tr>
                            <td><a href="/mqtt2knx?group_address=${qga}">MQTT→KNX</a></td>
                            <td><a href="/knx2lox?group_address=${qga}">KNX→Loxone</a></td>
                        </tr>
                        <tr>
                            <td><button class="${influxClass}" onclick='toggleKnxInflux(${gaJson})'>${influxLabel}</button></td>
                            <td><select class="influx-type-select" onchange='setKnxInfluxType(${gaJson}, this.value)'>
                                <option value="auto" ${influxType === "auto" ? "selected" : ""}>Auto</option>
                                <option value="bool01" ${influxType === "bool01" ? "selected" : ""}>Bool 0/1</option>
                                <option value="number" ${influxType === "number" ? "selected" : ""}>Zahl</option>
                                <option value="text" ${influxType === "text" ? "selected" : ""}>Text</option>
                            </select></td>
                        </tr>
                        <tr>
                            <td colspan="2">
                                <input class="knx-influx-topic-input" value="${esc(aliasInputValue)}" placeholder="Influx Topic/Alias"
                                    onfocus='startKnxAliasEdit(${gaJson}, this.value)'
                                    oninput='setKnxAliasDraft(${gaJson}, this.value)'
                                    onkeydown='if(event.key === "Enter"){event.preventDefault(); setKnxAliasDraft(${gaJson}, this.value); saveKnxAliasEdit(${gaJson}); this.blur();} if(event.key === "Escape"){event.preventDefault(); cancelKnxAliasEdit(${gaJson}); this.blur();}'
                                    title="Leer = knx/${esc(e.ga)}">
                                <button class="knx-alias-save-btn" title="Alias speichern" onclick='saveKnxAliasEdit(${gaJson})'>OK</button>
                                <button class="knx-alias-cancel-btn" title="Änderung verwerfen" onclick='cancelKnxAliasEdit(${gaJson})'>×</button>
                            </td>
                        </tr>
                    </table>
                </details>
            </td>
        </tr>`;
    }).join("") || '<tr><td colspan="6" class="small">Keine passenden Einträge.</td></tr>';
}

function refresh() {
    if (paused) return;
    fetch("/knx_monitor_data?t=" + Date.now(), {cache:"no-store"})
        .then(r => r.json())
        .then(renderLast)
        .catch(err => {
            document.getElementById("summary").textContent = "Fehler beim Laden: " + err;
        });
}

function startKnxMonitorStream() {
    if (!window.EventSource) {
        refresh();
        setInterval(refresh, 1000);
        return;
    }
    const es = new EventSource("/events/knx_monitor");
    es.addEventListener("knx_monitor", ev => {
        if (paused) return;
        try { renderLast(JSON.parse(ev.data || "{}")); }
        catch(e) { document.getElementById("summary").textContent = "SSE Fehler: " + e; }
    });
    es.onerror = () => console.log("KNX Monitor SSE reconnect...");
}

document.getElementById("search").addEventListener("input", () => renderLast(window.lastKnxData || {}));
document.getElementById("direction").addEventListener("change", () => renderLast(window.lastKnxData || {}));
fetch("/knx_listener_start", {method:"POST"}).catch(() => {});
fetch("/monitor_topic_config?t=" + Date.now(), {cache:"no-store"})
    .then(r => r.json())
    .then(cfg => { topicConfig = cfg || {}; renderLast(window.lastKnxData || {}); })
    .catch(() => {});
startKnxMonitorStream();
</script>
</body>
</html>
"""


@app.route("/knx_monitor/influx", methods=["POST"])
def knx_monitor_influx():
    group_address = knx_service.normalize_knx_ga(request.form.get("group_address", ""))
    enabled = request.form.get("enabled", "1") == "1"

    if not group_address:
        return {"ok": False, "message": "KNX Gruppenadresse fehlt ❌"}, 400

    topic = knx_influx_topic(group_address)
    topic_settings = load_topic_config()
    current = topic_settings.get(topic, {})
    if not isinstance(current, dict):
        current = {}

    current["influx"] = bool(enabled)
    current.setdefault("enabled", True)
    current.setdefault("source", "knx")
    current.setdefault("group_address", group_address)
    topic_settings[topic] = current
    save_topic_config(topic_settings)

    return {
        "ok": True,
        "topic": topic,
        "enabled": bool(enabled),
        "message": f"KNX {group_address} für Influx {'aktiviert' if enabled else 'deaktiviert'} ✅"
    }


@app.route("/knx_monitor/influx_type", methods=["POST"])
def knx_monitor_influx_type():
    group_address = knx_service.normalize_knx_ga(request.form.get("group_address", ""))
    value_type = request.form.get("value_type", "auto").strip() or "auto"

    allowed = {"auto", "bool01", "number", "text"}
    if value_type not in allowed:
        value_type = "auto"

    if not group_address:
        return {"ok": False, "message": "KNX Gruppenadresse fehlt ❌"}, 400

    topic = knx_influx_topic(group_address)
    topic_settings = load_topic_config()
    current = topic_settings.get(topic, {})
    if not isinstance(current, dict):
        current = {}

    current["influx_value_type"] = value_type
    current.setdefault("enabled", True)
    current.setdefault("source", "knx")
    current.setdefault("group_address", group_address)
    topic_settings[topic] = current
    save_topic_config(topic_settings)

    labels = {"auto": "Auto", "bool01": "Bool 0/1", "number": "Zahl", "text": "Text"}
    return {
        "ok": True,
        "topic": topic,
        "value_type": value_type,
        "message": f"KNX Influx Typ {group_address} = {labels.get(value_type, value_type)} ✅"
    }


@app.route("/knx_monitor/influx_topic", methods=["POST"])
def knx_monitor_influx_topic():
    group_address = knx_service.normalize_knx_ga(request.form.get("group_address", ""))
    influx_topic = str(request.form.get("influx_topic", "") or "").strip().strip("/")

    if not group_address:
        return {"ok": False, "message": "KNX Gruppenadresse fehlt ❌"}, 400

    topic = knx_influx_topic(group_address)
    topic_settings = load_topic_config()
    current = topic_settings.get(topic, {})
    if not isinstance(current, dict):
        current = {}

    if influx_topic:
        current["influx_topic"] = influx_topic
    else:
        current.pop("influx_topic", None)

    current.setdefault("enabled", True)
    current.setdefault("source", "knx")
    current.setdefault("group_address", group_address)
    topic_settings[topic] = current
    save_topic_config(topic_settings)

    output_topic = get_knx_influx_output_topic(group_address, current)
    return {
        "ok": True,
        "topic": topic,
        "influx_topic": influx_topic,
        "output_topic": output_topic,
        "message": f"KNX Influx Topic {group_address} → {output_topic} ✅"
    }


@app.route("/knx_listener_start", methods=["POST"])
def knx_listener_start():
    ok = ensure_knx_listener_started("manuell")
    return {"ok": bool(ok), "enabled": bool(load_knx_config().get("enabled", False))}


@app.route("/knx_monitor_data")
def knx_monitor_data():
    print("[KNX MONITOR DATA]", len(knx_monitor_log))
    return knx_monitor_payload()


@app.route("/events/status")
def events_status():
    return status_sse_response()


@app.route("/events/live_log")
def events_live_log():
    return sse_response("live_log", live_log_payload, "log")


@app.route("/events/live_log_full")
def events_live_log_full():
    return sse_response("live_log", live_log_full_payload, "log")


@app.route("/events/mqtt_monitor")
def events_mqtt_monitor():
    return sse_response("mqtt_monitor", get_mqtt_monitor_values, "mqtt", interval=0.1)


@app.route("/events/knx_monitor")
def events_knx_monitor():
    def payload():
        print("[KNX SSE]", len(knx_monitor_log))
        return knx_monitor_payload()

    return sse_response("knx_monitor", payload, "knx")


@app.route("/templates")
def mapping_templates_page(message=""):
    return embedded_page("Mapping Templates", mapping_templates_content(message))


@app.route("/templates/export", methods=["POST"])
def templates_export():
    selected = []
    for section_id in get_template_export_sections().keys():
        if request.form.get(f"section_{section_id}"):
            selected.append(section_id)
    if not selected:
        return mapping_templates_page('<div class="message">Kein Bereich ausgewählt.</div>')
    template_name = request.form.get("template_name", "MQTT2Lox Mapping Template")
    package = make_template_package(template_name, selected)
    safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(package.get("name", "template")).strip()).strip("_") or "template"
    memory_file = io.BytesIO()
    memory_file.write(json.dumps(package, indent=2, ensure_ascii=False).encode("utf-8"))
    memory_file.seek(0)
    add_log_entry(f"Template Export erstellt: {package.get('name')} ({', '.join(selected)})")
    return send_file(
        memory_file,
        as_attachment=True,
        download_name=f"mqtt2lox_template_{safe_name}.json",
        mimetype="application/json"
    )


@app.route("/templates/import", methods=["POST"])
def templates_import():
    if "template_file" not in request.files:
        return mapping_templates_page('<div class="message">Keine Template-Datei empfangen.</div>')
    file = request.files["template_file"]
    if file.filename == "":
        return mapping_templates_page('<div class="message">Keine Datei ausgewählt.</div>')
    mode = request.form.get("mode", "append")
    if mode not in ["append", "replace"]:
        mode = "append"
    try:
        package = json.loads(file.read().decode("utf-8"))
        ok, messages = import_template_package(package, mode=mode)
        for msg in messages:
            add_log_entry(f"Template Import: {msg}")
        if ok:
            add_log_entry(f"Template importiert: {package.get('name', file.filename)} | Modus {mode}")
            restart_bridge_async()
            msg_html = '<div class="message">Template importiert ✅<br>' + '<br>'.join(escape(str(m)) for m in messages) + '</div>'
        else:
            msg_html = '<div class="message">Template nicht importiert.<br>' + '<br>'.join(escape(str(m)) for m in messages) + '</div>'
        return mapping_templates_page(msg_html)
    except Exception as e:
        add_log_entry(f"Template Import Fehler: {e}")
        return mapping_templates_page(f'<div class="message">Template Import Fehler: {escape(str(e))}</div>')

@app.route("/backup")
def backup_config():
    files_to_backup = get_backup_files()
    return backup_service.backup_config(files_to_backup, add_log_entry, send_file, redirect)




@app.route("/restore", methods=["POST"])
def restore_config():
    if "backup_file" not in request.files:
        add_log_entry("Restore Fehler: keine Datei empfangen")
        return redirect("/")

    file = request.files["backup_file"]

    if file.filename == "":
        add_log_entry("Restore Fehler: leerer Dateiname")
        return redirect("/")

    allowed_files = get_backup_files()
    return backup_service.restore_config(file, allowed_files, add_log_entry, redirect)


@app.route("/udp2mqtt")
def udp2mqtt():
    mappings = load_udp2mqtt_config()
    config = load_config()
    prefill_mqtt = request.args.get("mqtt_topic", "").strip()
    prefill_udp = request.args.get("udp_topic", "").strip()
    if prefill_mqtt and not prefill_udp:
        prefix = str(config.get("udp_input", {}).get("prefix", "") or "").strip().strip("/")
        if prefix and prefill_mqtt.startswith(prefix + "/"):
            prefill_udp = prefill_mqtt[len(prefix)+1:]
        else:
            prefill_udp = prefill_mqtt

    legacy_state = "AN" if load_config().get("udp_input", {}).get("legacy_fallback") else "AUS"
    description = (
        "Eingehende UDP Telegramme im Format topic:value gezielt auf MQTT Topics veröffentlichen. "
        f"Legacy Discovery aktuell: {legacy_state}."
    )

    def card(i, item, group_name, set_name, set_key, alias):
        last = get_udp_last_seen("udp2mqtt", str(item.get("udp_topic", "")).strip())
        top = f'''<div><label>UDP Topic</label><input type="text" name="udp_topic_{i}" value="{escape(str(item.get('udp_topic','')))}" placeholder="z.B. licht/eg/flur"></div><div><label>MQTT Topic</label><input type="text" name="mqtt_topic_{i}" value="{escape(str(item.get('mqtt_topic','')))}" placeholder="z.B. loxone/licht/flur/set"></div>'''
        bottom = f'''<div><label>Retain</label><input type="checkbox" name="retain_{i}" {'checked' if item.get('retain', False) else ''}></div><div><label>Letzter Wert</label><div class="small" id="udp2mqtt_value_{i}">{escape(str(last.get('value','-')))}</div></div><div><label>Zuletzt</label><div class="small" id="udp2mqtt_time_{i}">{escape(str(last.get('time','-')))}</div></div><div><label>Testwert</label><input type="text" name="test_value_{i}" value="{escape(str(item.get('test_value','123')))}"></div>'''
        actions = f'''<button type="submit" formaction="/udp2mqtt/test/{i}" formmethod="post">Test</button><button type="button" class="delete-btn" onclick="document.getElementById('delete_{i}').checked=true; this.closest('.mapping-card').style.display='none';">🗑</button><input type="checkbox" id="delete_{i}" name="delete_{i}" style="display:none;">'''
        return render_shared_live_mapping_card(
            'udp2mqtt', i, group_name, set_name, set_key, alias,
            item.get('enabled', True), last.get('value','-'), last.get('time','-'),
            top, bottom, actions
        )

    def new_card(i, group_name='', set_name='', set_key='__new__'):
        top = f'''<div><label>UDP Topic</label><input type="text" name="udp_topic_{i}" value="{escape(str(prefill_udp))}" placeholder="z.B. licht/eg/flur"></div><div><label>MQTT Topic</label><input type="text" name="mqtt_topic_{i}" value="{escape(str(prefill_mqtt))}" placeholder="z.B. loxone/licht/flur/set"></div>'''
        bottom = f'''<div><label>Retain</label><input type="checkbox" name="retain_{i}"></div><div><label>Letzter Wert</label><div class="small" id="udp2mqtt_value_{i}">-</div></div><div><label>Zuletzt</label><div class="small" id="udp2mqtt_time_{i}">-</div></div><div><label>Testwert</label><input type="text" name="test_value_{i}" value="123"></div>'''
        return render_shared_live_mapping_card(
            'udp2mqtt', i, group_name, set_name, set_key,
            'Neues Mapping', True, '-', '-', top, bottom, '', is_new=True
        )

    extra_script = '''
function autoOpenUdp2MqttNewMapping(){
    try {
        var params = new URLSearchParams(window.location.search || '');
        if(params.get('udp_topic') || params.get('mqtt_topic')){
            createNewSetFromCurrentSelection();
        }
    } catch(e) {}
}
setTimeout(autoOpenUdp2MqttNewMapping, 0);
'''

    return render_shared_mapping_explorer_page(
        'udp2mqtt',
        'UDP → MQTT',
        description,
        '/mqtt',
        '/udp2mqtt/save',
        mappings,
        card,
        new_card,
        '/udp2mqtt_data',
        'udp2mqtt_value_',
        'udp2mqtt_time_',
        extra_script=extra_script
    )


@app.route("/udp2mqtt/save", methods=["POST"])
def udp2mqtt_save():
    count = int(request.form.get("count", 0))
    new_data = []
    for i in range(count):
        if f"delete_{i}" in request.form:
            continue
        if request.form.get(f"save_row_{i}", "1") == "0":
            continue
        udp_topic = request.form.get(f"udp_topic_{i}", "").strip()
        mqtt_topic = request.form.get(f"mqtt_topic_{i}", "").strip()
        group = request.form.get(f"group_{i}", "").strip()
        set_name = request.form.get(f"set_name_{i}", "").strip()
        mapping_alias = request.form.get(f"mapping_alias_{i}", "").strip()
        test_value = request.form.get(f"test_value_{i}", "123").strip() or "123"

        if not any([udp_topic, mqtt_topic, group, set_name, mapping_alias]):
            continue
        if not set_name:
            set_name = udp_topic or mqtt_topic or mapping_alias or "Neues UDP → MQTT Set"

        new_data.append({
            "enabled": f"enabled_{i}" in request.form,
            "udp_topic": udp_topic,
            "mqtt_topic": mqtt_topic,
            "retain": f"retain_{i}" in request.form,
            "test_value": test_value,
            "group": group,
            "set_name": set_name,
            "mapping_alias": mapping_alias
        })
    save_udp2mqtt_config(new_data)
    add_log_entry("UDP2MQTT Mappings gespeichert")
    restart_bridge_async()
    return redirect("/udp2mqtt")


@app.route("/udp2mqtt/test/<int:index>", methods=["POST"])
def udp2mqtt_test(index):
    publish_func = None
    if mqtt_client:
        publish_func = lambda topic, payload, retain=False: mqtt_client.publish(topic, payload, retain=bool(retain))
    udp.run_udp2mqtt_test(
        index,
        request.form,
        load_udp2mqtt_config,
        save_udp2mqtt_config,
        publish_func,
        add_log_entry,
        update_udp_last_seen,
    )
    return redirect("/udp2mqtt")


@app.route("/udp2mqtt_data")
def udp2mqtt_data():
    data = {}
    for i, item in enumerate(load_udp2mqtt_config()):
        udp_topic = str(item.get("udp_topic", "")).strip()
        info = get_udp_last_seen("udp2mqtt", udp_topic)
        data[str(i)] = {"value": str(info.get("value", "-")), "time": str(info.get("time", "-"))}
    return data


@app.route("/udp_input")
def udp_input_page():
    config = load_config()
    udp_cfg = config.get("udp_input", {})

    enabled = udp_cfg.get("enabled", False)
    port = udp_cfg.get("port", 7002)
    prefix = udp_cfg.get("prefix", "")
    retain = udp_cfg.get("retain", False)
    legacy_fallback = udp_cfg.get("legacy_fallback", False)

    checked_enabled = "checked" if enabled else ""
    checked_retain = "checked" if retain else ""
    checked_legacy = "checked" if legacy_fallback else ""

    html = f"""
<!doctype html>
<html>
<head>
    <title>UDP → MQTT Input</title>
    <style>
        body {{
            font-family: Arial;
            background:#202830;
            color:#f4f7fb;
            margin:30px;
        }}

        input[type=text] {{
            width:300px;
            background:#111820;
            color:white;
            border:1px solid #4a5663;
            padding:8px;
            box-sizing:border-box;
        }}

        table {{
            border-collapse: collapse;
            background:#151c23;
            margin-top:10px;
        }}

        th, td {{
            border:1px solid #303b45;
            padding:8px 12px;
        }}

        button,a {{
            background:#5f686f;
            color:white;
            padding:10px 15px;
            text-decoration:none;
            border:none;
            border-radius:8px;
            cursor:pointer;
            display:inline-block;
            font-size:14px;
        }}

        .testbtn {{
            background:#5f686f;
        }}

        code {{
            color:#7ee787;
        }}
    </style>
</head>
<body>

<h1>UDP → MQTT Input</h1>

<form method="post" action="/udp_input/save">

    <p>
        <label>
            <input type="checkbox" name="enabled" {checked_enabled}>
            Aktivieren
        </label>
    </p>

    <p>
        UDP Port:<br>
        <input type="text" name="port" value="{escape(str(port))}">
    </p>

    <p>
        MQTT Prefix optional:<br>
        <input type="text" name="prefix" value="{escape(str(prefix))}">
    </p>

    <p>
        <label>
            <input type="checkbox" name="retain" {checked_retain}>
            Letzten Wert speichern
        </label>
    </p>

    <p>
        <label>
            <input type="checkbox" name="legacy_fallback" {checked_legacy}>
            Legacy UDP→MQTT Discovery aktiv
        </label><br>
        <span style="color:#aeb8c4;font-size:13px;">Wenn aktiv, werden UDP Telegramme ohne passendes Mapping zusätzlich automatisch mit Prefix nach MQTT veröffentlicht. Praktisch zum Finden/Kopieren, standardmäßig lieber aus.</span>
    </p>

    <p>
        Erwartetes Format:<br>
        <code>topic:value</code> oder <code>topic=value</code>
    </p>

    <button type="submit">Speichern</button>
    <a href="/mqtt" style="margin-left:8px;">Zurück zum MQTT Hub</a>
    <a href="/udp2mqtt" style="margin-left:8px;">UDP→MQTT Mappings</a>

</form>

<hr>

<h2>UDP Test senden</h2>

<form method="post" action="/udp_input/test">
    <p>
        Topic:<br>
        <input type="text" name="test_topic" value="test/udp">
    </p>

    <p>
        Payload:<br>
        <input type="text" name="test_value" value="123">
    </p>

    <button class="testbtn" type="submit">Test senden</button>
</form>

<hr>

<h2>Letztes UDP Paket</h2>

<table>
    <tr>
        <th>IP</th>
        <th>Port</th>
        <th>Payload</th>
        <th>Zeit</th>
    </tr>
    <tr>
        <td id="udp_ip">-</td>
        <td id="udp_port">-</td>
        <td id="udp_raw">-</td>
        <td id="udp_time">-</td>
    </tr>
</table>

<script>
function refreshUdpInputData() {{
    fetch("/udp_input_data")
        .then(r => r.json())
        .then(data => {{
            if (data.last) {{
                document.getElementById("udp_ip").innerText = data.last.ip || "-";
                document.getElementById("udp_port").innerText = data.last.port || "-";
                document.getElementById("udp_raw").innerText = data.last.raw || "-";
                document.getElementById("udp_time").innerText = data.last.time || "-";
            }}
        }})
        .catch(err => console.log(err));
}}

setInterval(refreshUdpInputData, 2000);
refreshUdpInputData();
</script>

</body>
</html>
"""

    return html


@app.route("/udp_input/save", methods=["POST"])
def udp_input_save():
    config = load_config()

    if "udp_input" not in config:
        config["udp_input"] = {}

    config["udp_input"]["enabled"] = "enabled" in request.form
    config["udp_input"]["port"] = int(request.form.get("port", "7002").strip())
    config["udp_input"]["prefix"] = request.form.get("prefix", "").strip()
    config["udp_input"]["retain"] = "retain" in request.form
    config["udp_input"]["legacy_fallback"] = "legacy_fallback" in request.form

    save_config(config)

    add_log_entry("UDP Input Konfiguration gespeichert")

    return redirect("/udp_input")


@app.route("/udp_input/test", methods=["POST"])
def udp_input_test():
    config = load_config()
    udp_cfg = config.get("udp_input", {})

    port = int(udp_cfg.get("port", 7002))

    test_topic = request.form.get("test_topic", "test/udp").strip()
    test_value = request.form.get("test_value", "123").strip()
    udp.send_udp_input_test(port, test_topic, test_value, add_log_entry)

    return redirect("/udp_input")


@app.route("/udp_input_data")
def udp_input_data():
    return get_udp_last_seen("udp_input")


@app.route("/mqtt_brokers")
def mqtt_brokers_page():
    brokers = load_mqtt_brokers()
    new_i = len(brokers)

    html = """
<!doctype html>
<html>
<head>
    <title>MQTT Broker Manager</title>
    <style>
        body {
            font-family: Arial;
            background:#202830;
            color:#f4f7fb;
            margin:30px;
        }

        table {
            width:100%;
            border-collapse: collapse;
            background:#151c23;
        }

        th, td {
            border:1px solid #303b45;
            padding:8px;
        }

        input[type=text],
        input[type=password] {
            width:100%;
            background:#111820;
            color:white;
            border:1px solid #4a5663;
            padding:6px;
            box-sizing:border-box;
        }

        button,a {
            background:#5f686f;
            color:white;
            padding:10px 15px;
            text-decoration:none;
            border:none;
            border-radius:8px;
            cursor:pointer;
            display:inline-block;
        }
    </style>
</head>
<body>

<h1>Zusätzliche MQTT Broker</h1>

<p>
Der Hauptbroker bleibt weiterhin in den Bridge Einstellungen.<br>
Hier kannst du zusätzliche Broker hinzufügen, von denen ebenfalls empfangen wird.
</p>

<form method="post" action="/mqtt_brokers/save">

<table>
<tr>
    <th>Aktiv</th>
    <th>Name</th>
    <th>Host</th>
    <th>Port</th>
    <th>User</th>
    <th>Passwort</th>
    <th>Löschen</th>
</tr>
"""
    for i, item in enumerate(brokers):
        enabled = item.get("enabled", True)
        checked = "checked" if enabled else ""

        html += f"""
<tr>
    <td>
        <input type="checkbox" name="enabled_{i}" {checked}>
    </td>

    <td>
        <input type="text" name="name_{i}" value="{escape(item.get("name", ""))}">
    </td>

    <td>
        <input type="text" name="host_{i}" value="{escape(item.get("host", ""))}">
    </td>

    <td>
        <input type="text" name="port_{i}" value="{escape(str(item.get("port", 1883)))}">
    </td>

    <td>
        <input type="text" name="user_{i}" value="{escape(item.get("user", ""))}">
    </td>

    <td>
        <input type="password" name="password_{i}" value="{escape(item.get("password", ""))}">
    </td>

    <td>
        <input type="checkbox" name="delete_{i}">
    </td>
</tr>
"""
    html += f"""
<tr>
    <td>
        <input type="checkbox" name="enabled_{new_i}" checked>
    </td>

    <td>
        <input type="text" name="name_{new_i}">
    </td>

    <td>
        <input type="text" name="host_{new_i}">
    </td>

    <td>
        <input type="text" name="port_{new_i}" value="1883">
    </td>

    <td>
        <input type="text" name="user_{new_i}">
    </td>

    <td>
        <input type="password" name="password_{new_i}">
    </td>

    <td>-</td>
</tr>
"""

    html += f"""
</table>

<br>

<input type="hidden" name="count" value="{len(brokers)+1}">

<button type="submit">Speichern</button>


</form>

</body>
</html>
"""

    return html



@app.route("/test/mqtt_broker/<int:index>", methods=["POST"])
def test_mqtt_broker(index):
    try:
        name = request.form.get(f"name_{index}", "").strip() or f"Broker {index + 1}"
        host = request.form.get(f"host_{index}", "").strip()
        port = int(request.form.get(f"port_{index}", "1883").strip())
        user = request.form.get(f"user_{index}", "").strip()
        password = request.form.get(f"password_{index}", "").strip()

        if not host:
            raise Exception("Host fehlt")

        mqtt_module.test_connection(mqtt, host, port, user, password, 5)

        notice = f'<div class="card ok">✅ MQTT Broker erreichbar<br>{escape(str(name))} · {escape(str(host))}:{port}</div>'
        return embedded_page('MQTT Broker', mqtt_settings_content(load_config(), notice))

    except Exception as e:
        notice = f'<div class="card bad">❌ MQTT Broker Test Fehler: {escape(str(e))}</div>'
        return embedded_page('MQTT Broker', mqtt_settings_content(load_config(), notice))


@app.route("/mqtt_brokers/save", methods=["POST"])
def mqtt_brokers_save():
    count = int(request.form.get("count", 0))

    new_data = []

    for i in range(count):
        if f"delete_{i}" in request.form:
            continue

        name = request.form.get(f"name_{i}", "").strip()
        host = request.form.get(f"host_{i}", "").strip()
        port = request.form.get(f"port_{i}", "1883").strip()
        user = request.form.get(f"user_{i}", "").strip()
        password = request.form.get(f"password_{i}", "").strip()

        enabled = f"enabled_{i}" in request.form

        if not name or not host:
            continue

        new_data.append({
            "enabled": enabled,
            "name": name,
            "host": host,
            "port": port,
            "user": user,
            "password": password
        })

    save_mqtt_brokers(new_data)

    add_log_entry("MQTT Broker Liste gespeichert")
    restart_bridge_async()

    return redirect("/mqtt_settings_embed")



@app.route("/udp_discovery_status")
def udp_discovery_status():
    cfg = load_config().get("udp_input", {})
    state = {
        "enabled": bool(cfg.get("enabled", False)),
        "legacy_fallback": bool(cfg.get("legacy_fallback", False)),
        "port": cfg.get("port", 7002),
        "prefix": cfg.get("prefix", "")
    }
    with runtime_context.udp.lock:
        runtime_context.udp.discovery_enabled = bool(state.get("legacy_fallback", False))
        runtime_context.udp.discovery_state = dict(state)
    return state


@app.route("/udp_discovery_toggle", methods=["POST"])
def udp_discovery_toggle():
    config = load_config()
    udp_cfg = config.setdefault("udp_input", {})
    raw = str(request.form.get("legacy_fallback", "")).strip().lower()
    udp_cfg["legacy_fallback"] = raw in ["1", "true", "on", "yes", "ja"]
    save_config(config)
    with runtime_context.udp.lock:
        runtime_context.udp.discovery_enabled = bool(udp_cfg.get("legacy_fallback", False))
        runtime_context.udp.discovery_state = {"ok": True, "legacy_fallback": runtime_context.udp.discovery_enabled}
    add_log_entry("UDP Discovery " + ("aktiviert" if udp_cfg["legacy_fallback"] else "deaktiviert"))
    return {"ok": True, "legacy_fallback": bool(udp_cfg.get("legacy_fallback", False))}


@app.route("/monitor_data")
def monitor_data():
    return get_mqtt_monitor_values()


@app.route("/monitor_settings")
def monitor_settings():
    return load_monitor_settings()


@app.route("/monitor_topic_config")
def monitor_topic_config():
    return load_topic_config()


@app.route("/monitor/influx_topic", methods=["POST"])
def monitor_influx_topic():
    topic = request.form.get("topic", "").strip()
    enabled = request.form.get("enabled", "1") == "1"

    if not topic:
        return {"ok": False, "message": "Topic fehlt ❌"}, 400

    topic_settings = load_topic_config()
    current = topic_settings.get(topic, {})
    if not isinstance(current, dict):
        current = {}

    current["influx"] = bool(enabled)
    current.setdefault("enabled", True)
    topic_settings[topic] = current
    save_topic_config(topic_settings)

    return {"ok": True, "enabled": bool(enabled), "message": f"Topic für Influx {'aktiviert' if enabled else 'deaktiviert'} ✅"}


@app.route("/monitor/influx_json_key", methods=["POST"])
def monitor_influx_json_key():
    topic = request.form.get("topic", "").strip()
    json_key = request.form.get("json_key", "").strip()
    enabled = request.form.get("enabled", "1") == "1"

    if not topic:
        return {"ok": False, "message": "Topic fehlt ❌"}, 400
    if not json_key:
        return {"ok": False, "message": "JSON-Key fehlt ❌"}, 400

    topic_settings = load_topic_config()
    current = topic_settings.get(topic, {})
    if not isinstance(current, dict):
        current = {}

    keys = current.get("influx_json_keys", [])
    if not isinstance(keys, list):
        keys = []

    types = current.get("influx_json_key_types", {})
    if not isinstance(types, dict):
        types = {}

    if enabled and json_key not in keys:
        keys.append(json_key)
        types.setdefault(json_key, "auto")
    if not enabled and json_key in keys:
        keys = [k for k in keys if k != json_key]
        # Typ merken wir absichtlich, falls man den Key später wieder aktiviert.

    current["influx_json_keys"] = keys
    current["influx_json_key_types"] = types
    current.setdefault("enabled", True)
    topic_settings[topic] = current
    save_topic_config(topic_settings)

    return {"ok": True, "message": f"JSON-Key '{json_key}' für Influx {'aktiviert' if enabled else 'deaktiviert'} ✅", "keys": keys, "types": types}


@app.route("/monitor/influx_json_key_type", methods=["POST"])
def monitor_influx_json_key_type():
    topic = request.form.get("topic", "").strip()
    json_key = request.form.get("json_key", "").strip()
    value_type = request.form.get("value_type", "auto").strip() or "auto"

    allowed = {"auto", "bool01", "number", "text"}
    if value_type not in allowed:
        value_type = "auto"

    if not topic:
        return {"ok": False, "message": "Topic fehlt ❌"}, 400
    if not json_key:
        return {"ok": False, "message": "JSON-Key fehlt ❌"}, 400

    topic_settings = load_topic_config()
    current = topic_settings.get(topic, {})
    if not isinstance(current, dict):
        current = {}

    types = current.get("influx_json_key_types", {})
    if not isinstance(types, dict):
        types = {}

    types[json_key] = value_type
    current["influx_json_key_types"] = types
    current.setdefault("enabled", True)
    topic_settings[topic] = current
    save_topic_config(topic_settings)

    labels = {"auto": "Auto", "bool01": "Bool 0/1", "number": "Zahl", "text": "Text"}
    return {"ok": True, "message": f"Influx Typ für '{json_key}' = {labels.get(value_type, value_type)} ✅", "types": types}


@app.route("/monitor/favorite", methods=["POST"])
def monitor_favorite():
    topic = request.form.get("topic", "")
    action = request.form.get("action", "")

    settings = load_monitor_settings()
    favorites = settings.get("favorites", [])

    if action == "add" and topic and topic not in favorites:
        favorites.append(topic)

    if action == "remove" and topic in favorites:
        favorites.remove(topic)

    settings["favorites"] = favorites
    save_monitor_settings(settings)

    return {"ok": True, "favorites": favorites}


@app.route("/monitor/alias", methods=["POST"])
def monitor_alias():
    topic = request.form.get("topic", "")
    alias = request.form.get("alias", "").strip()

    settings = load_monitor_settings()
    aliases = settings.get("aliases", {})

    if topic:
        if alias:
            aliases[topic] = alias
        elif topic in aliases:
            del aliases[topic]

    settings["aliases"] = aliases
    save_monitor_settings(settings)

    return {"ok": True, "aliases": aliases}

# -----------------------------------------------------------------------------
# Legacy Influx Explorer / Datenverwaltung + Menüpunkt im Shell-Menü
# -----------------------------------------------------------------------------


def influx_explorer_page(notice=""):
    search = str(request.args.get("q", "") or "").strip()
    ok, msg, topics = influx_service.influx_get_topics(search=search, limit=400, load_config=load_config, start=str(request.args.get("start", "-30d") if request else "-30d") or "-30d")
    cfg = load_config().get("influx", {})
    bucket = str(cfg.get("bucket", "") or "")
    org = str(cfg.get("org", "") or "")
    measurement = str(cfg.get("measurement", "loxone") or "loxone")
    notice_html = f'<div class="notice">{escape(notice)}</div>' if notice else ""
    if not ok:
        notice_html += f'<div class="notice bad">{escape(msg)}</div>'
        topics = []
    rows = ""
    for item in topics:
        t = item["topic"]
        et = escape(t)
        rows += f'''
<tr>
  <td><input type="checkbox" name="topic" value="{et}"></td>
  <td><b>{et}</b></td>
  <td>{escape(item.get('fields',''))}</td>
  <td>{escape(item.get('last_value',''))}</td>
  <td>{escape(item.get('last_time',''))}</td>
  <td style="text-align:right;">{escape(item.get('count',''))}</td>
  <td><form method="post" action="/influx_explorer/delete" onsubmit="return confirm('Topic wirklich löschen?\\n{et}');"><input type="hidden" name="topic" value="{et}"><button type="submit" class="danger">Löschen</button></form></td>
</tr>'''
    if not rows:
        rows = '<tr><td colspan="7" class="small">Keine Topics gefunden. Zeitraum/Search prüfen oder erst neue Werte schreiben lassen.</td></tr>'
    return f'''
<!doctype html><html><head><meta charset="utf-8"><title>Influx Explorer</title><style>
body {{ font-family:Arial; background:#202830; color:#f4f7fb; margin:24px; }}
a {{ color:inherit; }}
.card {{ background:#1b2229; border:1px solid #303b45; border-radius:12px; padding:16px; margin-bottom:16px; }}
.header {{ display:flex; justify-content:space-between; gap:12px; align-items:flex-start; flex-wrap:wrap; }}
.badge {{ display:inline-block; padding:4px 8px; border-radius:999px; background:#2a333d; color:#dbe6f2; font-size:12px; margin-right:6px; }}
.small {{ color:#aeb8c4; font-size:13px; line-height:1.35; }} .mini-row {{ display:flex; gap:6px; align-items:center; }} .mini-row input {{ flex:1; }} .mini-btn {{ padding:9px 10px; white-space:nowrap; }}
.notice {{ border:1px solid #355b3f; background:#132015; padding:10px 12px; border-radius:10px; margin-bottom:12px; }}
.notice.bad {{ border-color:#7a3434; background:#281717; }}
button,.button-link {{ background:#5f686f; color:white; padding:9px 13px; border:0; border-radius:8px; cursor:pointer; text-decoration:none; display:inline-flex; align-items:center; font-weight:700; }}
button:hover,.button-link:hover {{ background:#727d85; }}
button.danger {{ background:#b93b3b; }} button.danger:hover {{ background:#d14a4a; }}
input[type=text],select {{ background:#111820; color:white; border:1px solid #4a5663; border-radius:8px; padding:9px; }}
input[type=checkbox] {{ width:18px; height:18px; accent-color:#35c75a; }}
table {{ width:100%; border-collapse:collapse; background:#151c23; }} th,td {{ border:1px solid #303b45; padding:8px; vertical-align:middle; }} th {{ background:#2a333d; text-align:left; }}
.toolbar {{ display:flex; gap:8px; align-items:center; flex-wrap:wrap; }}
</style></head><body>
<div class="header">
  <div><h1>Influx Explorer</h1><div class="small">Datenbank direkt aus MQTT2Lox verwalten. Erste Ausbaustufe: Topics anzeigen, suchen und gezielt löschen.</div></div>
  <a class="button-link" href="/mqtt">← MQTT Hub</a>
</div>
<div class="card">
  <span class="badge">Bucket: {escape(bucket)}</span><span class="badge">Org: {escape(org)}</span><span class="badge">Measurement: {escape(measurement)}</span>
  <p class="small">Tipp: falsch getippte KNX-Aliase über Suche markieren und löschen. Löschen nutzt die Influx Delete-API mit Predicate <code>topic="..."</code>.</p>
</div>
{notice_html}
<div class="card">
  <form method="get" action="/influx_explorer" class="toolbar">
    <input type="text" name="q" value="{escape(search)}" placeholder="Topic suchen..." style="min-width:340px; flex:1;">
    <button type="submit">Suchen</button>
    <a class="button-link" href="/influx_explorer">Zurücksetzen</a>
  </form>
</div>
<form method="post" action="/influx_explorer/delete_selected" onsubmit="return confirm('Markierte Topics wirklich löschen?');">
<div class="card">
  <div class="toolbar" style="margin-bottom:12px;"><button type="button" onclick="document.querySelectorAll('input[name=topic]').forEach(x=>x.checked=true)">Alle markieren</button><button type="button" onclick="document.querySelectorAll('input[name=topic]').forEach(x=>x.checked=false)">Alle abwählen</button><button type="submit" class="danger">Markierte löschen</button></div>
  <table><tr><th style="width:40px;"></th><th>Topic</th><th>Fields</th><th>Letzter Wert</th><th>Letzte Zeit</th><th style="width:100px; text-align:right;">Werte</th><th style="width:115px;">Aktion</th></tr>{rows}</table>
</div>
</form>
</body></html>'''


@app.route("/influx_explorer")
def influx_explorer():
    return influx_explorer_page()


@app.route("/influx_explorer/delete", methods=["POST"])
def influx_explorer_delete():
    topic = request.form.get("topic", "")
    ok, msg = influx_service.influx_delete_topic(topic, load_config, add_log_entry)
    return influx_explorer_page(("✅ " if ok else "❌ ") + msg)


@app.route("/influx_explorer/delete_selected", methods=["POST"])
def influx_explorer_delete_selected():
    topics = request.form.getlist("topic")
    if not topics:
        return influx_explorer_page("Keine Topics ausgewählt")
    ok_count = 0
    errors = []
    for topic in topics:
        ok, msg = influx_service.influx_delete_topic(topic, load_config, add_log_entry)
        if ok:
            ok_count += 1
        else:
            errors.append(msg)
    notice = f"✅ {ok_count} Topic(s) gelöscht"
    if errors:
        notice += " | Fehler: " + "; ".join(errors[:3])
    return influx_explorer_page(notice)



def objects_page(notice=""):
    objects = load_objects_config()
    search = str(request.args.get("q", "") or "").strip().lower()
    filtered = []
    for item in objects:
        blob = " ".join(str(item.get(k, "")) for k in ["name", "room", "type", "mqtt_topic", "mqtt_json_key", "loxone_topic", "knx_ga", "udp_topic", "influx_topic", "notes"]).lower()
        if not search or search in blob:
            filtered.append(item)
    notice_html = f'<div class="notice">{escape(notice)}</div>' if notice else ""
    rows = ""
    for idx, item in enumerate(filtered):
        src, value, tm = object_service._object_value_from_sources(item)
        badges = ""
        links = [
            ("MQTT", item.get("mqtt_topic", ""), "/monitor"),
            ("Loxone", item.get("loxone_topic", ""), "/topics2"),
            ("KNX", item.get("knx_ga", ""), "/knx_monitor"),
            ("UDP", item.get("udp_topic", ""), "/monitor"),
            ("Influx", item.get("influx_topic", ""), "/influx_explorer?q=" + quote(str(item.get("influx_topic", "")), safe="")),
        ]
        for label, val, url in links:
            if val:
                badges += f'<a class="badge active" href="{escape(url)}" title="{escape(str(val))}">{escape(label)}</a>'
            else:
                badges += f'<span class="badge off">{escape(label)}</span>'
        rows += f'''
<tr>
  <td>{'✅' if item.get('enabled', True) else '⏸'}</td>
  <td><b>{escape(item.get('name') or '(ohne Name)')}</b><br><span class="small">{escape(item.get('room',''))} {escape(item.get('type',''))}</span></td>
  <td>{badges}</td>
  <td><b>{escape(str(value))}</b><br><span class="small">{escape(src)} {escape(str(tm or ''))}</span></td>
  <td><a class="button-link" href="/objects/edit/{escape(str(item.get('id')))}">Bearbeiten</a></td>
</tr>'''
    if not rows:
        rows = '<tr><td colspan="5" class="small">Noch keine Objekte gefunden. Leg das erste Objekt an — dann wird aus Kabelsalat langsam Spaghetti Bolognese.</td></tr>'
    return f'''
<!doctype html><html><head><meta charset="utf-8"><title>Objektmanager</title><style>
body {{ font-family:Arial; background:#202830; color:#f4f7fb; margin:24px; }}
a {{ color:inherit; }}
.card {{ background:#1b2229; border:1px solid #303b45; border-radius:12px; padding:16px; margin-bottom:16px; }}
.header {{ display:flex; justify-content:space-between; gap:12px; align-items:flex-start; flex-wrap:wrap; }}
.small {{ color:#aeb8c4; font-size:13px; line-height:1.35; }} .mini-row {{ display:flex; gap:6px; align-items:center; }} .mini-row input {{ flex:1; }} .mini-btn {{ padding:9px 10px; white-space:nowrap; }}
.notice {{ border:1px solid #355b3f; background:#132015; padding:10px 12px; border-radius:10px; margin-bottom:12px; }}
button,.button-link {{ background:#5f686f; color:white; padding:9px 13px; border:0; border-radius:8px; cursor:pointer; text-decoration:none; display:inline-flex; align-items:center; font-weight:700; }}
button:hover,.button-link:hover {{ background:#727d85; }} .danger {{ background:#b93b3b; }}
input[type=text],textarea,select {{ background:#111820; color:white; border:1px solid #4a5663; border-radius:8px; padding:9px; }}
table {{ width:100%; border-collapse:collapse; background:#151c23; }} th,td {{ border:1px solid #303b45; padding:8px; vertical-align:middle; }} th {{ background:#2a333d; text-align:left; }}
.toolbar {{ display:flex; gap:8px; align-items:center; flex-wrap:wrap; }}
.badge {{ display:inline-block; padding:4px 8px; border-radius:999px; margin:2px; font-size:12px; text-decoration:none; }}
.badge.active {{ background:#143b26; color:#6dff91; border:1px solid #276b3c; }} .badge.off {{ background:#2a333d; color:#8793a0; }}
</style></head><body>
<div class="header"><div><h1>Objektmanager</h1><div class="small">Objektmanager: Ein Objekt bündelt MQTT, Loxone, KNX, UDP und Influx. Expertenmapping-Übernahme läuft nur noch manuell.</div></div><a class="button-link" href="/">← Dashboard</a></div>
<div class="card toolbar">
<a class="button-link" href="/objects/edit/new">＋ Neues Objekt</a>
<form method="post" action="/objects/sync_from_mappings" onsubmit="return confirm('Experten-Mappings als Objekte übernehmen?');"><button type="submit">↔ Expertenmapping übernehmen</button></form>
<form method="post" action="/objects/rebuild_mappings" onsubmit="return confirm('Alle technischen Mappings leeren und sauber aus den Objekten neu erzeugen?');"><button type="submit" class="danger">Mappings aus Objekten neu bauen</button></form>
<form method="post" action="/objects/delete_all" onsubmit="return confirm('Wirklich ALLE Objekte löschen? Technische Mappings bleiben nur bestehen, wenn du sie nicht separat leerst.');"><button type="submit" class="danger">Alle Test-Objekte löschen</button></form>
<form method="get" action="/objects" class="toolbar" style="flex:1;"><input type="text" name="q" value="{escape(search)}" placeholder="Objekt, Topic, Raum suchen..." style="min-width:320px; flex:1;"><button type="submit">Suchen</button><a class="button-link" href="/objects">Zurücksetzen</a></form>
</div>
{notice_html}
<div class="card"><table><tr><th style="width:45px;">Aktiv</th><th>Objekt</th><th>Verknüpfungen</th><th>Livewert</th><th style="width:120px;">Aktion</th></tr>{rows}</table></div>
</body></html>'''


@app.route('/objects')
def objects():
    return objects_page(str(request.args.get('notice', '') or ''))


@app.route('/objects/edit/<object_id>')
def objects_edit(object_id):
    objects = load_objects_config()
    item = next((x for x in objects if str(x.get('id')) == str(object_id)), None)
    is_new = item is None
    if is_new:
        import time as _time
        item = {"id": f"obj_{int(_time.time()*1000)}", "enabled": True, "name": "", "room": "", "type": "", "mqtt_topic": "", "mqtt_json_key": "", "loxone_topic": "", "knx_ga": "", "udp_topic": "", "influx_topic": "", "notes": ""}
    item = object_service._object_apply_prefill(item)
    def val(k): return escape(str(item.get(k, "") or ""))
    checked = "checked" if item.get("enabled", True) else ""
    mqtt_datalist = object_service._object_datalist_html("mqtt", "mqttObjectCandidates")
    loxone_datalist = object_service._object_datalist_html("loxone", "loxoneObjectCandidates")
    knx_datalist = object_service._object_datalist_html("knx", "knxObjectCandidates")
    udp_datalist = object_service._object_datalist_html("udp", "udpObjectCandidates")
    influx_datalist = object_service._object_datalist_html("influx", "influxObjectCandidates")
    return f'''
<!doctype html><html><head><meta charset="utf-8"><title>Objekt bearbeiten</title><style>
body {{ font-family:Arial; background:#202830; color:#f4f7fb; margin:24px; }} .card {{ background:#1b2229; border:1px solid #303b45; border-radius:12px; padding:16px; margin-bottom:16px; max-width:1050px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:12px; }} label {{ display:block; color:#cfe0f5; font-size:12px; margin-bottom:4px; }}
input[type=text],textarea {{ width:100%; box-sizing:border-box; background:#111820; color:white; border:1px solid #4a5663; border-radius:8px; padding:9px; }} textarea {{ min-height:90px; }}
button,.button-link {{ background:#5f686f; color:white; padding:9px 13px; border:0; border-radius:8px; cursor:pointer; text-decoration:none; display:inline-flex; align-items:center; font-weight:700; }} .danger {{ background:#b93b3b; }}
.small {{ color:#aeb8c4; font-size:13px; line-height:1.35; }} .mini-row {{ display:flex; gap:6px; align-items:center; }} .mini-row input {{ flex:1; }} .mini-btn {{ padding:9px 10px; white-space:nowrap; }}
</style></head><body>
<h1>{'Neues Objekt' if is_new else 'Objekt bearbeiten'}</h1>
<form method="post" action="/objects/save"><input type="hidden" name="id" value="{val('id')}">
<div class="card"><div class="grid">
<div><label>Name</label><input type="text" name="name" value="{val('name')}" placeholder="z.B. Schlafzimmer Licht"></div>
<div><label>Raum</label><input type="text" name="room" value="{val('room')}" placeholder="Schlafzimmer"></div>
<div><label>Typ</label><input type="text" name="type" value="{val('type')}" placeholder="Licht, Temperatur, Kontakt..."></div>
<div><label>Aktiv</label><input type="checkbox" name="enabled" {checked}></div>
</div></div>
<div class="card"><h2>Verknüpfungen</h2><div class="grid">
<div><label>MQTT Topic</label><div class="mini-row"><input type="text" name="mqtt_topic" list="mqttObjectCandidates" value="{val('mqtt_topic')}" placeholder="zigbee2mqtt/... oder shellies/..."><a class="button-link mini-btn" href="/monitor">MQTT wählen</a></div></div>
<div><label>MQTT JSON-Key optional</label><input type="text" name="mqtt_json_key" value="{val('mqtt_json_key')}" placeholder="z.B. contact, temperature, power"></div>
<div><label>Loxone Topic / Eingang</label><div class="mini-row"><input type="text" name="loxone_topic" list="loxoneObjectCandidates" value="{val('loxone_topic')}" placeholder="loxone/... oder Alias"><a class="button-link mini-btn" href="/topics2">Loxone wählen</a></div></div>
<div><label>KNX Gruppenadresse</label><div class="mini-row"><input type="text" name="knx_ga" list="knxObjectCandidates" value="{val('knx_ga')}" placeholder="0/2/5"><a class="button-link mini-btn" href="/knx_monitor">KNX wählen</a></div></div>
<div><label>UDP Topic</label><div class="mini-row"><input type="text" name="udp_topic" list="udpObjectCandidates" value="{val('udp_topic')}" placeholder="UDP Name"><a class="button-link mini-btn" href="/udp2mqtt">UDP wählen</a></div></div>
<div><label>Influx Topic/Alias</label><div class="mini-row"><input type="text" name="influx_topic" list="influxObjectCandidates" value="{val('influx_topic')}" placeholder="Schlafzimmer/Licht"><a class="button-link mini-btn" href="/influx_explorer">Influx wählen</a></div></div>
</div><p class="small">Tipp: Du kannst tippen und aus vorhandenen MQTT-/KNX-/Influx-Daten wählen. In den Explorern gibt es zusätzlich einen direkten Button „Objekt erstellen“.</p>
<label style="display:flex; gap:8px; align-items:center; margin-top:10px;"><input type="checkbox" name="auto_create_mappings" checked> Fehlende Mappings beim Speichern automatisch anlegen</label>
<p class="small">Bestehende Mappings werden nicht überschrieben. Es werden nur fehlende Verbindungen ergänzt — Mapping-Konfetti bleibt also im Schrank.</p>{mqtt_datalist}{loxone_datalist}{knx_datalist}{udp_datalist}{influx_datalist}</div>
<div class="card"><label>Notizen</label><textarea name="notes">{val('notes')}</textarea></div>
<div class="card" style="display:flex; gap:8px; flex-wrap:wrap; align-items:center;"><button type="submit">💾 Speichern</button><a class="button-link" href="/objects">Abbrechen</a><label class="small" style="display:flex; gap:6px; align-items:center;"><input type="checkbox" name="delete_mappings" checked> zugehörige Mappings mit löschen</label><button class="danger" type="submit" formaction="/objects/delete" onclick="return confirm('Objekt wirklich löschen?')">🗑 Löschen</button></div>
</form></body></html>'''


@app.route('/objects/sync_from_mappings', methods=['POST'])
def objects_sync_from_mappings():
    changed = object_service.sync_objects_from_expert_mappings()
    msg = "Experten-Mappings wurden in die Objektverwaltung übernommen" if changed else "Keine neuen Experten-Mappings gefunden"
    add_log_entry(msg)
    return redirect('/objects?notice=' + quote(msg))


@app.route('/objects/rebuild_mappings', methods=['POST'])
def objects_rebuild_mappings():
    removed, created, warnings = object_service.rebuild_technical_mappings_from_objects(clear_first=True)
    msg = "Technische Mappings aus Objekten neu aufgebaut"
    if removed:
        msg += " | geleert: " + ", ".join(removed[:8])
    if created:
        msg += " | erzeugt: " + ", ".join(created)
    if warnings:
        msg += " | Hinweis: " + "; ".join(warnings[:3])
    add_log_entry(msg)
    return redirect('/objects?notice=' + quote(msg))


@app.route('/objects/save', methods=['POST'])
def objects_save():
    objects = load_objects_config()
    object_id = request.form.get('id','').strip()
    item = {
        'id': object_id,
        'enabled': 'enabled' in request.form,
        'name': request.form.get('name','').strip(),
        'room': request.form.get('room','').strip(),
        'type': request.form.get('type','').strip(),
        'mqtt_topic': request.form.get('mqtt_topic','').strip(),
        'mqtt_json_key': request.form.get('mqtt_json_key','').strip(),
        'loxone_topic': request.form.get('loxone_topic','').strip(),
        'knx_ga': knx_service.normalize_knx_ga(request.form.get('knx_ga','').strip()),
        'udp_topic': request.form.get('udp_topic','').strip(),
        'influx_topic': request.form.get('influx_topic','').strip(),
        'notes': request.form.get('notes','').strip(),
    }
    found = False
    for i, old in enumerate(objects):
        if str(old.get('id')) == object_id:
            objects[i] = item; found = True; break
    if not found:
        objects.append(item)
    save_objects_config(objects)

    created = []
    warnings = []
    if 'auto_create_mappings' in request.form:
        created, warnings = object_service.ensure_object_mappings(item)

    msg = f"Objekt gespeichert: {item.get('name') or object_id}"
    if created:
        msg += " | Mappings: " + ", ".join(created)
    if warnings:
        msg += " | Hinweis: " + "; ".join(warnings[:3])
    add_log_entry(msg)
    return redirect('/objects?notice=' + quote(msg))


@app.route('/objects/delete', methods=['POST'])
def objects_delete():
    object_id = request.form.get('id','').strip()
    old_objects = load_objects_config()
    item = next((x for x in old_objects if str(x.get('id')) == object_id), None)
    removed = []
    warnings = []
    if item and 'delete_mappings' in request.form:
        removed, warnings = object_service.cleanup_object_mappings(item)
    objects = [x for x in old_objects if str(x.get('id')) != object_id]
    save_objects_config(objects)
    msg = f"Objekt gelöscht: {object_id}"
    if removed:
        msg += " | entfernt: " + ", ".join(removed)
    if warnings:
        msg += " | Hinweise: " + "; ".join(warnings[:3])
    add_log_entry(msg)
    return redirect('/objects?notice=' + quote(msg))


@app.route('/objects/delete_all', methods=['POST'])
def objects_delete_all():
    count = len(load_objects_config())
    save_objects_config([])
    msg = f"Alle Test-Objekte gelöscht: {count}"
    add_log_entry(msg)
    return redirect('/objects?notice=' + quote(msg))



object_service.bind_context(__import__(__name__))
object_service.normalize_knx_group_address = knx_service.normalize_knx_ga


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8099, debug=False)










