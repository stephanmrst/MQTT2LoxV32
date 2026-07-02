import asyncio
import re
import threading
import time
from datetime import datetime

import requests


def normalize_knx_ga(value):
    """Normalize KNX group addresses."""
    text = str(value or "").strip().replace(" ", "")
    if not text:
        return ""

    if "/" in text:
        parts = [p for p in text.split("/") if p != ""]
        if len(parts) >= 3:
            return f"{parts[0]}/{parts[1]}/{parts[2]}"
        if len(parts) == 2:
            a, b = parts[0], parts[1]
            b_digits = re.sub(r"\D", "", b)
            if len(b_digits) >= 2:
                return f"{a}/{b_digits[0]}/{b_digits[1:]}"
            return f"{a}/{b}"
        if len(parts) == 1:
            return normalize_knx_ga(parts[0])
        return ""

    digits = re.sub(r"\D", "", text)
    if not digits:
        return text
    if len(digits) == 1:
        return digits
    if len(digits) == 2:
        return f"{digits[0]}/{digits[1]}"
    return f"{digits[0]}/{digits[1]}/{digits[2:]}"


normalize_knx_group_address = normalize_knx_ga


def _normalize_knx_dpt(dpt):
    text = str(dpt or "").strip().lower()
    if not text:
        return "1.001"
    if text in {"bool", "boolean", "switch"}:
        return "1.001"
    match = re.search(r"(\d+\.\d{3})", text)
    if match:
        return match.group(1)
    text = text.replace("dpt", "", 1).strip()
    text = text.replace(" ", "")
    return text


def _knx_parse_number(value):
    text = str(value or "").strip().replace(",", ".")
    if not text:
        return 0.0
    return float(text)


def _knx_parse_int(value):
    return int(round(_knx_parse_number(value)))


def _knx_send_value_for_dpt(value, dpt, invert=False):
    dpt = _normalize_knx_dpt(dpt)
    raw = value
    text = str(raw).strip().lower() if isinstance(raw, str) else ""

    if dpt.startswith("1."):
        if isinstance(raw, bool):
            b = raw
        elif isinstance(raw, (int, float)):
            b = float(raw) != 0
        elif text in ["true", "on", "1", "yes", "ja", "open", "auf"]:
            b = True
        elif text in ["false", "off", "0", "no", "nein", "closed", "zu"]:
            b = False
        else:
            b = bool(raw)
        return (not b) if invert else b

    if dpt.startswith("5.001"):
        return max(0.0, min(100.0, float(_knx_parse_number(raw))))

    if dpt.startswith("5."):
        return max(0, min(255, _knx_parse_int(raw)))

    if dpt.startswith("7.") or dpt.startswith("12."):
        return max(0, _knx_parse_int(raw))

    if dpt.startswith("8.") or dpt.startswith("13."):
        return _knx_parse_int(raw)

    if dpt.startswith("9.") or dpt.startswith("14."):
        return float(_knx_parse_number(raw))

    if dpt.startswith("16."):
        return str(raw)

    return raw


def resolve_knx_test_dpt(raw_value, selected_dpt):
    dpt = _normalize_knx_dpt(selected_dpt)
    if dpt != "auto":
        return dpt

    text = str(raw_value or "").strip().lower()
    if not text:
        return "1.001"

    bool_like = {"true", "false", "on", "off", "1", "0", "yes", "no", "ja", "nein", "open", "closed", "auf", "zu"}
    if text in bool_like:
        return "1.001"

    if "%" in text:
        return "5.001"
    if "°c" in text or " c" in text or text.endswith("c") or "temp" in text:
        return "9.001"
    if "w" in text or "watt" in text or "leistung" in text or "power" in text:
        return "14.056"
    if "a" in text or "amp" in text or "strom" in text:
        return "14.019"
    if "v" in text or "volt" in text or "spannung" in text:
        return "14.027"

    if re.fullmatch(r"-?\d+(?:[.,]\d+)?", text):
        return "9.001"

    return "16.001"


