# Roadmap

## Aktueller Stand: 32.7.1

Die Anwendung laeuft als bereinigte v32-Basis. Technische Versionspraefixe wurden aus Python-Dateinamen, Imports und internen Modulreferenzen entfernt. Config-, MQTT-, UDP-, Object-, Loxone-, KNX-, Influx-, Runtime-, Backup- und Template-Hilfsfunktionen sind in Service-Module ausgelagert. Unter `app/runtime/` existiert ein Dataclass-Grundgeruest fuer den RuntimeContext; LiveLog, Bridge-State, MQTT-Monitor-State, UDP-Laufzeitdaten, Broker-State und KNX-Runtime-State sind angebunden. Phase A bis H der Legacy-Entfernung haben die Route-Registrierungen in Blueprints ueberfuehrt. Phase J hat in 32.7.0 den bisherigen App-Kern nach `app/core.py` umgehaengt, `app/__init__.py` als zentrale App Factory aktiviert und den Importlib-Dateilader entfernt. 32.7.1 hat die letzten Legacy-Ordnerreste entfernt und die Analyse-/Plan-Dokumente nachgezogen.

## Naechste Schritte

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
