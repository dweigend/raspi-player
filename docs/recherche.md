# Recherche: Raspberry-Pi-5-4K-Media-Player

**Stand der Recherche:** 7. September 2026

Dieses Dokument sammelt die relevanten technischen Grundlagen, Bibliotheken und Betriebssystem-Werkzeuge für das Vorhaben. Die Recherche ist eine Entscheidungsgrundlage; sie stellt noch keine Implementierung dar.

## 1. Anforderungen und Randbedingungen

### Wiedergabe

- Raspberry Pi 5
- 4K-Videoausgabe, möglichst bis 4Kp60
- optional Bilder zwischen oder anstelle von Videos
- lokales Abspielen von der SD-Karte
- Fullscreen ohne Benutzerinteraktion
- bei einem einzelnen Video vorzugsweise Endloswiedergabe
- automatisches Wiederanlaufen nach Prozessfehlern

### Companion-Programm

- läuft auf dem Computer des Betreibers, zunächst naheliegend auf macOS
- einfache Rich-basierte TUI/CLI
- Auswahl und Kopieren von Medien
- Playlist-/Slideshow-Erstellung
- Erkennung und Formatierung von SD-Karten
- sichere Bestätigung vor destruktiven Operationen
- verifiziertes und sicheres Auswerfen

### Robustheit

- keine Abhängigkeit von Internet, DNS, Netzwerkfreigaben oder Cloud-Diensten im Wiedergabebetrieb
- keine laufenden Schreibvorgänge während der Wiedergabe, soweit möglich
- definierter Zustand nach Stromausfall
- keine automatische Formatierung eines falsch ausgewählten Laufwerks

## 2. Raspberry Pi 5 und Betriebssystem

### Hardware

Die offizielle Raspberry-Pi-5-Produktseite nennt unter anderem:

- BCM2712 mit 64-bit Arm Cortex-A76
- VideoCore-VII-GPU
- zwei 4Kp60-HDMI-Ausgänge mit HDR-Unterstützung
- hardwarebeschleunigte HEVC-Decodierung bis 4Kp60

Für dauerhafte 4K-Last ist eine aktive Kühlung einzuplanen. Für einen stabilen Betrieb sollte außerdem das offizielle 27-W-USB-C-Netzteil beziehungsweise eine geeignete 5-V-/5-A-Versorgung verwendet werden. Ein älteres oder unterdimensioniertes Netzteil kann zu Instabilität oder Drosselung führen.

### Raspberry Pi OS

Für den Pi 5 ist ein aktuelles 64-bit Raspberry Pi OS auf Basis von Bookworm oder neuer die naheliegende Ausgangsbasis. Raspberry Pi OS Desktop bringt bereits eine grafische Umgebung und typische Medienwerkzeuge mit. Raspberry Pi OS Lite ist schlanker, erfordert aber eine eigene Display- und Session-Initialisierung.

Seit Bookworm ist Wayland mit `labwc` der relevante Standardpfad. Das ist für die Wahl und Konfiguration eines Players wichtig: Ein Player, der unter X11 funktioniert, muss nicht automatisch mit Wayland und der verwendeten GPU-Ausgabe korrekt zusammenspielen.

Relevante Themen in der offiziellen Dokumentation:

- Boot- und Display-Konfiguration
- `kmsprint` zur Anzeige und Prüfung verfügbarer Displaymodi
- Abschalten von Screen Blanking, beispielsweise über `raspi-config` oder `consoleblank=0`
- Overlay Filesystem für ein schreibgeschütztes Root-Dateisystem
- Pi-5-spezifische Konfiguration in `config.txt`

Das Overlay Filesystem ist für ein Gerät interessant, das nach der Einrichtung kaum noch Systemdaten schreibt. Es schützt die Root-Partition jedoch nicht vor jedem möglichen Hardwaredefekt und sollte erst nach einem funktionierenden Basisaufbau aktiviert werden.

## 3. Player-Bibliotheken und Renderer

### `mpv`

`mpv` ist ein schlanker nativer Media-Player mit guter Automatisierbarkeit. Für das Projekt sind besonders relevant:

- `--fullscreen` für die Vollbildausgabe
- `--loop-playlist=inf` für die Endlosschleife
- `--playlist=<datei>` für eine explizite Reihenfolge
- `--image-display-duration=<sekunden>` für Bilder in einer Slideshow
- Unterstützung für Videos und Bilder in einer gemeinsamen Wiedergabe
- `--hwdec=auto` für einen zunächst automatisch getesteten Hardware-Decoding-Modus
- `--input-ipc-server=<socket>` für lokale Steuerung über JSON IPC
- `--vo=gpu-next` als moderner Videoausgabepfad, der auf dem Zielsystem getestet werden muss

