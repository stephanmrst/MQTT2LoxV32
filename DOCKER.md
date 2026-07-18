# MP-Gateway 33.4.68 RC1 – Docker

## Voraussetzungen

- Docker Engine mit Docker Compose Plugin
- Linux-Host oder Linux-VM
- Freier TCP-Port `8099`

Für KNX und frei konfigurierbare UDP-Ports verwendet die Compose-Datei bewusst `network_mode: host`. Dadurch sieht MP-Gateway das lokale Netzwerk direkt und KNX-Tunneling sowie UDP-Empfang funktionieren ohne zusätzliche Portfreigaben.

## Start

Im entpackten Projektordner:

```bash
docker compose up -d --build
```

Danach ist die Oberfläche erreichbar unter:

```text
http://<IP-des-Docker-Hosts>:8099
```

Status prüfen:

```bash
docker compose ps
docker compose logs -f mp-gateway
```

## Persistente Daten

Die Compose-Datei bindet diese Ordner direkt ein:

- `./config` → Konfigurationen und Objekte
- `./data` → Laufzeitdaten und interne Brokerdaten
- `./backups` → Backups

Damit bleiben alle Einstellungen beim Neuaufbau oder Austausch des Containers erhalten.

## Update

Vor einem Update zuerst ein Backup über MP-Gateway erstellen. Danach den neuen Projektordner verwenden und die vorhandenen Ordner `config`, `data` und `backups` übernehmen.

```bash
docker compose down
docker compose up -d --build
```

## Stoppen

```bash
docker compose down
```

## Hinweise

- Die Compose-Datei ist für einen Linux-Docker-Host ausgelegt. Docker Desktop unter Windows und macOS unterstützt Host-Networking nicht in jeder Konstellation gleich zuverlässig.
- Die Anwendung läuft absichtlich als einzelner Prozess. Mehrere Web-Worker würden die MQTT-, UDP- und KNX-Runtime mehrfach starten.
- Mosquitto ist im Image enthalten, damit der optionale interne Broker weiterhin genutzt werden kann.
