#!/bin/sh
set -eu

mkdir -p \
  "${MQTT2LOX_CONFIG_DIR:-/app/config}" \
  "${MQTT2LOX_DATA_DIR:-/app/data}" \
  "${MQTT2LOX_BACKUP_DIR:-/app/backups}"

exec "$@"
