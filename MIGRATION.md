# Migration

## Aktueller Stand: 33.2.8a

Der Projektstand basiert auf dem bereinigten v32-Port und fuehrt mit 33.2.8a die V33-Entwicklung fuer Objektmanager 2.0 fort. Die aktive Startkette ist:

- `app/main.py`
- `app/__init__.py`
- `app/engine/port.py`
- `app/core.py`

Die Config-/JSON-Dateifunktionen liegen in `app/services/config.py`. MQTT-Verbindungsaufbau, Brokerliste, Monitor-State und Testverbindung liegen in `app/services/mqtt.py`. UDP Listener, UDP-Sendefunktionen, UDP-Presets und MQTT/UDP-Mapping-Hilfen liegen in `app/services/udp.py`. Objektmanager-Hilfsfunktionen liegen in `app/services/object.py`; der alte Objektmanager bleibt technisch auf `/objects` erreichbar und der neue Objektmanager V33 bleibt auf `/objects_v33` erreichbar. 33.2.8a ist nur ein UI-Feinschliff: Objektliste und Editorbereich des Objektmanager V33 nutzen dieselbe Arbeitsflaeche. Es gibt keine Routing-, Runtime-, Objektlogik- oder Adapterlogik-Aenderung.

## Von 33.2.8 nach 33.2.8a

Keine manuelle Migration der bestehenden Konfigurations- oder Mapping-Dateien erforderlich.

33.2.8a ist nur eine UI-/CSS-Angleichung:

- Linke Objektliste und rechter Editorbereich nutzen denselben Arbeitsflaechen-Hintergrund.
- Sidebar bleibt unveraendert dunkel.
- Objektkarten, Panels, Buttons und Protokoll-Badges bleiben unveraendert.
- Keine Route umgestellt, keine Runtime-Aenderung, keine Objektlogik- oder Adapterlogik-Aenderung.

## Von 33.2.7g nach 33.2.8

Keine manuelle Migration der bestehenden Konfigurations- oder Mapping-Dateien erforderlich.

33.2.8 ist nur eine UI-/CSS-Angleichung:

- `/objects_v33` nutzt fuer Hauptflaeche und Detailbereich den Standard-Grundhintergrund.
- Sidebar bleibt unveraendert.
- Objektkarten-Farben und Protokoll-Badges bleiben unveraendert.
- Keine Route umgestellt, keine Runtime-Aenderung, keine Objektlogik- oder Adapterlogik-Aenderung.

## Von 33.2.7c nach 33.2.7g

Keine manuelle Migration der bestehenden Konfigurations- oder Mapping-Dateien erforderlich.

33.2.7g ist nur ein Restore der externen Sidebar-Buttons:

- Externe Dienste werden generisch aus der Sidebar-Button-Konfiguration geladen.
- Nur aktive Eintraege mit Name und URL werden angezeigt.
- Name, URL, Reihenfolge und `new_tab` werden aus der Config uebernommen.
- `new_tab=true` oeffnet im neuen Browser-Tab.
- `new_tab=false` oeffnet im Shell-Betrieb wieder im rechten Content-Bereich.
- `Influx Explorer` bleibt die interne MP-Gateway-Seite `/influx_explorer`.
- Keine Route umgestellt, keine Runtime-Aenderung, keine Objektlogik- oder Adapterlogik-Aenderung.

## Von 33.2.7a nach 33.2.7c

Keine manuelle Migration der bestehenden Konfigurations- oder Mapping-Dateien erforderlich.

33.2.7c ist nur eine Sidebar-Link-Korrektur:

- `Influx Explorer` bleibt intern auf `/influx_explorer`.
- `InfluxDB` verwendet die externe URL aus der Konfiguration.
- `Grafana` verwendet die externe URL aus der Konfiguration.
- Fehlt eine externe URL, wird der Eintrag deaktiviert angezeigt.
- Kein falscher Fallback auf interne Seiten.
- Keine Route umgestellt, keine Runtime-Aenderung, keine Objektlogik- oder Adapterlogik-Aenderung.

## Von 33.2.7 nach 33.2.7a

Keine manuelle Migration der bestehenden Konfigurations- oder Mapping-Dateien erforderlich.

33.2.7a ist nur ein Sidebar-Feinschliff:

