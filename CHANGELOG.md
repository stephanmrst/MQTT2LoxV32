# Changelog

## 32.7.1

- Aufraeumen nach Legacy Removal: der leere `legacy/`-Ordner und der alte `legacy/__pycache__/`-Rest wurden entfernt.
- Alte Architektur-/Blueprint-/Runtime-Plan-Dokumente auf den aktuellen `app/core.py`-Stand aktualisiert.
- `templates/CHANGELOG_v32_1_0.txt` auf die neue Startkette angepasst.
- Keine App-Logik und keine UI geaendert.
- Versionsstand auf `32.7.1` gesetzt.

## 32.7.0

- Legacy Removal Phase J final umgesetzt: der bisherige App-Kern liegt jetzt in `app/core.py`.
- Der alte Legacy-Dateipfad wurde aus dem aktiven Projekt entfernt.
- `app/main.py` startet ausschliesslich ueber `from app import create_app`.
- `app/__init__.py` ist die zentrale App Factory und registriert RuntimeContext, App-Core und Blueprints.
- Der Importlib-Dateilader wurde aus `app/engine/port.py` entfernt; dort bleiben Startup-/Dependency-Checks und Versionsinformationen.
- Interne Blueprint-Delegation verwendet jetzt `app_core` statt eines Legacy-Extension-Keys.
- Versionsstand auf `32.7.0` gesetzt.

## 32.6.8

- Legacy Removal Phase H umgesetzt: System- und Runtime-Routen als System-Blueprint registriert.
- `app/routes/system.py` registriert Bridge Start/Stop, Loxone-/MQTT-Test und interne Broker-Routen.
- `app/engine/bridge.py` enthaelt die ausgelagerten Bridge-Start/Stop-Helfer.
- Die entsprechenden `@app.route`-Registrierungen wurden aus `app/core.py` entfernt.
- Die eigentliche Bridge-Logik (`bridge_async`, `bridge_runner`), MQTT-Logik, RuntimeContext und UI bleiben unveraendert.
- Versionsstand auf `32.6.8` gesetzt.

## 32.6.7

- Legacy Removal Phase G Teil 2 umgesetzt: KNX Monitor, KNX Monitor Config und Listener-Start als KNX-Blueprint-Routen registriert.
- `app/routes/knx.py` registriert jetzt zusaetzlich `/knx_monitor`, `/knx_monitor_data`, `/knx_monitor/influx`, `/knx_monitor/influx_type`, `/knx_monitor/influx_topic` und `/knx_listener_start`.
- Die migrierten KNX-Monitor-Routen delegieren waehrend der Migration unveraendert auf die bestehenden Legacy-Handler.
- Die entsprechenden `@app.route`-Registrierungen wurden aus `app/core.py` entfernt.
- KNX Listener, xknx-nahe Logik, AsyncIO-/Thread-Logik, RuntimeContext, Eventnamen und JSON-Strukturen bleiben unveraendert.
- Versionsstand auf `32.6.7` gesetzt.

## 32.6.6

- Legacy Removal Phase G Teil 1 umgesetzt: KNX-Seiten und KNX-Mapping-Routen als Blueprint registriert.
- `app/routes/knx.py` registriert KNX Hub, KNX Settings, MQTT->KNX, UDP->KNX, KNX->MQTT und KNX->Loxone.
- Die migrierten KNX-Routen delegieren waehrend der Migration unveraendert auf die bestehenden Legacy-Handler.
- Die entsprechenden `@app.route`-Registrierungen wurden aus `app/core.py` entfernt.
- KNX Monitor, KNX Listener, xknx-nahe Logik, RuntimeContext und Thread-Logik bleiben unveraendert im Legacy-Core.
- URLs, UI, JSON-Datenstrukturen und Benutzerverhalten bleiben unveraendert.
- Versionsstand auf `32.6.6` gesetzt.

## 32.6.5