def build_knx_send_diagnostic(group_address, dpt, value):
    try:
        from xknx.dpt import DPTBinary
        from xknx.dpt.dpt_5 import DPTScaling, DPTValue1Ucount
        from xknx.dpt.dpt_7 import DPT2ByteUnsigned
        from xknx.dpt.dpt_8 import DPT2ByteSigned
        from xknx.dpt.dpt_9 import DPTTemperature, DPTLux, DPTWsp, DPTPressure2Byte, DPTHumidity
        from xknx.dpt.dpt_12 import DPT4ByteUnsigned
        from xknx.dpt.dpt_13 import DPT4ByteSigned
        from xknx.dpt.dpt_14 import DPTPower, DPTElectricCurrent, DPTElectricPotential
        from xknx.dpt.dpt_16 import DPTString
        from xknx.telegram import Telegram
        from xknx.telegram.address import parse_device_group_address
        from xknx.telegram.apci import GroupValueWrite
    except Exception as e:
        return {
            "ok": False,
            "error": f"xknx fehlt oder laedt nicht: {e}",
            "telegram_type": "GroupValueWrite",
            "group_address": normalize_knx_ga(group_address),
            "dpt": _normalize_knx_dpt(dpt),
            "raw_value": value,
            "converted_value": value,
            "apdu": "",
        }

    ga = normalize_knx_ga(group_address)
    dpt = resolve_knx_test_dpt(value, dpt)
    converted_value = _knx_send_value_for_dpt(value, dpt)
    value_type = None
    if dpt.startswith("1."):
        value_type = DPTBinary
    elif dpt.startswith("5.001"):
        value_type = DPTScaling
    elif dpt.startswith("5."):
        value_type = DPTValue1Ucount
    elif dpt.startswith("7."):
        value_type = DPT2ByteUnsigned
    elif dpt.startswith("8."):
        value_type = DPT2ByteSigned
    elif dpt.startswith("9.001"):
        value_type = DPTTemperature
    elif dpt.startswith("9.004"):
        value_type = DPTLux
    elif dpt.startswith("9.005"):
        value_type = DPTWsp
    elif dpt.startswith("9.006"):
        value_type = DPTPressure2Byte
    elif dpt.startswith("9.007"):
        value_type = DPTHumidity
    elif dpt.startswith("12."):
        value_type = DPT4ByteUnsigned
    elif dpt.startswith("13."):
        value_type = DPT4ByteSigned
    elif dpt.startswith("14.056"):
        value_type = DPTPower
    elif dpt.startswith("14.019"):
        value_type = DPTElectricCurrent
    elif dpt.startswith("14.027"):
        value_type = DPTElectricPotential
    elif dpt.startswith("16."):
        value_type = DPTString

    if value_type is None:
        return {
            "ok": False,
            "error": f"KNX DPT {dpt} wird nicht unterstuetzt",
            "telegram_type": "GroupValueWrite",
            "group_address": ga,
            "dpt": dpt,
            "raw_value": value,
            "converted_value": converted_value,
            "apdu": "",
        }

    if dpt.startswith("1."):
        knx_payload = DPTBinary(1 if bool(converted_value) else 0)
    else:
        knx_payload = value_type.to_knx(converted_value)

    telegram = Telegram(
        destination_address=parse_device_group_address(ga),
        payload=GroupValueWrite(knx_payload),
    )
    try:
        apdu_hex = bytes(telegram.payload.to_knx()).hex()
    except Exception:
        apdu_hex = ""
    return {
        "ok": True,
        "error": "",
        "telegram_type": "GroupValueWrite",
        "group_address": ga,
        "dpt": dpt,
        "raw_value": value,
        "converted_value": converted_value,
        "apdu": apdu_hex,
    }


def convert_knx_value(value, dpt, invert=False):
    return _knx_send_value_for_dpt(value, dpt, invert=invert)


knx_convert_value = convert_knx_value


def infer_knx_dpt(group_address, default="", load_knx2mqtt_config=None, load_knx2lox_config=None, load_mqtt2knx_config=None, load_udp2knx_config=None):
    """Find configured DPT for a KNX group address from all mapping tables."""
    ga_in = normalize_knx_ga(group_address)
    if not ga_in:
        return default

    sources = []
    for loader in [load_knx2mqtt_config, load_knx2lox_config, load_mqtt2knx_config, load_udp2knx_config]:
        if not loader:
            continue
        try:
            sources += loader()
        except Exception:
            pass

    for item in sources:
        if not isinstance(item, dict):
            continue
        ga = normalize_knx_ga(item.get("group_address", ""))
        if ga and ga == ga_in:
            dpt = str(item.get("dpt", "") or "").strip()
            if dpt:
                return dpt
    return default


