# Changelog

## 33.3.50

- Der Routing-Tab baut seine Eintraege jetzt aus der Objektkonfiguration mit allen aktivierten Quellen und Zielen auf und zeigt keine Selbst- oder Legacy-Routen mehr an.
- Influx-Adressen im Routing-Tab zeigen jetzt `Measurement / Field / Topic`.
- Versionsstand auf `33.3.50` gesetzt.

## 33.3.49

- Die Livewert-Quelle im Objektmanager bleibt jetzt die echte Eingangsquelle, z. B. `loxone`, auch wenn der Wert nach MQTT, UDP oder Influx weitergeleitet wird.
- Geroutete Zieladapter werden separat als `last_target_adapter(s)` im Runtime-Live-Cache erfasst.
- MQTT-Echos eigener Objektmanager-Publishes ueberschreiben frische Loxone-Livewerte nicht mehr als Quelle `mqtt`.
- Livewert-Logging enthaelt `object_id`, `incoming_source`, `stored_source`, `target_adapter`, Wert und `ignored_echo`.
- Versionsstand auf `33.3.49` gesetzt.

## 33.3.48

- Der Objektmanager-Influx-Adapter speichert jetzt Measurement, Field und Topic pro Objekt.
- Leere Influx-Felder werden beim Speichern auf Defaults gesetzt: Measurement aus bereinigtem Objektname, Field `value`, Topic `<object.name>/value`.
- Influx schreibt das konfigurierte Topic als Tag `topic`; optionale Tags `object_id`, `source`, `unit` bleiben erhalten.
- Influx-Routing loggt jetzt `object_id`, Wert, Measurement, Field, Topic, Bucket und Ergebnis.
- Versionsstand auf `33.3.48` gesetzt.

## 33.3.47

- Influx kann im Objektmanager als Zieladapter aktiviert werden, ohne Legacy-Topic-Mappings zu erzeugen.
- Loxone-Livewerte werden bei aktivem Influx-Ziel direkt nach Influx geschrieben; Measurement, Field, Bucket und optionale Tags kommen aus dem Objektadapter.
- Influx-Werte werden numerisch geschrieben, wenn moeglich; Bool-Werte werden als 0/1 geschrieben, Text nur bei Datentyp `text`/`string`.
- Influx-Routing loggt `object_id`, Wert, Measurement, Field, Bucket und Ergebnis.
- Versionsstand auf `33.3.47` gesetzt.

## 33.3.46

- Neue Objekte erhalten beim Anlegen automatisch ein passives UDP Default Topic nach dem Muster `<Objektname>/value`.
- Leere UDP-Topic-Felder werden beim Speichern wieder auf `<Objektname>/value` gesetzt, statt dauerhaft leer gespeichert zu werden.
- Der UDP Payload-Modus steuert den Versand: `topic_value` sendet `<udp_topic>:<value>`, `value_only` sendet nur `<value>` und `json` sendet Topic plus Wert als JSON.
- Versionsstand auf `33.3.46` gesetzt.

## 33.3.45

- UDP Custom Topics im Objektmanager koennen vom alten Legacy-`format`-Fallback getrennt gespeichert werden.
- Das UDP-Adapterformular schreibt keinen alten `format`-Wert mehr als Hidden-Fallback zurueck.
- Legacy-`format`-Werte werden nur noch beim Laden alter Objekte einmalig als `udp_topic` interpretiert, nicht beim Speichern leerer Felder wiederhergestellt.
- Der Adapter-Merge im `object_service` verwirft leere Strings nicht mehr, damit der UDP-Speicherpfad leere Formularwerte erkennen und ab 33.3.46 wieder auf den Default setzen kann.
- Versionsstand auf `33.3.45` gesetzt.

## 33.3.44

- Der Objektmanager-UDP-Adapter speichert jetzt ein eigenes `udp_topic` und einen `payload_mode` direkt am Objekt.
- Loxone->UDP nutzt beim Senden das konfigurierte Objektmanager-UDP-Topic; ohne Topic wird nur der Wert gesendet.
- UDP-Zielrouten benoetigen nur noch Ziel-IP und Ziel-Port; der Textpraefix ist optional.
- Das UDP-Adapterformular zeigt das Feld `UDP Topic` mit Hilfetext und Payload-Modus.
- Versionsstand auf `33.3.44` gesetzt.

## 33.3.43

- Objektmanager-Routen werden nicht mehr in die Legacy-Loader fuer `MQTT -> Loxone`, `MQTT -> UDP` und `UDP -> MQTT` gemischt.
- Legacy-Seiten, Dashboard-Kacheln, globale Suche und Konfliktpruefung zaehlen/zeigen fuer diese Bereiche nur noch echte Legacy-Mapping-Dateien.
- MQTT-Publishes aus dem Objektmanager-Routing werden mit Runtime-Origin (`object_id`, `original_source`, `target_adapter`) markiert und im MQTT-Eingang als Echo uebersprungen.
- Loxone-Livewerte behalten dadurch im Objektmanager ihre Quelle `loxone`, auch wenn daraus MQTT- oder UDP-Zielsendungen entstehen.
- Versionsstand auf `33.3.43` gesetzt.

## 33.3.42

- Loxone->UDP sendet den Wert jetzt nur noch einmal pro Zielpaket; die MQTT-Loopback-Sperre greift jetzt auch fuer MQTT->UDP-Weiterleitungen aus dem Loxone-Publishpfad.
- UDP-Payloads senden ohne Topic jetzt nur noch den nackten Wert statt ein leeres Prefix.
- Das UDP-Logging schreibt pro Paket eine detaillierte INFO-Zeile mit `object_id`, `source`, `value`, `udp_target`, `payload`, `target_host` und `target_port`.
- Im MQTT->UDP-Mapping wurde das UI-Label von `Format` auf `UDP-Topic` umbenannt.
- Versionsstand auf `33.3.42` gesetzt.

## 33.3.41

