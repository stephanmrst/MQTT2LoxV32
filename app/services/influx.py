import csv
import json
from urllib.parse import quote

import requests


def influx_escape_measurement(value):
    return str(value or "loxone").replace("\\", "\\\\").replace(",", "\\,").replace(" ", "\\ ")


def influx_escape_tag(value):
    return str(value or "").replace("\\", "\\\\").replace(",", "\\,").replace("=", "\\=").replace(" ", "\\ ")


def influx_escape_field_key(value):
    return str(value or "value").replace("\\", "\\\\").replace(",", "\\,").replace("=", "\\=").replace(" ", "\\ ")


def influx_escape_string_field(value):
    return str(value or "").replace("\\", "\\\\").replace('"', '\\"')


def influx_bool_to_01(value):
    """Bool-/Schaltwerte einheitlich als 0/1 für Influx aufbereiten."""
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return 1 if float(value) != 0 else 0
    txt = str(value or "").strip().lower()
    if txt in ["true", "1", "on", "yes", "ja", "ein", "open", "auf", "active", "aktiv"]:
        return 1
    if txt in ["false", "0", "off", "no", "nein", "aus", "closed", "zu", "inactive", "inaktiv"]:
        return 0
    raise ValueError(f"kein Bool-Wert: {value}")


def influx_format_field_value(value, value_type="auto"):
    """Return fertigen Line-Protocol Field-Wert."""
    mode = str(value_type or "auto").strip().lower()

    if mode in ["bool", "boolean", "bool01", "boolean01", "0/1", "schalter"]:
        return str(influx_bool_to_01(value))

    if mode in ["number", "numeric", "zahl"]:
        return str(float(value))

    if mode in ["text", "string", "str"]:
        return f'"{influx_escape_string_field(value)}"'

    if isinstance(value, bool):
        return "1" if value else "0"

    txt = str(value or "").strip()
    low = txt.lower()
    if low in ["true", "false", "on", "off", "yes", "no", "ja", "nein", "ein", "aus", "open", "closed", "auf", "zu", "active", "inactive", "aktiv", "inaktiv"]:
        return str(influx_bool_to_01(txt))

    try:
        return str(float(value))
    except Exception:
        return f'"{influx_escape_string_field(value)}"'


def influx_object_field_value(value, datatype="auto"):
    mode = str(datatype or "auto").strip().lower()
    if isinstance(value, bool):
        return "1" if value else "0", ""

    text = str(value if value is not None else "").strip()
    low = text.lower()
    if low in ["true", "false", "on", "off", "yes", "no", "ja", "nein", "ein", "aus", "open", "closed", "auf", "zu", "active", "inactive", "aktiv", "inaktiv"]:
        try:
            return str(influx_bool_to_01(text)), ""
        except Exception:
            pass

    try:
        return str(float(value)), ""
    except Exception:
        pass

    if mode in {"text", "string", "str"}:
        return f'"{influx_escape_string_field(value)}"', ""
    return "", "non_numeric_value"


def influx_parse_object_tags(tags, object_id="", source="", unit=""):
    result = {}
    for raw in str(tags or "").split(","):
        token = raw.strip()
        if not token:
            continue
        if "=" in token:
            key, value = token.split("=", 1)
            key = key.strip()
            if key:
                result[key] = value.strip()
            continue
        if token == "object_id" and object_id:
            result["object_id"] = object_id
        elif token == "source" and source:
            result["source"] = source
        elif token == "unit" and unit:
            result["unit"] = unit
    return result


