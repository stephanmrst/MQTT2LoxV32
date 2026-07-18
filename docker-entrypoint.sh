#!/bin/sh
set -eu

SOURCE_DIR="/opt/mpgateway-source"
APP_DIR="${MQTT2LOX_APP_ROOT:-/mpgateway}"
CONFIG_DIR="${MQTT2LOX_CONFIG_DIR:-$APP_DIR/config}"
DATA_DIR="${MQTT2LOX_DATA_DIR:-$APP_DIR/data}"
BACKUP_DIR="${MQTT2LOX_BACKUP_DIR:-$APP_DIR/backups}"

mkdir -p "$APP_DIR" "$CONFIG_DIR" "$DATA_DIR" "$BACKUP_DIR" "$APP_DIR/logs"

# V34: Anwendungscode bei jedem Containerstart aus dem Image aktualisieren.
# Persistente Verzeichnisse bleiben unangetastet.
echo "MP-Gateway: aktualisiere Anwendungscode aus dem Container-Image ..."
for path in app templates docs tests; do
    rm -rf "$APP_DIR/$path"
    if [ -e "$SOURCE_DIR/$path" ]; then
        cp -a "$SOURCE_DIR/$path" "$APP_DIR/$path"
    fi
done

for file in requirements.txt VERSION Dockerfile docker-compose.yml DOCKER.md GITHUB_RELEASE.md CHANGELOG.md AGENTS.md ARCHITECTURE_REVIEW.md BLUEPRINT_PLAN.md CLEANUP_REPORT.md KNX_RUNTIME_MIGRATION_PLAN.md LEGACY_REMOVAL_PLAN.md MIGRATION.md ROADMAP.md RUNTIME_CONTEXT_PLAN.md TODO.md .gitignore .gitattributes; do
    if [ -e "$SOURCE_DIR/$file" ]; then
        cp -a "$SOURCE_DIR/$file" "$APP_DIR/$file"
    fi
done
cp "$SOURCE_DIR/.image-requirements.sha256" "$APP_DIR/.image-requirements.sha256.image"

# Alte Mapping-Dateien werden einmalig aus dem aktiven Config-Verzeichnis entfernt
# und sicher archiviert. Die V34-Runtime liest ausschließlich objects.json.
LEGACY_ARCHIVE="$BACKUP_DIR/legacy_v33_disabled"
mkdir -p "$LEGACY_ARCHIVE"
for file in topic_config.json mqtt2lox.json mqtt2udp_config.json udp2mqtt.json mqtt2knx.json knx2mqtt.json udp2knx.json knx2lox.json; do
    if [ -f "$CONFIG_DIR/$file" ]; then
        mv "$CONFIG_DIR/$file" "$LEGACY_ARCHIVE/$file"
        echo "MP-Gateway: Legacy-Konfiguration deaktiviert und archiviert: $file"
    fi
done

# Abhängigkeiten nur bei geänderter requirements.txt nachziehen.
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