Das JSON-IPC-Interface ist ausdrücklich nicht als sicherer Netzwerkdienst gedacht. Ein IPC-Socket darf nicht ungeschützt über das Netzwerk exponiert werden; wenn er benötigt wird, sollte er auf einen lokalen Unix-Socket beschränkt bleiben.

`mpv` ist für den Hauptfall „eine lokale Videodatei abspielen und wiederholen“ gut geeignet. Es kann auch Bilder anzeigen, sodass für die Slideshow kein separater Python-Renderer erforderlich ist.

**Risiko:** Hardware-Decoding, Wayland-Ausgabe, HDR und konkrete 4K-Dateien müssen auf dem echten Pi 5 validiert werden. `--hwdec=auto` sollte als Ausgangspunkt dienen, nicht als ungeprüfte Garantie.

### VLC

VLC wird in der Raspberry-Pi-OS-Dokumentation als mögliche Lösung beschrieben. Typische Varianten sind:

- `vlc --play-and-exit --fullscreen`
- `cvlc` für eine Wiedergabe ohne grafische Benutzeroberfläche

Auf Raspberry Pi OS Lite kann eine minimale Installation beispielsweise mit `vlc-bin` und `vlc-plugin-base` erfolgen. VLC ist für einen ersten Hardwaretest attraktiv, weil es auf Raspberry Pi OS gut dokumentiert ist und viele Formate unterstützt.

VLC bleibt eine sinnvolle Fallback-Option, insbesondere wenn `mpv` mit der konkreten Wayland-/GPU-Konfiguration Schwierigkeiten macht. Für die endgültige Auswahl sollten dieselben Testdateien und dieselbe Display-Konfiguration verglichen werden.

### Chromium-Kiosk

Chromium kann eine Webanwendung im Kiosk-Modus darstellen, ist aber für diesen Anwendungsfall nicht die bevorzugte erste Lösung:

- Autoplay-Regeln und Browserzustände können die unbeaufsichtigte Wiedergabe stören.
- Hardwarebeschleunigung und 4K-Ausgabe hängen von Browser-, Treiber- und Compositor-Version ab.
- Ein Browser bringt mehr laufende Komponenten und mehr potenzielle Fehlerquellen mit.

Chromium kann später sinnvoll sein, wenn eine interaktive Oberfläche, Overlays oder eine webbasierte Verwaltung benötigt werden. Für einen reinen Player ist ein nativer Renderer einfacher und robuster.

## 4. Autostart und Prozessüberwachung

### `systemd`

Ein Player-Dienst sollte über `systemd` gestartet werden und nicht primär über eine zufällige Shell-Autostartdatei. Relevante Eigenschaften eines Dienstes:

- `Type=exec` für einen normalen lang laufenden Prozess
- `Restart=on-failure` für einen Neustart nach Prozessfehlern
- `RestartSec` zur Vermeidung einer zu schnellen Neustartschleife
- Start nach der grafischen Sitzung beziehungsweise nach der Display-Initialisierung
- ein fester Benutzer, beispielsweise `pi`, statt unnötiger Ausführung als `root`
- explizite Umgebungsvariablen für `XDG_RUNTIME_DIR` und `WAYLAND_DISPLAY`, falls die Session das erfordert

Die grafische Session ist der anspruchsvollste Teil eines systemweiten Dienstes. Ein `systemd`-Service kann zwar zuverlässig den Prozess überwachen, benötigt aber die korrekte Benutzer- und Wayland-Umgebung. Das genaue Setup muss auf dem verwendeten Raspberry Pi OS getestet werden.

### Mögliche Autostart-Varianten

1. Benutzer-Service innerhalb der grafischen Session
2. systemweiter Service mit festem Benutzer und expliziter Session-Umgebung
3. `labwc`-Autostart als sehr einfache, aber weniger umfassende Variante
4. Lite-System mit eigener DRM-/Wayland-Initialisierung

Für den ersten MVP ist ein Desktop-/Wayland-Setup mit einem über `systemd` überwachten Benutzerprozess wahrscheinlich der geringste Integrationsaufwand. Ein späteres Read-only- oder Lite-Setup kann daraus abgeleitet werden.

## 5. Python-Ökosystem für das Companion-Programm

### `uv`

`uv` übernimmt Projektinitialisierung, virtuelle Umgebung, Dependency-Management und Lockfile. Der erwartete Workflow ist:

- Projekt initialisieren
- Laufzeitabhängigkeiten wie `rich` und `typer` hinzufügen
- Entwicklungsabhängigkeiten wie `ruff`, `ty` und `pytest` hinzufügen
- mit `uv lock` reproduzierbar sperren
- mit `uv sync` die Umgebung herstellen
- Werkzeuge über `uv run ...` ausführen