def write_object_value(influx_adapter, value, load_config, add_log_entry, object_id="", source="", unit="", requests_module=requests):
    config = load_config()
    influx = dict(config.get("influx", {}) or {})
    if not influx.get("enabled", False):
        return False, "disabled", "", ""

    bucket = str(getattr(influx_adapter, "bucket", "") or influx.get("bucket", "") or "").strip()
    measurement = str(getattr(influx_adapter, "measurement", "") or influx.get("measurement", "loxone") or "loxone").strip()
    field = str(getattr(influx_adapter, "field", "") or "value").strip() or "value"
    topic = str(getattr(influx_adapter, "topic", "") or measurement or "").strip()
    datatype = str(getattr(influx_adapter, "datatype", "") or "auto").strip() or "auto"
    tags = influx_parse_object_tags(getattr(influx_adapter, "tags", ""), object_id=object_id, source=source, unit=unit)
    if topic:
        tags["topic"] = topic

    field_value, error = influx_object_field_value(value, datatype)
    if error:
        return False, error, bucket, topic

    version = str(influx.get("version", "2") or "2")
    measurement_key = influx_escape_measurement(measurement)
    tag_parts = [f"{influx_escape_tag(key)}={influx_escape_tag(val)}" for key, val in sorted(tags.items()) if str(val or "").strip()]
    tag_suffix = "," + ",".join(tag_parts) if tag_parts else ""
    line = f"{measurement_key}{tag_suffix} {influx_escape_field_key(field)}={field_value}"

    try:
        if version == "2":
            host = str(influx.get("host", "")).strip()
            port = int(influx.get("port", 8086))
            org = str(influx.get("org", "")).strip()
            token = str(influx.get("token", "")).strip()
            if not host:
                return False, "Host fehlt", bucket, topic
            if not bucket:
                return False, "Bucket fehlt", bucket, topic
            if not org:
                return False, "Organisation fehlt", bucket, topic
            if not token:
                return False, "Token fehlt", bucket, topic
            url = (
                f"http://{host}:{port}/api/v2/write"
                f"?org={quote(org, safe='')}"
                f"&bucket={quote(bucket, safe='')}"
                f"&precision=s"
            )
            headers = {"Authorization": f"Token {token}", "Content-Type": "text/plain; charset=utf-8"}
            response = requests_module.post(url, headers=headers, data=line.encode("utf-8"), timeout=5)
            if response.status_code == 204:
                return True, "ok", bucket, topic
            return False, f"HTTP {response.status_code}: {(response.text or '').strip()}", bucket, topic

        host = str(influx.get("host", "")).strip()
        port = int(influx.get("port", 8086))
        database = str(influx.get("database", "") or bucket or "").strip()
        user = str(influx.get("user", "")).strip()
        password = str(influx.get("password", ""))
        if not host:
            return False, "Host fehlt", database, topic
        if not database:
            return False, "Datenbank fehlt", database, topic
        url = f"http://{host}:{port}/write?db={quote(database, safe='')}&precision=s"
        auth = (user, password) if user or password else None
        response = requests_module.post(url, data=line.encode("utf-8"), auth=auth, timeout=5)
        if response.status_code in (200, 204):
            return True, "ok", database, topic
        return False, f"HTTP {response.status_code}: {(response.text or '').strip()}", database, topic
    except Exception as exc:
        return False, str(exc), bucket, topic


def influx_v2_write(influx, topic, value, test=False, field_key_name="value", value_type="auto", requests_module=requests):
    host = str(influx.get("host", "")).strip()
    port = int(influx.get("port", 8086))
    bucket = str(influx.get("bucket", "")).strip()
    org = str(influx.get("org", "")).strip()
    token = str(influx.get("token", "")).strip()
    measurement = influx_escape_measurement(influx.get("measurement", "loxone"))

    if not host:
        return False, "Host fehlt"
    if not bucket:
        return False, "Bucket fehlt"
    if not org:
        return False, "Organisation fehlt"
    if not token:
        return False, "Token fehlt"

    try:
        field_value = influx_format_field_value(value, value_type)
    except Exception as e:
        return False, f"Wert kann nicht konvertiert werden ({value_type}): {e}"

    topic_tag = influx_escape_tag(topic)
    field_key = influx_escape_field_key(field_key_name or "value")
    line = f"{measurement},topic={topic_tag} {field_key}={field_value}"
    if test:
        line = f"{measurement},topic=mqtt2lox_influx_test {field_key}={field_value}"

    url = (
        f"http://{host}:{port}/api/v2/write"
        f"?org={quote(org, safe='')}"
        f"&bucket={quote(bucket, safe='')}"
        f"&precision=s"
    )

    headers = {
        "Authorization": f"Token {token}",
        "Content-Type": "text/plain; charset=utf-8"
    }

    r = requests_module.post(url, headers=headers, data=line.encode("utf-8"), timeout=5)
    if r.status_code == 204:
        return True, "Schreiben erfolgreich"

    body = (r.text or "").strip()
    if r.status_code == 401:
        return False, "401 Unauthorized: Token falsch, nicht komplett kopiert oder ohne Schreibrecht für Bucket/Org"
    if r.status_code == 404:
        return False, f"404 Nicht gefunden: Bucket/Org prüfen. Antwort: {body}"
    if r.status_code == 400:
        return False, f"400 Fehlerhafte Anfrage: Measurement/Line-Protocol prüfen. Antwort: {body}"
    return False, f"HTTP {r.status_code}: {body}"