- Legacy Removal Phase F umgesetzt: alle Server-Sent-Events als Events-Blueprint registriert.
- `app/routes/events.py` registriert Status-SSE, Live-Log-SSE, Live-Log-Full-SSE, MQTT-Monitor-SSE und KNX-Monitor-SSE.
- `app/utils/sse.py` enthaelt den ausgelagerten generischen SSE-Helper mit unveraendertem Keepalive-, Error- und EventSource-Verhalten.
- Die Event-Routen verwenden weiterhin die bestehenden Payload-Funktionen und Runtime-State-Quellen.
- Die entsprechenden `@app.route`-Registrierungen und der alte SSE-Helper wurden aus `app/core.py` entfernt.
- Eventnamen, JSON-Payloads, Keepalive-Verhalten, RuntimeContext und Thread-Logik bleiben unveraendert.
- Versionsstand auf `32.6.5` gesetzt.

## 32.6.4

- Legacy Removal Phase E umgesetzt: API-, Such- und Konflikt-Routen als Blueprint registriert.
- `app/routes/api.py` registriert globale Suche, Suchseite, Konfliktpruefung und Konfliktseite.
- Die migrierten API-Routen delegieren waehrend der Migration unveraendert auf die bestehenden Legacy-Handler.
- Die entsprechenden `@app.route`-Registrierungen wurden aus `app/core.py` entfernt.
- Domain-nahe Data-/JSON-Routen bleiben bei ihren Blueprints oder im geplanten Domain-/Event-/System-Bereich.
- URLs, UI, JSON-Strukturen, Suchlogik, Konfliktlogik und Benutzerverhalten bleiben unveraendert.
- Versionsstand auf `32.6.4` gesetzt.

## 32.6.3

- Legacy Removal Phase D Teil 4 umgesetzt: kompletter Influx-Bereich als Blueprint registriert.
- `app/routes/influx.py` registriert Influx-Test, Influx Explorer, einzelnes Loeschen und Mehrfach-Loeschen.
- Die migrierten Influx-Routen delegieren waehrend der Migration unveraendert auf die bestehenden Legacy-Handler.
- Die entsprechenden `@app.route`-Registrierungen wurden aus `app/core.py` entfernt.
- URLs, UI, JSON-Strukturen, Services, Influx-Logik und Benutzerverhalten bleiben unveraendert.
- Versionsstand auf `32.6.3` gesetzt.

## 32.6.2

- Legacy Removal Phase D Teil 3 umgesetzt: kompletter Loxone-Bereich als Blueprint registriert.
- `app/routes/loxone.py` registriert MQTT->Loxone, Speichern, Test und Live-Daten.
- Die migrierten Loxone-Routen delegieren waehrend der Migration unveraendert auf die bestehenden Legacy-Handler.
- Die entsprechenden `@app.route`-Registrierungen wurden aus `app/core.py` entfernt.
- URLs, UI, Services, RuntimeContext und Benutzerverhalten bleiben unveraendert.
- Versionsstand auf `32.6.2` gesetzt.

## 32.6.1

- Legacy Removal Phase D Teil 2 umgesetzt: kompletter UDP-Bereich als Blueprint registriert.
- `app/routes/udp.py` registriert MQTT->UDP, UDP->MQTT, UDP Input, UDP Presets und UDP Discovery.
- Die migrierten UDP-Routen delegieren waehrend der Migration unveraendert auf die bestehenden Legacy-Handler.
- Die entsprechenden `@app.route`-Registrierungen wurden aus `app/core.py` entfernt.
- URLs, UI, Services, RuntimeContext und Benutzerverhalten bleiben unveraendert.
- Versionsstand auf `32.6.1` gesetzt.

## 32.6.0

