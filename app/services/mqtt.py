from datetime import datetime


mqtt_monitor_values = {}
mqtt_clients = {}
mqtt_client = None


def reset_clients():
    global mqtt_client
    mqtt_clients.clear()
    mqtt_client = None


def get_main_client():
    return mqtt_client


def set_main_client(client):
    global mqtt_client
    mqtt_client = client
    return mqtt_client


def get_effective_mqtt_config(config, load_internal_broker_config):
    mq = dict((config or {}).get("mqtt", {}))
    ib = load_internal_broker_config()
    if ib.get("enabled") and ib.get("use_as_main"):
        mq["host"] = ib.get("connect_host", "127.0.0.1") or "127.0.0.1"
        mq["port"] = int(ib.get("port", 1883))
        if not ib.get("allow_anonymous", True):
            mq["user"] = ib.get("user", "")
            mq["password"] = ib.get("password", "")
        else:
            mq["user"] = ""
            mq["password"] = ""
    return mq


def build_broker_list(config, load_mqtt_brokers, load_internal_broker_config):
    mqtt_cfg = (config or {}).get("mqtt", {})
    effective_mqtt = get_effective_mqtt_config(config, load_internal_broker_config)
    brokers = [
        {
            "name": "Hauptbroker",
            "host": effective_mqtt.get("host", mqtt_cfg.get("host", "127.0.0.1")),
            "port": effective_mqtt.get("port", mqtt_cfg.get("port", 1883)),
            "user": effective_mqtt.get("user", ""),
            "password": effective_mqtt.get("password", ""),
            "enabled": True,
            "is_main": True,
        }
    ]
    for broker in load_mqtt_brokers():
        if broker.get("enabled", True):
            item = dict(broker)
            item["is_main"] = False
            brokers.append(item)
    return brokers


def record_mqtt_message(broker_name, topic, payload):
    monitor_key = f"{broker_name}::{topic}"
    mqtt_monitor_values[monitor_key] = {
        "broker": broker_name,
        "topic": topic,
        "payload": payload,
        "time": datetime.now().strftime("%H:%M:%S"),
    }
    return mqtt_monitor_values[monitor_key]


def connect_brokers(config, mqtt_module, load_mqtt_brokers, load_internal_broker_config, on_message, add_log_entry):
    reset_clients()
    for broker in build_broker_list(config, load_mqtt_brokers, load_internal_broker_config):
        try:
            client = mqtt_module.Client(userdata={"broker": broker["name"]})

            user = broker.get("user", "")
            password = broker.get("password", "")
            if user:
                client.username_pw_set(user, password)

            client.on_message = on_message
            client.connect(broker["host"], int(broker["port"]), 60)
            client.subscribe("#")
            client.loop_start()

            mqtt_clients[broker["name"]] = client
            if broker.get("is_main"):
                set_main_client(client)

            add_log_entry(
                f"MQTT verbunden: {broker['name']} "
                f"({broker['host']}:{broker['port']})"
            )
        except Exception as exc:
            add_log_entry(f"MQTT Broker Fehler {broker.get('name')}: {exc}")
    return mqtt_client, mqtt_clients


def stop_clients(add_log_entry):
    for name, client in list(mqtt_clients.items()):
        try:
            client.loop_stop()
            client.disconnect()
            add_log_entry(f"MQTT getrennt: {name}")
        except Exception:
            pass
    reset_clients()


def publish(topic, payload, retain=False):
    if mqtt_client:
        return mqtt_client.publish(topic, payload, retain=bool(retain))
    return None


def test_connection(mqtt_module, host, port, user="", password="", timeout=5):
    client = mqtt_module.Client()
    if user:
        client.username_pw_set(user, password)
    client.connect(host, int(port), timeout)
    client.disconnect()
    return True
