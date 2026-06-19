# TODO

## 32.0.x

- Umbenannte Module im laufenden Betrieb gegenpruefen: Dashboard, MQTT -> Loxone, MQTT -> UDP, MQTT -> KNX und Log-Leerzustand.
- Object-Service im laufenden Betrieb gegenpruefen: Objektliste, Objekt bearbeiten, Mapping-Sync, Mapping-Rebuild und Objekt loeschen.
- Loxone-Service im laufenden Betrieb gegenpruefen: MQTT -> Loxone, Loxone IO-Datalist und Dashboard-Zaehler.
- KNX-Service im laufenden Betrieb gegenpruefen: MQTT -> KNX, UDP -> KNX, KNX Monitor mit `[KNX MONITOR ADD]`/`[KNX SSE]`, KNX -> MQTT und KNX -> Loxone.
- Influx-Service im laufenden Betrieb gegenpruefen: Dashboard-Status, Influx Explorer, MQTT/KNX/UDP-Schreibpfade und Testverbindung.
- Runtime-Service im laufenden Betrieb gegenpruefen: Statusanzeige, Live Log, `/events/status`, `/events/live_log` und interner Broker.
- Backup-Service im laufenden Betrieb gegenpruefen: Backup erstellen, Restore-Route, Backup-Dateiliste und Live-Log-Eintraege.
- Template-Service im laufenden Betrieb gegenpruefen: Dashboard, MQTT Hub, Influx Explorer, Objektmanager, KNX Monitor und Mapping-Selects.
- MQTT-Publish-Hilfen aus dem Legacy-Core in `app/services/mqtt.py` ziehen.
- MQTT-Monitor-Endpunkte schrittweise kapseln, ohne URLs zu aendern.
- Service-Tests fuer MQTT-Brokerliste, Monitor-State und Testverbindung ergaenzen.
- Service-Tests fuer `app/services/udp.py` ergaenzen: Message-Format, Mapping, Presets und UDP-Testsendung.
- Weitere UDP-Routen nur bei Bedarf duenner an den Service anbinden; URLs und Formulare bleiben stabil.

## Spaeter

- Interne Broker-Prozessverwaltung aus dem Legacy-Core herausloesen.
- Runtime-/Bridge-Logik erst nach weiterer Port-Stabilisierung modularisieren.
- Objektmanager nur nach ausdruecklicher Freigabe umbauen.