- Legacy Removal Phase D Teil 1 umgesetzt: kompletter MQTT-Bereich als Blueprint registriert.
- `app/routes/mqtt.py` registriert MQTT Hub, MQTT Monitor, Monitor-JSON-/Config-Routen, Topic Explorer, Topic Manager, Brokerverwaltung und Broker-Test.
- Die migrierten MQTT-Routen delegieren waehrend der Migration unveraendert auf die bestehenden Legacy-Handler.
- Die entsprechenden `@app.route`-Registrierungen wurden aus `app/core.py` entfernt.
- URLs, HTML, JavaScript, Services, RuntimeContext und Benutzerverhalten bleiben unveraendert.
- Versionsstand auf `32.6.0` gesetzt.

## 32.5.1

- Legacy Removal Phase C umgesetzt: Config-, Backup- und Object-Routen als eigene Blueprints registriert.
- `app/routes/config.py` registriert Einstellungen, Core-/MQTT-/Influx-Speichern, Sidebar-Link-Speichern und Plugin-Speichern.
- `app/routes/backup.py` registriert Backup und Restore.
- `app/routes/objects.py` registriert Objektmanager, Objektbearbeitung, Mapping-Sync, Mapping-Rebuild, Speichern und Loeschen.
- Die migrierten Routen delegieren waehrend der Migration unveraendert auf die bestehenden Legacy-Handler.
- Die entsprechenden `@app.route`-Registrierungen wurden aus `app/core.py` entfernt.
- URLs, HTML-Ausgaben, Runtime-Logik und Benutzerverhalten bleiben unveraendert.
- Versionsstand auf `32.5.1` gesetzt.

## 32.5.0

- Legacy Removal Phase B umgesetzt: Dashboard als erster echter Blueprint registriert.
- `app/routes/dashboard.py` registriert jetzt die Routen `/`, `/dashboard_embed`, `/shell_status`, `/live_log`, `/live_log_page`, `/live_log_data`, `/clear_log` und `/clear_monitor`.
- Die Dashboard-Routen delegieren waehrend der Migration unveraendert auf die bestehenden Legacy-Handler.
- Die entsprechenden `@app.route`-Registrierungen wurden aus `app/core.py` entfernt.
- URLs, Rueckgabedaten, UI, RuntimeContext und Benutzerverhalten bleiben unveraendert.
- Versionsstand auf `32.5.0` gesetzt.

## 32.4.9

- Phase A aus `LEGACY_REMOVAL_PLAN.md` umgesetzt.
- `app/routes/` mit Blueprint-Platzhaltermodulen vorbereitet.
- `app/extensions.py` mit RuntimeContext-Zugriffshilfe angelegt.
- `app/__init__.py` als vorsichtige App-Factory-Vorbereitung angelegt.
- `app/main.py` startet weiterhin unveraendert ueber `app/engine/port.py` und `create_app()`.
- Keine Routen aus `app/core.py` verschoben, keine Logik geaendert, keine UI geaendert.
- Versionsstand auf `32.4.9` gesetzt.

## 32.4.8

- Legacy Removal Plan erstellt.
- Neue Datei `LEGACY_REMOVAL_PLAN.md` dokumentiert die aktuelle Startstruktur, verbleibende Aufgaben von `app/core.py`, Routen-/Helper-Gruppen, Zielstruktur und Migrationsphasen A bis J.
- Exit-Kriterien fuer die spaetere Entfernung von `app/core.py` definiert.
- Keine Routen verschoben, keine Logik geaendert, keine UI geaendert.
- Versionsstand auf `32.4.8` gesetzt.

## 32.4.7

- Alte KNX-Global-State-Reste aus `app/core.py` bereinigt.
- Entfernt wurden die alten Legacy-Globals fuer KNX Monitor-Log, KNX Monitor-Werte, KNX LastSeen-Dicts und Listener-Thread.
- KNX Monitor, LastSeen, Listener-Verwaltung und KNX-SSE-Versionierung verwenden nun ausschliesslich `runtime_context.knx`.
- Listener-Logik, xknx, UI und SSE-Route bleiben unveraendert.
- Keine UI-Aenderungen.
- Versionsstand auf `32.4.7` gesetzt.

