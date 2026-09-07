# Provisioning- und SD-Karten-Strategie

**Status:** Konzept, noch nicht implementiert.

## 1. Wichtige Unterscheidung

Eine SD-Karte kann in diesem Projekt zwei unterschiedliche Rollen haben:

1. **Systemkarte:** enthält Boot-Partition und Raspberry-Pi-OS-Root-Dateisystem.
2. **Medienkarte:** enthält im Wesentlichen Mediendaten und Playlist.

Das Companion-Programm muss diese Rollen explizit unterscheiden. Das einfache Kopieren von Dateien auf eine sichtbare Boot- oder Datenpartition konfiguriert ein beliebiges vorhandenes Raspberry-Pi-OS nicht automatisch vollständig. Für Bootloader, Root-Dateisystem, Benutzer, grafische Session, Dienste und Pakete braucht es entweder ein vorbereitetes Image, ein bereits installiertes System oder eine laufende SSH-Verbindung.

## 2. Drei praktikable Betriebsmodelle

### Modell A: Vorbereitetes Basis-Image

Ein Raspberry-Pi-OS-Basisimage wird einmalig erstellt und enthält bereits:

- 64-bit Raspberry Pi OS
- benötigte Player-Pakete
- Benutzer und grafische Session
- `systemd`-Service
- Player-Konfiguration
- Medienverzeichnis
- optional Overlay Filesystem

Das Companion-Programm schreibt dieses Image beziehungsweise ein vorbereitetes Layout auf die SD-Karte und kopiert anschließend die ausgewählten Medien.

**Vorteile**

- reproduzierbarer Zielzustand
- komplett offline nach Bereitstellung der Image-Datei
- kein SSH und kein laufender Pi nötig
- geeignet für viele gleichartige Karten

**Nachteile**

- Images sind groß
- Image-Versionen müssen gepflegt werden
- Plattformabhängigkeit beim Schreiben und Mounten
- ein Image-Schreibvorgang ist destruktiv und braucht besonders starke Sicherheitsprüfungen

### Modell B: Bereits installierte Systemkarte

Der Pi-OS-Datenträger wird vorher eingerichtet. Das Companion-Programm mountet die passende Datenpartition und aktualisiert nur:

- Medien
- Playlist/Manifest
- gegebenenfalls Player-Konfiguration

**Vorteile**

- schneller Medienaustausch
- weniger komplex als vollständiges Image-Schreiben
- System bleibt unverändert

**Nachteile**

- die Karte muss bereits korrekt vorbereitet sein
- Mounting und Schreibrechte sind plattformabhängig
- nicht jedes OS-Layout ist automatisch erkennbar
- ein laufendes oder nicht sauber ausgehängtes Root-Dateisystem ist riskant

### Modell C: SSH-Provisioning

Der Pi bootet zunächst ein vorhandenes System. Das Companion-Programm verbindet sich über SSH und richtet Pakete, Dienste und Medien auf dem laufenden Gerät ein.

**Vorteile**

- vollständige OS-Konfiguration möglich
- gute Fehlermeldungen und Rückmeldungen
- kein direktes Schreiben fremder Root-Dateisysteme vom Host aus

**Nachteile**

- benötigt Netzwerk und einen erreichbaren Pi
- widerspricht dem vollständig offline gedachten Karten-Workflow
- Zugangsdaten, Host-Key und Netzwerkfehler müssen behandelt werden

## 3. Empfehlung für die Phasen

### Phase 1: Hardware- und Player-MVP

Manuell oder mit Raspberry Pi Imager:

1. Raspberry Pi OS 64-bit schreiben.
2. Erststart und Display konfigurieren.
3. `mpv` und/oder VLC installieren.
4. Playlist und Service manuell testen.
5. Kühlung, Netzteil und 4K-Quellen prüfen.

### Phase 2: Medien-Workflow

Das Companion-Programm bearbeitet eine bereits vorbereitete Zielstruktur:

```text
<mountpoint>/
├── media/
├── playlist.m3u
└── config/
```

Der Fokus liegt zunächst auf Medienauswahl, Kopieren, Sortierung, Verifikation und sicherem Auswerfen.

### Phase 3: Reproduzierbares Image

Erst wenn der Player stabil ist, wird ein Basisimage automatisiert. Das Image sollte versioniert werden und einen eindeutigen Kompatibilitätsstand des Companion-Programms besitzen.

## 4. Medien- und Playlist-Workflow

1. Benutzer wählt eine oder mehrere Dateien beziehungsweise Verzeichnisse.
2. Das Programm erkennt nur unterstützte Video- und Bilddateien.
3. Dateigröße und freier Zielplatz werden verglichen.
4. Die Reihenfolge wird explizit und reproduzierbar festgelegt, zum Beispiel nach relativem Pfad, case-insensitiv sortiert.
5. Medien werden zunächst in temporäre Dateien im Zielverzeichnis kopiert.
6. Nach erfolgreichem Kopieren und `fsync` werden die Dateien atomar aktiviert.
7. Die Playlist wird als temporäre Datei erstellt, synchronisiert und atomar ersetzt.
8. Die Zielstruktur wird aus der Playlist heraus verifiziert.
9. Erst danach werden alle Schreibvorgänge synchronisiert und der Datenträger ausgeworfen.

