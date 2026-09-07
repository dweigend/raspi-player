# Raspi Player

Konzept- und Recherchebasis für einen robusten 4K-Media-Player auf einem Raspberry Pi 5.

> **Status:** Recherche und Architekturplanung. Es gibt lediglich ein minimales Projekt-Scaffold; die Player- und Companion-Funktionalität ist noch nicht implementiert.

## Ziel

Der Raspberry Pi soll nach dem Einschalten ohne Benutzerinteraktion Medien lokal von einer SD-Karte abspielen:

- Start direkt in einen Fullscreen-/Kiosk-Modus
- Wiedergabe von 4K-Videos und optional Bildern
- bevorzugter Hauptfall: eine Videodatei pro Karte
- keine Netzwerkverbindung und keine Cloud-Abhängigkeit während der Wiedergabe
- automatischer Neustart des Players nach einem Prozessfehler
- möglichst unempfindlich gegenüber Stromausfällen und harten Neustarts

Ein Companion-Programm auf dem Computer soll später:

- SD-Karten erkennen und mit Sicherheitsabfragen formatieren
- ein Raspberry-Pi-System vorbereiten
- Medien auswählen und auf die Karte kopieren
- daraus eine deterministische Playlist bzw. Slideshow erzeugen
- die Karte sicher abschließen und auswerfen

## Dokumentation

- [`docs/recherche.md`](docs/recherche.md) – Quellen, Bibliotheken und technische Erkenntnisse
- [`docs/architektur.md`](docs/architektur.md) – vorgeschlagener Aufbau und Designentscheidungen
- [`docs/provisioning.md`](docs/provisioning.md) – SD-Karten-, Image- und Provisioning-Strategien

## Vorläufige Empfehlung

Für einen ersten Hardware-MVP bietet sich folgende Basis an:

1. Raspberry Pi OS 64-bit auf Raspberry Pi 5
2. native Wiedergabe mit `mpv` oder alternativ VLC statt eines Browser-Kiosks
3. `systemd` als Prozess- und Autostart-Manager
4. lokale Medien auf der Karte
5. ein Manifest oder eine Playlist, die erst nach vollständig abgeschlossenen Kopiervorgängen atomar aktiviert wird
6. aktive Kühlung und ein geeignetes 27-W-USB-C-Netzteil

Die Wahl zwischen `mpv` und VLC sollte auf der tatsächlich verwendeten Raspberry-Pi-OS-, Wayland- und Treiberkombination mit den eigenen 4K-Dateien getestet werden.

## Noch nicht festgelegt

- verwendetes Basis-Image und genaue Raspberry-Pi-OS-Version
- `mpv` oder VLC als endgültiger Renderer
- Dateisystem und Partitionslayout der Medienkarte
- Dauer der Bildanzeige in der Slideshow
- gewünschtes Verhalten bei defekten oder nicht unterstützten Medien
- ob das Companion-Programm zuerst macOS, Linux oder beide Hostsysteme unterstützt
- ob Offline-Provisioning, Image-Erstellung oder SSH-Provisioning der primäre Workflow wird