- Gruppenueberschrift `MP-Gateway` entfernt.
- Alter Objektmanager-Link aus der Sidebar entfernt.
- `Objektmanager V33` bleibt unveraendert sichtbar.
- `Externe Dienste` zeigt nur InfluxDB und Grafana.
- Keine Route umgestellt, kein Redirect eingefuehrt, kein alter Objektmanager entfernt.
- Keine Registry-Logik-Aenderung, keine Objektlogik-Aenderung, keine Adapterlogik-Aenderung, keine Runtime-Aenderung.

## Von 33.2.6 nach 33.2.7

Keine manuelle Migration der bestehenden Konfigurations- oder Mapping-Dateien erforderlich.

33.2.7 ist nur eine Layout-Fundament-Version:

- Sidebar ist in `MP-Gateway` und `Externe Dienste` gegliedert.
- Beide Objektmanager-Links bleiben erhalten: `/objects` und `/objects_v33`.
- Externe Dienste zeigen InfluxDB und Grafana getrennt.
- `templates/layout/base.html` und `templates/layout/page_header.html` wurden vorbereitet.
- `/objects_v33` nutzt die neue Base-Struktur.
- Keine Route umgestellt, kein Redirect eingefuehrt, kein alter Objektmanager entfernt.
- Keine Registry-Logik-Aenderung, keine Objektlogik-Aenderung, keine Adapterlogik-Aenderung, keine Runtime-Aenderung, keine Mapping-Erzeugung.

## Von 33.2.5 nach 33.2.6

Keine manuelle Migration der bestehenden Konfigurations- oder Mapping-Dateien erforderlich.

33.2.6 ist nur eine UI-/Template-Version:

- Die globale Sidebar liegt als gemeinsame Komponente in `templates/shared/sidebar.html`.
- Die Sidebar-Optik liegt zentral in `static/css/sidebar.css`.
- Shell-Layout und Standardlayout binden dieselbe Sidebar-Komponente ein.
- Aktiver Menuepunkt, Header, Status, Abstaende, Schriftgroessen und Sidebar-Breite sind vereinheitlicht.
- Keine Registry-Logik-Aenderung, keine Runtime-Aenderung, keine Routing-Logik-Aenderung, keine Mapping-Erzeugung.

## Von 33.2.4 nach 33.2.5

Keine manuelle Migration der bestehenden Konfigurations- oder Mapping-Dateien erforderlich.

33.2.5 ist nur eine UI-/Layout-Version:

- Filterchips zeigen keine vorangestellten Anfangsbuchstaben mehr.
- Protokoll-Badges bleiben immer sichtbar und nutzen die festgelegten MP-Gateway-Protokollfarben.
- Ausgewaehlte Objektkarten werden deutlicher hervorgehoben.
- `docs/UI_GUIDELINES.md` dokumentiert Layout und Protokollfarben.
- Keine Registry-Logik-Aenderung, keine Adapterlogik-Aenderung, keine Runtime-Aenderung, keine Mapping-Erzeugung.

## Von 33.2.3 nach 33.2.4

Keine manuelle Migration der bestehenden Konfigurations- oder Mapping-Dateien erforderlich.

33.2.4 passt nur das Layout des Objektmanagers V33 an:

- Pro Objektkarte werden MQTT, Loxone, UDP, KNX und Influx immer angezeigt.
- Aktive Adapter-Badges sind farbig, inaktive Adapter-Badges grau gedimmt.
- Objektkarten haben klarere Initialen, Abstaende und eine deutlichere Auswahlmarkierung.
- Keine Registry-Logik-Aenderung, keine Adapterlogik-Aenderung, keine Runtime-Aenderung, keine Mapping-Erzeugung.

## Von 33.2.2 nach 33.2.3

Keine manuelle Migration der bestehenden Konfigurations- oder Mapping-Dateien erforderlich.

33.2.3 verlinkt nur den neuen Objektmanager V33 in der Sidebar:

- Neuer Sidebar-Eintrag `Objektmanager V33`.
- Ziel-URL ist `/objects_v33`.
- Bestehender Eintrag `Objektmanager` bleibt unveraendert auf `/objects`.
- `/objects_v33` nutzt nun ein zweigeteiltes Industrial-Dark-Layout mit Tabs fuer Allgemein, Adapter und Routing.
- Keine Runtime-Aenderung, keine Registry-Logik-Aenderung, keine Adapterlogik-Aenderung, keine V32-Objects-Aenderung.

## Von 33.2.1 nach 33.2.2

Keine manuelle Migration der bestehenden Konfigurations- oder Mapping-Dateien erforderlich.

33.2.2 ergaenzt nur eine passive Routing-Vorschau im Objektmanager V33:

