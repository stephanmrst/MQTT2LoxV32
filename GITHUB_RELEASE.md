# MP-Gateway 33.4.68-rc2

GitHub-saubere Docker-RC ohne lokale Konfigurationen oder Objektdaten.

## Start

```bash
docker compose up -d --build
```

Die Anwendung läuft mit Host-Netzwerk und ist über Port `8099` des Docker-Hosts erreichbar.
Die komplette Installation und alle später erzeugten Einstellungen liegen im Docker-Volume `mpgateway_data`.

## Wichtig

Die Verzeichnisse `config`, `data`, `backups` und `logs` sind im Repository absichtlich leer. Beim Betrieb erzeugt das MP-Gateway die benötigten Dateien selbst.