- Loxone->UDP sendet pro Wert nur noch einmal pro Zielroute; MQTT-Loopbacks aus dem Loxone-Publishpfad werden kurzzeitig erkannt und als Duplikat uebersprungen.
- UDP-Logging erfasst jetzt `object_id`, `value`, `udp_target`, `used_format` und `skipped_duplicate`.
- Versionsstand auf `33.3.41` gesetzt.

## 33.3.40

- Loxone-Livewerte werden jetzt nach der Objektzuordnung auch an aktive Zieladapter weitergereicht.
- Prioritaet ist dabei MQTT vor UDP; KNX wird nur als vorbereitete Route erkannt und noch nicht gesendet.
- Der Loxone-Publishpfad loggt jetzt `object_id`, `value`, `target` und `result` fuer erfolgreiche oder uebersprungene Zielsendungen.
- Versionsstand auf `33.3.40` gesetzt.

## 33.3.39

- Der temporäre Single-Object-Fallback fuer Loxone-Livewerte wurde entfernt.
- `record_live_value()` loggt fehlende Loxone-Zuordnungen nun auf INFO/WARNING statt stiller Fallback-Zuordnung.
- Versionsstand auf `33.3.39` gesetzt.

## 33.3.38

- `/api/objects/live` zieht nun Loxone-Livewerte aus `core.display_values` und `core.last_values` nach und synchronisiert sie wieder in den Objekt-Live-Cache.
- Der Sync berücksichtigt bei Loxone zusätzlich `custom_name` aus der Topic-Config, damit echte Livewerte nicht mehr als `value:null` im Objektmanager landen.
- Versionsstand auf `33.3.38` gesetzt.

## 33.3.37

- Loxone-Livewerte matchen jetzt auch auf `object.name`, `loxone.name` und die Alias-Felder `io`, `io_address`, `loxone_io`, `uuid` und `loxone_uuid`.
- Wenn kein Treffer gefunden wird, loggt `record_live_value()` nun eine Debug-Sicht mit den relevanten Objektfeldern.
- Bei genau einem Objekt kann ein Loxone-Livewert als temporärer Fallback auf dieses Objekt gelegt werden.
- Versionsstand auf `33.3.37` gesetzt.

## 33.3.36

- Loxone-Livewerte matchen jetzt robuster ueber UUID, IO-Adresse und Objektname und loggen Debug-Hinweise, wenn kein Treffer gefunden wird.
- Der Live-Endpoint-Index wird nach Objekt-CRUD direkt neu aufgebaut, damit frische Objekte sofort fuer Live-Zuordnungen verfuegbar sind.
- Versionsstand auf `33.3.36` gesetzt.

## 33.3.35

- Objektmanager zeigt Live-Werte jetzt mit erkannter Quelle und erkanntem Endpunkt in Karten und Live-Tab an.
- Live-Wert-Zuordnung nutzt den vorbereiteten In-Memory-Index fuer Loxone UUID/IO-Adresse und MQTT Topic, ohne `objects.json` pro Wert zu scannen.
- `GET /api/objects/live` und `GET /api/objects/<id>/live` liefern jetzt auch `source_address` und `recognized_endpoint`.
- Versionsstand auf `33.3.35` gesetzt.

## 33.3.34

- object_service nutzt jetzt keine Lock-Inversion mehr: Datei- und Cache-Zugriffe sind entkoppelt, CRUD ruft nicht mehr unter `OBJECTS_FILE_LOCK` wieder `list_objects()` auf.
- Live-Wert-Erfassung arbeitet jetzt mit einem vorbereiteten In-Memory-Endpoint-Index statt pro Wert die komplette Objektliste zu scannen.
- Objekt-Cache, Endpoint-Index und Route-Cache werden gemeinsam invalidiert, damit Bridge-Callbacks und CRUD sich nicht gegenseitig blockieren.
- Versionsstand auf `33.3.34` gesetzt.

## 33.3.32

- Delete entkoppelt jetzt den Reload noch deutlicher: `objects.json` wird geschrieben, Cache invalidiert und der Route-Reload nur asynchron angestossen.
- Delete-Requests loggen `delete_start`, `write_objects_done`, `cache_invalidated`, `reload_requested` und `delete_response_sent`.
- `reload_object_routes()` loggt nun Start, Dauer und Fehler separat, damit Reload-Blockaden schneller sichtbar werden.
- Versionsstand auf `33.3.32` gesetzt.

## 33.3.31

- Objekt-Routen werden jetzt ueber einen In-Memory-Cache erzeugt und nicht bei jedem Zugriff neu aus `config/objects.json` berechnet.
- CRUD-Reloads laufen asynchron, damit der Flask-Thread nicht auf Route-Neuberechnung warten muss.
- Loxone->MQTT-Routencheck bleibt cachebasiert, Skip-Logs bleiben debug-only und das UI-Log wird nicht mehr mit Skip-Meldungen geflutet.
- Versionsstand auf `33.3.31` gesetzt.

## 33.3.30

- Loxone->MQTT Skip-Meldungen laufen nicht mehr ueber das normale Live-Log; im Debug-Fall werden sie pro UUID nur noch rate-limited geloggt.
- Die Loxone->MQTT-Routensuche nutzt jetzt einen In-Memory-Index statt pro Wert die komplette Objektliste zu durchsuchen.
- `config/objects.json`-Lesen fuer den Routing-Check wird damit aus dem Loxone-Hot-Path entfernt; Live-Werte werden weiter aktualisiert.
- Versionsstand auf `33.3.30` gesetzt.

## 33.3.29

- `config/objects.json` wird beim Objekt-CRUD jetzt ueber einen zentralen Schreiblock und eindeutige Temp-Dateien geschrieben.
- Atomisches Schreiben versucht `os.replace()` mehrfach erneut, damit Windows-Dateisperren nicht sofort zu einem 500 fuehren.
- API-Routen geben bei gesperrter Objektdatei einen sauberen `423`-Hinweis statt eines generischen Serverfehlers zurueck.
- Versionsstand auf `33.3.29` gesetzt.