def write_to_influx_field(topic, field_key, value, load_config, add_log_entry, value_type="auto", requests_module=requests):
    config = load_config()
    influx = config.get("influx", {})

    if not influx.get("enabled", False):
        return False

    try:
        version = str(influx.get("version", "2"))
        clean_field = str(field_key or "value").strip().replace(".", "_").replace("/", "_") or "value"

        if version == "2":
            ok, msg = influx_v2_write(influx, topic, value, test=False, field_key_name=clean_field, value_type=value_type, requests_module=requests_module)
            if ok:
                add_log_entry(f"Influx -> {topic} [{clean_field}] = {value}")
            else:
                add_log_entry(f"Influx Fehler {topic} [{clean_field}]: {msg}")
            return ok

        host = str(influx.get("host", "")).strip()
        port = int(influx.get("port", 8086))
        database = str(influx.get("database", "")).strip()
        measurement = influx_escape_measurement(influx.get("measurement", "loxone"))
        user = str(influx.get("user", "")).strip()
        password = str(influx.get("password", ""))

        try:
            field_value = influx_format_field_value(value, value_type)
        except Exception as e:
            add_log_entry(f"Influx übersprungen {topic} [{clean_field}]: {e}")
            return False

        if not host or not database:
            add_log_entry("Influx Fehler: Host oder Datenbank fehlt")
            return False

        line = f"{measurement},topic={influx_escape_tag(topic)} {influx_escape_field_key(clean_field)}={field_value}"
        url = f"http://{host}:{port}/write?db={quote(database, safe='')}"
        auth = (user, password) if user else None
        r = requests_module.post(url, data=line.encode("utf-8"), auth=auth, timeout=5)
        if r.status_code in (200, 204):
            add_log_entry(f"Influx -> {topic} [{clean_field}] = {value}")
            return True
        add_log_entry(f"Influx Fehler: {r.status_code} {r.text}")
        return False

    except Exception as e:
        add_log_entry(f"Influx Exception {topic} [{field_key}]: {e}")
        return False


def write_to_influx(topic, value, load_config, load_topic_config, add_log_entry, requests_module=requests):
    config = load_config()
    influx = config.get("influx", {})

    if not influx.get("enabled", False):
        return

    topic_settings = load_topic_config()
    influx_allowed = False

    settings = topic_settings.get(topic, {})
    if not isinstance(settings, dict):
        settings = {}
    value_type = settings.get("influx_value_type", "auto")
    output_topic = str(settings.get("influx_topic", "") or "").strip().strip("/") or topic
    if settings.get("influx", False):
        influx_allowed = True

    for original_topic, s in topic_settings.items():
        if not isinstance(s, dict):
            continue
        custom = str(s.get("custom_name", "") or "").strip()
        if custom == topic and s.get("influx", False):
            influx_allowed = True
            value_type = s.get("influx_value_type", value_type)
            output_topic = str(s.get("influx_topic", "") or "").strip().strip("/") or topic
            break

    if not influx_allowed:
        return

    try:
        version = str(influx.get("version", "2"))

        if version == "2":
            ok, msg = influx_v2_write(influx, output_topic, value, test=False, value_type=value_type, requests_module=requests_module)
            if ok:
                add_log_entry(f"Influx -> {output_topic} = {value}")
            else:
                add_log_entry(f"Influx Fehler: {msg}")
            return

        host = str(influx.get("host", "")).strip()
        port = int(influx.get("port", 8086))
        database = str(influx.get("database", "")).strip()
        measurement = influx_escape_measurement(influx.get("measurement", "loxone"))
        user = str(influx.get("user", "")).strip()
        password = str(influx.get("password", ""))

        try:
            field_value = influx_format_field_value(value, value_type)
        except Exception:
            return

        if not host or not database:
            add_log_entry("Influx Fehler: Host oder Datenbank fehlt")
            return

        line = f"{measurement},topic={influx_escape_tag(topic)} value={field_value}"
        url = f"http://{host}:{port}/write?db={quote(database, safe='')}&precision=s"
        auth = (user, password) if user or password else None
        r = requests_module.post(url, data=line.encode("utf-8"), auth=auth, timeout=5)

        if r.status_code == 204:
            add_log_entry(f"Influx -> {topic} = {value}")
        else:
            add_log_entry(f"Influx Fehler: {r.status_code} {r.text}")

    except Exception as e:
        add_log_entry(f"Influx Exception: {e}")


