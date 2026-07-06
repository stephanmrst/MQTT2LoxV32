# Roadmap

## Aktueller Stand: 33.4.27

- Ab 33.4.27 liest die Live-API den Objekt-Live-State aus demselben Service-Store wie der UDP-Core-Pfad.
- Ab 33.4.27 zeigen Debug-Logs `LIVE TAB DEBUG` und `UDP LIVE UPDATE DEBUG`, ob Wert und API-Return denselben Runtime-State verwenden.
- Ab 33.4.26 gibt es einen zentralen Objekt-Livewert-Updater, den MQTT, Loxone, KNX und UDP gemeinsam nutzen.
- Ab 33.4.26 liefern UDP-Matches im Live-Tab wieder Wert, Zeitstempel und Status `aktiv`, ohne die Routing-Quelle anzufassen.
- Ab 33.4.25 aktualisieren UDP-Objektmatches den gemeinsamen Objekt-Live-State wieder zuverlaessig, inklusive Topic:Wert und JSON-Leaf-Werten.
- Ab 33.4.25 gewinnen konkrete UDP-Topics und JSON-Pfade vor dem reinen Listen-Port-Match, damit Livewerte objektgenau bleiben.
- Ab 33.4.24 liest die Objektkarte die Quelle nur noch aus der Routing-Konfiguration bzw. `display_source` und nicht mehr aus dem Live-State.
- Ab 33.4.24 kann UDP->MQTT die Source-Anzeige nicht mehr auf MQTT verschieben.
- Ab 33.4.23 bleibt der MQTT-Zielweg als Target im Live-Cache, ohne die Eingangsquelle zu ueberschreiben.
- Ab 33.4.23 erkennt der MQTT-Echo-Guard interne Objekt-Publishes robuster auch ueber topic-basierten Ruecklauf.
- Ab 33.4.22 bleibt die Objektkarten-Quelle nach Browser-Reload an der echten Eingangsseite haengen und nicht mehr an MQTT-Zielinfos.
- Ab 33.4.22 liefert die Objekt-API `route_source` sowie `input_protocol`, damit UI und Routing denselben Eingang sehen.
- Ab 33.4.21 zeigt der Objektmanager die Quelle auch ohne Livecache aus der echten Eingangsseite der Konfiguration und faellt nicht mehr blind auf MQTT zurueck.
- Ab 33.4.21 traegt die Objekt-API live, source_protocol, last_source, input_protocol, route_sources und route_targets mit, damit Karte und Routing dieselbe Wahrheit sehen.
- Ab 33.4.21 bleibt die Objektliste bei Refreshs ruhiger, weil Scrollposition und Auswahl moeglichst erhalten bleiben.
- Ab 33.4.20 aktualisieren UDP-Eingaenge den Objekt-Live-Cache vor der Weiterleitung, damit Wert und Quelle schon beim Eingang korrekt sichtbar sind.
- Ab 33.4.19 lesen Objektkarten ihre Quelle strikt aus dem Live-Cache und fallen nicht mehr auf Routing-Badges oder erste aktive Routen zurueck.
- Ab 33.4.18 laeuft UDP-JSON-Extraktion nur noch bei echtem JSON-Eingang; Topic:Wert wird nicht mehr durch einen JSON-Path blockiert.
- Ab 33.4.17 tragen UDP-Livewerte ihre echte Eingangsquelle in der Live-Map, damit die Objektkarte nicht mehr aus Routing-Badges eine falsche Quelle ableitet.
- Ab 33.4.17 bleibt UDP Topic:Wert im Live-Match stabil und nutzt weiterhin den extrahierten Wert statt eines generischen Platzhalters.
- Ab 33.4.16 werden UDP-JSON-Leaf-Werte aus dem vollstaendigen JSON-Pfad extrahiert und statt des Platzhalters `JSON` geroutet.
- Ab 33.4.15 korrigiert der UDP-Monitor `[object Object]` wieder zu JSON-Text, wenn aus dem Datensatz JSON-Struktur ermittelt werden kann.
- Ab 33.4.14 verwendet der UDP-Explorer fuer Rohpayload-Anzeige, Kopieren und Objektanlage eine gemeinsame Textdarstellung, damit `[object Object]` nicht mehr in der UI erscheint.
- Ab 33.4.13 kann der UDP-Explorer JSON auch dann direkt anzeigen, wenn `payload_raw` bereits als Objekt in der Monitor-Kette ankommt.
- Ab 33.4.12 werden UDP-Monitor-Rohpayloads beim Normalisieren auch dann wieder zu Text, wenn sie als Objekt ankommen, damit JSON-Erkennung und Key-Ansicht stabil bleiben.
- Ab 33.4.11 werden bei UDP-Eingang Rohbytes, Text-Repr und Details direkt geloggt, damit JSON-Diagnosen bis zum Explorer nachvollziehbar bleiben.
- Ab 33.4.10 gewinnen JSON-UDP-Payloads im Backend immer gegen vorherige `mode=Wert`-Zustaende, sobald `payload_raw` gueltiges JSON enthaelt.
 Die Anwendung laeuft als bereinigte v32-Basis und fuehrt mit 33.3.36 die saubere Objektmanager-Architektur fuer MP-Gateway V33 ein. Technische Versionspraefixe wurden aus Python-Dateinamen, Imports und internen Modulreferenzen entfernt. Config-, MQTT-, UDP-, Object-, Loxone-, KNX-, Influx-, Runtime-, Backup- und Template-Hilfsfunktionen sind in Service-Module ausgelagert. Unter `app/runtime/` existiert ein Dataclass-Grundgeruest fuer den RuntimeContext; LiveLog, Bridge-State, MQTT-Monitor-State, UDP-Laufzeitdaten, Broker-State und KNX-Runtime-State sind angebunden. Objekte enthalten nur noch logische Stammdaten und kanonische Protokoll-Endpunkte als top-level Protokollbloecke wie `loxone`; Legacy-Felder und alte `adapters` werden nur noch beim Lesen migriert. Die interne MP-Gateway Objekt-UUID ist die einzige dauerhafte Objektidentitaet, wird als echte `obj_<uuid4hex>`-ID erzeugt und bleibt unabhaengig von Name oder Adapterdaten stabil; alte Slug-IDs werden nur noch fuer Lookup-Kompatibilitaet erkannt, aber nicht mehr als Delete-Identitaet verwendet. Der Objektmanager zeigt Live-Werte runtime-only im neuen Live-Tab und in der Objektliste, ohne `config/objects.json` mit Messwerten zu beschreiben. Der Loxone Explorer erstellt oder oeffnet Objekte anhand der Loxone-UUID idempotent, speichert die Loxone-UUID aber ausschliesslich im Loxone-Tab und loggt fehlende Mindestdaten explizit. Loxone-State-Erfassung bleibt aktiv, MQTT-Publishing erfolgt aber nur noch bei aktiver Objektmanager-Route `Loxone -> MQTT` mit vollstaendigen Loxone- und MQTT-Endpunkten. Die V33-Pipeline nutzt nur noch `config/objects.json`, der alte JS-Renderer ist entfernt und `/objects_v33/new` erzeugt keine unsichtbaren Detail-Geisterobjekte mehr. Loeschen im Objektmanager erfolgt ueber die interne Objekt-UUID und fuehrt immer zur neu geladenen Liste ohne geloeschte Auswahl zurueck. Objekt-CRUD aktualisiert die Objekt-Routen jetzt ohne Bridge-Neustart und ersetzt den rechten Detailbereich per API statt per Full-Page-Reload, damit Speichern und Loeschen die laufende Runtime nicht unterbrechen. Der CRUD-State wird nach Create/Update/Delete komplett invalidiert, damit geladene Live-/Cache-Reste keinen Folge-CRUD blockieren. Die Objektdatei wird zentral ueber einen Write-Lock und Retry-Replace geschrieben, damit Windows-Dateisperren nicht sofort Create/Delete blockieren. Objekt-Routen werden per In-Memory-Cache erzeugt und CRUD-Reloads laufen asynchron, damit der Flask-Thread nicht auf Route-Neuberechnung warten muss. Delete-Requests geben den Reload nur noch als Background-Job frei und loggen Start, Write, Cache-Invalidierung und Response separat. Loxone->MQTT Skip-Meldungen laufen nicht mehr ueber das normale Live-Log, und die Loxone->MQTT-Routensuche nutzt einen In-Memory-Index statt pro Wert die Objektliste erneut zu scannen. Der object_service vermeidet jetzt die Lock-Inversion zwischen Datei- und Cache-Locks und nutzt fuer Live-Wert-Matches einen vorbereiteten Endpoint-Index statt pro Callback die Objektliste neu zu scannen. Loxone-Livewerte matchen jetzt robuster ueber UUID, IO-Adresse und Objektname und der Live-Index wird nach CRUD direkt neu aufgebaut. Objektmanager-Routing bleibt ab 33.3.43 von den alten Mapping-Loadern fuer MQTT->Loxone, MQTT->UDP und UDP->MQTT getrennt; eigene MQTT-Ausgaben werden mit Runtime-Origin markiert und im MQTT-Eingang als Echo uebersprungen. Ab 33.3.44 besitzt der Objektmanager-UDP-Adapter ein eigenes optionales `udp_topic` und einen `payload_mode`, sodass Loxone->UDP mit Custom-Textpraefix oder als reiner Wert senden kann. Ab 33.3.46 erhalten neue und mit leerem UDP Topic gespeicherte Objekte ein Default Topic `<Objektname>/value`; ob das Topic gesendet wird, entscheidet der Payload-Modus `topic_value`, `value_only` oder `json`. Ab 33.3.48 kann der Influx-Zieladapter Measurement, Field und Topic pro Objekt konfigurieren; leere Werte werden auf Objekt-Defaults gesetzt und Topic wird als Influx-Tag geschrieben. Ab 33.3.49 bleibt die Livewert-Quelle bei der echten Eingangsquelle wie Loxone, waehrend geroutete Zieladapter getrennt als letzte Targets erfasst werden. Ab 33.3.50 baut der Routing-Tab seine Eintraege direkt aus der Objektkonfiguration mit allen aktivierten Quellen und Zielen auf und blendet Selbst- oder Legacy-Routen aus. Ab 33.3.51 zeigt der Routing-Tab zusaetzlich getrennte Haupt-Routen und direkte Rueck-Routen zur aktuellen Quelle. Ab 33.3.52 zeigt der Objektmanager pro Objekt nur noch ein Status-Badge, damit die Objekt-UI ruhiger und klarer bleibt. Ab 33.3.53 ist KNX als weiterer Objektmanager-Ausgang mit Loxone, MQTT und UDP verdrahtet und erscheint in der Routing-Vorschau und im Runtime-Dispatch. Ab 33.3.54 nutzt der KNX-Sendepfad die laufende Runtime-Verbindung; neue Tunnel pro Wert werden nicht mehr aufgebaut und der Monitor markiert Objektmanager-Sends als `OUT`. Ab 33.3.57 werden KNX-Sends erst nach erfolgreichem Write als `OUT_OK` markiert, Fehler loggen die konkrete Exception und die Monitor-Ansicht zeigt `OUT_PENDING`/`OUT_OK`/`OUT_ERROR` getrennt. Ab 33.3.58 sendet der KNX-Pfad als explizites `GroupValueWrite`-Telegramm mit kodiertem APDU-Payload. Ab 33.3.59 trennt der KNX-Monitor RX und OUT mit passenden Richtungsfiltern und zeigt Gateway-Sends nicht mehr als RX-Echo. Ab 33.3.60 gibt es im KNX-Hub einen eigenen Testbereich mit kopierbarer Diagnose und Wiederholen/Leeren-Funktionen. Ab 33.3.88 laufen externe MQTT-Broker pro Instanz mit eigenem Client, Worker-Queue, Reconnect-Backoff und Statusanzeige, ohne den internen Mosquitto-Pfad zu vermischen. Ab 33.3.89 werden Queue-voll-Faelle pro Broker gedrosselt und der Gateway-Stop ruft MQTT, UDP und KNX jetzt wirklich herunter, statt nur den Status zu beschriften. Ab 33.4.0 wird UDP jetzt auch als Eingangsquelle in dieselbe protokollneutrale Object-Routing-Schiene aufgenommen und kann JSON-Payloads mit Topic/Wert direkt zerlegen. Ab 33.4.2 arbeitet der UDP Explorer als Live-Explorer: ein Live-Eintrag pro Quelle bleibt stabil, Pakete aktualisieren denselben Eintrag und Auswahl sowie Scroll-Position springen nicht mehr bei jedem Paket. Ab 33.4.3 ist die Ansicht kompakt als Explorer-Spalte links und Detailkarte rechts aufgebaut. Ab 33.4.4 orientiert sich der UDP Explorer optisch und in der Bedienung enger am MQTT Discover Mode. Ab 33.4.5 wurden die Live-Quellen als Explorer-Baum mit Topic-Detailansicht und einklappbarem Expertenbereich weiter an das MQTT Discover-Verhalten angenaehert.

