# Changelog

## 32.4.0

- BrokerState vollstaendig in den RuntimeContext migriert.
- `BrokerState` enthaelt jetzt `process`, `running`, `status`, `start_requested`, `stop_requested`, `restart_requested` und `lock`.
- Interner-Broker-Status, Start und Stop lesen/schreiben nun `runtime_context.broker`.
- Alte globale Variable `internal_broker_process` entfernt.
- Keine Bridge-, MQTT-, UDP- oder KNX-States geaendert.
- Keine UI-Aenderungen.
- Versionsstand auf `32.4.0` gesetzt.

## 32.3.9

- UDP-Laufzeitdaten schrittweise in den RuntimeContext migriert.
- `UDPState` enthaelt jetzt MQTT->UDP, UDP->MQTT, UDP->KNX, UDP-Input, Discovery-State, Discovery-Flag und Lock.
- Legacy-Wrapper fuer UDP-Last-Seen-Lesen, Schreiben und Leeren ergaenzt.
- UDP-Service schreibt Last-Seen-Daten optional zusaetzlich in `runtime_context.udp`.
- UDP-Seiten und UDP-Datenrouten lesen bevorzugt aus `runtime_context.udp` mit Fallback auf bestehende parallele Globals.
- Alte UDP-Globals bleiben parallel bestehen.
- Keine MQTT-, KNX-, Bridge- oder Broker-States geaendert.
- Keine UI- oder UDP-Logik-Aenderungen.
- Versionsstand auf `32.3.9` gesetzt.

## 32.3.8

- MQTT-Monitor-State schrittweise in den RuntimeContext vorbereitet.
- `MQTTState` enthaelt jetzt `mqtt_monitor_values`, `mqtt_clients`, `mqtt_client`, `monitor_version` und `lock`.
- Legacy-Wrapper fuer MQTT-Monitor-Lesen, Schreiben und Leeren ergaenzt.
- MQTT-Callback schreibt Monitorwerte zusaetzlich in `runtime_context.mqtt`.
- MQTT Monitor, MQTT Hub, `/monitor_data` und MQTT-Monitor-SSE lesen bevorzugt aus `runtime_context.mqtt`.
- Alte MQTT-Globals bleiben parallel bestehen.
- Keine KNX-, UDP-, Bridge- oder Broker-States migriert.
- Keine UI- oder MQTT-Broker-Logik geaendert.
- Versionsstand auf `32.3.8` gesetzt.

## 32.3.7

- Bridge-State vollstaendig in `runtime_context.bridge` migriert.
- `BridgeState` enthaelt jetzt `running`, `status`, `stop_requested` und `thread`.
- Alte globale Variablen `bridge_running`, `bridge_status`, `bridge_stop_requested` und `bridge_thread` entfernt.
- Bridge Start/Stop, Status-SSE, Dashboard-Status und Layout-Status lesen/schreiben nun den RuntimeContext.
- Keine MQTT-, UDP-, KNX- oder Broker-States migriert.
- Keine UI-Aenderungen.
- Versionsstand auf `32.3.7` gesetzt.

## 32.3.5

- LiveLog-State im RuntimeContext-Grundgeruest vorbereitet.
- `LiveLogState` enthaelt jetzt `entries`, `lock` und `version`.
- Factory `create_runtime_context()` ergaenzt und in `legacy/app_legacy.py` eine globale RuntimeContext-Instanz erzeugt.
- Bestehendes Legacy-`live_log` bleibt aktiv; `add_log_entry` spiegelt neue Eintraege zusaetzlich in `runtime_context.live_log`.
- Keine Bridge-, MQTT-, KNX-, UDP- oder Broker-States veraendert.
- Keine UI-Aenderungen und keine Routen-Aenderungen.
- Versionsstand auf `32.3.5` gesetzt.

## 32.3.4

- Grundgeruest fuer den zukuenftigen RuntimeContext unter `app/runtime/` erstellt.
- Leere Dataclass-Platzhalter fuer Bridge, Live-Log, MQTT, KNX, UDP und Broker angelegt.
- `RuntimeContext` als reine Struktur in `app/runtime/context.py` definiert.
- Noch keine Instanz erzeugt, nichts importiert und keine Laufzeitdaten verschoben.
- Keine Logikaenderungen, keine UI-Aenderungen und keine Service-Aenderungen.
- Versionsstand auf `32.3.4` gesetzt.

## 32.3.3