def payload_to_bytes(payload):
    """Extract raw KNX payload bytes from xknx Telegram payload variants."""
    raw = payload
    try:
        if hasattr(raw, "value"):
            raw = raw.value
        if hasattr(raw, "value"):
            raw = raw.value
    except Exception:
        pass

    if isinstance(raw, (bytes, bytearray)):
        return list(raw)
    if isinstance(raw, (list, tuple)):
        out = []
        for x in raw:
            try:
                out.append(int(x) & 0xFF)
            except Exception:
                pass
        return out

    txt = str(raw)
    nums = re.findall(r"\b\d{1,3}\b", txt)
    vals = []
    for n in nums:
        try:
            v = int(n)
            if 0 <= v <= 255:
                vals.append(v)
        except Exception:
            pass
    return vals


def _decode_knx_dpt9_float(data):
    """Decode KNX DPT 9.xxx 2-byte float (EIS5)."""
    if len(data) < 2:
        return None
    b1, b2 = int(data[-2]) & 0xFF, int(data[-1]) & 0xFF
    raw = (b1 << 8) | b2
    sign = -1 if (raw & 0x8000) else 1
    exponent = (raw >> 11) & 0x0F
    mantissa = raw & 0x07FF
    if sign < 0:
        mantissa = -(~(mantissa - 1) & 0x07FF)
    return 0.01 * mantissa * (2 ** exponent)


def _decode_knx_dpt14_float(data):
    """Decode KNX DPT 14.xxx 4-byte IEEE float."""
    if len(data) < 4:
        return None
    import struct
    return struct.unpack(">f", bytes(data[-4:]))[0]


def auto_decode_value(data):
    """Best-effort decode for KNX monitor when no mapping/DPT exists yet."""
    if not data:
        return "", ""

    if len(data) == 2:
        val = _decode_knx_dpt9_float(data)
        if val is not None and -273.15 <= float(val) <= 100000:
            return _format_knx_number(val), "9.xxx auto"

    if len(data) == 4:
        val = _decode_knx_dpt14_float(data)
        if val is not None and abs(float(val)) < 1e12:
            return _format_knx_number(val), "14.xxx auto"

    if len(data) == 1:
        return str(data[-1]), "5.xxx auto"

    return "0x" + "".join(f"{x:02X}" for x in data), ""


def _format_knx_number(value):
    try:
        v = float(value)
        txt = f"{v:.3f}".rstrip("0").rstrip(".")
        return txt if txt != "-0" else "0"
    except Exception:
        return str(value)


def parse_knx_payload_value(payload, dpt="1.001", invert=False):
    dpt = str(dpt or "").strip().lower()
    raw = payload

    try:
        if hasattr(raw, "value"):
            raw = raw.value
        if hasattr(raw, "value"):
            raw = raw.value
    except Exception:
        pass

    data = payload_to_bytes(payload)

    if dpt.startswith("1.") or dpt in ["bool", "boolean", "switch"]:
        try:
            if isinstance(raw, (bytes, bytearray)):
                b = bool(raw[-1] & 0x01)
            elif isinstance(raw, (list, tuple)):
                b = bool(int(raw[-1]) & 0x01)
            elif isinstance(raw, bool):
                b = raw
            elif isinstance(raw, (int, float)):
                b = bool(int(raw) & 0x01)
            elif data:
                b = bool(data[-1] & 0x01)
            else:
                txt = str(raw).strip().lower()
                b = txt in ["1", "true", "on", "yes", "ein", "open", "auf"]
            b = (not b) if invert else b
            return "1" if b else "0"
        except Exception:
            return str(raw)

    if dpt.startswith("5."):
        if data:
            val = data[-1]
            if dpt.startswith("5.001"):
                return _format_knx_number(val * 100.0 / 255.0)
            return str(val)

    if dpt.startswith("7.") and len(data) >= 2:
        return str((data[-2] << 8) | data[-1])

    if dpt.startswith("8.") and len(data) >= 2:
        val = (data[-2] << 8) | data[-1]
        if val & 0x8000:
            val -= 0x10000
        return str(val)

    if dpt.startswith("9.") or dpt in ["eis5", "analog", "float2"]:
        val = _decode_knx_dpt9_float(data)
        if val is not None:
            return _format_knx_number(val)

    if dpt.startswith("14."):
        val = _decode_knx_dpt14_float(data)
        if val is not None:
            return _format_knx_number(val)

    try:
        if isinstance(raw, (int, float, bool)):
            return str(raw)
        if data:
            auto_value, _auto_dpt = auto_decode_value(data)
            if auto_value:
                return auto_value
    except Exception:
        pass
    return str(raw)


format_knx_value_for_mqtt = parse_knx_payload_value
_knx_payload_to_bytes = payload_to_bytes
_knx_auto_decode_value = auto_decode_value
_knx_payload_to_text = parse_knx_payload_value