## 32.4.6

- KNX RuntimeContext Phase E umgesetzt.
- `KNXState` enthaelt jetzt `monitor_version`.
- `sse_versions["knx"]` wurde durch `runtime_context.knx.monitor_version` ersetzt.
- `bump_sse("knx")` erhoeht jetzt die KNX-Monitor-Version im RuntimeContext.
- KNX-SSE liest die Version fuer `version_name == "knx"` aus `runtime_context.knx.monitor_version`.
- Andere SSE-Versionen (`log`, `mqtt`, `status`) bleiben im bestehenden `sse_versions`-Dict.
- Keine UI-Aenderungen.
- Versionsstand auf `32.4.6` gesetzt.

## 32.4.5

- KNX RuntimeContext Phase D1 umgesetzt.
- `KNXState` enthaelt jetzt Listener-Verwaltung: `listener_thread`, `listener_running`, `start_requested` und `stop_requested`.
- Wrapper fuer KNX-Listener-Verwaltung in `app/core.py` ergaenzt.
- `ensure_knx_listener_started` nutzt fuer Thread-Referenz und Running-State jetzt `runtime_context.knx`.
- Alte globale Variable `knx_listener_thread` entfernt.
- `_knx_listener_async`, `telegram_received_cb`, xknx, asyncio, `send_knx_value`, `add_knx_monitor_entry`, Monitor und SSE bleiben unveraendert.
- Keine UI-Aenderungen.
- Versionsstand auf `32.4.5` gesetzt.

## 32.4.4

- KNX RuntimeContext Phase C umgesetzt.
- `KNXState` enthaelt jetzt zusaetzlich `monitor_log` als `deque(maxlen=15)`.
- Wrapper fuer KNX-Monitor-Log in `app/core.py` ergaenzt.
- `add_knx_monitor_entry` schreibt `knx_monitor_log` weiterhin wie bisher und spiegelt zusaetzlich nach `runtime_context.knx.monitor_log`.
- KNX Monitor Payload liest Log-Eintraege bevorzugt aus `runtime_context.knx`.
- `knx_listener_thread`, xknx, asyncio, `ensure_knx_listener_started`, `knx_listener_runner`, `sse_versions["knx"]` und `/events/knx_monitor` bleiben unveraendert.
- Keine UI-Aenderungen.
- Versionsstand auf `32.4.4` gesetzt.

## 32.4.3

- KNX RuntimeContext Phase B umgesetzt.
- `KNXState` enthaelt jetzt zusaetzlich `monitor_values`.
- Wrapper fuer KNX-Monitor-Werte in `app/core.py` ergaenzt.
- `add_knx_monitor_entry` schreibt `knx_monitor_values` weiterhin wie bisher und spiegelt zusaetzlich nach `runtime_context.knx.monitor_values`.
- KNX Hub und KNX Monitor Payload lesen Monitor-Werte bevorzugt aus `runtime_context.knx`.
- `knx_monitor_log`, `knx_listener_thread`, SSE-Versionierung, Eventstream-Route und xknx Listener bleiben unveraendert.
- Keine UI-Aenderungen.
- Versionsstand auf `32.4.3` gesetzt.

## 32.4.2

- KNX RuntimeContext Phase A umgesetzt.
- `KNXState` enthaelt jetzt `mqtt2knx_last_seen`, `knx2mqtt_last_seen`, `knx2lox_last_seen` und `lock`.
- KNX-LastSeen-Wrapper in `app/core.py` ergaenzt.
- KNX-Service schreibt LastSeen-Daten optional zusaetzlich in `runtime_context.knx`.
- KNX-Routen fuer MQTT->KNX, KNX->MQTT und KNX->Loxone lesen bevorzugt aus `runtime_context.knx` mit Fallback auf alte Dicts.
- `udp2knx_last_seen` bleibt weiterhin in `runtime_context.udp`.
- Monitor-Log, Monitor-Werte, Listener-Thread, SSE und xknx bleiben unveraendert.
- Keine UI-Aenderungen.
- Versionsstand auf `32.4.2` gesetzt.