Das Lockfile gehört ins Repository. Die Python-Version muss passend zum Host-Tool gewählt werden; Python 3.12 oder neuer ist für die geplante Codebasis eine vernünftige Zielbasis.

### `Rich`

`Rich` eignet sich für die Darstellung der TUI:

- Tabellen für erkannte Datenträger
- farbige Warnungen vor destruktiven Aktionen
- Prompts und Bestätigungen
- Fortschrittsbalken beim Kopieren
- Statusanzeigen für Prüfung, Mounten und Auswerfen
- strukturierte Fehlerausgaben

Eine zusätzliche TUI-Bibliothek ist für den Start nicht nötig. Eine einfache Kommandozeilenstruktur mit Rich-Ausgaben hält die Anwendung leichter testbar.

### `Typer`

`Typer` basiert auf Python-Type-Hints und eignet sich als CLI-Schicht. Sinnvolle Kommandos sind:

```text
raspi-player disks
raspi-player format
raspi-player prepare
raspi-player verify
raspi-player eject
```

Eine optionale `wizard`- oder `setup`-Funktion kann diese Schritte später in einem interaktiven Ablauf bündeln. Destruktive Aktionen sollten trotzdem eine eigene Bestätigung mit Gerätekennung und Kapazität verlangen.

### `pathlib` und `shutil`

Die Python-Standardbibliothek reicht für die Medienverwaltung weitgehend aus:

- `pathlib` für plattformgerechte Pfade, Scans und relative Pfade
- `shutil.copyfile`/`copytree` für Kopiervorgänge
- `shutil.disk_usage` für eine Größenprüfung vor dem Kopieren
- `tempfile` und `Path.replace()` für atomare temporäre Dateien
- `subprocess.run([...], check=True)` für native Betriebssystemwerkzeuge

`shutil` kopiert nicht automatisch alle möglichen Metadaten, Owner, ACLs oder erweiterten Attribute. Für normale Mediendateien ist das meist unkritisch; Systemdateien sollten damit nicht blind kopiert werden.

### `ruff`

`ruff` übernimmt im Projekt sowohl Linting als auch Formatierung. Eine kleine, konsistente Regelmenge mit pycodestyle-, Pyflakes-, Bugbear-, Import- und modernen Python-Regeln ist als Ausgangspunkt ausreichend.

### `ty`

`ty` ist der schnelle Typechecker aus dem Astral-Ökosystem. Er sollte als Entwicklungsabhängigkeit im Projekt verwaltet und über `uv run ty check` ausgeführt werden. Die Typgrenzen sind besonders für Plattformadapter, `subprocess`-Rückgabewerte und Pfadsicherheitslogik wertvoll.

### `pytest`

Unit-Tests sollten unabhängig von einer echten SD-Karte funktionieren. Wichtige Testszenarien:

- erkannte Medienendungen
- deterministische Sortierung
- Ignorieren nicht unterstützter Dateien
- Verhinderung von Pfaden außerhalb des Medienverzeichnisses
- atomare Manifest-/Playlist-Erstellung
- freie Kartengröße gegenüber geplanter Kopiergröße
- Prüfung unvollständiger oder beschädigter Zielinhalte

## 6. SD-Karten und native Betriebssystemwerkzeuge

Für Partitionierung und Formatierung sind Python-Abstraktionen allein nicht ausreichend. Das Companion-Programm muss vorhandene Systemwerkzeuge kontrolliert aufrufen.

### macOS

Relevante Befehle:

- `diskutil list` – Datenträger anzeigen
- `diskutil info -plist /dev/diskN` – maschinenlesbare Detailinformationen
- `diskutil unmountDisk` – Datenträger vor Operationen aushängen
- `diskutil eraseDisk` – Partitionstabelle und Dateisystem anlegen
- `diskutil eject` – Datenträger sicher auswerfen

Die Anwendung darf keine Shell-Kommandos als zusammengebauten String ausführen. Stattdessen sollten Argumentlisten an `subprocess.run` übergeben werden. Das ausgewählte Gerät muss vor der Formatierung geprüft werden:

- vollständiges Gerät statt einzelner Partition
- erwartete Gerätekennung
- nicht intern verbaut
- vom Benutzer explizit bestätigt
- Anzeige von Modell, Größe und Device-Identifier in der zweiten Bestätigung

### Linux

Relevante Werkzeuge sind unter anderem:

- `lsblk --json` zur strukturierten Geräteerkennung
- `umount` zum Aushängen
- `parted` oder `sfdisk` für Partitionierung
- `mkfs.vfat` oder `mkfs.ext4` für Dateisysteme
- je nach Desktop `udisksctl` für Mounting und Power-off

