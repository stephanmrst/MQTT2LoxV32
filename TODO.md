# TODO

## 32.0.x

- Architektur-Review 32.3.1 auswerten: zuerst RuntimeContext/Blueprint-Plan festlegen, dann weitere Auslagerungen angehen.
- Blueprint-Plan 32.3.2 pruefen und vor der ersten Route-Migration Smoke-Tests fuer Seiten, JSON-Endpunkte und SSE vorbereiten.
- RuntimeContext-Plan 32.3.3 pruefen und vor State-Verschiebungen Tests fuer Live-Log, Status-SSE, MQTT Monitor, KNX Monitor und Bridge Start/Stop festlegen.
- RuntimeContext-Grundgeruest 32.3.4 vorerst ungenutzt lassen; erst nach Smoke-Tests Instanzierung und schrittweise Verdrahtung planen.
- LiveLog-Spiegelung 32.3.5 pruefen: Dashboard, Live Log, `/events/live_log` und keine doppelten sichtbaren Eintraege.
- Bridge-State 32.3.7 pruefen: Start/Stop, `/events/status`, Dashboard-Status und Live-Log-Meldungen.
- MQTT-Monitor-State 32.3.8 pruefen: MQTT Monitor, MQTT Hub, `/monitor_data`, `/events/mqtt_monitor`, Topic Explorer und Dashboard.
- UDP-State 32.3.9 pruefen: MQTT -> UDP, UDP -> MQTT, UDP -> KNX, UDP Input, Discovery, Dashboard und Live Log.
- BrokerState 32.4.0 pruefen: Broker starten, stoppen, Statusroute, Dashboard, LiveLog, MQTT und Bridge.
- KNX Runtime Migration Plan 32.4.1 pruefen und vor KNX-State-Migration Smoke-Tests fuer Monitor, `[KNX MONITOR ADD]`, `[KNX SSE]`, MQTT->KNX, UDP->KNX, KNX->MQTT und KNX->Loxone vorbereiten.
- KNX Runtime Phase A 32.4.2 pruefen: MQTT -> KNX, KNX -> MQTT, KNX -> Loxone, Dashboard und LiveLog.
- KNX Runtime Phase B 32.4.3 pruefen: KNX Monitor, `/knx_monitor_data`, KNX Hub, MQTT -> KNX, KNX -> MQTT und KNX -> Loxone.
- KNX Runtime Phase C 32.4.4 pruefen: KNX Monitor, `/knx_monitor_data`, `[KNX MONITOR ADD]`, `[KNX SSE]`, MQTT -> KNX, KNX -> MQTT, KNX -> Loxone, Dashboard und Live Log.
- KNX Runtime Phase D1 32.4.5 pruefen: KNX Monitor, Listener Auto-Start, manueller Listener-Start, KNX Telegramm, `[KNX MONITOR ADD]`, `[KNX SSE]`, MQTT -> KNX, KNX -> MQTT und KNX -> Loxone.
- KNX Runtime Phase E 32.4.6 pruefen: `/events/knx_monitor`, `[KNX SSE]`, KNX Monitor, `/knx_monitor_data`, LiveLog-SSE und Status-SSE.
- KNX Runtime Cleanup 32.4.7 pruefen: KNX Monitor, KNX Telegramm, `[KNX MONITOR ADD]`, `[KNX SSE]`, MQTT -> KNX, KNX -> MQTT und KNX -> Loxone.
- Legacy Removal Plan 32.4.8 auswerten: zuerst App Factory und Blueprint-Grundstruktur planen, dann Routen schrittweise aus `legacy/app_legacy.py` entfernen.
- Legacy Removal Phase A 32.4.9 pruefen: App startet unveraendert, `app/routes`-Platzhalter sind vorhanden, `app/extensions.py` und `app/__init__.py` brechen den Legacy-Start nicht.
- Legacy Removal Phase B 32.5.0 pruefen: Dashboard, Sidebar, `/shell_status`, Live Log, `/live_log_data`, `/clear_log` und `/clear_monitor`.
- Legacy Removal Phase C 32.5.1 pruefen: `/settings`, `/settings_embed`, Core-/MQTT-/Influx-Speichern, Sidebar-Links, Plugins, `/backup`, `/restore`, `/objects` und Objektaktionen.
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