## 33.3.27

- CRUD-State im Objektmanager weiter abgesichert: Objekt-Runtime-State wird nach Create/Update/Delete komplett verworfen, damit geladene Live-/Cache-Reste keinen Folge-CRUD blockieren.
- Loxone-Create loggt jetzt vor dem Fehlerpfad zusaetzlich `request.args`, `request.form`, JSON-Payload und die konkrete Ursache im exakten Debug-Format.
- Create/Import-Logging erfasst den Request-Snapshot mit Form- und JSON-Daten sowie den aktuellen Objektbestand vor dem Duplicate-Check.
- Versionsstand auf `33.3.27` gesetzt.

## 33.3.26

- Jinja2-kompatible JavaScript-Strings im Objektmanager auf `tojson` umgestellt.
- `e('js')` im Objektmanager-Template entfernt, damit der Seite kein Template-500 mehr erzeugt.
- Versionsstand auf `33.3.26` gesetzt.

## 33.3.24

- Objekt-CRUD loest keinen Bridge-Neustart mehr aus.
- `reload_object_routes()` berechnet die Objekt-Routen neu, laesst die laufende Bridge aber aktiv.
- Flask wird beim Direktstart explizit ohne Reloader gestartet, damit `objects.json` keine Dev-Restarts triggert.
- Delete setzt die Objektansicht nach dem Loeschen auf keine Auswahl mehr und loggt IDs vor/nach dem Vorgang.
- Versionsstand auf `33.3.24` gesetzt.

## 33.3.25

- Objektwahl im Objektmanager laedt den rechten Bereich jetzt per API/Fragment statt per Full-Page-Navigation.
- Delete verwendet die vorher gemerkte `selectedObjectId`, loescht idempotent und setzt danach die Auswahl sauber auf leer.
- Objektliste wird nach Delete per API neu aufgebaut, ohne den kompletten Content-Bereich neu zu laden.
- Versionsstand auf `33.3.25` gesetzt.

## 33.3.21

- Objekt-Loeschen nach interner UUID-Umstellung repariert.
- Delete-Button uebergibt die interne MP-Gateway Objekt-UUID aus `object.uuid`/`object.id`.
- `delete_object()` entfernt Objekte nur noch anhand der gespeicherten `id` in `config/objects.json`; Name, Key, Slug und Legacy-IDs werden nicht mehr als Delete-Identitaet verwendet.
- Delete-Route loggt `DELETE REQUEST uuid=... object found=... deleted=...`.
- Nach Delete wird ohne 500 auf `/objects_v33` redirectet und die Objektliste neu geladen.
- Versionsstand auf `33.3.21` gesetzt.

## 33.3.20

- Loxone-Explorer-Objektanlage stabilisiert.
- Fehlermeldung `Objekt konnte nicht erstellt werden...` wird jetzt mit Request-Daten, ausgewaehlter UUID, Name, IO-Adresse, Explorer/Source und konkretem `reason` geloggt.
- Loxone-Create prueft nur die erforderliche Loxone-UUID als Mindestfeld; Name, IO-Adresse, Control-Type, Raum und Einheit bleiben tolerant optional.
- Route-Reload-Fehler nach erfolgreichem Speichern erzeugen keinen Create-Abbruch mehr, sondern werden nur geloggt.
- Erfolgreiche Anlage redirectet weiter auf `/objects_v33?selected=<object_id>&tab=loxone`.
- Versionsstand auf `33.3.20` gesetzt.

## 33.3.19

- Objektmanager um neuen Tab `Live` erweitert.
- Live-Werte werden runtime-only im Prozesscache gefuehrt und nicht in `config/objects.json` gespeichert.
- Objektliste zeigt pro Objekt aktuellen Wert und Quelle, aktualisiert per `/api/objects/live` ohne Seiten-Reload.
- Neue Live-APIs ergaenzt: `GET /api/objects/live` und `GET /api/objects/<id>/live`.
- Runtime-Ereignisse aus Loxone, MQTT, KNX und UDP koennen Live-Werte anhand der Objekt-Endpunkte zuordnen.
- Versionsstand auf `33.3.19` gesetzt.

## 33.3.18

- Interne MP-Gateway Objekt-UUIDs auf echte stabile `obj_<uuid4hex>`-IDs umgestellt.
- Neue Objekte leiten ihre Objekt-UUID nicht mehr aus Name, Key, Topic, Loxone-UUID oder anderen Adapterdaten ab.
- Bestehende Slug-IDs in `config/objects.json` werden beim Laden einmalig migriert und als interne `legacy_ids` fuer alte Links/Referenzen erhalten.
- Objektmanager-Kopf zeigt die Identitaet als `MP-Gateway Objekt-UUID`; Loxone-UUID bleibt ausschliesslich im Loxone-Tab.
- Objekt-Update und -Delete akzeptieren weiterhin alte Slug-Referenzen, speichern aber nur die stabile interne Objekt-ID.
- Versionsstand auf `33.3.18` gesetzt.

## 33.3.17

- Loxone-Explorer-JavaScript-Escape in `tm2CssEscape()` repariert.
- Fragiles Regex-Literal im Python-gerenderten Script durch robuste `replaceAll`-Fallback-Variante ersetzt.
- `/topics2` rendert wieder gueltiges JavaScript, damit `tm2Reload(false)` ausgefuehrt werden kann.
- Keine Backend- oder Importlogik geaendert.
- Versionsstand auf `33.3.17` gesetzt.

## 33.3.16

- Loxone-Explorer-Create nutzt beim Klick einen frischen Snapshot aus `tm2Topics` statt eine moeglicherweise veraltete `tm2Selected`-Objektreferenz.
- Debug-Log vor `create_from_explorer` um `selectedRow`, `selectedUuid`, `selectedObject`, Ziel-URL und Request-Parameter erweitert.
- Tree-Zeilen tragen `data-topic`, damit die aktuell markierte Row vor dem Create eindeutig geloggt werden kann.
- Create-Button-State wird bei Browser-Page-Restore zurueckgesetzt, damit keine alte In-Progress-/Button-Referenz erhalten bleibt.
- Keine Backend-Aenderung am Import.
- Versionsstand auf `33.3.16` gesetzt.

