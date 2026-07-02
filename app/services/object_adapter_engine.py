"""Passive V33 object adapter interface.

Adapters provide validation and serialization hooks only. They do not open
network connections and are not connected to routes or runtime state.
"""

from dataclasses import dataclass, fields
from typing import Any, ClassVar

try:
    from app.services.object_model import is_supported_direction
except ModuleNotFoundError:
    from services.object_model import is_supported_direction


ADAPTER_TYPES: dict[str, type["BaseAdapter"]] = {}


@dataclass
class BaseAdapter:
    """Common adapter interface for future object-centric protocol bindings."""

    enabled: bool = True
    direction: str = "both"
    datatype: str = "auto"

    protocol: ClassVar[str] = "base"

    def validate(self) -> list[str]:
        errors = []
        if not is_supported_direction(self.direction):
            errors.append(f"Unsupported direction: {self.direction}")
        if not str(self.datatype or "").strip():
            errors.append("Datatype is required")
        return errors

    def serialize(self) -> dict[str, Any]:
        payload = {"protocol": self.protocol}
        for field in fields(self):
            value = getattr(self, field.name)
            payload[field.name] = value
        payload["enabled"] = bool(payload.get("enabled", True))
        payload["direction"] = str(payload.get("direction") or "both")
        payload["datatype"] = str(payload.get("datatype") or "auto")
        return payload

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> "BaseAdapter":
        values = {
            "enabled": bool(data.get("enabled", True)),
            "direction": str(data.get("direction", "both") or "both"),
            "datatype": str(data.get("datatype", data.get("value_type", "auto")) or "auto"),
        }
        for field in fields(cls):
            if field.name in values:
                continue
            if field.name in data:
                values[field.name] = data.get(field.name)
        return cls(**values)


@dataclass
class MQTTAdapter(BaseAdapter):
    protocol: ClassVar[str] = "mqtt"
    topic: str = ""
    qos: int = 0
    retain: bool = False
    json_key: str = ""


@dataclass
class LoxoneAdapter(BaseAdapter):
    protocol: ClassVar[str] = "loxone"
    uuid: str = ""
    io_address: str = ""
    control_type: str = ""
    visu_name: str = ""
    room: str = ""
    unit: str = ""
    source_uuid: str = ""
    source_name: str = ""
    target_uuid: str = ""
    target_name: str = ""
    target_room: str = ""
    target_category: str = ""
    target_type: str = ""

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> "LoxoneAdapter":
        payload = dict(data or {})
        payload.setdefault("source_uuid", payload.get("uuid", ""))
        payload.setdefault("source_name", payload.get("visu_name", payload.get("name", "")))
        payload.setdefault("target_uuid", payload.get("target_uuid", ""))
        payload.setdefault("target_name", payload.get("target_name", ""))
        payload.setdefault("target_room", payload.get("target_room", payload.get("room", "")))
        payload.setdefault("target_category", payload.get("target_category", payload.get("category", "")))
        payload.setdefault("target_type", payload.get("target_type", payload.get("control_type", payload.get("type", ""))))
        adapter = super().deserialize(payload)
        if not str(adapter.source_uuid or "").strip():
            adapter.source_uuid = str(adapter.uuid or "").strip()
        if not str(adapter.source_name or "").strip():
            adapter.source_name = str(adapter.visu_name or "").strip()
        if not str(adapter.target_room or "").strip():
            adapter.target_room = str(adapter.room or "").strip()
        if not str(adapter.target_category or "").strip():
            adapter.target_category = str(data.get("category", "") or "").strip()
        if not str(adapter.target_type or "").strip():
            adapter.target_type = str(adapter.control_type or "").strip() or str(data.get("type", "") or "").strip()
        if str(adapter.uuid or "").strip() == "" and str(adapter.source_uuid or "").strip():
            adapter.uuid = str(adapter.source_uuid or "").strip()
        return adapter


@dataclass
class UDPAdapter(BaseAdapter):
    protocol: ClassVar[str] = "udp"
    target_ip: str = ""
    target_port: str = ""
    format: str = "text"
    udp_topic: str = ""
    payload_mode: str = "topic_value"

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> "UDPAdapter":
        payload = dict(data or {})
        if "udp_topic" not in payload:
            legacy_format = str(payload.get("format", "") or "").strip()
            if legacy_format and legacy_format not in {"text", "topic_value", "value_only", "json", "json_number"}:
                payload["udp_topic"] = legacy_format
        return super().deserialize(payload)


@dataclass
class KNXAdapter(BaseAdapter):
    protocol: ClassVar[str] = "knx"
    group_address: str = ""
    dpt: str = ""

    def validate(self) -> list[str]:
        errors = super().validate()
        if not str(self.group_address or "").strip():
            errors.append("KNX: Gruppenadresse fehlt")
        if not str(self.dpt or "").strip():
            errors.append("KNX: DPT fehlt")
        return errors


@dataclass
class InfluxAdapter(BaseAdapter):
    protocol: ClassVar[str] = "influx"
    bucket: str = ""
    measurement: str = ""
    field: str = ""
    topic: str = ""
    tags: str = ""


def _register(adapter_cls: type[BaseAdapter]) -> type[BaseAdapter]:
    ADAPTER_TYPES[adapter_cls.protocol] = adapter_cls
    return adapter_cls


for _adapter_cls in (MQTTAdapter, LoxoneAdapter, UDPAdapter, KNXAdapter, InfluxAdapter):
    _register(_adapter_cls)


def deserialize_adapter(data: dict[str, Any]) -> BaseAdapter:
    protocol = str(data.get("protocol", "") or "").strip().lower()
    adapter_cls = ADAPTER_TYPES.get(protocol, BaseAdapter)
    return adapter_cls.deserialize(data)


def adapter_from_form(protocol: str, form_data: Any) -> BaseAdapter:
    """Build a passive adapter instance from an adapter editor form."""
    protocol = str(protocol or "").strip().lower()
    payload = {
        "protocol": protocol,
        "enabled": "enabled" in form_data,
        "direction": form_data.get("direction", "both"),
        "datatype": form_data.get("datatype", "auto"),
    }
    adapter_cls = ADAPTER_TYPES.get(protocol, BaseAdapter)
    for field in fields(adapter_cls):
        if field.name in payload:
            continue
        if field.name in form_data:
            payload[field.name] = form_data.get(field.name, "")
    if protocol == "mqtt":
        payload["retain"] = "retain" in form_data
        try:
            payload["qos"] = int(form_data.get("qos", 0) or 0)
        except (TypeError, ValueError):
            payload["qos"] = 0
    return deserialize_adapter(payload)


def adapter_template_name(protocol: str) -> str:
    protocol = str(protocol or "").strip().lower()
    if protocol not in ADAPTER_TYPES:
        return "objects_v33/adapters/base.html"
    return f"objects_v33/adapters/{protocol}.html"