- RuntimeContext-Plan fuer globale Variablen und Laufzeit-States in `legacy/app_legacy.py` erstellt.
- Neue Datei `RUNTIME_CONTEXT_PLAN.md` mit Zweck, Lese-/Schreibstellen, betroffenen Routen, Services, Thread-/SSE-Risiko und Zielbereich.
- Listen, Dicts, Locks, Threads, Eventstream-Versionen sowie Start/Stop-Flags gesondert markiert.
- Keine Dateien verschoben, keine Funktionen verschoben, keine Logikänderungen und keine UI-Änderungen.
- Versionsstand auf `32.3.3` gesetzt.

## 32.3.2

- Blueprint-Migrationsplan fuer alle 117 Flask-Routen in `legacy/app_legacy.py` erstellt.
- Neue Datei `BLUEPRINT_PLAN.md` mit Ziel-Blueprint, Methode, aktueller Funktion, Abhaengigkeiten, Risiko, Markierungen und empfohlener Reihenfolge.
- SSE-, JSON-, Write- und globale-State-Routen gesondert markiert.
- Keine Routen verschoben, keine Logikänderungen und keine UI-Änderungen.
- Versionsstand auf `32.3.2` gesetzt.

## 32.3.1

- Architektur-Review nach der ersten Modularisierung aktualisiert und vertieft.
- `ARCHITECTURE_REVIEW.md` neu strukturiert mit Datei-Bewertung, Routen-Kandidaten, Import-/State-Befunden und Zielstruktur.
- Keine Dateien verschoben, keine Funktionen verschoben, keine Logikänderungen und keine UI-Änderungen.
- Versionsstand auf `32.3.1` gesetzt.

## 32.3.0

- Architektur-Review nach der ersten Modularisierungsrunde erstellt.
- Neuer Bericht `ARCHITECTURE_REVIEW.md` mit aktueller Struktur, Problemen, Prioritäten, Aufwand und Empfehlungen.
- Keine Funktionsverschiebungen, keine Logikänderungen und keine UI-Änderungen.
- Versionsstand auf `32.3.0` gesetzt.

## 32.2.9

- Template-/HTML-Hilfsfunktionen nach `app/services/template.py` ausgelagert.
- Legacy-Core importiert den neuen Template-Service als `template_service`; bestehende Render-Routen und große `render_template_string`-Blöcke bleiben unverändert.
- Eingebetteter Seitenrahmen, Layout-Renderer, Datalist-Builder und Select-Builder nutzen nun den Template-Service.
- Keine UI-, Text-, Logik- oder Feature-Änderungen.
- Versionsstand auf `32.2.9` gesetzt.

## 32.2.8

- Backup-Dateisuche sowie Backup-/Restore-Zip-Logik nach `app/services/backup.py` ausgelagert.
- Legacy-Core importiert den neuen Backup-Service als `backup_service` und behält die bestehenden `/backup`- und `/restore`-Routen unverändert.
- Backup-Pfade, Backup-Ordner und Restore-Zielprüfung bleiben unverändert.
- Keine UI-, Logik- oder Feature-Änderungen.
- Versionsstand auf `32.2.8` gesetzt.

## 32.2.7

- Runtime-/Status-/Live-Log- und interner-Broker-Hilfsfunktionen nach `app/services/runtime.py` ausgelagert.
- Legacy-Core importiert den neuen Runtime-Service als `runtime_service` und übergibt Live-Log, Status-State, Config-Loader und Broker-Prozess gezielt als Parameter.
- Bestehende Status-, Live-Log- und Broker-Routen bleiben unverändert.
- Keine UI-, Logik- oder Feature-Änderungen.
- Versionsstand auf `32.2.7` gesetzt.

## 32.2.6

- Influx-Schreib-, Formatierungs- und Explorer-Hilfsfunktionen aus `legacy/app_legacy.py` nach `app/services/influx.py` ausgelagert.
- Legacy-Core importiert den neuen Influx-Service als `influx_service` und übergibt Config-Loader, Topic-Loader und Logger gezielt als Parameter.
- Influx Settings, Influx Explorer UI und bestehende Routen bleiben unverändert im Legacy-Core.
- Keine UI-, Logik- oder Feature-Änderungen.
- Versionsstand auf `32.2.6` gesetzt.

## 32.2.5

- KNX-Hilfs- und Bridge-Funktionen nach `app/services/knx.py` ausgelagert.
- KNX Listener, Monitor-Listen, Monitor-Payload und Monitor-Routen bleiben in `legacy/app_legacy.py`.
- KNX TX-Monitor-Eintraege laufen ueber den uebergebenen `add_knx_monitor_entry`-Callback weiter in die zentrale Legacy-Liste.
- KNX RX-Monitor-Eintraege werden weiterhin direkt im Legacy-Listener geschrieben.
- Keine UI- oder Feature-Aenderungen.
- Versionsstand auf `32.2.5` gesetzt.

