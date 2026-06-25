# TODO

## 33.0.x

- Object Manager V33 Plan pruefen: Leitbild "Ein Objekt. Alle Protokolle.", Objektmodell, Adaptermodell, Migrationsstrategie und Exit-Kriterien.
- Object Adapter Model 33.0.1 pruefen: MQTT, Loxone, UDP, KNX und Influx gegen bestehende Mapping-Felder abgleichen.
- Passive Object Registry 33.0.2 pruefen: fehlende `data/objects_v33.json` liefert leere Liste, Speichern/Lesen funktioniert, keine bestehende Config wird veraendert.
- Passive Object Adapter Engine 33.0.3 pruefen: `validate`, `serialize`, `deserialize` und Registry-Roundtrip fuer alle Adapterklassen.
- Objektmanager V33 33.1.0 pruefen: `/objects_v33`, Suche, neues Objekt, Bearbeiten, Loeschen, keine Adapterbearbeitung und keine Aenderung bestehender Mappings.
- Objektidentitaet V33 33.1.1 pruefen: `uuid` als feste interne ID, `key` als technischer Schluessel, `name` frei aenderbar, Edit/Delete ueber `uuid`.
- Adapterverwaltung V33 33.1.2 pruefen: MQTT, UDP, KNX, Loxone und Influx als Cards/Chips anzeigen, Kurzstatus pruefen, aktivieren/deaktivieren, Platzhalterdialoge bearbeiten.
- Adapter-Komponenten V33 33.2.0 pruefen: eigene Editor-Komponenten fuer MQTT, UDP, KNX, Loxone und Influx, getrennte Objekt-/Adapter-Speicherung und Registry-Roundtrip.
- Branding 33.2.1 pruefen: App-Header und Browser-Titel zeigen `MP-Gateway`; `MQTT2Lox` bleibt technischer Projekt-/Repo-Name.
- `app/services/object_model.py` vorerst passiv lassen; keine Runtime-, UI-, Routen- oder Config-Verdrahtung ohne separate Migrationsphase.
- Vor aktiver Objektmanager-2.0-Arbeit Smoke-Tests fuer bestehende Mappings, Objektmanager, Dashboard, MQTT, UDP, Loxone, KNX, Influx, Live Log, SSE, Bridge und internen Broker festlegen.
- Read-only Analyse bestehender Mapping-Dateien als naechsten sicheren V33-Schritt planen.

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
- Legacy Removal Plan 32.4.8 auswerten: zuerst App Factory und Blueprint-Grundstruktur planen, dann Routen schrittweise aus `app/core.py` entfernen.
- Legacy Removal Phase A 32.4.9 pruefen: App startet unveraendert, `app/routes`-Platzhalter sind vorhanden, `app/extensions.py` und `app/__init__.py` brechen den Legacy-Start nicht.
- Legacy Removal Phase B 32.5.0 pruefen: Dashboard, Sidebar, `/shell_status`, Live Log, `/live_log_data`, `/clear_log` und `/clear_monitor`.
- Legacy Removal Phase C 32.5.1 pruefen: `/settings`, `/settings_embed`, Core-/MQTT-/Influx-Speichern, Sidebar-Links, Plugins, `/backup`, `/restore`, `/objects` und Objektaktionen.
- Legacy Removal Phase D Teil 1 32.6.0 pruefen: `/mqtt`, `/monitor`, `/monitor_data`, `/topics`, `/topics2`, `/mqtt_brokers`, Topic-Speichern und Broker-Test.
- Legacy Removal Phase D Teil 2 32.6.1 pruefen: `/mqtt2udp`, `/udp2mqtt`, `/udp_input`, `/udp_presets`, UDP-Data-Routen, UDP Discovery Status/Toggle und Test-Routen.
- Legacy Removal Phase D Teil 3 32.6.2 pruefen: `/mqtt2lox`, `/mqtt2lox/save`, `/mqtt2lox/test/<int:index>` und `/mqtt2lox_data`.
- Legacy Removal Phase D Teil 4 32.6.3 pruefen: `/test/influx`, `/influx_explorer`, `/influx_explorer/delete` und `/influx_explorer/delete_selected`.
- Legacy Removal Phase E 32.6.4 pruefen: `/global_search`, `/global_search_page`, `/conflicts`, `/conflicts_page` und Dashboard-AJAX-Routen.
- Legacy Removal Phase F 32.6.5 pruefen: `/events/status`, `/events/live_log`, `/events/live_log_full`, `/events/mqtt_monitor`, `/events/knx_monitor`, Reconnect und Keepalive.
- Legacy Removal Phase G Teil 1 32.6.6 pruefen: `/knx`, `/knx_settings_embed`, `/mqtt2knx`, `/udp2knx`, `/knx2mqtt`, `/knx2lox` und jeweilige Data-/Save-/Test-Routen.
- Legacy Removal Phase G Teil 2 32.6.7 pruefen: `/knx_monitor`, `/knx_monitor_data`, `/knx_monitor/influx`, `/knx_monitor/influx_type`, `/knx_monitor/influx_topic`, `/knx_listener_start` und KNX-SSE.
- Legacy Removal Phase H 32.6.8 pruefen: `/start`, `/stop`, `/test/loxone`, `/test/mqtt`, `/internal_broker/save`, `/internal_broker/start`, `/internal_broker/stop`, `/internal_broker/status`.
- Legacy Removal Phase J 32.7.0 pruefen: App Factory, Dashboard, MQTT, UDP, Loxone, KNX, Influx, Backup, Restore, Objektmanager, Live Log, SSE, Bridge und interner Broker.
- Legacy Cleanup 32.7.1 pruefen: alter Ordner entfernt, aktive App-Code-Suche nach alten Legacy-Lader-Begriffen ohne Treffer, Doku auf `app/core.py` aktualisiert.
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
