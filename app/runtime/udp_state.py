from dataclasses import dataclass, field
from threading import RLock


@dataclass
class UDPState:
    mqtt2udp_last_seen: dict = field(default_factory=dict)
    udp2mqtt_last_seen: dict = field(default_factory=dict)
    udp2knx_last_seen: dict = field(default_factory=dict)
    udp_input_last_seen: dict = field(default_factory=dict)
    discovery_state: dict = field(default_factory=dict)
    discovery_enabled: bool = False
    listener_running: bool = False
    stop_requested: bool = False
    listener_thread: object = None
    status: str = "stopped"
    lock: RLock = field(default_factory=RLock)