## 33.3.15

- Direkt vor der Create-Fehlermeldung explizite Error-Logs ergaenzt: `CREATE OBJECT FAILED`, `request.args`, `request.form`, JSON-Payload und `reason`.
- Keine Aenderung an Create-Logik, Importlogik, Redirects oder Bedingungen.
- Versionsstand auf `33.3.15` gesetzt.

## 33.3.14

- Debug-Logging fuer Loxone-Explorer-Create ergaenzt, ohne Backend-Importlogik zu aendern.
- Frontend loggt vor der Navigation Embedded-Status, aktuelle URL, ausgewaehlte UUID, Name, Topic/IO, Objekt und Ziel-URL.
- `/objects_v33/create_from_explorer` loggt Request-URL, Referrer, Query-Args, ausgewaehlte Werte, erzeugtes Payload und Notice-Ursprung.
- Die Meldung `Objekt konnte nicht erstellt werden. Bitte Auswahl pruefen und erneut versuchen.` wird mit Generator-Funktion und Datei/Zeile geloggt.
- Versionsstand auf `33.3.14` gesetzt.

## 33.3.13

- Legacy-Auto-Publish von Loxone-State-Updates nach MQTT gestoppt.
- `publish_value()` aktualisiert weiterhin Anzeige-/Explorer-Werte, publisht aber nur noch bei aktiver Objektmanager-Route `Loxone -> MQTT`.
- Objekt-Routengenerator um aktive `loxone2mqtt`-Routen aus vollständigen Loxone- und MQTT-Endpunkten erweitert.
- Runtime-Gate prueft aktives Objekt, aktivierte Loxone-/MQTT-Adapter, vollstaendige Endpunkte und passende Loxone-UUID/IO-Adresse.
- Loxone-Erfassung bleibt aktiv; ungefragtes MQTT-Publishing ohne Objekt-Route wird uebersprungen und gedrosselt geloggt.
- Versionsstand auf `33.3.13` gesetzt.

## 33.3.12

- Eingebetteten Loxone-Explorer-Create an den separaten Fenster-Flow angeglichen.
- `tm2CreateObjectSelected()` ruft `/objects_v33/create_from_explorer` nun auch im IFrame per direktem `window.location.href` auf.
- Die Loxone-Create-Sondernavigation ueber `postMessage` und Shell-Frame-Rewrite wird fuer diesen Button nicht mehr verwendet.
- Backend-Importlogik bleibt unveraendert.
- Versionsstand auf `33.3.12` gesetzt.

## 33.3.11

- Objektmanager-V33-Loeschen robust gemacht: Delete akzeptiert `id`, `uuid` oder `key` und bleibt bei fehlendem oder bereits geloeschtem Objekt ohne 500.
- Delete-Route faengt Such-, Schreib- und Route-Reload-Fehler ab, loggt sie und leitet immer sauber auf `/objects_v33` ohne `selected` zurueck.
- Objektliste wird nach dem Loeschen neu geladen; ein geloeschtes Objekt wird rechts nicht mehr als Auswahl uebergeben.
- Loesch-Button postet nur bei vorhandener Objekt-ID, deaktiviert sich beim ersten Submit und ignoriert Mehrfachklicks.
- Delete-Logging fuer `object_id`, `found`, `deleted`, `redirect` und `error` ergaenzt.
- Versionsstand auf `33.3.11` gesetzt.

## 33.3.10

- Loxone-Explorer-Button gegen Mehrfachklick gesichert; nach dem ersten Klick wird er deaktiviert und zeigt `Erstelle...`.
- `/objects_v33/create_from_explorer` fuer Loxone idempotent gemacht: gleiche Loxone-UUID oeffnet das vorhandene Objekt statt ein zweites zu erstellen.
- Explorer-Create-Fehler werden abgefangen, geloggt und per Objektmanager-Redirect mit Hinweis behandelt statt als Internal Server Error zu enden.
- Erfolgreiche Loxone-Explorer-Creates leiten stabil auf `/objects_v33?selected=<object_id>&tab=loxone` weiter.
- Import-Logging fuer `source`, `uuid`, `name`, `object_id` und `action=created/existing/error` ergaenzt.
- Versionsstand auf `33.3.10` gesetzt.

## 33.3.9

- Eingebettete Explorer-Objektanlage ueber eine `postMessage`-Bruecke zur Shell gefuehrt.
- Die Shell setzt bei Explorer-Create den `contentFrame` gezielt auf den Objektmanager V33 und markiert den Sidebar-Link.
- Cache-Busting fuer eingebettete Objektmanager-Navigation ergaenzt und nach dem Create-Redirect beibehalten.
- Direkte Explorer-Fenster behalten den bestehenden Redirect unveraendert bei.
- Versionsstand auf `33.3.9` gesetzt.

## 33.3.8

- Sidebar-Versionsanzeige dynamisiert: `app_version` wird beim Rendern aus der zentralen `VERSION`-Datei gelesen.
- App-Context-Processor stellt `app_name`, `app_subtitle`, `app_legacy_name` und die aktuelle `app_version` fuer Templates bereit.
- Versionsstand auf `33.3.8` gesetzt.

## 33.3.7

- `APP_VERSION` wird aus der zentralen `VERSION`-Datei gelesen; hart codierte alte Versionswerte in `app/engine/port.py` entfallen.
- Alter toter JavaScript-Renderer in `templates/objects_v33/list.html` entfernt, damit nur noch die serverseitige Objektmanager-V33-Pipeline aktiv ist.
- `/objects_v33/new` oeffnet fuer manuelle Neuanlage kein ungespeichertes Detailobjekt mehr; Explorer-Parameter werden weiterhin nach `/objects_v33/create_from_explorer` umgeleitet.
- Object Service erkennt alle kanonischen top-level Protokollbloecke beim Speichern und normalisiert sie in das zentrale Objektmodell.
- `object_registry.py` und `data/objects_v33.json` als deprecated markiert; produktive V33-Objekte bleiben in `config/objects.json`.
- Versionsstand auf `33.3.7` gesetzt.