def build_knx_mqtt_topic(item):
    return str((item or {}).get("mqtt_topic", "") or "").strip()


def build_knx_udp_payload(value):
    return str(value)


def _load_core_runtime_api():
    try:
        from app import core as core_module
        return core_module
    except Exception:
        return None


def _log_core_runtime_identity(core_api, add_log_entry, prefix):
    try:
        module_name = getattr(core_api, "__name__", "<unknown>")
        module_file = getattr(core_api, "__file__", "<unknown>")
        knx_state = getattr(getattr(core_api, "runtime_context", None), "knx", None)
        add_log_entry(
            f"{prefix} core module={module_name} file={module_file} knx_state_id={id(knx_state)}"
        )
    except Exception:
        pass


async def _send_knx_runtime(group_address, dpt, value, xknx, add_log_entry, add_monitor_entry=None):
    try:
        from xknx.dpt import DPTBinary
        from xknx.dpt.dpt_5 import DPTScaling, DPTValue1Ucount
        from xknx.dpt.dpt_7 import DPT2ByteUnsigned
        from xknx.dpt.dpt_8 import DPT2ByteSigned
        from xknx.dpt.dpt_9 import DPTTemperature, DPTLux, DPTWsp, DPTPressure2Byte, DPTHumidity
        from xknx.dpt.dpt_12 import DPT4ByteUnsigned
        from xknx.dpt.dpt_13 import DPT4ByteSigned
        from xknx.dpt.dpt_14 import DPTPower, DPTElectricCurrent, DPTElectricPotential
        from xknx.dpt.dpt_16 import DPTString
        from xknx.telegram import Telegram
        from xknx.telegram.address import parse_device_group_address
        from xknx.telegram.apci import GroupValueWrite
    except Exception as e:
        add_log_entry(f"KNX Fehler: xknx fehlt oder laedt nicht ({e})")
        add_log_entry("KNX Hinweis: pip install xknx")
        return False
    dpt = _normalize_knx_dpt(dpt)
    converted_value = _knx_send_value_for_dpt(value, dpt)
    add_log_entry(
        f"KNX Senden Start ga={group_address} dpt={dpt} value_raw={value} value_conv={converted_value}"
    )
    value_type = None
    if dpt.startswith("1."):
        value_type = DPTBinary
    elif dpt.startswith("5.001"):
        value_type = DPTScaling
    elif dpt.startswith("5."):
        value_type = DPTValue1Ucount
    elif dpt.startswith("7."):
        value_type = DPT2ByteUnsigned
    elif dpt.startswith("8."):
        value_type = DPT2ByteSigned
    elif dpt.startswith("9.001"):
        value_type = DPTTemperature
    elif dpt.startswith("9.004"):
        value_type = DPTLux
    elif dpt.startswith("9.005"):
        value_type = DPTWsp
    elif dpt.startswith("9.006"):
        value_type = DPTPressure2Byte
    elif dpt.startswith("9.007"):
        value_type = DPTHumidity
    elif dpt.startswith("12."):
        value_type = DPT4ByteUnsigned
    elif dpt.startswith("13."):
        value_type = DPT4ByteSigned
    elif dpt.startswith("14.056"):
        value_type = DPTPower
    elif dpt.startswith("14.019"):
        value_type = DPTElectricCurrent
    elif dpt.startswith("14.027"):
        value_type = DPTElectricPotential
    elif dpt.startswith("16."):
        value_type = DPTString
    else:
        add_log_entry(f"KNX DPT {dpt} wird nicht unterstuetzt")
        if add_monitor_entry:
            add_monitor_entry(group_address, value, "OUT", dpt, status="ERROR", update_live=False, source="Objektmanager")
        return False
    try:
        add_log_entry(f"KNX Senden Diagnose vor GroupValueWrite ga={group_address} dpt={dpt} value={converted_value}")
        if dpt.startswith("1."):
            knx_payload = DPTBinary(1 if bool(converted_value) else 0)
        else:
            knx_payload = value_type.to_knx(converted_value)
        telegram = Telegram(
            destination_address=parse_device_group_address(group_address),
            payload=GroupValueWrite(knx_payload),
        )
        try:
            apdu_hex = bytes(telegram.payload.to_knx()).hex()
        except Exception:
            apdu_hex = ""
        add_log_entry(
            f"KNX Senden Diagnose telegram_type=GroupValueWrite ga={group_address} dpt={dpt} value={converted_value} apdu={apdu_hex or '-'}"
        )
        xknx.telegrams.put_nowait(telegram)
        add_log_entry(f"KNX Senden Diagnose queued GroupValueWrite ga={group_address} dpt={dpt}")
        await asyncio.wait_for(xknx.join(), timeout=5)
        add_log_entry(f"KNX Senden Diagnose after join ga={group_address} dpt={dpt}")
        if add_monitor_entry:
            add_monitor_entry(group_address, converted_value, "OUT", dpt, status="OK", update_live=False, source="Objektmanager")
        add_log_entry(f"KNX Senden OK ga={group_address} dpt={dpt} value={converted_value}")
        return True
    except Exception as e:
        add_log_entry(f"KNX Senden Fehler konkret: {type(e).__name__}: {e}")
        if dpt.startswith("14."):
            add_log_entry("KNX Hinweis: einige Ziele erwarten fuer Leistung/Temp. eher DPT 9.xxx statt 14.xxx")
        if add_monitor_entry:
            add_monitor_entry(group_address, value, "OUT", dpt, status="ERROR", update_live=False, source="Objektmanager")
        return False