## Naechste Schritte

- Objektmanager V33 Plan auswerten: zuerst Read-only Analyse bestehender Mappings, danach Objektkandidaten und Adaptervorschlaege.
- Adaptermodell V33 pruefen: gemeinsame Felder, Protokoll-Pflichtfelder und Validierungsregeln fuer spaetere Read-only Analyse verwenden.
- Passive Objekt-Registry 33.0.2 pruefen: Laden fehlender Datei, Speichern nach `data/objects_v33.json`, Validierung und Roundtrip mit `ObjectDefinition`.
- Passive Adapter-Engine 33.0.3 pruefen: Serialisierung/Deserialisierung fuer MQTT, Loxone, UDP, KNX und Influx sowie Registry-Roundtrip.
- Objektmanager V33 33.1.0 pruefen: `/objects_v33`, Suche, neues Objekt, Bearbeiten, Loeschen und unveraenderter bestehender `/objects`-Objektmanager.
- Loxone-Zielroute 33.3.86 pruefen: Zielstatus, linke Infokachel und Routing-Tab muessen Loxone nur dann aktiv anzeigen, wenn Zielhaken, Ziel-UUID und Loxone-Verbindung zusammen vorhanden sind.
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
- Objektmanager-Core 33.9.0 pruefen: CRUD ueber `/objects_v33` und `/api/objects`, Speicherung in `config/objects.json`, MQTT-Topic-Vorbefuellung und keine Runtime-Mapping-Erzeugung.
- Naechster V33-Schritt: Adapterdaten aus dem Core-Objektmodell sauber in technische Mapping-Vorschau ueberfuehren, weiterhin ohne Runtime-Schreibpfade.
- Objektbasierte Routen 33.3.0 pruefen: MQTT-Objekte mit Zieladresse erzeugen aktive virtuelle Routen, unvollstaendige Objekte bleiben sichtbar ohne Runtime-Route.
- Objektmanager-Architektur 33.3.1 pruefen: Allgemein-Tab nur Stammdaten, Status aus aktiven Endpunkten, Routing-Tab mit erzeugten Routen und fehlenden Endpunkten.
- Explorer-Create 33.3.2 pruefen: Loxone Explorer erstellt Objekt mit Klardaten im Allgemein-Tab und technischen Daten nur im Loxone-Tab.
- Loxone-Explorer-Fix 33.3.3 pruefen: Control-UUID, IO-Adresse und Adapter-Aktivierung landen zuverlaessig im Loxone-Tab; Status bleibt ohne zweiten Endpunkt unvollstaendig.
- Loxone-Import 33.3.4 pruefen: Key aus Anzeigename mit Unterstrich, Datenpunkt-UUID im Loxone-Tab, Datentyp-Erkennung und Reload aus `config/objects.json`.
- Objektmodell-Konsolidierung 33.3.5 pruefen: `objects.json` schreibt nur einen Protokollblock pro Protokoll, Liste/Detail/Tab laden dieselbe gespeicherte Quelle.
- Loxone-Protokollblock 33.3.6 pruefen: Explorer-Create schreibt `object.loxone`, alte `adapters.loxone` werden nur gelesen/migriert.
- Objektmanager-Pipeline 33.3.7 pruefen: Versionsanzeige aus `VERSION`, kein toter JS-Renderer, `/new` ohne temporaeres Detailobjekt und alte `data/objects_v33.json` nur deprecated.
- Sidebar-Version 33.3.8 pruefen: unten links zeigt nach Server-Neustart den Inhalt der zentralen `VERSION`-Datei.
- Eingebetteten Explorer 33.3.9 pruefen: Loxone Explorer im Shell-IFrame erstellt ein Objekt, oeffnet danach `/objects_v33` im `contentFrame`, markiert den Sidebar-Link und zeigt den Loxone-Tab ohne alte Listenansicht.
- Loxone-Race-Fix 33.3.10 pruefen: Doppelklick oder Reload erstellt kein zweites Objekt, gleiche UUID oeffnet den bestehenden Eintrag, Fehler werden geloggt und per Redirect statt 500 behandelt.
- Objekt-Loeschen 33.3.11 pruefen: vorhandenes, fehlendes und bereits geloeschtes Objekt fuehren nie zu 500, Route-Reload-Fehler werden geloggt und `/objects_v33` wird ohne `selected` neu geladen.
- IFrame-Loxone-Create 33.3.12 pruefen: eingebetteter und separater Loxone Explorer erzeugen denselben `/objects_v33/create_from_explorer?...`-Aufruf ohne `postMessage`-Sonderroute.
- Loxone-Auto-Publish-Gate 33.3.13 pruefen: leere `objects.json` und reine Loxone-Objekte publishen nichts, Loxone+MQTT-Objekte publishen nur ihr konfiguriertes MQTT-Topic.
- Embedded-Explorer-Debug 33.3.14 auswerten: Browser-Konsole und Live-Log auf Unterschiede bei URL, UUID, Name, Topic/IO und Request-Args zwischen Standalone und IFrame vergleichen.
- Create-Failure-Logging 33.3.15 auswerten: `CREATE OBJECT FAILED` und `reason=` zeigen die konkrete Phase und Exception direkt vor der Benutzer-Meldung.
- Loxone-Explorer-State 33.3.16 pruefen: nach wiederholtem Klick/Navigation nutzt Create einen frischen Snapshot, loggt `selectedRow` und behaelt keine alte Button-/Objektreferenz.
- Loxone-Explorer-JS 33.3.17 pruefen: `/topics2` ohne SyntaxError laden, `tm2Reload(false)` ausfuehren und Topics anzeigen.
- object_service Lock-Inversion 33.3.34 pruefen: Bridge und CRUD laufen parallel ohne Dateisperren, Live-Werte nutzen nur den In-Memory-Endpoint-Index.
- Live-Werte 33.3.35 pruefen: Karten und Live-Tab zeigen Quelle, erkannte Endpunkte und Werte ohne `objects.json`-Zugriffe pro Poll.
- Loxone-Live 33.3.36 pruefen: UUID, IO-Adresse und Objektname sollen zu einem Treffer fuehren und Debug-Logs sollen fehlende Zuordnungen sichtbar machen.
- Objekt-UUID 33.3.18 pruefen: neue Objekte erhalten `obj_<uuid4hex>`, Namensaenderungen behalten dieselbe ID und alte Slug-Links bleiben ueber `legacy_ids` aufloesbar.
- Objekt-Live-Werte 33.3.19 pruefen: `/api/objects/live`, Live-Tab und Objektkarten aktualisieren Werte ohne Page-Reload und ohne Speicherung in `objects.json`.
- Objektanlage 33.3.20 pruefen: Loxone-Create mit `uuid` plus Name/Visu-Name funktioniert wieder, optionale Felder fehlen tolerant und Route-Reload-Fehler erzeugen keinen Notice-Abbruch.
- Objekt-Delete 33.3.21 pruefen: Delete-Button sendet interne Objekt-UUID, `delete_object()` entfernt nur `id` aus `config/objects.json`, Slug/Key loeschen nicht mehr.
- Naechster Runtime-Schritt: Loxone als Quelle separat bewerten, ohne bestehende Listener umzubauen.
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