## 32.4.1

- KNX Runtime Migration Plan erstellt.
- Neue Datei `KNX_RUNTIME_MIGRATION_PLAN.md` mit KNX-States, Lesern/Schreibern, Routen, Services, Thread-/Async-/SSE-Risiken und empfohlener Migrationsreihenfolge.
- Besonders betrachtet: KNX Listener, Monitor, xknx Callback, MQTT->KNX, UDP->KNX, KNX->MQTT und KNX->Loxone.
- Keine KNX-State-Migration, keine Logikaenderungen, keine UI-Aenderungen, keine Service-Aenderungen.
- Versionsstand auf `32.4.1` gesetzt.

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
- Factory `create_runtime_context()` ergaenzt und in `app/core.py` eine globale RuntimeContext-Instanz erzeugt.
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

- RuntimeContext-Plan fuer globale Variablen und Laufzeit-States in `app/core.py` erstellt.
- Neue Datei `RUNTIME_CONTEXT_PLAN.md` mit Zweck, Lese-/Schreibstellen, betroffenen Routen, Services, Thread-/SSE-Risiko und Zielbereich.
- Listen, Dicts, Locks, Threads, Eventstream-Versionen sowie Start/Stop-Flags gesondert markiert.
- Keine Dateien verschoben, keine Funktionen verschoben, keine Logikänderungen und keine UI-Änderungen.
- Versionsstand auf `32.3.3` gesetzt.

## 32.3.2

- Blueprint-Migrationsplan fuer alle 117 Flask-Routen in `app/core.py` erstellt.
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

- Influx-Schreib-, Formatierungs- und Explorer-Hilfsfunktionen aus `app/core.py` nach `app/services/influx.py` ausgelagert.
- Legacy-Core importiert den neuen Influx-Service als `influx_service` und übergibt Config-Loader, Topic-Loader und Logger gezielt als Parameter.
- Influx Settings, Influx Explorer UI und bestehende Routen bleiben unverändert im Legacy-Core.
- Keine UI-, Logik- oder Feature-Änderungen.
- Versionsstand auf `32.2.6` gesetzt.

## 32.2.5

- KNX-Hilfs- und Bridge-Funktionen nach `app/services/knx.py` ausgelagert.
- KNX Listener, Monitor-Listen, Monitor-Payload und Monitor-Routen bleiben in `app/core.py`.
- KNX TX-Monitor-Eintraege laufen ueber den uebergebenen `add_knx_monitor_entry`-Callback weiter in die zentrale Legacy-Liste.
- KNX RX-Monitor-Eintraege werden weiterhin direkt im Legacy-Listener geschrieben.
- Keine UI- oder Feature-Aenderungen.
- Versionsstand auf `32.2.5` gesetzt.

## 32.2.4

- Loxone-Hilfsfunktionen aus `app/core.py` nach `app/services/loxone.py` ausgelagert.
- Legacy-Core importiert den neuen Loxone-Service als `loxone_service` und übergibt benötigte Legacy-Abhängigkeiten gezielt als Parameter.
- Keine Logik-, UI- oder Feature-Aenderungen.
- Versionsstand auf `32.2.4` gesetzt.

## 32.2.3

- Object-/Objektmanager-Hilfsfunktionen aus `app/core.py` nach `app/services/object.py` ausgelagert.
- Legacy-Core importiert den neuen Object-Service als `object_service` und ruft die verschobenen Funktionen mit Modulpräfix auf.
- Keine Logik-, UI- oder Feature-Aenderungen.
- Versionsstand auf `32.2.3` gesetzt.

## 32.0.0

- Technische Versionspraefixe aus Python-Dateinamen und Imports entfernt.
- Startkette auf `app/engine/port.py` und `app/core.py` umgestellt.
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