- `app/services/object_routing_preview.py` baut Vorschau-Eintraege aus aktiven Adaptern.
- `/objects_v33/edit/<uuid>` zeigt Quelle, Ziel, Richtung und Status `Vorschau`.
- Influx wird nur als Ziel bewertet.
- Inaktive Adapter werden ignoriert.
- Keine Runtime-Anbindung, keine Mapping-Aenderung, keine V32-Objects-Aenderung.

## Von 33.2.0 nach 33.2.1

Keine manuelle Migration der bestehenden Konfigurations- oder Mapping-Dateien erforderlich.

33.2.1 bereitet das Branding vor:

- Neuer sichtbarer App-Name: `MP-Gateway`.
- Untertitel: `Das Multiprotokoll-Gateway`.
- Legacy-/Technikname: `MQTT2Lox`.
- Paket-, Ordner-, Routen-, Env- und Config-Namen bleiben unveraendert.
- Keine Runtime-Aenderung, keine Mapping-Aenderung.

## Von 33.1.2 nach 33.2.0

Keine manuelle Migration der bestehenden Konfigurations- oder Mapping-Dateien erforderlich.

33.2.0 strukturiert die passive Adapterbearbeitung im neuen Objektmanager V33:

- Adapter-Komponenten liegen unter `app/templates/objects_v33/adapters/`.
- MQTT, UDP, KNX, Loxone und Influx speichern eigene Grundeinstellungen am V33-Objekt.
- Allgemeine Objektdaten und Adapterdaten werden in getrennten Formularen gespeichert.
- `object_adapter_engine.py` verwaltet Deserialisierung und Serialisierung der Adapterdaten.
- Keine Runtime-Anbindung, keine Mapping-Erzeugung, keine Aenderung bestehender Mappings.

## Von 33.1.1 nach 33.1.2

Keine manuelle Migration der bestehenden Konfigurations- oder Mapping-Dateien erforderlich.

33.1.2 integriert die Adapterverwaltung in den neuen Objektmanager V33:

- Objektbearbeitung zeigt MQTT, UDP, KNX, Loxone und Influx.
- Adapterbereich nutzt schlichte Cards/Chips mit aktiv/inaktiv, Richtung, Datentyp und Kurzstatus.
- Adapter koennen aktiviert, deaktiviert und in Platzhalterdialogen bearbeitet werden.
- Adapterdaten kommen aus `object_registry.py`; Instanzen werden ueber `object_adapter_engine.py` verwaltet.
- Keine Runtime-Anbindung, keine Mapping-Erzeugung, keine V32-Objects-Aenderung.

## Von 33.1.0 nach 33.1.1

Keine manuelle Migration der bestehenden Konfigurations- oder Mapping-Dateien erforderlich.

33.1.1 stabilisiert die interne Identitaet von V33-Objekten:

- `uuid` ist die feste interne ID.
- `key` ist der technische lesbare Schluessel.
- `name` bleibt der frei aenderbare Anzeigename.
- Bestehende V33-Registry-Eintraege ohne `uuid` oder `key` werden beim Laden automatisch ergaenzt.
- Bearbeiten und Loeschen in `/objects_v33` verwenden nun `uuid`.
- Keine Runtime-Aenderung, keine V32-Objects-Aenderung, keine Mapping-Aenderung.

## Von 33.0.3 nach 33.1.0

Keine manuelle Migration der bestehenden Konfigurations- oder Mapping-Dateien erforderlich.

33.1.0 startet den neuen Objektmanager V33 parallel:

- Neue Route `/objects_v33`.
- Neuer Blueprint `app/routes/objects_v33.py`.
- Neue Templates unter `templates/objects_v33/`.
- Datenquelle ist `app/services/object_registry.py`.
- Bestehender Objektmanager unter `/objects` bleibt unveraendert.
- Keine Runtime-Anbindung, keine Adapterbearbeitung, keine Aenderung bestehender Mappings.

## Von 33.0.2 nach 33.0.3

Keine manuelle Migration der Konfigurationsdateien erforderlich.

33.0.3 bereitet nur die einheitliche V33-Adapter-Schnittstelle vor:

- `app/services/object_adapter_engine.py` enthaelt passive Adapterklassen fuer MQTT, Loxone, UDP, KNX und Influx.
- Adapter besitzen nur Validierung, Serialisierung, Deserialisierung und die gemeinsamen Felder `enabled`, `direction`, `datatype`.
- `object_registry.py` kann diese Adapterobjekte speichern und laden.
- Keine Kommunikation, keine Runtime-Logik, keine UI-Aenderung, keine Routen-Aenderung.

