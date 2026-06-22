# Roadmap

## Aktueller Stand: 32.4.6

Die Anwendung laeuft als bereinigte v32-Basis. Technische Versionspraefixe wurden aus Python-Dateinamen, Imports und internen Modulreferenzen entfernt. Config-, MQTT-, UDP-, Object-, Loxone-, KNX-, Influx-, Runtime-, Backup- und Template-Hilfsfunktionen sind in Service-Module ausgelagert. Mit `ARCHITECTURE_REVIEW.md`, `BLUEPRINT_PLAN.md`, `RUNTIME_CONTEXT_PLAN.md` und `KNX_RUNTIME_MIGRATION_PLAN.md` liegen Architektur-, Blueprint-, Runtime-State- und KNX-Migrationsplan fuer die naechste Modularisierungsphase vor. Unter `app/runtime/` existiert ein Dataclass-Grundgeruest fuer den RuntimeContext; LiveLog, Bridge-State, MQTT-Monitor-State, UDP-Laufzeitdaten, Broker-State, KNX-LastSeen-Dicts, KNX-Monitor-Werte, KNX-Monitor-Log, KNX-Listener-Verwaltung und KNX-Monitor-Version sind angebunden.

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
- Bridge-Kernlogik erst nach vollstaendiger Port-Stabilisierung modularisieren.
- Objektmanager vorerst nicht neu bauen, sondern nur stabil uebernehmen.
- Optional-Abhaengigkeiten weiter klar im Startstatus sichtbar halten.
- Tests fuer Hauptseiten, Config-Loader und Backup/Restore ausbauen.

## Leitplanken

- Keine neue Runtime, solange die technische Basis nicht vollstaendig stabil ist.
- Keine neue Objektmanager-Logik ohne ausdrueckliche Anforderung.
- Keine UI-Aenderungen bei reinen Portierungs- oder Service-Auslagerungen.
- Jede neue Version muss `CHANGELOG.md`, `ROADMAP.md` und `MIGRATION.md` aktualisieren.