Ab 33.3.68 wird MQTT als Eingangsquelle im Objektmanager nicht mehr wie ein reiner Ausgang behandelt; die linke Kachel bevorzugt den Runtime-Cache fuer die Herkunftsanzeige und MQTT->UDP bekommt zusaetzliche Diagnose-Logs.
Ab 33.3.69 loggt der MQTT->UDP-Objektrouter den Eintritt, die verfuegbaren Routen und die Abbruchgruende vor dem UDP-Sender.
Ab 33.3.70 nutzt der MQTT-Routenloader die lokale UDP-Pruefung und meldet, warum eine Route vor dem Versand verworfen wird.
Ab 33.3.71 bewertet der Objektmanager den Status ueber echte Quelle-Ziel-Paare statt nur ueber die Anzahl vollstaendiger Endpunkte.
Ab 33.3.72 aktiviert der Objektmanager den UDP-Adapter beim Speichern, sobald echte Zielwerte vorhanden sind, damit konfigurierte UDP-Routen nicht inaktiv bleiben.
Ab 33.3.73 nutzt der MQTT-Objektrouter wieder die lokalen Core-Adapterpruefungen, damit MQTT->UDP nicht vor dem Sender mit einem internen Helper-Fehler abbricht.
Ab 33.3.74 ruft der MQTT->UDP-Dispatch die Wrapper-Signatur korrekt auf, damit `add_log_entry` nicht als `object_id` missverstanden wird.
Ab 33.3.75 nutzt MQTT->UDP fuer normale Topics den frischen Payload, waehrend JSON-Key-Objekte weiterhin den extrahierten Live-Wert verwenden.