## Von 33.0.1 nach 33.0.2

Keine manuelle Migration der Konfigurationsdateien erforderlich.

33.0.2 bereitet nur die V33-Objekt-Registry vor:

- `app/services/object_registry.py` enthaelt passive CRUD- und Validierungsfunktionen fuer `ObjectDefinition`.
- Speicherziel ist `data/objects_v33.json`; wenn die Datei fehlt, wird eine leere Liste verwendet.
- Bestehende Objektmanager-Logik, Mapping-Dateien, Runtime, UI und Routen bleiben unveraendert.

## Von 33.0.0 nach 33.0.1

Keine manuelle Migration der Konfigurationsdateien erforderlich.

33.0.1 dokumentiert nur das V33-Adaptermodell:

- `docs/OBJECT_ADAPTER_MODEL.md` beschreibt gemeinsame Adapterfelder und die Protokollprofile fuer MQTT, Loxone, UDP, KNX und Influx.
- Bestehende Mappings bleiben unveraendert.
- Keine Runtime-Logik geaendert, keine UI-Aenderung, keine Routen-Aenderung.

## Von 32.7.1 nach 33.0.0

Keine manuelle Migration der Konfigurationsdateien erforderlich.

33.0.0 legt nur die Grundlage fuer den objektzentrierten Umbau:

- `docs/OBJECT_MANAGER_V33_PLAN.md` beschreibt Leitbild, Objektmodell, Adaptermodell, Migrationsstrategie, Risiken und Exit-Kriterien.
- `app/services/object_model.py` enthaelt passive Dataclasses und Validierungshelfer fuer spaetere Objektmanager-2.0-Arbeit.
- Bestehende Mappings bleiben aktive Kompatibilitaets- und Runtime-Quelle.
- Keine Runtime-Logik geaendert, keine UI-Aenderung, keine Routen-Aenderung.

## Von 32.7.0 nach 32.7.1

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geaendert wurde nur die Nacharbeit nach Legacy Removal:

- Der alte `legacy/`-Ordner wurde entfernt, nachdem nur noch `__pycache__` enthalten war.
- Historische Architektur- und Runtime-Dokumente wurden auf den aktuellen `app/core.py`-Stand angepasst.
- Keine App-Logik geaendert, keine UI-Aenderung.

## Von 32.6.8 nach 32.7.0

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geaendert wurde nur die finale App-Factory-/Core-Umstellung:

- Der bisherige App-Kern liegt jetzt in `app/core.py`.
- `app/main.py` startet ueber `from app import create_app`.
- `app/__init__.py` ist die zentrale Factory und registriert Blueprints, RuntimeContext und App-Core.
- `app/engine/port.py` enthaelt nur noch Startup-/Dependency-Checks und Versionsinformationen.
- Die alten Importlib-Dateilader und Legacy-Dateipfade wurden entfernt.
- Keine UI-Aenderung, keine URL-Aenderung, keine Konfigurationsmigration.

## Von 32.6.7 nach 32.6.8

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geaendert wurde nur die System-/Runtime-Blueprint-Migration:

- Bridge Start/Stop, Loxone-Test, MQTT-Test und interne Broker-Routen werden jetzt ueber `app/routes/system.py` registriert.
- Bridge Start/Stop-Helfer liegen in `app/engine/bridge.py`.
- Die eigentliche Bridge-Logik (`bridge_async`, `bridge_runner`) bleibt unveraendert.
- Keine MQTT-Logik geaendert, keine Runtime-Aenderung, keine UI-Aenderung.

## Von 32.6.6 nach 32.6.7

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geaendert wurde nur die KNX-Monitor-Blueprint-Migration:

- KNX Monitor, KNX Monitor Data, KNX Monitor Influx-Schalter, Influx-Typ, Influx-Topic und Listener-Start werden jetzt ueber `app/routes/knx.py` registriert.
- Die URLs und HTML-/JSON-/Redirect-Rueckgaben bleiben unveraendert.
- Die Handler delegieren weiterhin auf die bestehenden Legacy-Funktionen.
- Keine xknx-Logik geaendert, keine AsyncIO-/Thread-Logik geaendert, keine Runtime-Aenderung, keine UI-Aenderung.

## Von 32.6.5 nach 32.6.6

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geaendert wurde nur die KNX-Seiten-/Mapping-Blueprint-Migration:

