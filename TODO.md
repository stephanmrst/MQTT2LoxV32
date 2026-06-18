# TODO

## 32.0.x

- Umbenannte Module im laufenden Betrieb gegenpruefen: Dashboard, MQTT -> Loxone, MQTT -> UDP, MQTT -> KNX und Log-Leerzustand.
- Object-Service im laufenden Betrieb gegenpruefen: Objektliste, Objekt bearbeiten, Mapping-Sync, Mapping-Rebuild und Objekt loeschen.
- Loxone-Service im laufenden Betrieb gegenpruefen: MQTT -> Loxone, Loxone IO-Datalist und Dashboard-Zaehler.
- MQTT-Publish-Hilfen aus dem Legacy-Core in `app/services/mqtt.py` ziehen.
- MQTT-Monitor-Endpunkte schrittweise kapseln, ohne URLs zu aendern.
- Service-Tests fuer MQTT-Brokerliste, Monitor-State und Testverbindung ergaenzen.
- Service-Tests fuer `app/services/udp.py` ergaenzen: Message-Format, Mapping, Presets und UDP-Testsendung.
- Weitere UDP-Routen nur bei Bedarf duenner an den Service anbinden; URLs und Formulare bleiben stabil.

## Spaeter

- Interne Broker-Prozessverwaltung aus dem Legacy-Core herausloesen.
- Runtime-/Bridge-Logik erst nach weiterer Port-Stabilisierung modularisieren.
- Objektmanager nur nach ausdruecklicher Freigabe umbauen.