## 33.3.6

- Objekt-Speicherform fuer V33 final auf Stammdaten plus top-level Protokollbloecke konsolidiert, z.B. `object.loxone`.
- Neue Loxone-Explorer-Objekte schreiben Loxone-Daten direkt nach `loxone` statt in eine zusaetzliche `adapters`-Speicherstruktur.
- Alte `adapters`-Eintraege bleiben lesbar und werden beim Speichern in die kanonische Protokollblock-Form migriert.
- Adapter-Speichern schreibt den bearbeiteten Protokollblock direkt auf `object.<protocol>`.
- Versionsstand auf `33.3.6` gesetzt.

## 33.3.5

- Objektmodell fuer Objektmanager V33 konsolidiert: neue Objekte schreiben Protokolldaten nur noch kanonisch in Protokollbloecke.
- Legacy-Felder wie `source_type`, `source_address`, `target_type`, `loxone_topic`, `mqtt_topic`, `knx_ga`, `udp_topic` und top-level `loxone` werden beim Lesen migriert, aber nicht mehr neu in `config/objects.json` geschrieben.
- Loxone-Explorer-Create speichert den Loxone-Endpunkt als Loxone-Protokollblock mit `enabled`, `direction`, `datatype`, `uuid`, `io_address`, `control_type`, `visu_name`, `room` und `unit`.
- Objektliste und Detailansicht laden nach Explorer-Create aus derselben gespeicherten Service-Quelle; der clientseitige `/api/objects`-Listenersatz wurde entfernt.
- Adapter werden intern weiter als Liste nutzbar gemacht, aber in `objects.json` nicht als zweite Struktur gespeichert.
- Versionsstand auf `33.3.5` gesetzt.

## 33.3.4

- Loxone-Explorer-Create nachgezogen: Loxone-Adapter wird mit Aktiv, Richtung, Datentyp, UUID, IO-Adresse, Control-Typ, Visu-Name, Raum und Einheit befuellt.
- Key-Erzeugung fuer neue Explorer-Objekte nutzt Klarnamen mit Unterstrichen, z.B. `gesamtleistungw_value`, und uebernimmt keine UUID als Allgemein-Key.
- Loxone-Create akzeptiert zusaetzliche Parameter-Aliase fuer UUID, IO-Adresse, Name/Pfad, Control-Type, Visu-Name, Raum und Einheit.
- Explorer-JavaScript uebergibt die Datenpunkt-UUID bevorzugt als Loxone-UUID und den letzten Wert zur Datentyp-Erkennung.
- Nach Explorer-Create bleibt die Weiterleitung auf das neu erstellte Objekt mit aktivem Loxone-Tab erhalten.
- Versionsstand auf `33.3.4` gesetzt.

## 33.3.3

- Loxone-Explorer-Objektanlage robust nachgezogen.
- Loxone-Endpunkt wird beim Explorer-Create immer als aktivierter `loxone`-Adapter gespeichert.
- Alte `/objects_v33/new`-Vorbelegungen mit Loxone-Parametern fuellen nun ebenfalls den Loxone-Tab statt Allgemein-Quelle/Ziel.
- Leere Legacy-Quelle erzeugt keinen aktivierten MQTT-Fallback-Adapter mehr.
- Loxone Explorer uebergibt bevorzugt die Control-UUID als UUID und den State-/IO-Pfad als IO-Adresse.
- Status bleibt bei nur einem vollstaendigen Loxone-Endpunkt `unvollstaendig`; Routing wird erst mit zweitem vollstaendigem Endpunkt aktiv.
- Versionsstand auf `33.3.3` gesetzt.

## 33.3.2

- Loxone Explorer kann Objekte direkt im Objektmanager V33 erstellen.
- Explorer-Create speichert ausschliesslich Klardaten im Allgemein-Bereich: Name, Key, Datentyp, Kategorie, Raum, Einheit, Beschreibung und Aktiv.
- Technische Loxone-Daten werden nur im Loxone-Adapter gespeichert: UUID, IO-Adresse, Control-Typ, Visu-Name, Raum und Einheit.
- Nach dem Erstellen oeffnet der Objektmanager automatisch den Loxone-Tab des neuen Objekts.
- Loxone-Tab um Felder fuer IO-Adresse, Control-Typ, Visu-Name, Raum und Einheit erweitert.
- `/objects_v33/new` nutzt technische Vorbelegungen als Adapterdaten statt als Allgemein-Quelle/-Ziel.
- Versionsstand auf `33.3.2` gesetzt.

## 33.3.1

- Objektmanager V33 auf objektzentrierte Anschluss-Architektur umgestellt.
- Allgemein-Tab enthaelt nur noch Objekt-Stammdaten: Name, Key, Datentyp, Kategorie, Raum, Einheit, Icon, Skalierung, Beschreibung und Aktiv.
- Quelle, Quelladresse, Ziel, Zieladresse und Influx-Aktivierung aus dem Allgemein-Tab entfernt.
- Objektstatus wird nicht mehr aus Allgemein-Feldern berechnet, sondern aus vollstaendigen aktiven Protokoll-Endpunkten.
- Routing-Tab zeigt erzeugte Adapter-Routen, Status und fehlende Endpunkte fuer unvollstaendige Objekte.
- Route-Generator erzeugt aktive Runtime-Routen aus Protokoll-Endpunkten fuer bestehende Mapping-Strukturen, inklusive KNX-/UDP-Richtungen.
- Adapter-Speichern schreibt keine Quelle-/Ziel-Felder mehr in das Objekt zurueck.
- Versionsstand auf `33.3.1` gesetzt.