- KNX Hub, KNX Settings, MQTT->KNX, UDP->KNX, KNX->MQTT und KNX->Loxone werden jetzt ueber `app/routes/knx.py` registriert.
- KNX Monitor, KNX Listener, xknx-nahe Logik und RuntimeContext bleiben unveraendert im Legacy-Core.
- Die URLs und HTML-/JSON-/Redirect-Rueckgaben bleiben unveraendert.
- Die Handler delegieren weiterhin auf die bestehenden Legacy-Funktionen.
- Keine Listener-Logik geaendert, keine Runtime-Aenderung, keine UI-Aenderung.

## Von 32.6.4 nach 32.6.5

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geaendert wurde nur die Event-/SSE-Blueprint-Migration:

- Status-SSE, Live-Log-SSE, Live-Log-Full-SSE, MQTT-Monitor-SSE und KNX-Monitor-SSE werden jetzt ueber `app/routes/events.py` registriert.
- Der generische SSE-Helper liegt in `app/utils/sse.py`.
- Eventnamen, JSON-Payloads und Keepalive-Verhalten bleiben unveraendert.
- Keine RuntimeContext-Aenderung, keine Thread-Logik-Aenderung, keine UI-Aenderung.

## Von 32.6.3 nach 32.6.4

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geaendert wurde nur die API-/Such-Blueprint-Migration:

- Globale Suche, Suchseite, Konfliktpruefung und Konfliktseite werden jetzt ueber `app/routes/api.py` registriert.
- Domain-nahe Data-/JSON-Routen bleiben bei ihren bestehenden Blueprints oder im geplanten Domain-/Event-/System-Bereich.
- Die URLs und HTML-/JSON-Rueckgaben bleiben unveraendert.
- Die Handler delegieren weiterhin auf die bestehenden Legacy-Funktionen.
- Keine Suchlogik geaendert, keine Konfliktlogik geaendert, keine UI-Aenderung.

## Von 32.6.2 nach 32.6.3

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geaendert wurde nur die Influx-Blueprint-Migration:

- Influx-Test, Influx Explorer, einzelnes Loeschen und Mehrfach-Loeschen werden jetzt ueber `app/routes/influx.py` registriert.
- Die URLs und HTML-/JSON-/Redirect-Rueckgaben bleiben unveraendert.
- Die Handler delegieren weiterhin auf die bestehenden Legacy-Funktionen.
- Keine Services geaendert, keine Influx-Logik geaendert, keine UI-Aenderung.

## Von 32.6.1 nach 32.6.2

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geaendert wurde nur die Loxone-Blueprint-Migration:

- MQTT->Loxone, Speichern, Test und Live-Daten werden jetzt ueber `app/routes/loxone.py` registriert.
- Die URLs und HTML-/JSON-/Redirect-Rueckgaben bleiben unveraendert.
- Die Handler delegieren weiterhin auf die bestehenden Legacy-Funktionen.
- Keine Services geaendert, keine RuntimeContext-Aenderung, keine UI-Aenderung.

## Von 32.6.0 nach 32.6.1

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geaendert wurde nur die UDP-Blueprint-Migration:

- MQTT->UDP, UDP->MQTT, UDP Input, UDP Presets und UDP Discovery werden jetzt ueber `app/routes/udp.py` registriert.
- Die URLs und HTML-/JSON-/Redirect-Rueckgaben bleiben unveraendert.
- Die Handler delegieren weiterhin auf die bestehenden Legacy-Funktionen.
- Keine Services geaendert, keine RuntimeContext-Aenderung, keine UI-Aenderung.

## Von 32.5.1 nach 32.6.0

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geaendert wurde nur die MQTT-Blueprint-Migration:

- MQTT Hub, MQTT Monitor, Topic Explorer, Topic Manager, Brokerverwaltung und Broker-Test werden jetzt ueber `app/routes/mqtt.py` registriert.
- Die URLs und HTML-/JavaScript-/JSON-Rueckgaben bleiben unveraendert.
- Die Handler delegieren weiterhin auf die bestehenden Legacy-Funktionen.
- Keine Services geaendert, keine RuntimeContext-Aenderung, keine UI-Aenderung.

## Von 32.5.0 nach 32.5.1

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geaendert wurde nur die naechste Blueprint-Migration:

- Config-Routen werden jetzt ueber `app/routes/config.py` registriert.
- Backup- und Restore-Routen werden jetzt ueber `app/routes/backup.py` registriert.
- Object-Manager-Routen werden jetzt ueber `app/routes/objects.py` registriert.
- Die URLs und HTML-/Redirect-/JSON-Rueckgaben bleiben unveraendert.
- Die Handler delegieren weiterhin auf die bestehenden Legacy-Funktionen.
- Keine Runtime-Logik geaendert, keine UI geaendert.

## Von 32.4.9 nach 32.5.0

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geaendert wurde nur die erste Blueprint-Migration:

- Dashboard-Routen werden jetzt ueber `app/routes/dashboard.py` registriert.
- Die URLs `/`, `/dashboard_embed`, `/shell_status`, `/live_log`, `/live_log_page`, `/live_log_data`, `/clear_log` und `/clear_monitor` bleiben unveraendert.
- Die Handler delegieren weiterhin auf die bestehenden Legacy-Funktionen.
- Keine Rueckgabedaten geaendert, keine UI geaendert, keine RuntimeContext-Aenderung.

## Von 32.4.8 nach 32.4.9

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geaendert wurde nur die Strukturvorbereitung:

- `app/routes/` enthaelt Platzhaltermodule fuer die spaeteren Blueprints.
- `app/extensions.py` enthaelt eine RuntimeContext-Zugriffshilfe.
- `app/__init__.py` enthaelt eine vorsichtige App-Factory-Vorbereitung.
- `app/main.py` startet weiterhin ueber `app/engine/port.py` und Legacy.
- Keine Routen verschoben, keine Logik geaendert, keine UI geaendert.

## Von 32.4.7 nach 32.4.8

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geaendert wurde nur die Dokumentation:

- `LEGACY_REMOVAL_PLAN.md` ergaenzt.
- Keine Routen verschoben.
- Keine Logik geaendert.
- Keine UI geaendert.

## Von 32.4.6 nach 32.4.7

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geaendert wurde nur die KNX RuntimeContext-Bereinigung:

- Alte KNX-Global-State-Reste wurden aus `app/core.py` entfernt.
- KNX Monitor, LastSeen, Listener-Verwaltung und KNX-SSE-Versionierung nutzen `runtime_context.knx`.
- Listener-Logik, xknx, UI und SSE-Route bleiben unveraendert.

## Von 32.4.5 nach 32.4.6

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geaendert wurde nur KNX RuntimeContext Phase E:

- `sse_versions["knx"]` wurde durch `runtime_context.knx.monitor_version` ersetzt.
- `bump_sse("knx")` aktualisiert nun den KNX RuntimeContext.
- Andere SSE-Versionen bleiben unveraendert im bestehenden Dict.

## Von 32.4.4 nach 32.4.5

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geaendert wurde nur KNX RuntimeContext Phase D1:

- Die KNX-Listener-Verwaltung liegt jetzt in `runtime_context.knx`.
- `ensure_knx_listener_started` nutzt RuntimeContext-Wrapper statt der alten globalen Thread-Variable.
- Der Listener selbst, xknx, asyncio, Monitor, SSE und Callback-Verarbeitung bleiben unveraendert.

## Von 32.4.3 nach 32.4.4

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geaendert wurde nur KNX RuntimeContext Phase C:

- `knx_monitor_log` wird zusaetzlich in `runtime_context.knx.monitor_log` geschrieben.
- KNX Monitor Payload liest Log-Eintraege bevorzugt aus dem RuntimeContext.
- Listener, xknx, asyncio, SSE und Eventstream-Route bleiben unveraendert.

## Von 32.4.2 nach 32.4.3

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geaendert wurde nur KNX RuntimeContext Phase B:

- `knx_monitor_values` wird zusaetzlich in `runtime_context.knx.monitor_values` geschrieben.
- KNX Hub und KNX Monitor Payload lesen Monitor-Werte bevorzugt aus dem RuntimeContext.
- `knx_monitor_log`, Listener, SSE und xknx bleiben unveraendert.

## Von 32.4.1 nach 32.4.2

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geaendert wurde nur KNX RuntimeContext Phase A:

- KNX LastSeen-Dicts werden zusaetzlich in `runtime_context.knx` geschrieben.
- KNX-LastSeen-Routen lesen bevorzugt aus dem RuntimeContext.
- Monitor, Listener, SSE und xknx bleiben unveraendert.

## Von 32.4.0 nach 32.4.1

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geaendert wurde nur die Dokumentation:

- `KNX_RUNTIME_MIGRATION_PLAN.md` ergaenzt.
- Keine KNX-Variablen, Funktionen, Services oder Routen verschoben.

## Von 32.3.9 nach 32.4.0

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geaendert wurde nur der interne Broker-Runtime-State:

- Broker-Prozess, Status und Start-/Stop-Flags liegen jetzt in `runtime_context.broker`.
- `internal_broker_process` wurde als Legacy-Global entfernt.
- Bridge-, MQTT-, UDP- und KNX-State bleiben unveraendert.

## Von 32.3.8 nach 32.3.9

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geaendert wurde nur der UDP-Runtime-State:

- UDP Last-Seen-Daten werden zusaetzlich in `runtime_context.udp` geschrieben.
- UDP-Seiten lesen bevorzugt aus dem RuntimeContext.
- Bestehende UDP-Globals bleiben parallel erhalten.

## Von 32.3.7 nach 32.3.8

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geaendert wurde nur der MQTT-Monitor-Runtime-State:

- MQTT-Monitor-Werte werden zusaetzlich in `runtime_context.mqtt` geschrieben.
- Monitor-Datenrouten lesen bevorzugt aus dem RuntimeContext.
- Bestehende MQTT-Globals bleiben parallel erhalten.

## Von 32.3.5 nach 32.3.7

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geaendert wurde nur der Bridge-Runtime-State:

- Bridge-Status, Running-Flag, Stop-Flag und Thread-Referenz liegen jetzt in `runtime_context.bridge`.
- Alte Bridge-Globals wurden entfernt.
- MQTT-, UDP-, KNX- und Broker-State bleiben unveraendert.

## Von 32.3.4 nach 32.3.5

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geaendert wurde nur die vorsichtige LiveLog-Vorbereitung:

- `LiveLogState` enthaelt eine eigene Deque, einen Lock und eine Version.
- Neue Logeintraege werden zusaetzlich in `runtime_context.live_log` gespiegelt.
- Bestehende LiveLog-Routen und sichtbare UI bleiben unveraendert.

## Von 32.3.3 nach 32.3.4

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geaendert wurde nur das Architektur-Grundgeruest:

- `app/runtime/` mit leeren Dataclass-Platzhaltern ergaenzt.
- `RuntimeContext` definiert, aber nicht instanziiert und nicht verwendet.
- Keine Laufzeitdaten verschoben.

## Von 32.3.2 nach 32.3.3

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geändert wurde nur die Dokumentation:

- `RUNTIME_CONTEXT_PLAN.md` ergänzt.
- Globale Runtime-States wurden fuer einen spaeteren Context geplant.
- Keine Variablen, Funktionen oder Routen verschoben.

## Von 32.3.1 nach 32.3.2

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geändert wurde nur die Dokumentation:

- `BLUEPRINT_PLAN.md` ergänzt.
- Alle aktuellen Flask-Routen wurden geplanten Blueprints zugeordnet.
- Keine Routen verschoben, umbenannt oder gelöscht.

## Von 32.3.0 nach 32.3.1

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geändert wurde nur die Dokumentation:

- `ARCHITECTURE_REVIEW.md` aktualisiert und um Datei-Bewertungen ergänzt.
- Keine Funktionen verschoben, umbenannt oder gelöscht.

## Von 32.2.9 nach 32.3.0

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geändert wurde nur die Dokumentation:

- `ARCHITECTURE_REVIEW.md` ergänzt.
- Keine Funktionen verschoben, umbenannt oder gelöscht.

## Von 32.2.8 nach 32.2.9

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geändert wurde nur die technische Modulstruktur:

- Template-/HTML-Hilfsfunktionen liegen jetzt in `app/services/template.py`.
- `app/core.py` importiert diesen Service als `template_service`.
- Bestehende URLs, sichtbare Texte und große Template-Blöcke bleiben unverändert.

## Von 32.2.7 nach 32.2.8

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geändert wurde nur die technische Modulstruktur:

- Backup-Hilfsfunktionen liegen jetzt in `app/services/backup.py`.
- `app/core.py` importiert diesen Service als `backup_service`.
- Backup-Download, Restore-Upload, Pfade und Backup-Dateinamen bleiben unverändert.

## Von 32.2.6 nach 32.2.7

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geändert wurde nur die technische Modulstruktur:

- Runtime-Hilfsfunktionen liegen jetzt in `app/services/runtime.py`.
- `app/core.py` importiert diesen Service als `runtime_service`.
- Status-Events, Live-Log, interner Broker und bestehende URLs bleiben unverändert.

