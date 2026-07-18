#!/bin/sh
set -eu

SOURCE_DIR="/opt/mpgateway-source"
APP_DIR="${MQTT2LOX_APP_ROOT:-/mpgateway}"

mkdir -p "$APP_DIR"

# Beim allerersten Start wird die komplette Anwendung in das Docker-Volume kopiert.
# Danach wird ausschließlich aus dem Volume gestartet und nichts automatisch überschrieben.
if [ ! -f "$APP_DIR/app/main.py" ]; then
    echo "MP-Gateway: initialisiere Daten-Volume unter $APP_DIR ..."
    cp -a "$SOURCE_DIR/." "$APP_DIR/"
    cp "$SOURCE_DIR/.image-requirements.sha256" "$APP_DIR/.requirements.sha256"
fi

mkdir -p \
    "${MQTT2LOX_CONFIG_DIR:-$APP_DIR/config}" \
    "${MQTT2LOX_DATA_DIR:-$APP_DIR/data}" \
    "${MQTT2LOX_BACKUP_DIR:-$APP_DIR/backups}" \
    "$APP_DIR/logs"

# Falls requirements.txt später im Volume aktualisiert wurde, Abhängigkeiten nachziehen.
if [ -f "$APP_DIR/requirements.txt" ]; then
    CURRENT_HASH="$(sha256sum "$APP_DIR/requirements.txt" | awk '{print $1}')"
    INSTALLED_HASH="$(cat "$APP_DIR/.requirements.sha256" 2>/dev/null || true)"
    if [ "$CURRENT_HASH" != "$INSTALLED_HASH" ]; then
        echo "MP-Gateway: requirements.txt geändert, installiere Abhängigkeiten ..."
        python -m pip install -r "$APP_DIR/requirements.txt"
        printf '%s\n' "$CURRENT_HASH" > "$APP_DIR/.requirements.sha256"
    fi
fi

cd "$APP_DIR"
exec "$@"