Die konkrete Linux-Unterstützung sollte als eigener Plattformadapter umgesetzt werden. Ein Befehlspfad darf nicht einfach von macOS übernommen werden.

### Dateisystem

Die Wahl hängt vom Workflow ab:

- FAT32 ist sehr kompatibel, hat aber eine maximale Einzeldateigröße von etwa 4 GiB.
- exFAT erlaubt große Videodateien und ist auf aktuellen Desktop-Systemen gut nutzbar.
- ext4 ist für Linux technisch attraktiv, aber auf macOS ohne Zusatzsoftware unpraktisch.
- Eine Pi-OS-Systemkarte hat typischerweise ohnehin ein eigenes Boot-/Root-Layout und sollte nicht wie eine reine Datenkarte behandelt werden.

Für eine einzelne große 4K-Videodatei ist FAT32 nur dann geeignet, wenn die Datei sicher unterhalb der Einzeldateigrenze bleibt. exFAT oder ein Pi-OS-Image mit separater Datenpartition kann bei größeren Medien sinnvoller sein.

## 7. Datenintegrität und Stromausfälle

Ein harter Stromausfall kann vor allem während des Schreibens die Dateisystemstruktur oder eine gerade kopierte Datei beschädigen. Folgende Maßnahmen reduzieren das Risiko:

1. Medien zunächst in temporäre Dateien kopieren.
2. Daten und Datei-Deskriptor mit `fsync` abschließen.
3. Temporäre Datei per atomarem Rename/`Path.replace()` aktivieren.
4. Playlist oder Manifest erst schreiben, wenn alle Mediendateien vollständig vorhanden sind.
5. Auch die Playlist temporär schreiben, flushen, synchronisieren und atomar ersetzen.
6. Vor dem Auswerfen `sync` ausführen und danach die Partition aushängen.
7. Während der Wiedergabe möglichst keine Dateien verändern.
8. Root-Dateisystem erst nach erfolgreichem Test schreibgeschützt beziehungsweise mit Overlay Filesystem betreiben.

Atomare Ersetzungen schützen nicht vor einem Ausfall während des physischen Kopiervorgangs, verhindern aber, dass die Wiedergabe auf ein teilweise geschriebenes Manifest zeigt. Eine Dateikopie kann bei Ausfall unvollständig bleiben; sie darf erst nach erfolgreichem Abschluss in die aktive Playlist gelangen.

## 8. Quellen

### Primärquellen

- Raspberry Pi 5: <https://www.raspberrypi.com/products/raspberry-pi-5/>
- Raspberry Pi OS: <https://www.raspberrypi.com/documentation/computers/os.html>
- Raspberry-Pi-Konfiguration und Boot-Optionen: <https://www.raspberrypi.com/documentation/computers/configuration.html#boot-options>
- `mpv`-Handbuch: <https://mpv.io/manual/stable/>
- `systemd.service`: <https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html>
- `uv`: <https://docs.astral.sh/uv/>
- Ruff: <https://docs.astral.sh/ruff/>
- ty: <https://docs.astral.sh/ty/>
- Python `pathlib`: <https://docs.python.org/3/library/pathlib.html>
- Python `shutil`: <https://docs.python.org/3/library/shutil.html>
- Rich: <https://rich.readthedocs.io/en/stable/>
- Typer: <https://typer.tiangolo.com/>

## 9. Ergebnis und Priorisierung

### Für den ersten Hardwaretest

- Pi 5 mit aktiver Kühlung
- geeignetes Netzteil
- aktuelles Raspberry Pi OS 64-bit
- lokales Testvideo in einem bekannten Format
- VLC und/oder `mpv`
- Prüfung der tatsächlichen 4K-Ausgabe mit `kmsprint`
- Fullscreen-Start über eine kontrollierte Session

### Für den ersten Companion-MVP

1. Medien scannen und nach relativen Pfaden deterministisch sortieren
2. freien Platz prüfen
3. Medien atomar bzw. über temporäre Dateien kopieren
4. Playlist/Manifest atomar schreiben
5. Zielinhalt verifizieren
6. sicher synchronisieren und auswerfen
7. Formatierung erst danach und nur mit starken Sicherheitsbarrieren

### Bewusste Nicht-Ziele der ersten Phase

- kein Netzwerk-Streaming
- keine Cloud-Synchronisation
- keine Webverwaltung auf dem Pi
- keine automatische Zerstörung eines nicht eindeutig identifizierten Laufwerks
- keine Behauptung, dass simples Kopieren auf eine Boot-Partition ein beliebiges Pi-OS vollständig provisioniert