Bei einem einzelnen Video bleibt die Playlist bewusst einfach. Zusätzliche Dateien werden nicht automatisch abgespielt, wenn sie nicht in der aktiven Playlist stehen.

## 5. Formatierung auf macOS

Relevante `diskutil`-Schritte:

```text
diskutil list
diskutil info -plist /dev/diskN
diskutil unmountDisk force /dev/diskN
diskutil eraseDisk <FORMAT> <LABEL> GPT /dev/diskN
diskutil eject /dev/diskN
```

Diese Befehle sind eine Ablaufskizze, kein Befehlsskript zum unkritischen Kopieren.

### Sicherheitsanforderungen

Vor `eraseDisk` müssen mindestens geprüft werden:

- das Gerät ist ein vollständiger Datenträger
- der Identifier entspricht dem erwarteten Format
- `Internal` ist nicht wahr
- Größe und Name werden dem Benutzer angezeigt
- der Benutzer bestätigt exakt dieses Gerät
- das Gerät wird unmittelbar vor dem destruktiven Schritt erneut geprüft

Die Implementierung sollte `diskutil info -plist` maschinenlesbar auswerten und die Argumente als Liste an `subprocess.run` übergeben. Shell-Interpolation und frei zusammengesetzte Shell-Kommandos sind zu vermeiden.

### Dateisystementscheidung

- FAT32 ist kompatibel, beschränkt eine einzelne Datei aber auf ungefähr 4 GiB.
- exFAT ist für größere Videodateien naheliegend, muss aber auf der konkreten Pi-OS-Konfiguration getestet werden.
- ext4 ist auf dem Pi gut, aber auf macOS im Standardworkflow unkomfortabel.

Für eine Systemkarte wird nicht einfach eine reine Datenpartition formatiert. Das Partitionslayout des gewählten Images ist maßgeblich.

## 6. Linux-Unterstützung

Unter Linux sollten Geräte über `lsblk --json` erkannt und nicht durch Parsing einer menschenlesbaren Tabelle erraten werden. Je nach Setup kommen für die restlichen Schritte `umount`, `parted`, `sfdisk`, `mkfs.vfat`, `mkfs.ext4` und `udisksctl` in Betracht.

Die Linux- und macOS-Adapter sollten getrennt bleiben. Gleiche fachliche Operationen können eine gemeinsame Schnittstelle haben, die konkrete Befehlsfolge darf aber plattformspezifisch sein.

## 7. Sicheres Auswerfen

Nach dem Kopieren:

1. offene Dateioperationen beenden
2. temporäre Dateien und aktive Playlist prüfen
3. `sync` beziehungsweise die plattformspezifische Synchronisierung ausführen
4. die Zielpartition beziehungsweise den Datenträger aushängen
5. den Datenträger auswerfen oder vom System abmelden
6. erst danach die Karte physisch entfernen

Unter macOS ist `diskutil eject` der vorgesehene Abschluss. Unter Linux hängt der genaue Befehl vom Mount- und Desktop-Setup ab; `udisksctl` ist eine mögliche Desktop-Integration.

## 8. Fehler- und Wiederanlaufverhalten

Das Programm sollte bei einem Fehler:

- die konkrete Quelle und das Ziel nennen
- keine unvollständige Playlist aktivieren
- temporäre Dateien kenntlich hinterlassen oder kontrolliert bereinigen
- den Benutzer nicht zum voreiligen Entfernen auffordern
- vor einem erneuten Versuch den Zielzustand verifizieren

Der Player auf dem Pi sollte auch mit einem fehlenden oder ungültigen Manifest nicht in eine unverständliche Endlosschleife geraten. Ein sichtbarer Fehlerzustand, ein kontrolliertes Warten oder ein Dienstneustart sind mögliche spätere Entscheidungen.

## 9. Offline- und Online-Grenzen

Der reine Wiedergabebetrieb sollte offline funktionieren. Für die Herstellung gibt es dagegen drei unterschiedliche Abhängigkeiten:

- Paket- und Image-Download beim initialen Setup
- direkter Zugriff auf eine gemountete SD-Karte
- Netzwerkzugriff bei SSH-Provisioning

Diese Phasen sollten im UI getrennt angezeigt werden. Besonders wichtig ist, nicht den Eindruck zu erwecken, das Tool könne ein beliebiges ungeändertes Pi-OS allein durch Kopieren auf eine FAT-Bootpartition vollständig in einen Kiosk-Player verwandeln.

## 10. Akzeptanzkriterien für eine spätere Implementierung

- Eine Testkarte wird nicht formatiert, wenn das Gerät intern ist oder nicht eindeutig bestätigt wurde.
- Ein einzelnes Video erscheint nach dem Einschalten automatisch im Vollbild.
- Das Video läuft nach dem Ende wieder von vorne.
- Eine Bildserie wird in stabiler Reihenfolge angezeigt.
- Ein Stromausfall während der Wiedergabe erfordert keine manuelle Reparatur im Normalfall.
- Ein Stromausfall während des Kopierens aktiviert keine halbfertige Playlist.
- Nach dem Kopieren wird die Karte erst nach erfolgreichem Verifizieren zum Entfernen freigegeben.
- Der Prozess startet nach einem unerwarteten Player-Abbruch automatisch neu.
- Die Hardwaredecodierung und die gewünschte 4K-Ausgabe sind auf der realen Zielhardware nachgewiesen.
