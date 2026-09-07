# Technologie- und Entscheidungsübersicht

Dieses Dokument fasst die Recherche als kompakte Entscheidungsvorlage zusammen. Es enthält keine Implementierung.

## Kandidatenvergleich

| Bereich | Kandidat | Einschätzung für den MVP | Begründung |
|---|---|---|---|
| Betriebssystem | Raspberry Pi OS 64-bit | empfohlen | Offizieller, naheliegender Pi-5-Pfad; gute Hardware- und Displayintegration |
| nativer Player | `mpv` | bevorzugter Kandidat | Videos und Bilder, Playlists, IPC, gute Automatisierbarkeit |
| nativer Player | VLC/`cvlc` | Fallback/Testalternative | auf Raspberry Pi OS dokumentiert, breites Formatangebot |
| Browser-Kiosk | Chromium | später möglich | sinnvoll für UI, aber mehr Autoplay-, Browser- und GPU-Komplexität |
| Autostart | `systemd` | empfohlen | Neustarts, Status und Abhängigkeiten nachvollziehbar steuerbar |
| Host-CLI | Typer | empfohlen | typisierte Kommandos und klare CLI-Struktur |
| Host-Ausgabe | Rich | empfohlen | Tabellen, Prompts, Fortschritt und verständliche Warnungen |
| Pfade/Kopieren | `pathlib`, `shutil` | empfohlen | Standardbibliothek reicht für Medienoperationen weitgehend aus |
| Formatierung | `diskutil`/`lsblk`/`mkfs` | erforderlich | native OS-Werkzeuge statt unsicherer Python-Abstraktion |
| Projektmanagement | `uv` | empfohlen | Umgebung, Abhängigkeiten und Lockfile in einem Workflow |
| Lint/Format | `ruff` | empfohlen | ein schnelles Werkzeug für Stil und häufige Fehler |
| Typechecking | `ty` | empfohlen | passt zum Astral-Tooling und stärkt Plattform-/Pfadcode |
| Tests | `pytest` | empfohlen | isolierte Tests ohne physische SD-Karte möglich |

## Empfohlene Abhängigkeiten

### Laufzeit

- `rich`
- `typer`

### Entwicklung

- `ruff`
- `ty`
- `pytest`

`pydantic` ist für den ersten Funktionsumfang nicht zwingend erforderlich. Es kann später sinnvoll werden, wenn mehrere Konfigurationsdateien, Versionen oder validierte Player-Profile eingeführt werden.

## Empfohlene CLI-Struktur

```text
raspi-player disks
raspi-player format --device /dev/diskN
raspi-player prepare --target <mountpoint> <datei-oder-verzeichnis> ...
raspi-player verify --target <mountpoint>
raspi-player eject --device /dev/diskN
```

Eine interaktive Rich-Oberfläche kann diese Kommandos als Wizard zusammenführen. Die fachlichen Operationen sollten trotzdem als getrennte, testbare Funktionen bestehen bleiben.

## Empfohlene Repository-Struktur

```text
README.md
docs/
├── recherche.md
├── architektur.md
├── entscheidungen.md
└── provisioning.md
src/
└── raspi_player/
    └── (aktuell nur minimales Scaffold)
tests/
deploy/
├── mpv/
├── systemd/
└── vlc/
```

Die Struktur ist als Zielstruktur dokumentiert. Die Quellcode- und Deploy-Verzeichnisse sind noch nicht implementiert.

## Risiken mit hoher Priorität

### 1. Falsches Laufwerk formatieren

**Risiko:** Datenverlust auf der internen Festplatte.

**Gegenmaßnahmen:** strukturierte Geräteerkennung, interne Datenträger blockieren, vollständigen Identifier und Größe anzeigen, doppelte Bestätigung, kein Standardgerät.

### 2. 4K-Decoding funktioniert nicht wie erwartet

**Risiko:** Ruckeln, hohe CPU-Last, schwarzes Bild oder thermische Drosselung.

**Gegenmaßnahmen:** echte Testdateien verwenden, Hardwaredecoding prüfen, Temperatur messen, aktive Kühlung und ausreichendes Netzteil einsetzen, `mpv` und VLC vergleichen.

### 3. Wayland-Session ist beim Playerstart nicht bereit

**Risiko:** Service läuft, aber es erscheint kein Bild.

**Gegenmaßnahmen:** Session-Abhängigkeiten testen, korrekte Benutzer- und Wayland-Umgebung setzen, gegebenenfalls User-Service statt systemweitem Service einsetzen.

### 4. Stromausfall während des Karten-Updates

**Risiko:** unvollständige Datei oder defekte Playlist.

**Gegenmaßnahmen:** temporäre Dateien, `fsync`, atomarer Rename, Playlist erst nach fertigen Medien aktivieren, anschließende Verifikation.

### 5. Zu große Videodatei für FAT32

**Risiko:** Kopieren schlägt trotz ausreichendem Gesamtspeicher fehl.

**Gegenmaßnahmen:** Einzeldateigröße prüfen, exFAT oder ein anderes Layout wählen.

## Nicht-technische Betriebsannahmen

- Die Karte wird nach der Einrichtung nicht regelmäßig beschrieben.
- Die Mediendaten liegen lokal vor.
- Der Pi benötigt im Normalbetrieb kein Netzwerk.
- Das Gerät soll nach dem Einstecken der Stromversorgung selbstständig starten.
- Medien werden bevorzugt offline und vor dem Einsatz vollständig geprüft.