## 33.3.0

- Objektbasierte aktive Routen fuer den ersten Runtime-Durchstich vorbereitet.
- `build_routes_from_objects()` erzeugt aus aktivierten Objekten virtuelle Routen in bestehenden Runtime-Strukturen.
- MQTT-Objekte werden zuerst angebunden: `mqtt -> loxone`, `mqtt -> knx`, `mqtt -> udp` und `mqtt -> influx` werden in vorhandene Loader-Formate uebersetzt.
- Bestehende Mapping-Dateien werden nicht als neue Parallelstruktur ersetzt; objektgenerierte Routen werden beim Laden zu `mqtt2lox`, `mqtt2udp`, `mqtt2knx` und `topic_config` gemerged.
- Nach Objekt-Speichern, Loeschen, Toggle und Adapter-Speichern werden Objektrouten neu berechnet; eine laufende Bridge wird neu geladen, eine gestoppte Bridge bleibt gestoppt.
- Objektmanager zeigt Route-Status-Badges: `aktiv`, `deaktiviert`, `unvollständig`, `fehler`.
- Logging fuer Objektrouten ergaenzt: Gesamtzahl, aktive Routen, uebersprungene Objekte und Fehler je Objekt.
- KNX/Loxone/UDP bleiben als Zieltypen vorbereitet; vollstaendige Nicht-MQTT-Quellen folgen spaeter.
- Versionsstand auf `33.3.0` gesetzt.

## 33.9.0

- Objektmanager-Core fuer MP-Gateway V33 eingefuehrt.
- Neues zentrales Objektmodell `GatewayObject` unter `app/models/object_model.py` ergaenzt.
- Neuer Service `app/services/object_service.py` speichert Objekte in `config/objects.json` und stellt CRUD-, Toggle- und Serialisierungsfunktionen bereit.
- Neue API-Routen ergaenzt: `GET/POST /api/objects`, `GET/PUT/DELETE /api/objects/<id>` und `POST /api/objects/<id>/toggle`.
- `/objects_v33` liest und schreibt nun ueber den neuen Object Service.
- Objektformular speichert Kernfelder wie Quelle, Quelladresse, Ziel, Datentyp, Einheit, Aktiv-Status und Influx-Status.
- MQTT Topic Manager/Explorer verlinkt `Objekt erstellen` auf den neuen Objektmanager mit MQTT-Quelle und Topic-Vorbefuellung.
- Bestehendes Layout bleibt erhalten; keine Runtime-Mapping-Erzeugung und keine Adapter-/Runtime-Anbindung.
- Versionsstand auf `33.9.0` gesetzt.

## 33.2.8a

- UI-Feinschliff fuer den Objektmanager V33.
- Linke Objektliste und rechter Editorbereich nutzen nun denselben Arbeitsflaechen-Hintergrund.
- Sidebar bleibt unveraendert dunkel.
- Objektkarten, Panels, Buttons und Protokoll-Badges bleiben unveraendert.
- Keine Runtime-Aenderung, keine Objektlogik-Aenderung und keine Adapterlogik-Aenderung.
- Versionsstand auf `33.2.8a` gesetzt.

## 33.2.8

- Objektmanager-V33-Hauptbereich optisch an Dashboard-/Standardseiten angeglichen.
- `/objects_v33` nutzt nun fuer Body, Hauptflaeche und Detailpanel den Standard-Grundhintergrund.
- Sidebar, Objektkarten-Farben und Protokoll-Badges bleiben unveraendert.
- Keine Runtime-Aenderung, keine Objektlogik-Aenderung und keine Adapterlogik-Aenderung.
- Versionsstand auf `33.2.8` gesetzt.

## 33.2.7g

- Externe Sidebar-Buttons wieder generisch aus der Sidebar-Button-Konfiguration gerendert.
- Unter `Externe Dienste` werden nur aktive Config-Eintraege angezeigt; Name, URL, Reihenfolge und `new_tab` kommen aus der Config.
- `new_tab=true` oeffnet externe Links mit `target="_blank"` und `rel="noopener noreferrer"`.
- `new_tab=false` oeffnet Links im Shell-Betrieb wieder im rechten Content-Bereich.
- Hart codierte externe Eintraege fuer InfluxDB/Grafana entfernt; neue aktive Config-Eintraege erscheinen automatisch.
- `Influx Explorer` bleibt unveraendert als interne MP-Gateway-Seite auf `/influx_explorer`.
- Keine Runtime-Aenderung, keine Objektmanager-Logik-Aenderung, keine Adapterlogik-Aenderung und keine Routen-Aenderung.
- Versionsstand auf `33.2.7g` gesetzt.

## 33.2.7c

- Sidebar-Link-Korrektur fuer externe Dienste.
- `Influx Explorer` bleibt im MP-Gateway-Menue intern auf `/influx_explorer`.
- `InfluxDB` unter `Externe Dienste` nutzt nun die externe URL aus der Sidebar-Konfiguration und zeigt keinen falschen internen Fallback mehr.
- `Grafana` unter `Externe Dienste` nutzt nun die externe URL aus der Sidebar-Konfiguration.
- Fehlt eine externe URL, wird der Eintrag deaktiviert angezeigt.
- Keine Runtime-Aenderung, keine Objektlogik-Aenderung, keine Adapterlogik-Aenderung und keine Routen-Aenderung.
- Versionsstand auf `33.2.7c` gesetzt.

## 33.2.7a

- Sidebar-Feinschliff ohne Routing- oder Runtime-Aenderung.
- Sichtbare Gruppenueberschrift `MP-Gateway` aus der Sidebar entfernt.
- Alter Objektmanager-Link aus der Sidebar entfernt; sichtbar bleibt nur `Objektmanager V33`.
- Bereich `Externe Dienste` auf `InfluxDB` und `Grafana` bereinigt.
- Keine Layoutaenderungen darueber hinaus, keine Objektlogik- oder Adapterlogik-Aenderung.
- Versionsstand auf `33.2.7a` gesetzt.