## Leitplanken

- Keine neue Runtime, solange die technische Basis nicht vollstaendig stabil ist.
- Keine neue Objektmanager-Logik ohne ausdrueckliche Anforderung.
- Keine UI-Aenderungen bei reinen Portierungs- oder Service-Auslagerungen.
- Jede neue Version muss `CHANGELOG.md`, `ROADMAP.md` und `MIGRATION.md` aktualisieren.





Ab 33.3.64 kann der MQTT-Hub JSON-Key-Zeilen direkt als Objekt anlegen; der JSON-Key wird im MQTT-Adapter gespeichert und beim Live-Match als `topic / json_key` aufgeloest.
Ab 33.3.65 wird MQTT->UDP im Objektmanager mit klaren MQTT-Eingangs- und UDP-Sende-Logs verfolgt; aktive UDP-Routen setzen Zielhost und Port voraus.
Ab 33.3.66 verwendet MQTT->UDP den bestehenden UDP-Ausgang wie Loxone->UDP und reicht den aus JSON-Key extrahierten Wert direkt an den Sendepfad weiter.
Ab 33.3.67 geht MQTT->UDP direkt ueber den existierenden UDP-Sendepfad, damit kein zusaetzlicher Mapper den Objektwert unterwegs veraendert oder blockiert.








