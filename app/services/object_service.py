"""Central object service for MP-Gateway V33."""

import json
import logging
import os
import re
import threading
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

try:
    from app.services.object_adapter_engine import ADAPTER_TYPES, deserialize_adapter
    from app.models.object_model import (
        GatewayObject,
        new_object_id,
        normalize_source_type,
        normalize_target_type,
        object_name_from_address,
        utc_now_iso,
    )
except ModuleNotFoundError:
    from services.object_adapter_engine import ADAPTER_TYPES, deserialize_adapter
    from models.object_model import (
        GatewayObject,
        new_object_id,
        normalize_source_type,
        normalize_target_type,
        object_name_from_address,
        utc_now_iso,
    )


LOGGER = logging.getLogger(__name__)
APP_ROOT = Path(os.environ.get("MQTT2LOX_APP_ROOT", Path.cwd()))
CONFIG_DIR = Path(os.environ.get("MQTT2LOX_CONFIG_DIR", APP_ROOT / "config"))
OBJECTS_FILE = CONFIG_DIR / "objects.json"
OBJECTS_FILE_LOCK = threading.RLock()
OBJECTS_CACHE_LOCK = threading.RLock()
OBJECTS_CACHE: list["GatewayObject"] = []
OBJECTS_CACHE_MTIME = 0.0
OBJECT_ENDPOINT_INDEX_LOCK = threading.RLock()
OBJECT_ENDPOINT_INDEX: dict[str, list["GatewayObject"]] = {}
OBJECT_ENDPOINT_INDEX_MTIME = 0.0
OBJECT_ROUTE_CACHE_LOCK = threading.RLock()
OBJECT_ROUTE_CACHE: dict[str, list[dict[str, Any]]] = {}
OBJECT_ROUTE_CACHE_MTIME = 0.0
OBJECT_ROUTE_EXPORT_CACHE_LOCK = threading.RLock()
OBJECT_ROUTE_EXPORT_CACHE: dict[str, Any] = {}
OBJECT_ROUTE_EXPORT_CACHE_MTIME = 0.0
CORE_FIELDS = {
    "id",
    "name",
    "datatype",
    "unit",
    "enabled",
    "created_at",
    "updated_at",
}
META_FIELDS = {"room", "category", "notes", "icon", "scaling", "legacy_ids"}
LEGACY_FIELDS = {
    "source_type",
    "source_address",
    "target_type",
    "target_address",
    "influx_enabled",
    "type",
    "mqtt_topic",
    "mqtt_json_key",
    "knx_ga",
    "loxone_topic",
    "udp_topic",
    "influx_topic",
    "protocols",
}
SUPPORTED_ROUTE_PAIRS = {
    ("mqtt", "loxone"),
    ("mqtt", "knx"),
    ("mqtt", "udp"),
    ("mqtt", "influx"),
    ("loxone", "mqtt"),
    ("knx", "mqtt"),
    ("knx", "loxone"),
    ("knx", "influx"),
    ("udp", "mqtt"),
    ("udp", "knx"),
    ("udp", "influx"),
}
INTERNAL_OBJECT_ID_RE = re.compile(r"(?:obj_[0-9a-f]{32}|[0-9a-f]{32}|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", re.IGNORECASE)
OBJECT_LIVE_CACHE: dict[str, dict[str, Any]] = {}


def is_internal_object_id(value: Any) -> bool:
    return bool(INTERNAL_OBJECT_ID_RE.fullmatch(str(value or "").strip()))


def _new_unique_object_id(existing_ids: set[str] | None = None) -> str:
    existing_ids = {str(value or "").strip() for value in (existing_ids or set())}
    object_id = new_object_id()
    while object_id in existing_ids:
        object_id = new_object_id()
    return object_id


def _legacy_ids_from_data(data: dict[str, Any], previous_id: str = "") -> list[str]:
    values = []
    raw = data.get("legacy_ids", [])
    if isinstance(raw, str):
        values.extend(part.strip() for part in raw.split(","))
    elif isinstance(raw, list):
        values.extend(str(part or "").strip() for part in raw)
    for key in ("key", "uuid"):
        values.append(str(data.get(key, "") or "").strip())
    if previous_id:
        values.append(str(previous_id or "").strip())
    result = []
    for value in values:
        if value and value not in result and not is_internal_object_id(value):
            result.append(value)
    return result


def _identity_values(item: GatewayObject) -> set[str]:
    values = {str(item.id or "").strip(), str(item.uuid or "").strip(), str(item.key or "").strip()}
    raw = item.meta.get("legacy_ids", [])
    if isinstance(raw, str):
        values.update(part.strip() for part in raw.split(","))
    elif isinstance(raw, list):
        values.update(str(part or "").strip() for part in raw)
    return {value for value in values if value}


def _now_live_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _migrate_raw_object_ids(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    existing_ids = {str(item.get("id", "") or "").strip() for item in items if is_internal_object_id(item.get("id", ""))}
    changed = False
    migrated = []
    for item in items:
        current = dict(item)
        current_id = str(current.get("id", "") or "").strip()
        if not is_internal_object_id(current_id):
            previous_id = current_id or str(current.get("uuid", "") or current.get("key", "") or "").strip()
            new_id = _new_unique_object_id(existing_ids)
            existing_ids.add(new_id)
            current["id"] = new_id
            legacy_ids = _legacy_ids_from_data(current, previous_id)
            if legacy_ids:
                current["legacy_ids"] = legacy_ids
            current.pop("key", None)
            changed = True
            LOGGER.info("Objekt-ID migriert old_id=%s new_id=%s", previous_id, new_id)
        migrated.append(current)
    return migrated, changed


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "on", "ja"}


def _ensure_file() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _objects_file_mtime() -> float:
    try:
        return float(OBJECTS_FILE.stat().st_mtime)
    except OSError:
        return 0.0


