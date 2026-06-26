# Roadmap

## Aktueller Stand: 33.2.8a

Die Anwendung laeuft als bereinigte v32-Basis und fuehrt mit 33.2.8a den neuen Objektmanager V33 parallel zum bestehenden Objektmanager weiter. Technische Versionspraefixe wurden aus Python-Dateinamen, Imports und internen Modulreferenzen entfernt. Config-, MQTT-, UDP-, Object-, Loxone-, KNX-, Influx-, Runtime-, Backup- und Template-Hilfsfunktionen sind in Service-Module ausgelagert. Unter `app/runtime/` existiert ein Dataclass-Grundgeruest fuer den RuntimeContext; LiveLog, Bridge-State, MQTT-Monitor-State, UDP-Laufzeitdaten, Broker-State und KNX-Runtime-State sind angebunden. 33.2.8a vereinheitlicht die Objektmanager-V33-Arbeitsflaeche: Objektliste und Editor nutzen denselben Dashboard-/Editor-Hintergrund, waehrend Sidebar, Karten und Badges unveraendert bleiben.

## Naechste Schritte

- Objektmanager V33 Plan auswerten: zuerst Read-only Analyse bestehender Mappings, danach Objektkandidaten und Adaptervorschlaege.
- Adaptermodell V33 pruefen: gemeinsame Felder, Protokoll-Pflichtfelder und Validierungsregeln fuer spaetere Read-only Analyse verwenden.
- Passive Objekt-Registry 33.0.2 pruefen: Laden fehlender Datei, Speichern nach `data/objects_v33.json`, Validierung und Roundtrip mit `ObjectDefinition`.
- Passive Adapter-Engine 33.0.3 pruefen: Serialisierung/Deserialisierung fuer MQTT, Loxone, UDP, KNX und Influx sowie Registry-Roundtrip.
- Objektmanager V33 33.1.0 pruefen: `/objects_v33`, Suche, neues Objekt, Bearbeiten, Loeschen und unveraenderter bestehender `/objects`-Objektmanager.
- Objektidentitaet V33 33.1.1 pruefen: alte Registry-Eintraege ohne `uuid`/`key`, Bearbeiten/Loeschen per `uuid`, frei aenderbarer `name`.
- Adapterverwaltung V33 33.1.2 pruefen: alle fuenf Adapter als Cards/Chips anzeigen, aktivieren/deaktivieren, Kurzstatus pruefen, Platzhalter bearbeiten und Registry-Roundtrip.
- Adapter-Komponenten V33 33.2.0 pruefen: dynamische Includes im Objekteditor, protokollspezifische Felder, getrennte Objekt-/Adapter-Formulare und Registry-Roundtrip.
- Branding 33.2.1 pruefen: Shell-Titel/Header zeigen `MP-Gateway`, technische Pfade und Config-Dateien bleiben bei `MQTT2Lox`.
- Routing-Vorschau 33.2.2 pruefen: aktive Adapter erzeugen nur Vorschau-Eintraege, Influx erscheint nur als Ziel, keine Mapping-Dateien werden geschrieben.
- Sidebar-Link 33.2.3 pruefen: `Objektmanager V33` oeffnet `/objects_v33`, alter `Objektmanager` oeffnet weiter `/objects`.
- Objektmanager-V33-Layout 33.2.3 pruefen: Objektliste links, Detail rechts, Tabs, Adapterformulare und Routing-Vorschau.
- Objektmanager-V33-Optik 33.2.4 pruefen: alle Protokoll-Badges immer sichtbar, aktive farbig, inaktive gedimmt, Auswahlmarkierung deutlich.
- UI-Guidelines 33.2.5 anwenden: neue Funktionen in Links-Uebersicht/Rechts-Detail-Layout integrieren und Protokollfarben wiederverwenden.
- Sidebar-Komponente 33.2.6 pruefen: alle Shell-Seiten nutzen `templates/shared/sidebar.html`, aktiver Menuepunkt ist automatisch markiert und `static/css/sidebar.css` bleibt die zentrale Quelle fuer Sidebar-Optik.
- Layout-Fundament 33.2.7 pruefen: Sidebar-Gruppen, externe Dienste, `/objects_v33` auf Base-Layout und unveraenderte Erreichbarkeit von `/objects`.
- Sidebar-Feinschliff 33.2.7a pruefen: keine `MP-Gateway`-Gruppenueberschrift, kein alter Objektmanager-Link, nur `Objektmanager V33`, externe Dienste nur InfluxDB und Grafana.
- Sidebar-Link-Korrektur 33.2.7c pruefen: Influx Explorer intern, InfluxDB/Grafana extern aus Config, leere externe URLs deaktiviert ohne internen Fallback.
- Sidebar-Button-Restore 33.2.7g pruefen: externe Dienste generisch aus Config, aktive Eintraege automatisch, `new_tab=true` neuer Tab, `new_tab=false` rechter Content-Bereich.
- Objektmanager-Hintergrund 33.2.8 pruefen: `/objects_v33` wirkt farblich mit Dashboard/Standardseiten zusammengehoerig, Sidebar und Objektkarten bleiben unveraendert.
- Objektmanager-Arbeitsflaeche 33.2.8a pruefen: linke Objektliste und rechter Editor haben denselben Hintergrund, Objektkarten heben sich weiterhin klar ab.
- `app/services/object_model.py` erst aktiv verdrahten, wenn Smoke-Tests fuer bestehende Mappings, Objektmanager und Bridge-Pfade definiert sind.
- Bestehende Mapping-Dateien bis zur ausdruecklichen V33-Migrationsphase als aktive Runtime-Quelle behalten.
- Weitere Funktionsbereiche schrittweise in v32-Module auslagern, ohne Verhalten zu aendern.
- MQTT-Service weiter entflechten: Publish-Hilfen und Monitor-Endpunkte schrittweise aus dem Legacy-Core herausloesen.
- UDP-Service spaeter um fokussierte Tests fuer Listener, Mapping und Presets ergaenzen.
- KNX-Service im laufenden Betrieb gegenpruefen: MQTT -> KNX, UDP -> KNX, KNX -> MQTT, KNX -> Loxone und Monitor-Callback.
- Influx-Service im laufenden Betrieb gegenpruefen: Status, Explorer, Schreibtest und MQTT/KNX/UDP-Schreibpfade.
- Runtime-Service im laufenden Betrieb gegenpruefen: Status-SSE, Live-Log-SSE und interner Broker.
- Backup-Service im laufenden Betrieb gegenpruefen: Backup-Download, Restore-Upload und Backup-Dateiliste.
- Template-Service im laufenden Betrieb gegenpruefen: Dashboard, Shell-Layout, eingebettete Seiten und Mapping-Selects.
- Architektur-Review 32.3.1 auswerten und danach priorisiert Blueprints, RuntimeContext und Monitor-/Mapping-Routen planen.
- Blueprint-Plan 32.3.2 als Reihenfolge fuer spaetere Routenmigration verwenden; zuerst Dashboard/Config/Backup, zuletzt Events/KNX/System.
- RuntimeContext-Plan 32.3.3 als Grundlage fuer Live-Log, Monitor-State, Bridge-State, Broker-State und UDP/MQTT/KNX Last-Seen-State verwenden.
- RuntimeContext-Grundgeruest 32.3.4 erst nach Tests schrittweise verdrahten; keine State-Verschiebung ohne Smoke-Checks.
- LiveLog-Spiegelung aus 32.3.5 beobachten und erst nach stabilen Tests als Primaerquelle fuer LiveLog-Routen planen.
- Bridge-State 32.3.7 im Betrieb gegenpruefen: Start, Stop, Status-SSE, Dashboard-Status und Fehlerstatus.
- MQTT-Monitor-State 32.3.8 im Betrieb gegenpruefen: Monitor, Hub, Live Updates, SSE und Topic Explorer.
- UDP-State 32.3.9 im Betrieb gegenpruefen: MQTT->UDP, UDP->MQTT, UDP->KNX, UDP Input und Discovery.
- BrokerState 32.4.0 im Betrieb gegenpruefen: Start, Stop, Statusroute, Dashboard, LiveLog, MQTT und Bridge.
- KNX Runtime Migration Plan 32.4.1 vor jeder KNX-State-Migration auswerten; Reihenfolge LastSeen, Monitor-Werte, Monitor-Log, Listener-Thread, SSE einhalten.
- KNX Phase A 32.4.2 im Betrieb pruefen: MQTT->KNX, KNX->MQTT, KNX->Loxone, Dashboard und LiveLog.
- KNX Phase B 32.4.3 im Betrieb pruefen: KNX Monitor, `/knx_monitor_data`, KNX Hub, MQTT->KNX, KNX->MQTT und KNX->Loxone.
- KNX Phase C 32.4.4 im Betrieb pruefen: KNX Monitor, `/knx_monitor_data`, `[KNX MONITOR ADD]`, `[KNX SSE]`, MQTT->KNX, KNX->MQTT und KNX->Loxone.
- KNX Phase D1 32.4.5 im Betrieb pruefen: Monitor oeffnen, Listener Auto-Start, manueller Listener-Start, KNX Telegramm, MQTT->KNX, KNX->MQTT und KNX->Loxone.
- KNX Phase E 32.4.6 im Betrieb pruefen: `/events/knx_monitor`, `[KNX SSE]`, KNX Monitor, `/knx_monitor_data` und LiveLog/Status-SSE als unveraenderte Nachbarn.
- KNX Cleanup 32.4.7 im Betrieb pruefen: KNX Monitor, KNX Telegramm, `[KNX MONITOR ADD]`, `[KNX SSE]`, MQTT->KNX, KNX->MQTT und KNX->Loxone.
- Legacy Removal Plan 32.4.8 als Reihenfolge fuer die spaetere Entfernung von `app/core.py` verwenden.
- Legacy Removal Phase A 32.4.9 pruefen: App startet weiter ueber Legacy, `app/routes`-Platzhalter sind importierbar, keine Routen wurden verschoben.
- Legacy Removal Phase B 32.5.0 pruefen: Dashboard, Sidebar, Shell-Status, Live Log, Clear Log und Clear Monitor laufen unveraendert ueber den Dashboard-Blueprint.
- Legacy Removal Phase C 32.5.1 pruefen: Einstellungen, Core/MQTT/Influx-Speichern, Sidebar-Links, Plugins, Backup, Restore und Objektmanager laufen unveraendert ueber Blueprints.
- Legacy Removal Phase D Teil 1 32.6.0 pruefen: MQTT Hub, Monitor, Monitor-SSE, Topic Explorer, Topic Manager, Brokerverwaltung und Broker-Test laufen unveraendert ueber den MQTT-Blueprint.
- Legacy Removal Phase D Teil 2 32.6.1 pruefen: MQTT->UDP, UDP->MQTT, UDP Input, UDP Presets und UDP Discovery laufen unveraendert ueber den UDP-Blueprint.
- Legacy Removal Phase D Teil 3 32.6.2 pruefen: MQTT->Loxone, Speichern, Test und Live-Daten laufen unveraendert ueber den Loxone-Blueprint.
- Legacy Removal Phase D Teil 4 32.6.3 pruefen: Influx-Test, Influx Explorer, einzelnes Loeschen und Mehrfach-Loeschen laufen unveraendert ueber den Influx-Blueprint.
- Legacy Removal Phase E 32.6.4 pruefen: Globale Suche, Suchseite, Konfliktpruefung, Konfliktseite und Dashboard-AJAX laufen unveraendert ueber die vorhandenen Blueprints.
- Legacy Removal Phase F 32.6.5 pruefen: Status-SSE, Live-Log-SSE, MQTT-Monitor-SSE und KNX-Monitor-SSE laufen dauerhaft und reconnecten sauber.
- Legacy Removal Phase G Teil 1 32.6.6 pruefen: KNX Hub, KNX Settings, MQTT->KNX, UDP->KNX, KNX->MQTT und KNX->Loxone laufen unveraendert ueber den KNX-Blueprint.
- Legacy Removal Phase G Teil 2 32.6.7 pruefen: KNX Monitor, Listener-Start, KNX-SSE, Monitor-Data und Influx-Schalter/-Typ/-Topic laufen unveraendert ueber den KNX-Blueprint.
- Legacy Removal Phase H 32.6.8 pruefen: Bridge Start/Stop, Loxone-/MQTT-Test und interne Broker-Routen laufen unveraendert ueber den System-Blueprint.
- Legacy Removal Phase J 32.7.0 pruefen: App Factory, App-Core, Dashboard, MQTT, UDP, Loxone, KNX, Influx, Backup, Restore, Objektmanager, Live Log, SSE, Bridge und interner Broker.
- Legacy Cleanup 32.7.1 pruefen: kein `legacy/`-Ordnerrest, keine aktiven Altdatei-/Legacy-Lader-Treffer im App-Code, Doku auf `app/core.py` aktualisiert.
- Als naechstes Template-Routen und verbleibende App-Core-Helfer weiter in Blueprints/Services aufteilen, ohne URLs oder Rueckgabedaten zu aendern.
- Bridge-Kernlogik erst nach vollstaendiger Port-Stabilisierung modularisieren.
- Objektmanager vorerst nicht neu bauen, sondern nur stabil uebernehmen.
- Optional-Abhaengigkeiten weiter klar im Startstatus sichtbar halten.
- Tests fuer Hauptseiten, Config-Loader und Backup/Restore ausbauen.

## Leitplanken

- Keine neue Runtime, solange die technische Basis nicht vollstaendig stabil ist.
- Keine neue Objektmanager-Logik ohne ausdrueckliche Anforderung.
- Keine UI-Aenderungen bei reinen Portierungs- oder Service-Auslagerungen.
- Jede neue Version muss `CHANGELOG.md`, `ROADMAP.md` und `MIGRATION.md` aktualisieren.