## 33.2.7

- Sidebar weiter bereinigt und in die Gruppen `MP-Gateway` und `Externe Dienste` gegliedert.
- MP-Gateway-Gruppe enthaelt Dashboard, MQTT Monitor, MQTT Hub, Loxone Monitor, Objektmanager, Objektmanager V33, KNX, KNX Monitor, Suche, Konfig pruefen, Influx Explorer und Einstellungen.
- Externe Dienste enthalten InfluxDB und Grafana klar getrennt von der internen Navigation.
- Neues Layout-Fundament vorbereitet: `templates/layout/base.html` und `templates/layout/page_header.html`.
- `/objects_v33` nutzt die neue Base-Struktur, bleibt funktional aber unveraendert.
- Keine Routen umgestellt, kein Redirect eingefuehrt, kein alter Objektmanager entfernt.
- Keine Runtime-Aenderung, keine Registry-Logik-Aenderung, keine Objektlogik-Aenderung, keine Adapterlogik-Aenderung und keine Mapping-Erzeugung.
- Versionsstand auf `33.2.7` gesetzt.

## 33.2.6

- Sidebar als gemeinsame MP-Gateway-Komponente nach `templates/shared/sidebar.html` ausgelagert.
- Zentrale Sidebar-Styles in `static/css/sidebar.css` ergaenzt und in Shell- sowie Standardlayout eingebunden.
- Shell-Navigation vereinheitlicht: Dashboard, MQTT Monitor, Loxone Monitor, MQTT Hub, Objektmanager, Objektmanager V33, KNX, KNX Monitor, Suche, Konfig pruefen, InfluxDB, Grafana und Einstellungen nutzen dieselbe Komponente.
- Aktiver Menuepunkt wird automatisch ueber die gemeinsame Klasse hervorgehoben und nutzt den gruenen linken Akzent.
- Header, App-Name, Untertitel, Status, Abstaende, Schriftgroessen, Buttonhoehen und Sidebar-Breite vereinheitlicht.
- Keine Runtime-Aenderung, keine Registry-Logik-Aenderung, keine Routing-Logik-Aenderung und keine Mapping-Erzeugung.
- Versionsstand auf `33.2.6` gesetzt.

## 33.2.5

- Objektmanager V33 weiter auf die festgelegte MP-Gateway-Designlinie gebracht.
- Filterchips bereinigt: `Alle`, `Aktiv`, `MQTT`, `Loxone`, `UDP`, `KNX`, `Influx`.
- Protokoll-Badges sind nun kraeftiger: MQTT blau, Loxone gruen, UDP violett, KNX orange, Influx tuerkis/blau.
- Inaktive Adapter-Badges bleiben grau und gedimmt.
- Ausgewaehlte Objektkarte deutlicher mit Rahmen, hellerem Hintergrund und dezentem Glow hervorgehoben.
- Sidebar-Active-State optisch geschaerft, ohne Navigation oder Routen zu aendern.
- Neue Doku `docs/UI_GUIDELINES.md` angelegt.
- Keine Runtime-Aenderung, keine Registry-Logik-Aenderung, keine Adapterlogik-Aenderung und keine Mapping-Erzeugung.
- Versionsstand auf `33.2.5` gesetzt.

## 33.2.4

- Objektmanager V33 optisch weiter an das Industrial-Dark-Referenzlayout angepasst.
- Linke Objektliste mit klareren Initialen, staerkerer Auswahlmarkierung, besseren Abstaenden und ruhigerer Zeilenhoehe ueberarbeitet.
- Jede Objektkarte zeigt nun immer alle Protokoll-Badges: MQTT, Loxone, UDP, KNX und Influx.
- Aktive Protokolle werden farbig hervorgehoben, inaktive Protokolle grau gedimmt.
- Projektfarbschema bleibt erhalten; Protokollfarben wurden dezent integriert.
- Keine Runtime-Aenderung, keine Registry-Logik-Aenderung, keine Adapterlogik-Aenderung und keine Mapping-Erzeugung.
- Versionsstand auf `33.2.4` gesetzt.

## 33.2.3

- Objektmanager V33 in der Sidebar verlinkt.
- Neuer Sidebar-Eintrag `Objektmanager V33` zeigt auf `/objects_v33`.
- `/objects_v33` optisch an das Industrial-Dark-Layout angepasst: Objektliste links, Detail-/Editorbereich rechts.
- Linke Spalte mit Suchfeld, Neu laden, Health Check, Filterchips und Objektkarten ergaenzt.
- Rechte Spalte mit Objektkopf, Aktionsbuttons und Tabs fuer Allgemein, MQTT, Loxone, UDP, KNX, Influx und Routing ergaenzt.
- Adapter-Editoren liegen nun in ihren jeweiligen Tabs; Routing-Vorschau liegt im Routing-Tab.
- Bestehender Objektmanager-Eintrag `/objects` bleibt unveraendert.
- Keine Runtime-Aenderung, keine Registry-Logik-Aenderung, keine Adapterlogik-Aenderung und keine V32-Objects-Routen geaendert.
- Versionsstand auf `33.2.3` gesetzt.

## 33.2.2

- Routing-Vorschau fuer den Objektmanager V33 ergaenzt.
- Neuer passiver Service `app/services/object_routing_preview.py` mit `build_object_routing_preview(object_def)`.
- `/objects_v33/edit/<uuid>` zeigt moegliche spaetere Verbindungen aktiver Adapter mit Quelle, Ziel, Richtung und Status `Vorschau`.
- Inaktive Adapter werden nicht beruecksichtigt; Influx wird nur als Ziel angezeigt.
- Keine Runtime-Anbindung, keine echten Mapping-Dateien geschrieben und keine V32-Objects-Aenderung.
- Versionsstand auf `33.2.2` gesetzt.

## 33.2.1