def write_mqtt_explorer_influx(topic, payload, load_topic_config, get_nested_value, write_to_influx_func, write_to_influx_field_func, add_log_entry):
    try:
        topic = str(topic or "").strip()
        if not topic:
            return

        topic_settings = load_topic_config()
        settings = topic_settings.get(topic, {})
        if not isinstance(settings, dict):
            settings = {}

        output_topic = str(settings.get("influx_topic", "") or "").strip().strip("/") or topic

        if settings.get("influx", False):
            write_to_influx_func(output_topic, payload)

        keys = settings.get("influx_json_keys", [])
        key_types = settings.get("influx_json_key_types", {})
        if not isinstance(key_types, dict):
            key_types = {}
        if not isinstance(keys, list) or not keys:
            return

        try:
            data = json.loads(payload) if isinstance(payload, str) else payload
        except Exception as e:
            add_log_entry(f"Influx JSON Fehler {topic}: {e}")
            return

        for key in keys:
            key = str(key or "").strip()
            if not key:
                continue
            value = get_nested_value(data, key)
            if value is None:
                continue
            value_type = key_types.get(key, "auto")
            write_to_influx_field_func(output_topic, key, value, value_type=value_type)

    except Exception as e:
        add_log_entry(f"MQTT Explorer Influx Fehler {topic}: {e}")


def influx_v2_request_config(load_config):
    """Return (ok, msg, cfg) for InfluxDB 2.x management calls."""
    cfg = load_config().get("influx", {})
    if not cfg.get("enabled", False):
        return False, "InfluxDB ist in den Einstellungen nicht aktiviert", cfg
    if str(cfg.get("version", "2")) != "2":
        return False, "Influx Explorer unterstützt in dieser Version nur InfluxDB 2.x", cfg
    for key, label in [("host", "Host"), ("bucket", "Bucket"), ("org", "Organisation"), ("token", "Token")]:
        if not str(cfg.get(key, "") or "").strip():
            return False, f"Influx {label} fehlt", cfg
    return True, "ok", cfg


def influx_v2_query(flux, load_config, timeout=10, requests_module=requests):
    ok, msg, cfg = influx_v2_request_config(load_config)
    if not ok:
        return False, msg, ""
    host = str(cfg.get("host", "")).strip()
    port = int(cfg.get("port", 8086))
    org = str(cfg.get("org", "")).strip()
    token = str(cfg.get("token", "")).strip()
    url = f"http://{host}:{port}/api/v2/query?org={quote(org, safe='')}"
    headers = {
        "Authorization": f"Token {token}",
        "Accept": "application/csv",
        "Content-Type": "application/vnd.flux",
    }
    try:
        r = requests_module.post(url, headers=headers, data=flux.encode("utf-8"), timeout=timeout)
    except Exception as e:
        return False, f"Influx Query Fehler: {e}", ""
    if r.status_code == 200:
        return True, "ok", r.text or ""
    if r.status_code == 401:
        return False, "401 Unauthorized: Token falsch/abgelaufen oder ohne Leserecht", r.text or ""
    return False, f"Influx Query HTTP {r.status_code}: {(r.text or '').strip()}", r.text or ""


def influx_csv_dicts(csv_text):
    """Influx CSV in Dicts umwandeln, Annotation-Zeilen ignorieren."""
    rows = []
    clean_lines = []
    for line in str(csv_text or "").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        clean_lines.append(line)
    if not clean_lines:
        return rows
    try:
        reader = csv.DictReader(clean_lines)
        for row in reader:
            rows.append(row)
    except Exception:
        return []
    return rows


def influx_flux_string(value):
    return json.dumps(str(value or ""), ensure_ascii=False)


