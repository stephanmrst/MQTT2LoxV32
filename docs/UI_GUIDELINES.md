# MP-Gateway UI Guidelines

## Grundlayout

- Neue Verwaltungsansichten folgen dem Muster: links Uebersicht, rechts Detail.
- Die linke Seite dient zum Suchen, Filtern und Auswaehlen.
- Die rechte Seite enthaelt Bearbeitung, Tabs, Aktionen und Vorschauen.
- Bestehende MP-Gateway-Farben bleiben die Basis: dunkle Flaechen, ruhige Rahmen, klare aktive Zustaende.

## Globale Sidebar

- Die globale MP-Gateway-Sidebar liegt in `templates/shared/sidebar.html`.
- Sidebar-CSS liegt zentral in `static/css/sidebar.css`.
- Header zeigt `MP-Gateway` und `Das Multiprotokoll-Gateway`.
- Der Status zeigt `gestoppt` oder `laeuft` im Sidebar-Kopf.
- Aktive Menuepunkte nutzen einen klaren Hintergrund und den gruenen linken Akzent.
- Menueabstaende, Schriftgroessen, Buttonhoehen und Sidebar-Breite bleiben ueber alle Shell-Seiten gleich.
- Es werden keine Icons in der globalen Sidebar verwendet.
- Sidebar-Eintraege sind in klare Gruppen zu sortieren. Interne MP-Gateway-Seiten stehen in `MP-Gateway`; externe Integrationen stehen in `Externe Dienste`.
- Nach dem Sidebar-Feinschliff 33.2.7a wird in der Sidebar nur `Objektmanager V33` angezeigt; die spaetere Umbenennung in `Objektmanager` erfolgt separat.
- Externe Sidebar-Dienste duerfen keinen internen Fallback-Link verwenden. `InfluxDB` und `Grafana` nutzen externe Config-URLs oder werden deaktiviert angezeigt.
- Neue Seiten sollen schrittweise auf `templates/layout/base.html` und `templates/layout/page_header.html` aufbauen.

## Objektkarten

- Objektkarten zeigen oben links ein Typ-Badge.
- Objektkarten zeigen oben rechts den Aktivstatus.
- Darunter stehen Name und Datentyp/Einheit.
- Jede Objektkarte zeigt immer alle Protokoll-Badges:
  - MQTT
  - Loxone
  - UDP
  - KNX
  - Influx
- Aktive Adapter werden farbig und intensiv dargestellt.
- Inaktive Adapter werden grau und gedimmt dargestellt.
- Das ausgewaehlte Objekt muss durch Rahmen, helleren Hintergrund oder dezenten Glow klar erkennbar sein.

## Protokollfarben

- MQTT: kraeftiges Blau
- Loxone: kraeftiges Gruen
- UDP: kraeftiges Violett
- KNX: kraeftiges Orange
- Influx: Tuerkis/Blau
- Inaktiv: Grau

## Erweiterungen

- Neue Funktionen muessen sich in das Links-Uebersicht/Rechts-Detail-Layout integrieren.
- Neue Protokoll- oder Adapterfunktionen sollen die bestehenden Badge- und Tab-Muster wiederverwenden.
- Vorschauen bleiben als Vorschauen gekennzeichnet und duerfen keine Runtime- oder Mapping-Aenderung ausloesen.