- Branding-Vorbereitung fuer MP-Gateway ergaenzt.
- Zentrale Konstanten `APP_NAME`, `APP_SUBTITLE` und `APP_LEGACY_NAME` in `app/branding.py` eingefuehrt.
- Sichtbare Shell-Titel und Header auf `MP-Gateway` und `Das Multiprotokoll-Gateway` umgestellt.
- `MQTT2Lox` bleibt vorerst technischer Projekt-/Repo-Name; Paket-, Ordner-, Routen- und Config-Namen bleiben unveraendert.
- Keine Runtime-Aenderung und keine Mapping-Erzeugung.
- Versionsstand auf `33.2.1` gesetzt.

## 33.2.0

- Adapter erhalten eigene Editor-Komponenten unter `app/templates/objects_v33/adapters/`.
- MQTT, UDP, KNX, Loxone und Influx besitzen eigene passive Editor-Bausteine fuer protokollspezifische Grundeinstellungen.
- Der Objekteditor bindet die Adapter dynamisch ein; allgemeine Objektdaten bleiben in einem getrennten Formular.
- `object_adapter_engine.py` verwaltet Laden, Serialisieren und Speichern der Adapterdaten aus den Editor-Formularen.
- Keine Runtime-Anbindung, keine Mapping-Erzeugung und keine bestehenden Mapping-Dateien geaendert.
- Versionsstand auf `33.2.0` gesetzt.

## 33.1.2

- Adapterverwaltung im neuen Objektmanager V33 integriert.
- `/objects_v33` zeigt bei der Objektbearbeitung alle bekannten Adapter: MQTT, UDP, KNX, Loxone und Influx.
- Adapter werden als schlichte Cards/Chips mit aktiv/inaktiv, Richtung, Datentyp und Kurzstatus angezeigt.
- Adapter koennen aktiviert, deaktiviert und ueber Platzhalterdialoge bearbeitet werden.
- Adapterdaten werden aus `object_registry.py` gelesen und ueber `object_adapter_engine.py` als Adapterinstanzen verwaltet.
- Keine Runtime-Anbindung, keine Mapping-Erzeugung, keine V32-Objects-Aenderung und keine bestehenden Mapping-Dateien geaendert.
- Versionsstand auf `33.1.2` gesetzt.

## 33.1.1

- Stabile interne Objekt-UUID fuer Objektmanager V33 ergaenzt.
- `ObjectDefinition` kompatibel um `uuid` und `key` erweitert: `uuid` ist die feste interne ID, `key` der technische lesbare Schluessel, `name` der frei aenderbare Anzeigename.
- `object_registry.py` ergaenzt bestehende V33-Eintraege ohne `uuid`/`key` beim Laden automatisch.
- `/objects_v33` bearbeitet und loescht Objekte nun ueber `uuid`.
- Keine Runtime-Logik, keine V32-Objects-Route und keine bestehenden Mapping-Dateien geaendert.
- Versionsstand auf `33.1.1` gesetzt.

## 33.1.0

- Parallelen Objektmanager V33 gestartet.
- Neuer Blueprint `app/routes/objects_v33.py` mit Route `/objects_v33`.
- Neue Templates unter `templates/objects_v33/` fuer Objektliste und Bearbeitung.
- Erste V33-Oberflaeche mit Suche, Neues Objekt, Bearbeiten und Loeschen ohne Adapterbearbeitung.
- Datenquelle ist die passive `object_registry.py`; bestehender Objektmanager, Runtime, UI, Routen und Mapping-Dateien bleiben unveraendert.
- Versionsstand auf `33.1.0` gesetzt.

## 33.0.3

- Einheitliche passive Adapter-Schnittstelle vorbereitet: `app/services/object_adapter_engine.py`.
- Basisklassen `BaseAdapter`, `MQTTAdapter`, `LoxoneAdapter`, `UDPAdapter`, `KNXAdapter` und `InfluxAdapter` mit `validate()`, `serialize()`, `deserialize()`, `enabled`, `direction` und `datatype` angelegt.
- `app/services/object_registry.py` kann neue Adapterobjekte speichern und laden.
- Keine Kommunikation, keine Runtime-Logik, keine UI, keine Routen und keine bestehenden Mapping-Dateien geaendert.
- Versionsstand auf `33.0.3` gesetzt.

## 33.0.2

- Passive V33-Objekt-Registry vorbereitet: `app/services/object_registry.py`.
- Registry-Funktionen fuer Laden, Speichern, Auflisten, Abrufen, Upsert, Loeschen und Validieren von `ObjectDefinition` vorbereitet.
- Speicherziel fuer spaetere V33-Objekte ist `data/objects_v33.json`; fehlende Datei liefert eine leere Liste.
- Bestehende Objektmanager-Logik, Runtime, UI, Routen, Configs und Mapping-Dateien bleiben unveraendert.
- Versionsstand auf `33.0.2` gesetzt.

## 33.0.1

- Adaptermodell V33 dokumentiert: `docs/OBJECT_ADAPTER_MODEL.md`.
- MQTT-, Loxone-, UDP-, KNX- und Influx-Adapterfelder mit gemeinsamen Feldern `enabled`, `direction`, `datatype`, `readonly` und `writeonly` beschrieben.
- Keine Runtime-Logik, keine UI, keine Routen und keine Config-Dateien geaendert.
- Versionsstand auf `33.0.1` gesetzt.

## 33.0.0

- Start der V33-Entwicklung mit Fokus auf Objektmanager 2.0.
- Neue Planungsdokumentation `docs/OBJECT_MANAGER_V33_PLAN.md` angelegt.
- Neues passives Service-Grundgeruest `app/services/object_model.py` mit `ObjectDefinition`, `ObjectAdapter`, `ObjectFlags` und Validierungshelfern angelegt.
- Bestehende Runtime-Logik, Routen, UI, Config-Dateien und Mapping-Dateien bleiben unveraendert.
- Versionsstand auf `33.0.0` gesetzt.

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
