from collections import deque
from dataclasses import dataclass, field
from threading import RLock


@dataclass
class KNXState:
    monitor_log: deque = field(default_factory=lambda: deque(maxlen=15))
    monitor_values: dict = field(default_factory=dict)
    mqtt2knx_last_seen: dict = field(default_factory=dict)
    knx2mqtt_last_seen: dict = field(default_factory=dict)
    knx2lox_last_seen: dict = field(default_factory=dict)
    listener_thread: object = None
    listener_running: bool = False
    start_requested: bool = False
    stop_requested: bool = False
    monitor_version: int = 0
    lock: RLock = field(default_factory=RLock)