def send_knx_value(group_address, dpt, value, load_knx_config, add_log_entry, add_monitor_entry=None):
    group_address = normalize_knx_ga(group_address)
    knx_cfg = load_knx_config()
    if not knx_cfg.get("enabled", False):
        add_log_entry("KNX deaktiviert - Wert nicht gesendet")
        return False
    if not group_address:
        add_log_entry("KNX Fehler: Gruppenadresse fehlt")
        return False
    core_api = _load_core_runtime_api()
    if core_api is None:
        add_log_entry("KNX Senden fehlgeschlagen: Runtime-Service nicht geladen")
        return False
    _log_core_runtime_identity(core_api, add_log_entry, "KNX SEND")

    state = {}
    try:
        state = core_api.get_knx_runtime_state()
    except Exception:
        state = {}

    if not state.get("listener_running") or state.get("connection_status") != "connected" or not state.get("xknx") or not state.get("loop"):
        try:
            core_api.ensure_knx_listener_started("KNX Senden")
        except Exception:
            pass
        deadline = time.time() + 5.0
        while time.time() < deadline:
            try:
                state = core_api.get_knx_runtime_state()
            except Exception:
                state = {}
            if state.get("listener_running") and state.get("connection_status") == "connected" and state.get("xknx") and state.get("loop"):
                break
            time.sleep(0.2)

    if not state.get("listener_running") or state.get("connection_status") != "connected" or not state.get("xknx") or not state.get("loop"):
        add_log_entry("KNX Senden fehlgeschlagen: keine aktive KNX Tunnel-Verbindung")
        return False

    xknx = state.get("xknx")
    try:
        if add_monitor_entry:
            add_monitor_entry(group_address, value, "OUT", dpt, status="PENDING", update_live=False, source="Objektmanager")
        future = core_api.submit_knx_runtime_coro(
            _send_knx_runtime(group_address, dpt, value, xknx, add_log_entry, add_monitor_entry)
        )
        if future is None:
            if add_monitor_entry:
                add_monitor_entry(group_address, value, "OUT", dpt, status="ERROR", update_live=False, source="Objektmanager")
            add_log_entry("KNX Senden fehlgeschlagen: keine aktive KNX Tunnel-Verbindung")
            return False
        result = future.result(timeout=10)
        return bool(result)
    except Exception as e:
        if add_monitor_entry:
            add_monitor_entry(group_address, value, "OUT", dpt, status="ERROR", update_live=False, source="Objektmanager")
        add_log_entry(f"KNX Senden fehlgeschlagen: {e}")
        return False


def handle_mqtt_to_knx(topic, payload, load_mqtt2knx_config, extract_mqtt_mapping_value, mqtt2knx_last_seen, send_value, add_log_entry, update_last_seen=None):
    for item in load_mqtt2knx_config():
        if not item.get("enabled", True):
            continue
        source_topic = item.get("source_topic", "").strip()
        if not source_topic or topic != source_topic:
            continue
        raw_value = extract_mqtt_mapping_value(item, payload)
        mqtt2knx_last_seen[source_topic] = {
            "value": raw_value if raw_value is not None else "-",
            "raw_payload": payload,
            "time": datetime.now().strftime("%H:%M:%S")
        }
        if update_last_seen:
            update_last_seen("mqtt2knx", source_topic, mqtt2knx_last_seen[source_topic])
        if raw_value is None:
            add_log_entry(f"MQTT2KNX kein gueltiger Wert fuer {topic}")
            return True
        try:
            knx_value = convert_knx_value(raw_value, item.get("dpt", "1.001"), bool(item.get("invert", False)))
        except Exception as e:
            add_log_entry(f"MQTT2KNX Wertfehler {topic}: {e}")
            return True
        send_value(item.get("group_address", "").strip(), item.get("dpt", "1.001"), knx_value)
        return True
    return False