def _invalidate_object_caches() -> None:
    global OBJECTS_CACHE_MTIME, OBJECT_ENDPOINT_INDEX_MTIME, OBJECT_ROUTE_CACHE_MTIME, OBJECT_ROUTE_EXPORT_CACHE_MTIME
    with OBJECTS_CACHE_LOCK:
        OBJECTS_CACHE.clear()
        OBJECTS_CACHE_MTIME = 0.0
    with OBJECT_ENDPOINT_INDEX_LOCK:
        OBJECT_ENDPOINT_INDEX.clear()
        OBJECT_ENDPOINT_INDEX_MTIME = 0.0
    with OBJECT_ROUTE_CACHE_LOCK:
        OBJECT_ROUTE_CACHE.clear()
        OBJECT_ROUTE_CACHE_MTIME = 0.0
    with OBJECT_ROUTE_EXPORT_CACHE_LOCK:
        OBJECT_ROUTE_EXPORT_CACHE.clear()
        OBJECT_ROUTE_EXPORT_CACHE_MTIME = 0.0


def _rebuild_object_endpoint_index() -> dict[str, list["GatewayObject"]]:
    global OBJECT_ENDPOINT_INDEX_MTIME
    index = _build_object_endpoint_index()
    with OBJECT_ENDPOINT_INDEX_LOCK:
        OBJECT_ENDPOINT_INDEX.clear()
        OBJECT_ENDPOINT_INDEX.update(index)
        OBJECT_ENDPOINT_INDEX_MTIME = _objects_file_mtime()
        return OBJECT_ENDPOINT_INDEX


def _read_raw() -> list[dict[str, Any]]:
    _ensure_file()
    if not OBJECTS_FILE.exists():
        return []
    try:
        with OBJECTS_FILE.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        LOGGER.exception("objects.json konnte nicht gelesen werden: %s", exc)
        return []
    items = raw.get("objects", raw) if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        LOGGER.warning("objects.json enthaelt keine Liste")
        return []
    clean_items = [item for item in items if isinstance(item, dict)]
    migrated_items, migrated = _migrate_raw_object_ids(clean_items)
    if migrated:
        _write_raw(migrated_items)
    return migrated_items


def _objects_tmp_path() -> Path:
    return OBJECTS_FILE.with_name(f"{OBJECTS_FILE.name}.{uuid4().hex}.tmp")


def _replace_with_retry(tmp_path: Path) -> None:
    attempts = 8
    delay_seconds = 0.12
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            os.replace(tmp_path, OBJECTS_FILE)
            return
        except OSError as exc:
            last_exc = exc
            winerror = getattr(exc, "winerror", None)
            if not isinstance(exc, PermissionError) and winerror not in {5, 32}:
                raise
            if attempt >= attempts:
                break
            time.sleep(delay_seconds)
            delay_seconds = min(delay_seconds + 0.08, 0.3)
    if last_exc is not None:
        raise last_exc


