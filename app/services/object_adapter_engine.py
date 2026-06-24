"""Passive V33 object adapter interface.

Adapters provide validation and serialization hooks only. They do not open
network connections and are not connected to routes or runtime state.
"""

from dataclasses import dataclass
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
        return {
            "protocol": self.protocol,
            "enabled": bool(self.enabled),
            "direction": str(self.direction or "both"),
            "datatype": str(self.datatype or "auto"),
        }

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> "BaseAdapter":
        return cls(
            enabled=bool(data.get("enabled", True)),
            direction=str(data.get("direction", "both") or "both"),
            datatype=str(data.get("datatype", data.get("value_type", "auto")) or "auto"),
        )


@dataclass
class MQTTAdapter(BaseAdapter):
    protocol: ClassVar[str] = "mqtt"


@dataclass
class LoxoneAdapter(BaseAdapter):
    protocol: ClassVar[str] = "loxone"


@dataclass
class UDPAdapter(BaseAdapter):
    protocol: ClassVar[str] = "udp"


@dataclass
class KNXAdapter(BaseAdapter):
    protocol: ClassVar[str] = "knx"


@dataclass
class InfluxAdapter(BaseAdapter):
    protocol: ClassVar[str] = "influx"


def _register(adapter_cls: type[BaseAdapter]) -> type[BaseAdapter]:
    ADAPTER_TYPES[adapter_cls.protocol] = adapter_cls
    return adapter_cls


for _adapter_cls in (MQTTAdapter, LoxoneAdapter, UDPAdapter, KNXAdapter, InfluxAdapter):
    _register(_adapter_cls)


def deserialize_adapter(data: dict[str, Any]) -> BaseAdapter:
    protocol = str(data.get("protocol", "") or "").strip().lower()
    adapter_cls = ADAPTER_TYPES.get(protocol, BaseAdapter)
    return adapter_cls.deserialize(data)