## Von 32.2.5 nach 32.2.6

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geändert wurde nur die technische Modulstruktur:

- Influx-Hilfsfunktionen liegen jetzt in `app/services/influx.py`.
- `app/core.py` importiert diesen Service als `influx_service`.
- Influx Settings, Influx Explorer URLs und gespeicherte Influx-Konfigurationen bleiben unverändert.

## Von 32.2.4 nach 32.2.5

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geaendert wurde nur die technische Modulstruktur:

- KNX-Hilfs- und Bridge-Funktionen liegen jetzt in `app/services/knx.py`.
- `app/core.py` importiert diesen Service als `knx_service`.
- KNX Listener, KNX Monitor und KNX Live-State bleiben in `app/core.py`.
- Monitor-Eintraege fuer KNX TX werden per Callback weiter in die zentrale Legacy-Liste geschrieben.
- Bestehende URLs, Formulare und Konfigurationsdateien bleiben unveraendert.

## Von 32.2.3 nach 32.2.4

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geaendert wurde nur die technische Modulstruktur:

- Loxone-Hilfsfunktionen liegen jetzt in `app/services/loxone.py`.
- `app/core.py` importiert diesen Service als `loxone_service`.
- Bestehende URLs, Formulare und Konfigurationsdateien bleiben unveraendert.

## Von 32.0.0 nach 32.2.3

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geaendert wurde nur die technische Modulstruktur:

- Object-/Objektmanager-Hilfsfunktionen liegen jetzt in `app/services/object.py`.
- `app/core.py` importiert diesen Service als `object_service`.
- Bestehende URLs, Formulare und Konfigurationsdateien bleiben unveraendert.

## Technische Basis 32.0.0

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geaendert wurden nur technische Modulnamen:

- `app/engine/v31_port.py` wurde zu `app/engine/port.py`.
- Config-Service: `app/services/config.py`.
- MQTT-Service: `app/services/mqtt.py`.
- UDP-Service: `app/services/udp.py`.
- Die historische v31-Portdatei wurde zum heutigen `app/core.py` ueberfuehrt.

## Von 32.2.0 nach 32.2.2

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Geaendert wurde nur die Zeichenkodierung der ausgelieferten Oberflaechen:

- HTML-Antworten werden mit `text/html; charset=utf-8` ausgeliefert.
- Flask-JSON bleibt UTF-8-lesbar und nutzt kein ASCII-Escaping.
- Defekte Umlaut-/Sonderzeichen im Port wurden repariert.

## Von 32.2.0 nach 32.2.1

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Unveraendert:

- MQTT->UDP Mappings bleiben in `config/mqtt2udp_config.json`.
- UDP->MQTT Mappings bleiben in `config/udp2mqtt.json`.
- UDP Port Presets bleiben in `config/udp_presets.json`.
- Seiten `/mqtt2udp`, `/udp2mqtt` und `/udp_input` behalten ihre URLs und Formulare.
- MQTT-Monitor und MQTT-Service bleiben unveraendert angebunden.

## Von 32.1.0 nach 32.2.0

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Unveraendert:

- MQTT-Hauptbroker bleibt in `config/config.json`.
- Zusatzbroker bleiben in `config/mqtt_brokers.json`.
- MQTT-Monitor und MQTT-Seiten behalten ihre URLs.
- Objektmanager bleibt unveraendert.

## Von 32.0.1 nach 32.1.0

Keine manuelle Migration der Konfigurationsdateien erforderlich.

Vorhandene Dateien unter `config/` bleiben unveraendert:

- `config.json`
- `topic_config.json`
- `mqtt2lox.json`
- `mqtt2udp_config.json`
- `udp2mqtt.json`
- `mqtt_brokers.json`
- `monitor_settings.json`
- `plugins.json`
- `knx_config.json`
- `mqtt2knx.json`
- `knx2mqtt.json`
- `udp2knx.json`
- `knx2lox.json`
- `sidebar_links.json`
- `internal_broker.json`
- `objects.json`

## Hinweise

- `objects.json` kann weiterhin im Listenformat oder im v32-Format mit `objects`-Liste gelesen werden.
- Optionale Bibliotheken duerfen fehlen; der Startstatus meldet sie, ohne den App-Start zu verhindern.
- Bei kuenftigen Versionen muessen `CHANGELOG.md`, `ROADMAP.md` und `MIGRATION.md` mitgepflegt werden.