def _write_raw(items: list[dict[str, Any]]) -> None:
    with OBJECTS_FILE_LOCK:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        tmp_path = _objects_tmp_path()
        try:
            with tmp_path.open("w", encoding="utf-8") as handle:
                json.dump(items, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            _replace_with_retry(tmp_path)
            _invalidate_object_caches()
        except OSError as exc:
            LOGGER.exception("objects.json konnte nicht geschrieben werden: %s", exc)
            raise
        finally:
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except OSError:
                pass


def _source_from_legacy(data: dict[str, Any]) -> tuple[str, str]:
    source_address = str(data.get("source_address", "") or "").strip()
    if source_address:
        return normalize_source_type(data.get("source_type", "mqtt")), source_address
    for source_type, key in (
        ("mqtt", "mqtt_topic"),
        ("knx", "knx_ga"),
        ("loxone", "loxone_topic"),
        ("udp", "udp_topic"),
    ):
        value = str(data.get(key, "") or "").strip()
        if value:
            return source_type, value
    return normalize_source_type(data.get("source_type", "mqtt")), str(data.get("source_address", "") or "").strip()


def _serialize_adapter_payload(protocol: str, payload: dict[str, Any], datatype: str) -> dict[str, Any]:
    payload = dict(payload or {})
    payload["protocol"] = protocol
    payload["enabled"] = _as_bool(payload.get("enabled", True), True)
    payload["direction"] = str(payload.get("direction", "both") or "both")
    payload["datatype"] = str(payload.get("datatype", payload.get("value_type", datatype)) or datatype or "auto")
    return deserialize_adapter(payload).serialize()


def _add_adapter(adapters: dict[str, dict[str, Any]], protocol: str, payload: dict[str, Any], datatype: str) -> None:
    protocol = str(protocol or "").strip().lower()
    if protocol not in ADAPTER_TYPES:
        return
    current = dict(adapters.get(protocol, {}))
    current.update({key: value for key, value in dict(payload or {}).items() if value not in (None, "")})
    adapters[protocol] = _serialize_adapter_payload(protocol, current, datatype)


def _normalize_adapters(data: dict[str, Any], datatype: str, existing: GatewayObject | None = None) -> dict[str, dict[str, Any]]:
    adapters: dict[str, dict[str, Any]] = {}
    if existing:
        for adapter in existing.adapters:
            if isinstance(adapter, dict):
                protocol = str(adapter.get("protocol", "") or "").strip().lower()
                payload = adapter
            else:
                protocol = str(getattr(adapter, "protocol", "") or "").strip().lower()
                payload = adapter.serialize() if hasattr(adapter, "serialize") else {}
            _add_adapter(adapters, protocol, payload, datatype)

    raw_adapters = data.get("adapters")
    if isinstance(raw_adapters, dict):
        for protocol, payload in raw_adapters.items():
            payload = payload if isinstance(payload, dict) else {}
            _add_adapter(adapters, protocol, payload, datatype)
    elif isinstance(raw_adapters, list):
        for payload in raw_adapters:
            if not isinstance(payload, dict):
                continue
            _add_adapter(adapters, payload.get("protocol", ""), payload, datatype)

    raw_protocols = data.get("protocols")
    if isinstance(raw_protocols, dict):
        for protocol, payload in raw_protocols.items():
            if isinstance(payload, dict):
                _add_adapter(adapters, protocol, payload, datatype)

    for protocol in ADAPTER_TYPES:
        payload = data.get(protocol)
        if isinstance(payload, dict):
            _add_adapter(adapters, protocol, payload, datatype)

    source_type, source_address = _source_from_legacy(data)
    if source_address and source_type in ADAPTER_TYPES and source_type not in adapters:
        _add_adapter(adapters, source_type, _legacy_adapter_payload(source_type, source_address, datatype, "in"), datatype)

    target_type = normalize_target_type(data.get("target_type", ""))
    target_address = str(data.get("target_address", "") or "").strip()
    if target_address and target_type in ADAPTER_TYPES and target_type not in adapters:
        _add_adapter(adapters, target_type, _legacy_adapter_payload(target_type, target_address, datatype, "out"), datatype)

    influx_topic = str(data.get("influx_topic", "") or "").strip()
    if (influx_topic or _as_bool(data.get("influx_enabled", False), False)) and "influx" not in adapters:
        _add_adapter(adapters, "influx", {"enabled": True, "direction": "out", "measurement": influx_topic, "datatype": datatype}, datatype)

    return adapters


def _legacy_adapter_payload(protocol: str, address: str, datatype: str, direction: str) -> dict[str, Any]:
    payload: dict[str, Any] = {"enabled": True, "direction": direction, "datatype": datatype}
    if protocol == "mqtt":
        payload["topic"] = address
    elif protocol == "knx":
        payload["group_address"] = address
    elif protocol == "loxone":
        payload["uuid"] = address
        payload["io_address"] = address
    elif protocol == "udp":
        payload["format"] = address
    elif protocol == "influx":
        payload["measurement"] = address
    return payload


def _object_from_dict(data: dict[str, Any]) -> GatewayObject:
    source_type, source_address = _source_from_legacy(data)
    now = utc_now_iso()
    object_id = str(data.get("id", "") or "").strip()
    if not is_internal_object_id(object_id):
        object_id = new_object_id()
    name = str(data.get("name", "") or "").strip() or object_name_from_address(source_address)
    datatype = str(data.get("datatype", data.get("type", "auto")) or "auto").strip() or "auto"
    meta = {key: data.get(key, "") for key in META_FIELDS if key in data}
    meta["adapters"] = _normalize_adapters(data, datatype)
    return GatewayObject(
        id=object_id,
        name=name,
        datatype=datatype,
        unit=str(data.get("unit", "") or "").strip(),
        enabled=_as_bool(data.get("enabled", True), True),
        created_at=str(data.get("created_at", "") or now),
        updated_at=str(data.get("updated_at", "") or now),
        meta=meta,
    )


def _object_to_dict(item: GatewayObject) -> dict[str, Any]:
    return item.to_dict()


def _payload_from_data(data: dict[str, Any], existing: GatewayObject | None = None) -> GatewayObject:
    now = utc_now_iso()
    source_type, source_address = _source_from_legacy(data)
    name = str(data.get("name", existing.name if existing else "") or "").strip() or object_name_from_address(source_address)
    datatype = str(data.get("datatype", data.get("type", existing.datatype if existing else "auto")) or "auto").strip() or "auto"
    meta = dict(existing.meta) if existing else {}
    if not existing:
        legacy_ids = _legacy_ids_from_data(data, str(data.get("id", "") or "").strip())
        if legacy_ids:
            meta["legacy_ids"] = legacy_ids
    protocol_keys = tuple(ADAPTER_TYPES.keys())
    if any(key in data for key in ("adapters", "protocols", "source_type", "source_address", "target_type", "target_address", "mqtt_topic", "knx_ga", "loxone_topic", "udp_topic", "influx_topic", *protocol_keys)):
        meta["adapters"] = _normalize_adapters(data, datatype, existing)
    for key in META_FIELDS:
        if key in data:
            meta[key] = data.get(key, "")
    return GatewayObject(
        id=existing.id if existing else (str(data.get("id", "") or "").strip() if is_internal_object_id(data.get("id", "")) else new_object_id()),
        name=name,
        datatype=datatype,
        unit=str(data.get("unit", existing.unit if existing else "") or "").strip(),
        enabled=_as_bool(data.get("enabled", existing.enabled if existing else True), True),
        created_at=str(data.get("created_at", existing.created_at if existing else "") or now),
        updated_at=now,
        meta=meta,
    )


def list_objects() -> list[GatewayObject]:
    global OBJECTS_CACHE_MTIME
    mtime = _objects_file_mtime()
    with OBJECTS_CACHE_LOCK:
        if OBJECTS_CACHE and OBJECTS_CACHE_MTIME == mtime:
            return list(OBJECTS_CACHE)
    objects = []
    for item in _read_raw():
        try:
            objects.append(_object_from_dict(item))
        except Exception as exc:
            LOGGER.exception("Objekt konnte nicht geladen werden: %s", exc)
    with OBJECTS_CACHE_LOCK:
        current_mtime = _objects_file_mtime()
        if OBJECTS_CACHE and OBJECTS_CACHE_MTIME == current_mtime:
            return list(OBJECTS_CACHE)
        OBJECTS_CACHE[:] = objects
        OBJECTS_CACHE_MTIME = current_mtime
        return list(OBJECTS_CACHE)


def _clone_route_export_result(routes: dict[str, list[dict[str, Any]] | dict[str, dict[str, Any]]]) -> dict[str, Any]:
    cloned: dict[str, Any] = {}
    for key, value in (routes or {}).items():
        if isinstance(value, list):
            cloned[key] = [dict(item) if isinstance(item, dict) else deepcopy(item) for item in value]
        elif isinstance(value, dict):
            cloned[key] = {sub_key: dict(sub_value) if isinstance(sub_value, dict) else deepcopy(sub_value) for sub_key, sub_value in value.items()}
        else:
            cloned[key] = deepcopy(value)
    return cloned


def _endpoint_index_key(protocol: str, value: Any) -> str:
    protocol = str(protocol or "").strip().lower()
    value = _normalize_match_value(value)
    if not protocol or not value:
        return ""
    return f"{protocol}:{value}"


def _collect_object_endpoint_keys(item: GatewayObject) -> list[str]:
    keys: list[str] = []
    for protocol, adapter in _adapter_map(item).items():
        if not _is_enabled_adapter(adapter):
            continue
        if protocol == "loxone":
            uuid_value = _normalize_uuid_value(_adapter_value(adapter, "uuid"))
            io_value = _normalize_match_value(_adapter_value(adapter, "io_address"))
            name_value = _normalize_match_value(getattr(item, "name", ""))
            visu_name_value = _normalize_match_value(_adapter_value(adapter, "visu_name"))
            if uuid_value:
                keys.append(_endpoint_index_key("loxone_uuid", uuid_value))
            if io_value:
                keys.append(_endpoint_index_key("loxone_io", io_value))
            if name_value:
                keys.append(_endpoint_index_key("loxone_name", name_value))
            if visu_name_value:
                keys.append(_endpoint_index_key("loxone_name", visu_name_value))
        elif protocol == "mqtt":
            topic = _normalize_match_value(_adapter_value(adapter, "topic"))
            if topic:
                keys.append(_endpoint_index_key("mqtt_topic", topic))
        elif protocol == "knx":
            ga = _normalize_match_value(_adapter_value(adapter, "group_address"))
            if ga:
                keys.append(_endpoint_index_key("knx_ga", ga))
        elif protocol == "udp":
            udp_topic = _normalize_match_value(_adapter_value(adapter, "format"))
            if udp_topic:
                keys.append(_endpoint_index_key("udp_topic", udp_topic))
    return [key for key in keys if key]


def _build_object_endpoint_index() -> dict[str, list[GatewayObject]]:
    index: dict[str, list[GatewayObject]] = {}
    for item in list_objects():
        for key in _collect_object_endpoint_keys(item):
            index.setdefault(key, []).append(item)
    return index


def _get_object_endpoint_index() -> dict[str, list[GatewayObject]]:
    global OBJECT_ENDPOINT_INDEX_MTIME
    with OBJECT_ENDPOINT_INDEX_LOCK:
        mtime = _objects_file_mtime()
        if OBJECT_ENDPOINT_INDEX and OBJECT_ENDPOINT_INDEX_MTIME == mtime:
            return OBJECT_ENDPOINT_INDEX
    return _rebuild_object_endpoint_index()


def build_object(data: dict[str, Any]) -> GatewayObject:
    return _payload_from_data(dict(data or {}))


def get_object(object_id: str) -> GatewayObject | None:
    needle = str(object_id or "").strip()
    if not needle:
        return None
    for item in list_objects():
        if needle in _identity_values(item):
            return item
    return None


def create_object(data: dict[str, Any]) -> GatewayObject:
    with OBJECTS_FILE_LOCK:
        objects = [_object_from_dict(item) for item in _read_raw()]
        item = _payload_from_data(dict(data or {}))
        existing_ids = {obj.id for obj in objects}
        while item.id in existing_ids:
            item.id = _new_unique_object_id(existing_ids)
        objects.append(item)
        _write_raw([_object_to_dict(obj) for obj in objects])
        clear_object_runtime_state()
    _rebuild_object_endpoint_index()
    return item


def update_object(object_id: str, data: dict[str, Any]) -> GatewayObject | None:
    with OBJECTS_FILE_LOCK:
        objects = [_object_from_dict(item) for item in _read_raw()]
        for index, current in enumerate(objects):
            if str(object_id or "").strip() in _identity_values(current):
                payload = dict(data or {})
                payload["id"] = current.id
                objects[index] = _payload_from_data(payload, current)
                _write_raw([_object_to_dict(obj) for obj in objects])
                clear_object_runtime_state()
                updated = objects[index]
                break
        else:
            return None
    _rebuild_object_endpoint_index()
    return updated


def delete_object(object_id: str) -> bool:
    with OBJECTS_FILE_LOCK:
        needle = str(object_id or "").strip()
        if not needle:
            return False

        objects = [_object_from_dict(item) for item in _read_raw()]
        remaining: list[GatewayObject] = []
        deleted_cache_ids: list[str] = []
        deleted = False
        for item in objects:
            if needle in _identity_values(item):
                deleted = True
                deleted_cache_ids.append(item.id)
                raw_legacy_ids = item.meta.get("legacy_ids", [])
                if isinstance(raw_legacy_ids, str):
                    deleted_cache_ids.extend(part.strip() for part in raw_legacy_ids.split(",") if part.strip())
                elif isinstance(raw_legacy_ids, list):
                    deleted_cache_ids.extend(str(value or "").strip() for value in raw_legacy_ids if str(value or "").strip())
                continue
            remaining.append(item)

        if not deleted:
            return False

        _write_raw([_object_to_dict(obj) for obj in remaining])
        clear_object_live_statuses(*deleted_cache_ids)
        clear_object_runtime_state()
    _rebuild_object_endpoint_index()
    return True


def clear_object_live_status(object_id: str) -> None:
    object_id = str(object_id or "").strip()
    if object_id:
        OBJECT_LIVE_CACHE.pop(object_id, None)


def clear_object_live_statuses(*object_ids: str) -> bool:
    cleared = False
    for object_id in object_ids:
        object_id = str(object_id or "").strip()
        if not object_id:
            continue
        if OBJECT_LIVE_CACHE.pop(object_id, None) is not None:
            cleared = True
    return cleared


def clear_object_runtime_state() -> bool:
    cleared = bool(OBJECT_LIVE_CACHE)
    OBJECT_LIVE_CACHE.clear()
    return cleared


def toggle_object(object_id: str, enabled: bool) -> GatewayObject | None:
    return update_object(object_id, {"enabled": bool(enabled)})


def serialize_object(item: GatewayObject) -> dict[str, Any]:
    payload = _object_to_dict(item)
    payload["route_status"] = get_object_route_status(item)
    payload["route_report"] = get_object_route_report(item)
    return payload


def _live_empty(item: GatewayObject | None, object_id: str = "") -> dict[str, Any]:
    resolved_id = str(getattr(item, "id", "") or object_id or "").strip()
    return {
        "object_id": resolved_id,
        "value": None,
        "unit": str(getattr(item, "unit", "") or ""),
        "source": "unbekannt",
        "source_address": "",
        "recognized_endpoint": "",
        "timestamp": "",
        "targets": [],
        "status": "unbekannt",
    }


def _live_targets(item: GatewayObject, source: str) -> list[str]:
    source = str(source or "").strip().lower()
    targets = []
    for protocol, adapter in _adapter_map(item).items():
        if protocol == source:
            continue
        if _is_enabled_adapter(adapter):
            targets.append(protocol)
    return sorted(set(targets))


def _live_unit(item: GatewayObject, source: str = "") -> str:
    unit = str(getattr(item, "unit", "") or "").strip()
    if unit:
        return unit
    adapter = _adapter_map(item).get(str(source or "").strip().lower())
    return _adapter_value(adapter, "unit") if adapter else ""


def _object_matches_live_source(item: GatewayObject, source: str, **endpoint: Any) -> bool:
    source = str(source or "").strip().lower()
    adapters = _adapter_map(item)
    adapter = adapters.get(source)
    if not adapter:
        return False
    if source == "mqtt":
        topic = _normalize_match_value(endpoint.get("topic"))
        return bool(topic and _normalize_match_value(_adapter_value(adapter, "topic")) == topic)
    if source == "loxone":
        uuid_value = _normalize_uuid_value(endpoint.get("loxone_uuid") or endpoint.get("uuid"))
        io_value = _normalize_match_value(endpoint.get("loxone_io") or endpoint.get("io_address") or endpoint.get("name"))
        adapter_uuid = _normalize_uuid_value(_adapter_value(adapter, "uuid"))
        adapter_io = _normalize_match_value(_adapter_value(adapter, "io_address"))
        return bool((uuid_value and adapter_uuid and uuid_value == adapter_uuid) or (io_value and adapter_io and io_value == adapter_io))
    if source == "knx":
        ga = _normalize_match_value(endpoint.get("group_address") or endpoint.get("ga"))
        return bool(ga and _normalize_match_value(_adapter_value(adapter, "group_address")) == ga)
    if source == "udp":
        topic = _normalize_match_value(endpoint.get("udp_topic") or endpoint.get("topic") or endpoint.get("format"))
        return bool(topic and _normalize_match_value(_adapter_value(adapter, "format")) == topic)
    return False


def _live_lookup_candidates(source: str, **endpoint: Any) -> list[tuple[str, str, str]]:
    source = str(source or "").strip().lower()
    if source == "loxone":
        uuid_value = _normalize_uuid_value(endpoint.get("loxone_uuid") or endpoint.get("uuid"))
        io_value = _normalize_match_value(endpoint.get("loxone_io") or endpoint.get("io_address") or endpoint.get("io") or endpoint.get("name"))
        name_value = _normalize_match_value(endpoint.get("name") or endpoint.get("visu_name"))
        return [
            ("loxone_uuid", uuid_value, "loxone.uuid"),
            ("loxone_io", io_value, "loxone.io_address"),
            ("loxone_name", name_value, "object.name"),
        ]
    if source == "mqtt":
        topic = _normalize_match_value(endpoint.get("topic"))
        return [("mqtt_topic", topic, "mqtt.topic")]
    if source == "knx":
        ga = _normalize_match_value(endpoint.get("group_address") or endpoint.get("ga"))
        return [("knx_ga", ga, "knx.group_address")]
    if source == "udp":
        udp_topic = _normalize_match_value(endpoint.get("udp_topic") or endpoint.get("topic") or endpoint.get("format"))
        return [("udp_topic", udp_topic, "udp.topic")]
    return [
        ("loxone_uuid", _normalize_uuid_value(endpoint.get("loxone_uuid") or endpoint.get("uuid")), "loxone.uuid"),
        ("loxone_io", _normalize_match_value(endpoint.get("loxone_io") or endpoint.get("io_address") or endpoint.get("io") or endpoint.get("name")), "loxone.io_address"),
        ("mqtt_topic", _normalize_match_value(endpoint.get("topic")), "mqtt.topic"),
        ("knx_ga", _normalize_match_value(endpoint.get("group_address") or endpoint.get("ga")), "knx.group_address"),
        ("udp_topic", _normalize_match_value(endpoint.get("udp_topic") or endpoint.get("topic") or endpoint.get("format")), "udp.topic"),
    ]


def _live_debug_snapshot(item: GatewayObject) -> dict[str, Any]:
    adapters = _adapter_map(item)
    loxone = adapters.get("loxone")
    mqtt = adapters.get("mqtt")
    knx = adapters.get("knx")
    udp = adapters.get("udp")
    return {
        "object_id": item.id,
        "name": item.name,
        "loxone": {
            "uuid": _adapter_value(loxone, "uuid") if loxone else "",
            "io_address": _adapter_value(loxone, "io_address") if loxone else "",
            "name": _adapter_value(loxone, "visu_name") if loxone else "",
        },
        "mqtt": {
            "topic": _adapter_value(mqtt, "topic") if mqtt else "",
        },
        "knx": {
            "group_address": _adapter_value(knx, "group_address") if knx else "",
        },
        "udp": {
            "address": _endpoint_address("udp", udp) if udp else "",
            "format": _adapter_value(udp, "format") if udp else "",
        },
    }


def record_live_value(source: str, value: Any, timestamp: str = "", **endpoint: Any) -> list[dict[str, Any]]:
    """Record a runtime-only live value for all objects matching the source endpoint."""
    source = str(source or "").strip().lower() or "unbekannt"
    timestamp = str(timestamp or "").strip() or _now_live_iso()
    updates = []
    index = _get_object_endpoint_index()
    lookup_candidates = _live_lookup_candidates(source, **endpoint)
    matched_items: list[tuple[GatewayObject, str, str]] = []
    seen_ids = set()
    for key, raw_value, endpoint_name in lookup_candidates:
        key = _endpoint_index_key(key, raw_value)
        if not key:
            continue
        for item in index.get(key, []):
            if item.id in seen_ids:
                continue
            seen_ids.add(item.id)
            matched_items.append((item, raw_value, endpoint_name))
    for item, source_address, recognized_endpoint in matched_items:
        payload = {
            "object_id": item.id,
            "value": value,
            "unit": _live_unit(item, source),
            "source": source,
            "source_address": source_address,
            "recognized_endpoint": recognized_endpoint,
            "timestamp": timestamp,
            "targets": _live_targets(item, source),
            "status": "online",
        }
        OBJECT_LIVE_CACHE[item.id] = payload
        updates.append(dict(payload))
    if source == "loxone" and not matched_items:
        all_objects = list(list_objects())
        LOGGER.info(
            "Live value not matched source=%s value=%s loxone_uuid=%s loxone_io=%s name=%s mqtt_topic=%s knx_ga=%s udp_address=%s object_id=%s objects=%s object_fields=%s",
            source,
            value,
            endpoint.get("loxone_uuid") or endpoint.get("uuid") or "",
            endpoint.get("loxone_io") or endpoint.get("io_address") or "",
            endpoint.get("name") or endpoint.get("visu_name") or "",
            endpoint.get("topic") or "",
            endpoint.get("group_address") or endpoint.get("ga") or "",
            endpoint.get("udp_topic") or endpoint.get("topic") or endpoint.get("format") or "",
            endpoint.get("object_id") or "",
            len({item.id for bucket in index.values() for item in bucket}),
            [_live_debug_snapshot(item) for item in all_objects[:10]],
        )
    return updates


def get_object_live_status(object_id: str) -> dict[str, Any] | None:
    item = get_object(object_id)
    if item is None:
        return None
    return dict(OBJECT_LIVE_CACHE.get(item.id) or _live_empty(item))


def list_object_live_status() -> list[dict[str, Any]]:
    result = []
    for item in list_objects():
        result.append(dict(OBJECT_LIVE_CACHE.get(item.id) or _live_empty(item)))
    return result


def _adapter_map(item: GatewayObject) -> dict[str, Any]:
    adapters = {}
    for adapter in item.adapters:
        if isinstance(adapter, dict):
            adapter = deserialize_adapter(adapter)
        protocol = str(getattr(adapter, "protocol", "") or "").strip().lower()
        if protocol:
            adapters[protocol] = adapter
    return adapters


def _adapter_value(adapter: Any, name: str) -> str:
    return str(getattr(adapter, name, "") or "").strip()


def _normalize_match_value(value: Any) -> str:
    return str(value or "").strip().lower()


def _normalize_uuid_value(value: Any) -> str:
    return _normalize_match_value(value).replace("-", "")


def _endpoint_address(protocol: str, adapter: Any) -> str:
    if protocol == "mqtt":
        return _adapter_value(adapter, "topic")
    if protocol == "loxone":
        return _adapter_value(adapter, "io_address") or _adapter_value(adapter, "uuid")
    if protocol == "knx":
        return _adapter_value(adapter, "group_address")
    if protocol == "udp":
        topic = _adapter_value(adapter, "format")
        host = _adapter_value(adapter, "target_ip")
        port = _adapter_value(adapter, "target_port")
        return f"{topic}@{host}:{port}" if topic and host and port else ""
    if protocol == "influx":
        return _adapter_value(adapter, "measurement")
    return ""


def _endpoint_missing_fields(protocol: str, adapter: Any) -> list[str]:
    required = {
        "mqtt": (("topic", "Topic"),),
        "loxone": (),
        "knx": (("group_address", "Gruppenadresse"),),
        "udp": (("format", "Topic/Format"), ("target_ip", "Ziel-IP"), ("target_port", "Ziel-Port")),
        "influx": (("measurement", "Measurement"),),
    }.get(protocol, ())
    if protocol == "loxone":
        return [] if (_adapter_value(adapter, "uuid") or _adapter_value(adapter, "io_address")) else ["UUID oder IO-Adresse"]
    return [label for field, label in required if not _adapter_value(adapter, field)]


def _is_enabled_adapter(adapter: Any) -> bool:
    return bool(getattr(adapter, "enabled", False))


def _is_complete_endpoint(protocol: str, adapter: Any) -> bool:
    return _is_enabled_adapter(adapter) and not _endpoint_missing_fields(protocol, adapter)


def _adapter_config_errors(protocol: str, adapter: Any) -> list[str]:
    errors = []
    if protocol not in ADAPTER_TYPES:
        errors.append(f"Unbekanntes Protokoll: {protocol}")
    direction = str(getattr(adapter, "direction", "both") or "both").strip().lower()
    if direction not in {"in", "out", "both"}:
        errors.append(f"{protocol.upper()}: ungueltige Richtung {direction}")
    datatype = str(getattr(adapter, "datatype", "auto") or "auto").strip()
    if not datatype:
        errors.append(f"{protocol.upper()}: Datentyp fehlt")
    return errors


def _can_source(adapter: Any) -> bool:
    protocol = str(getattr(adapter, "protocol", "") or "").strip().lower()
    direction = str(getattr(adapter, "direction", "both") or "both").strip().lower()
    return protocol != "influx" and direction in {"in", "both"}


def _can_target(adapter: Any) -> bool:
    direction = str(getattr(adapter, "direction", "both") or "both").strip().lower()
    return direction in {"out", "both"}


def get_object_route_status(item: GatewayObject) -> str:
    if not item.enabled:
        return "deaktiviert"
    adapters = _adapter_map(item)
    errors = []
    complete_count = 0
    for protocol, adapter in adapters.items():
        if not _is_enabled_adapter(adapter):
            continue
        errors.extend(_adapter_config_errors(protocol, adapter))
        if _is_complete_endpoint(protocol, adapter):
            complete_count += 1
    if errors:
        return "fehler"
    return "aktiv" if complete_count >= 2 else "unvollständig"


def build_generated_route_entries(item: GatewayObject) -> list[dict[str, str]]:
    adapters = {
        protocol: adapter
        for protocol, adapter in _adapter_map(item).items()
        if _is_complete_endpoint(protocol, adapter)
    }
    entries = []
    for source, source_adapter in adapters.items():
        if not _can_source(source_adapter):
            continue
        for target, target_adapter in adapters.items():
            if source == target or not _can_target(target_adapter):
                continue
            if (source, target) not in SUPPORTED_ROUTE_PAIRS:
                continue
            entries.append(
                {
                    "source": source.upper(),
                    "target": target.upper(),
                    "source_address": _endpoint_address(source, source_adapter),
                    "target_address": _endpoint_address(target, target_adapter),
                    "direction": f"{source.upper()} -> {target.upper()}",
                    "status": "aktiv",
                }
            )
    return entries


def get_object_route_report(item: GatewayObject) -> dict[str, Any]:
    adapters = _adapter_map(item)
    missing = []
    errors = []
    for protocol in ("mqtt", "loxone", "udp", "knx", "influx"):
        adapter = adapters.get(protocol)
        if not adapter or not _is_enabled_adapter(adapter):
            missing.append(f"{protocol.upper()} inaktiv")
            continue
        errors.extend(_adapter_config_errors(protocol, adapter))
        fields = _endpoint_missing_fields(protocol, adapter)
        if fields:
            missing.append(f"{protocol.upper()}: " + ", ".join(fields))

    complete_count = sum(
        1 for protocol, adapter in adapters.items()
        if _is_complete_endpoint(protocol, adapter)
    )
    if complete_count >= 2:
        missing = [entry for entry in missing if not entry.endswith("inaktiv")]
    return {
        "status": get_object_route_status(item),
        "routes": build_generated_route_entries(item),
        "missing_endpoints": missing,
        "errors": errors,
    }


def _route_lookup_key(kind: str, value: Any) -> str:
    value = _normalize_match_value(value)
    if not value:
        return ""
    return f"{kind}:{value}"


def _build_loxone_to_mqtt_route_index() -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for item in list_objects():
        if get_object_route_status(item) != "aktiv":
            continue
        adapters = _adapter_map(item)
        loxone_adapter = adapters.get("loxone")
        mqtt_adapter = adapters.get("mqtt")
        if not loxone_adapter or not mqtt_adapter:
            continue
        if not _is_complete_endpoint("loxone", loxone_adapter) or not _is_complete_endpoint("mqtt", mqtt_adapter):
            continue
        if not _can_source(loxone_adapter) or not _can_target(mqtt_adapter):
            continue
        route = {
            "object_id": item.id,
            "object_name": item.name,
            "mqtt_topic": _adapter_value(mqtt_adapter, "topic"),
            "retain": bool(getattr(mqtt_adapter, "retain", False)),
            "loxone_uuid": _adapter_value(loxone_adapter, "uuid"),
            "loxone_io": _adapter_value(loxone_adapter, "io_address"),
        }
        for key in (
            _route_lookup_key("uuid", route["loxone_uuid"]),
            _route_lookup_key("io", route["loxone_io"]),
            _route_lookup_key("name", item.name),
        ):
            if not key:
                continue
            index.setdefault(key, []).append(route)
    return index


def _get_loxone_to_mqtt_route_index() -> dict[str, list[dict[str, Any]]]:
    global OBJECT_ROUTE_CACHE_MTIME
    with OBJECT_ROUTE_CACHE_LOCK:
        mtime = _objects_file_mtime()
        if OBJECT_ROUTE_CACHE and OBJECT_ROUTE_CACHE_MTIME == mtime:
            return OBJECT_ROUTE_CACHE
        OBJECT_ROUTE_CACHE.clear()
        OBJECT_ROUTE_CACHE.update(_build_loxone_to_mqtt_route_index())
        OBJECT_ROUTE_CACHE_MTIME = _objects_file_mtime()
        return OBJECT_ROUTE_CACHE


def _route_base(item: GatewayObject, source_topic: str) -> dict[str, Any]:
    return {
        "enabled": True,
        "source_topic": source_topic,
        "mapping_alias": item.name,
        "group": "Objektmanager V33",
        "set_name": item.name or item.id,
        "__object_route": True,
        "__object_id": item.id,
    }


def build_routes_from_objects(log_func=None) -> dict[str, list[dict[str, Any]] | dict[str, dict[str, Any]]]:
    global OBJECT_ROUTE_EXPORT_CACHE_MTIME
    with OBJECT_ROUTE_EXPORT_CACHE_LOCK:
        mtime = _objects_file_mtime()
        if log_func is None and OBJECT_ROUTE_EXPORT_CACHE and OBJECT_ROUTE_EXPORT_CACHE_MTIME == mtime:
            return _clone_route_export_result(OBJECT_ROUTE_EXPORT_CACHE)

    objects = list_objects()
    routes: dict[str, Any] = {
        "mqtt2lox": [],
        "mqtt2udp": [],
        "mqtt2knx": [],
        "loxone2mqtt": [],
        "knx2mqtt": [],
        "udp2mqtt": [],
        "udp2knx": [],
        "knx2lox": [],
        "topic_config": {},
    }
    active = 0
    skipped = 0
    errors: list[str] = []

    for item in objects:
        name = item.name or item.id
        try:
            if get_object_route_status(item) != "aktiv":
                skipped += 1
                continue

            adapters = _adapter_map(item)
            for entry in build_generated_route_entries(item):
                source = entry["source"].lower()
                target = entry["target"].lower()
                source_adapter = adapters[source]
                target_adapter = adapters[target]
                base = _route_base(item, entry["source_address"])
                if source == "mqtt" and target == "loxone":
                    route = dict(base)
                    route.update({"loxone_io": _adapter_value(target_adapter, "io_address") or _adapter_value(target_adapter, "uuid"), "payload_mode": "raw", "json_key": "", "output_mode": "single", "test_value": "1"})
                    routes["mqtt2lox"].append(route)
                    active += 1
                elif source == "loxone" and target == "mqtt":
                    routes["loxone2mqtt"] = routes.get("loxone2mqtt", [])
                    routes["loxone2mqtt"].append({"enabled": True, "loxone_uuid": _adapter_value(source_adapter, "uuid"), "loxone_io": _adapter_value(source_adapter, "io_address"), "mqtt_topic": _adapter_value(target_adapter, "topic"), "retain": bool(getattr(target_adapter, "retain", False)), "group": "Objektmanager V33", "set_name": item.name or item.id, "mapping_alias": item.name, "__object_route": True, "__object_id": item.id})
                    active += 1
                elif source == "mqtt" and target == "knx":
                    route = dict(base)
                    route.update({"group_address": _adapter_value(target_adapter, "group_address"), "dpt": _adapter_value(target_adapter, "dpt"), "payload_mode": "raw", "json_key": "", "invert": False, "test_value": "1"})
                    routes["mqtt2knx"].append(route)
                    active += 1
                elif source == "mqtt" and target == "udp":
                    route = dict(base)
                    route.update({"udp_topic": _adapter_value(target_adapter, "format"), "udp_ip": _adapter_value(target_adapter, "target_ip"), "udp_port": _adapter_value(target_adapter, "target_port"), "udp_format": "topic_value", "payload_mode": "raw", "json_key": "", "test_value": "1"})
                    routes["mqtt2udp"].append(route)
                    active += 1
                elif source == "mqtt" and target == "influx":
                    routes["topic_config"][_adapter_value(source_adapter, "topic")] = {"enabled": True, "influx": True, "influx_topic": _adapter_value(target_adapter, "measurement"), "influx_value_type": getattr(target_adapter, "datatype", item.datatype) or "auto", "__object_route": True, "__object_id": item.id}
                    active += 1
                elif source == "knx" and target == "mqtt":
                    routes["knx2mqtt"].append({"enabled": True, "group_address": _adapter_value(source_adapter, "group_address"), "mqtt_topic": _adapter_value(target_adapter, "topic"), "dpt": _adapter_value(source_adapter, "dpt"), "retain": bool(getattr(target_adapter, "retain", True)), "invert": False, "group": "Objektmanager V33", "set_name": item.name or item.id, "mapping_alias": item.name, "__object_route": True, "__object_id": item.id})
                    active += 1
                elif source == "knx" and target == "loxone":
                    routes["knx2lox"].append({"enabled": True, "group_address": _adapter_value(source_adapter, "group_address"), "loxone_io": _adapter_value(target_adapter, "io_address") or _adapter_value(target_adapter, "uuid"), "dpt": _adapter_value(source_adapter, "dpt"), "invert": False, "group": "Objektmanager V33", "set_name": item.name or item.id, "mapping_alias": item.name, "__object_route": True, "__object_id": item.id})
                    active += 1
                elif source == "knx" and target == "influx":
                    topic = f"knx/{_adapter_value(source_adapter, 'group_address')}"
                    routes["topic_config"][topic] = {"enabled": True, "influx": True, "influx_topic": _adapter_value(target_adapter, "measurement"), "influx_value_type": getattr(target_adapter, "datatype", item.datatype) or "auto", "__object_route": True, "__object_id": item.id}
                    active += 1
                elif source == "udp" and target == "mqtt":
                    routes["udp2mqtt"].append({"enabled": True, "source_topic": _adapter_value(source_adapter, "format"), "mqtt_topic": _adapter_value(target_adapter, "topic"), "retain": bool(getattr(target_adapter, "retain", False)), "test_value": "123", "group": "Objektmanager V33", "set_name": item.name or item.id, "mapping_alias": item.name, "__object_route": True, "__object_id": item.id})
                    active += 1
                elif source == "udp" and target == "knx":
                    routes["udp2knx"].append({"enabled": True, "source_topic": _adapter_value(source_adapter, "format"), "group_address": _adapter_value(target_adapter, "group_address"), "dpt": _adapter_value(target_adapter, "dpt"), "invert": False, "test_value": "1", "group": "Objektmanager V33", "set_name": item.name or item.id, "mapping_alias": item.name, "__object_route": True, "__object_id": item.id})
                    active += 1
                elif source == "udp" and target == "influx":
                    routes["topic_config"][_adapter_value(source_adapter, "format")] = {"enabled": True, "influx": True, "influx_topic": _adapter_value(target_adapter, "measurement"), "influx_value_type": getattr(target_adapter, "datatype", item.datatype) or "auto", "__object_route": True, "__object_id": item.id}
                    active += 1
        except Exception as exc:
            skipped += 1
            errors.append(f"{name}/{item.id}: {exc}")

    if log_func:
        log_func(f"Objektrouten: gesamt={len(objects)}, aktiv={active}, übersprungen={skipped}")
        for message in errors:
            log_func(f"Objektroute Fehler {message}")

    with OBJECT_ROUTE_EXPORT_CACHE_LOCK:
        OBJECT_ROUTE_EXPORT_CACHE.clear()
        OBJECT_ROUTE_EXPORT_CACHE.update(_clone_route_export_result(routes))
        OBJECT_ROUTE_EXPORT_CACHE_MTIME = _objects_file_mtime()

    return routes


def find_loxone_to_mqtt_route(loxone_uuid: str = "", loxone_io: str = "", state_name: str = "") -> dict[str, Any] | None:
    """Return the active object route that permits publishing a Loxone state to MQTT."""
    route_index = _get_loxone_to_mqtt_route_index()
    candidates = [
        _route_lookup_key("uuid", loxone_uuid),
        _route_lookup_key("io", loxone_io),
        _route_lookup_key("name", state_name),
    ]
    seen_keys = set()
    for key in candidates:
        if not key or key in seen_keys:
            continue
        seen_keys.add(key)
        routes = route_index.get(key) or []
        if routes:
            return dict(routes[0])
    return None