## 32.2.4

- Loxone-Hilfsfunktionen aus `legacy/app_legacy.py` nach `app/services/loxone.py` ausgelagert.
- Legacy-Core importiert den neuen Loxone-Service als `loxone_service` und übergibt benötigte Legacy-Abhängigkeiten gezielt als Parameter.
- Keine Logik-, UI- oder Feature-Aenderungen.
- Versionsstand auf `32.2.4` gesetzt.

## 32.2.3

- Object-/Objektmanager-Hilfsfunktionen aus `legacy/app_legacy.py` nach `app/services/object.py` ausgelagert.
- Legacy-Core importiert den neuen Object-Service als `object_service` und ruft die verschobenen Funktionen mit Modulpräfix auf.
- Keine Logik-, UI- oder Feature-Aenderungen.
- Versionsstand auf `32.2.3` gesetzt.

## 32.0.0

- Technische Versionspraefixe aus Python-Dateinamen und Imports entfernt.
- Startkette auf `app/engine/port.py` und `legacy/app_legacy.py` umgestellt.
- Service-Module ohne Versionspraefix angebunden: `config.py`, `mqtt.py`, `udp.py`.
- Sichtbare Versionsanzeige auf `32.0.0` gesetzt.
- Keine UI-, Logik- oder Feature-Aenderungen.

## 32.2.2

- UTF-8-Auslieferung der Flask-App fuer HTML und JSON abgesichert.
- Mojibake-/Umlautfehler im Port korrigiert, unter anderem `MQTT → UDP`, `MQTT → KNX` und `Noch keine Logeinträge.`.
- `render_template_string`-HTML-Bloecke auf defekte Sonderzeichen geprueft und repariert.
- Keine Logik- oder UI-Aenderungen.
- Versionsstand auf `32.2.2` gesetzt.

## 32.2.1

- UDP Listener, UDP-Sendefunktionen, MQTT->UDP, UDP->MQTT, UDP-Presets und UDP-Testhilfen in `app/services/udp.py` gekapselt.
- Legacy-Core verwendet den neuen UDP-Service weiter ueber die bestehenden Funktionsnamen und URLs.
- Live-State fuer `mqtt2udp_last_seen`, `udp2mqtt_last_seen` und `udp_input_last_seen` liegt nun im Service und bleibt fuer die alten Seiten verfuegbar.
- Keine UI-Aenderungen und keine Config-Dateinamen geaendert.
- Versionsstand auf `32.2.1` angehoben.

## 32.2.0

- MQTT-Verbindungsaufbau, Brokerliste, MQTT-Monitor-State und MQTT-Testverbindung in `app/services/mqtt.py` gekapselt.
- Legacy-Core verwendet den neuen Service weiter mit dem bestehenden Routing-Callback.
- MQTT-Monitor-Werte bleiben unter dem alten Namen `mqtt_monitor_values` verfuegbar.
- Keine UI-Aenderungen und keine Config-Dateinamen geaendert.
- Versionsstand auf `32.2.0` angehoben.

## 32.1.0

- Config-/JSON-Dateifunktionen aus dem Port in `app/services/config.py` ausgelagert.
- Legacy-Core importiert und nutzt die v32-Service-Funktionen weiter unter den alten Funktionsnamen.
- Keine UI-Aenderungen und keine Objektmanager-Logikaenderungen.
- Versionsstand auf `32.1.0` angehoben.

## 32.0.1

- `loxwebsocket`, `paho-mqtt` und `requests` werden im Port optional abgefangen.
- Fehlen optionale Bibliotheken, startet die Anwendung trotzdem vollstaendig.
- Bridge-/Shell-Status zeigt bei fehlendem Loxone-Modul: `Loxone: Bibliothek nicht installiert`.
- Startpruefung ergaenzt: Python, Flask, MQTT, Loxone, Requests sowie optionale KNX/Influx-Module.
- `requirements.txt` fuer den Port ergaenzt.

## 32.0.0-port

- Legacy-Anwendung als funktionale Basis in die v32-Projektstruktur geladen.
- Config-, Mapping-, Monitor-, Backup-, MQTT-, UDP-, KNX-, Loxone-, Influx- und Objektmanager-Logik bleibt erhalten.
- v32 Startpunkt `app/main.py` delegiert an den Legacy-Core.
- Persistente Pfade werden auf `config/`, `data/` und `backups/` im v32-Projekt gesetzt.