def publish_knx_to_mqtt(group_address, payload_raw, load_knx2mqtt_config, mqtt_client_getter, knx2mqtt_last_seen, add_log_entry, update_last_seen=None):
    for item in load_knx2mqtt_config():
        if not item.get("enabled", True):
            continue
        ga = normalize_knx_ga(item.get("group_address", ""))
        mqtt_topic = build_knx_mqtt_topic(item)
        if not ga or not mqtt_topic or ga != normalize_knx_ga(group_address):
            continue
        try:
            value = parse_knx_payload_value(payload_raw, item.get("dpt", "1.001"), bool(item.get("invert", False)))
            knx2mqtt_last_seen[ga] = {"value": value, "time": datetime.now().strftime("%H:%M:%S"), "topic": mqtt_topic}
            if update_last_seen:
                update_last_seen("knx2mqtt", ga, knx2mqtt_last_seen[ga])
            mqtt_client = mqtt_client_getter() if mqtt_client_getter else None
            if mqtt_client:
                mqtt_client.publish(mqtt_topic, value, retain=bool(item.get("retain", True)))
                add_log_entry(f"KNX2MQTT -> {ga} => {mqtt_topic} = {value}")
            else:
                add_log_entry("KNX2MQTT Fehler: MQTT Client nicht bereit")
        except Exception as e:
            add_log_entry(f"KNX2MQTT Fehler {group_address}: {e}")


def publish_knx_to_loxone(group_address, payload_raw, load_knx2lox_config, load_config, knx2lox_last_seen, add_log_entry, requests_module=requests, update_last_seen=None):
    """Direct KNX telegram to Loxone virtual input/control."""
    ga_in = normalize_knx_ga(group_address)
    for item in load_knx2lox_config():
        if not item.get("enabled", True):
            continue
        ga = normalize_knx_ga(item.get("group_address", ""))
        loxone_io = str(item.get("loxone_io", "")).strip()
        if not ga or not loxone_io or ga != ga_in:
            continue
        try:
            value = parse_knx_payload_value(payload_raw, item.get("dpt", "1.001"), bool(item.get("invert", False)))
            knx2lox_last_seen[ga] = {"value": value, "time": datetime.now().strftime("%H:%M:%S"), "loxone_io": loxone_io}
            if update_last_seen:
                update_last_seen("knx2lox", ga, knx2lox_last_seen[ga])
            cfg = load_config()
            url = f"http://{cfg['loxone']['host']}/dev/sps/io/{loxone_io}/{value}"
            r = requests_module.get(url, auth=(cfg["loxone"]["user"], cfg["loxone"]["password"]), timeout=5)
            if r.status_code == 200:
                add_log_entry(f"KNX2LOX -> {ga} => {loxone_io} = {value}")
            else:
                add_log_entry(f"KNX2LOX Fehler HTTP {r.status_code}: {r.text}")
        except Exception as e:
            add_log_entry(f"KNX2LOX Fehler {ga_in}: {e}")


def handle_udp_to_knx(topic, value, load_udp2knx_config, udp2knx_last_seen, send_value, add_log_entry):
    """Direct UDP input topic/value to KNX mapping."""
    source_topic = str(topic or "").strip()
    if not source_topic:
        return False
    for item in load_udp2knx_config():
        if not item.get("enabled", True):
            continue
        mapped_topic = str(item.get("source_topic", "")).strip()
        if not mapped_topic or mapped_topic != source_topic:
            continue
        udp2knx_last_seen[mapped_topic] = {"value": value, "time": datetime.now().strftime("%H:%M:%S")}
        try:
            knx_value = convert_knx_value(value, item.get("dpt", "1.001"), bool(item.get("invert", False)))
            send_value(item.get("group_address", ""), item.get("dpt", "1.001"), knx_value)
            add_log_entry(f"UDP2KNX -> {mapped_topic} => {item.get('group_address','')} = {knx_value}")
        except Exception as e:
            add_log_entry(f"UDP2KNX Fehler {mapped_topic}: {e}")
        return True
    return False