def influx_get_topics(search="", limit=500, load_config=None, start="-30d"):
    ok, msg, cfg = influx_v2_request_config(load_config)
    if not ok:
        return False, msg, []
    bucket = str(cfg.get("bucket", "")).strip()
    measurement = str(cfg.get("measurement", "loxone") or "loxone").strip()
    start = str(start or "-30d") or "-30d"
    search = str(search or "").strip().lower()

    flux = f'''
import "influxdata/influxdb/schema"
schema.tagValues(
  bucket: {influx_flux_string(bucket)},
  tag: "topic",
  predicate: (r) => r._measurement == {influx_flux_string(measurement)},
  start: {start}
)
'''
    ok, msg, csv_text = influx_v2_query(flux, load_config)
    if not ok:
        return False, msg, []
    topics = []
    for row in influx_csv_dicts(csv_text):
        t = str(row.get("_value", "") or "").strip()
        if not t:
            continue
        if search and search not in t.lower():
            continue
        topics.append(t)
    topics = sorted(set(topics), key=lambda x: x.casefold())[:int(limit)]

    result = []
    for topic in topics:
        last_value = "-"
        last_time = "-"
        fields = ""
        count = "-"
        try:
            topic_json = influx_flux_string(topic)
            flux_last = f'''
from(bucket: {influx_flux_string(bucket)})
  |> range(start: {start})
  |> filter(fn: (r) => r._measurement == {influx_flux_string(measurement)} and r.topic == {topic_json})
  |> last()
  |> keep(columns: ["_time", "_field", "_value"])
'''
            ok2, _msg2, csv_last = influx_v2_query(flux_last, load_config, timeout=5)
            last_rows = influx_csv_dicts(csv_last) if ok2 else []
            if last_rows:
                lr = last_rows[0]
                last_value = str(lr.get("_value", "-") or "-")
                last_time = str(lr.get("_time", "-") or "-")
                fields = ", ".join(sorted(set(str(x.get("_field", "") or "") for x in last_rows if x.get("_field"))))

            flux_count = f'''
from(bucket: {influx_flux_string(bucket)})
  |> range(start: {start})
  |> filter(fn: (r) => r._measurement == {influx_flux_string(measurement)} and r.topic == {topic_json})
  |> count()
  |> sum()
'''
            ok3, _msg3, csv_count = influx_v2_query(flux_count, load_config, timeout=5)
            count_rows = influx_csv_dicts(csv_count) if ok3 else []
            if count_rows:
                count = str(count_rows[0].get("_value", "-") or "-")
        except Exception as e:
            last_value = f"Fehler: {e}"
        result.append({
            "topic": topic,
            "fields": fields or "value",
            "last_value": last_value,
            "last_time": last_time,
            "count": count,
        })
    return True, "ok", result


def influx_delete_topic(topic, load_config, add_log_entry, start="1970-01-01T00:00:00Z", stop=None, requests_module=requests):
    ok, msg, cfg = influx_v2_request_config(load_config)
    if not ok:
        return False, msg
    topic = str(topic or "").strip()
    if not topic:
        return False, "Topic fehlt"
    host = str(cfg.get("host", "")).strip()
    port = int(cfg.get("port", 8086))
    org = str(cfg.get("org", "")).strip()
    bucket = str(cfg.get("bucket", "")).strip()
    token = str(cfg.get("token", "")).strip()
    if not stop:
        from datetime import datetime, timezone, timedelta
        stop = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
    url = f"http://{host}:{port}/api/v2/delete?org={quote(org, safe='')}&bucket={quote(bucket, safe='')}"
    headers = {"Authorization": f"Token {token}", "Content-Type": "application/json"}
    safe_topic = topic.replace('"', '\\"')
    body = {"start": start, "stop": stop, "predicate": f'topic="{safe_topic}"'}
    try:
        r = requests_module.post(url, headers=headers, json=body, timeout=10)
    except Exception as e:
        return False, f"Influx Delete Fehler: {e}"
    if r.status_code in (200, 202, 204):
        add_log_entry(f"Influx gelöscht: topic={topic}")
        return True, f"Gelöscht: {topic}"
    if r.status_code == 401:
        return False, "401 Unauthorized: Token braucht Delete/Write-Recht für Bucket/Org"
    return False, f"Influx Delete HTTP {r.status_code}: {(r.text or '').strip()}"
