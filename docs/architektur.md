# Architekturvorschlag

**Status:** Entwurf, noch nicht implementiert.

## 1. Komponenten

```text
Computer
┌──────────────────────────────────────────────────────────────┐
│ Companion-Programm                                           │
│ Rich/Typer                                                   │
│  ├─ Datenträger-Erkennung                                    │
│  ├─ Sicherheitsprüfung und Formatierung                      │
│  ├─ Medienauswahl und Größenprüfung                          │
│  ├─ Kopier- und Verifikationsworkflow                        │
│  └─ Playlist-/Manifest-Erzeugung                             │
└──────────────────────┬───────────────────────────────────────┘
                       │ SD-Karte / Image / optional SSH
                       ▼
Raspberry Pi 5
┌──────────────────────────────────────────────────────────────┐
│ Raspberry Pi OS 64-bit                                      │
│  └─ grafische Wayland-Session / labwc                        │
│      └─ systemd-überwachter nativer Media-Player             │
│          ├─ mpv (bevorzugter MVP-Kandidat)                   │
│          └─ VLC (Fallback/Testalternative)                   │
│                                                              │
│ lokale Medien + Playlist/Manifest                            │
└──────────────────────────────────────────────────────────────┘
```

## 2. Wiedergabemodell

Die Wiedergabe soll vollständig lokal funktionieren. Der Player erhält eine vorbereitete Playlist oder ein Manifest, das auf Dateien innerhalb des Medienverzeichnisses zeigt.

Beispiel für die Zielstruktur:

```text
media/
├── video.mp4
├── 001.jpg
└── 002.jpg
playlist.m3u
player/
config/
```

Der häufigste Fall ist eine einzelne Videodatei:

```text
media/
└── film.mp4
playlist.m3u
```

Die Playlist wird mit Endlosschleife abgespielt. Wenn Bilder enthalten sind, übernimmt `mpv` deren Anzeigedauer über seine Bildkonfiguration. Dadurch bleibt die Logik auf dem Pi klein und es muss kein eigener Python-Renderer dauerhaft laufen.

## 3. Warum ein nativer Player statt Browser

Der Anwendungsfall benötigt zunächst keine Navigation, keine interaktive Webseite und keine Netzwerkdaten. Ein nativer Player hat daher weniger bewegliche Teile:

- keine Browser-Autoplay-Policy
- kein Web-Frontend als zusätzlicher Prozess
- keine JavaScript-Runtime für die Kernfunktion
- direkterer Zugriff auf Hardware-Decoding und Videoausgabe
- einfache Prozessüberwachung mit `systemd`

Ein Chromium-Kiosk bleibt eine mögliche spätere Option für interaktive Menüs oder Statusanzeigen. Er ist nicht der bevorzugte Renderer für die erste robuste 4K-Wiedergabe.

## 4. Prozess- und Session-Modell

Der Player soll als lang laufender Dienst ausgeführt werden:

- `Type=exec`
- fester nicht privilegierter Benutzer, typischerweise `pi`
- `Restart=on-failure`
- kurze, aber nicht hektische Restart-Verzögerung
- Start nach verfügbarer grafischer Session
- explizite Wayland-Umgebung, falls vom gewählten Setup benötigt

Wichtig: Ein systemweiter Dienst und eine grafische Wayland-Session sind nicht automatisch kompatibel. `WAYLAND_DISPLAY`, `XDG_RUNTIME_DIR`, Benutzerrechte und der Session-Start müssen auf dem realen Pi geprüft werden. Ein Benutzer-Service innerhalb der grafischen Session kann für den MVP einfacher sein als ein Root-Service mit künstlich gesetzter Umgebung.

## 5. Zustandsmodell des Companion-Workflows

Der Kopierworkflow sollte klar getrennte Zustände haben:

```text
Ausgewählt
   │
   ▼
Geprüft: Gerät, Kapazität, Dateitypen
   │
   ▼
Kopierplan erstellt
   │
   ▼
Medien in temporäre Zieldateien kopiert
   │
   ▼
Dateien synchronisiert und aktiviert
   │
   ▼
Playlist/Manifest atomar ersetzt
   │
   ▼
Ziel verifiziert
   │
   ▼
Dateisystem synchronisiert und Karte ausgeworfen
```

Ein Fehler vor dem atomaren Playlist-Ersatz darf die bisherige aktive Playlist nicht zerstören. Temporäre Dateien können bei einem späteren Lauf erkannt und entfernt werden, sofern sie nicht Teil der aktiven Playlist sind.

## 6. Pfad- und Playlistregeln

- Alle Dateien werden aus einem definierten Medienwurzelverzeichnis relativ referenziert.
- `Path.rglob()`-Ergebnisse werden explizit sortiert; Dateisystem-Reihenfolgen sind nicht ausreichend deterministisch.
- Nur unterstützte Video- und Bildendungen werden übernommen.
- Absolute Playlist-Einträge werden nicht verwendet.
- Ein Playlist-Eintrag darf nicht über `..` aus dem Zielverzeichnis herausführen.
- Symlinks sollten für den ersten MVP entweder ignoriert oder streng auf Ziele innerhalb des Medienverzeichnisses begrenzt werden.
- Kollisionen nach case-insensitivem Vergleich sollten gemeldet werden, da unterschiedliche Dateisysteme Groß-/Kleinschreibung unterschiedlich behandeln können.

## 7. Atomare Dateien und Stromausfallverhalten

### Medien

Eine Mediendatei wird zunächst unter einem temporären Namen im selben Zielverzeichnis geschrieben. Nach erfolgreichem Kopieren, Flush und `fsync` wird sie per Rename/`Path.replace()` auf den endgültigen Namen gesetzt. Das verhindert, dass der Player eine Datei mit dem finalen Namen sieht, während sie noch geschrieben wird.

### Playlist/Manifest

Die Playlist wird in einer temporären Datei im selben Verzeichnis geschrieben, synchronisiert und anschließend atomar ersetzt. Erst wenn die komplette Kopierphase erfolgreich ist, darf diese Datei die aktive Playlist werden.

### Grenzen

Atomare Ersetzungen sind keine Transaktionsdatenbank. Bei Stromverlust können trotzdem folgende Zustände entstehen:

- eine einzelne temporäre Datei bleibt liegen
- die zuletzt kopierte Mediendatei fehlt
- die alte Playlist ist noch aktiv
- ein Dateisystem muss repariert werden

Der Player sollte daher mit einer fehlenden oder ungültigen Playlist kontrolliert umgehen. Der Companion sollte beim nächsten Lauf temporäre Dateien erkennen und die Zielstruktur verifizieren.

## 8. SD-Karten-Sicherheitsmodell

Formatieren ist die gefährlichste Funktion des Companion-Programms. Der Ablauf sollte mindestens zwei Barrieren enthalten:

1. Geräteauswahl aus einer strukturierten Liste mit Device-Identifier, Modell, Größe und intern/extern-Status.
2. Zweite Bestätigung, die genau diese Informationen nochmals zeigt.

Zusätzlich:

- niemals standardmäßig das erste gefundene Gerät auswählen
- keine interne Festplatte zulassen
- für macOS nur ein vollständiges `/dev/diskN` akzeptieren, nicht blind eine Partition
- native Befehle als Argumentlisten aufrufen, nie als Shell-String
- Formatierung nur nach explizitem `--yes` oder interaktiver Bestätigung
- nach dem Formatieren neu einlesen und das erwartete Layout prüfen

## 9. Konfigurationsgrenzen

Konfigurationen sollten die veränderlichen Werte vom Code trennen:

- Medienwurzel beziehungsweise Playlist-Pfad
- Bildanzeigedauer
- Ausgabegerät oder Displaymodus
- Player-Argumente
- optional IPC-Socket
- Verhalten bei leerer Playlist

Der IPC-Socket von `mpv` darf nur lokal erreichbar sein. Es gibt keinen Grund, ihn für den Kernfall über das Netzwerk freizugeben.

## 10. Teststrategie

### Hostseitige Unit-Tests

Ohne Pi und SD-Karte testbar:

- Medienerkennung
- Sortierung und Playlist-Reihenfolge
- Pfadvalidierung
- Kollisionserkennung
- atomare Dateischreibvorgänge
- Größenberechnung und freier Platz
- Verifikation einer Zielstruktur

### Hardwaretests

Auf dem Pi erforderlich:

- 4Kp24, 4Kp30 und 4Kp60, soweit die Quelldateien verfügbar sind
- HEVC und typische H.264-Dateien
- lange Wiedergabe über mehrere Stunden
- Neustart nach Prozessabbruch
- Verhalten bei fehlender Playlist
- HDMI-Handshake nach Stromverlust
- Screen Blanking und Display-Wakeup
- Temperatur, Drosselung und Netzteilstabilität
- Wayland-Ausgabe und tatsächliches Hardware-Decoding

### Ausfalltests

- Stromverlust während des Kopierens
- Stromverlust nach Kopieren, aber vor Playlist-Aktivierung
- Stromverlust während der Wiedergabe
- Entfernen einer Datei aus dem Medienverzeichnis
- defekte oder nicht unterstützte Mediendatei
- Karte mit zu wenig freiem Speicher

## 11. Offene Architekturentscheidungen

1. Wird ein vollständiges Pi-OS-Image geschrieben oder eine vorhandene Systemkarte aktualisiert?
2. Wird `mpv` oder VLC der Standard?
3. Ist die Medienkarte eine reine Datenkarte oder Teil eines Pi-OS-Partitionslayouts?
4. Ist exFAT wegen großer Videos erforderlich?
5. Wird das Companion-Programm nur auf macOS oder auch auf Linux unterstützt?
6. Soll ein einzelnes Video bei Fehler übersprungen werden oder den Dienst neu starten?
7. Welche Bildreihenfolge und welche Slideshow-Dauer gelten als Standard?
8. Soll das System ein Read-only-Root mit Overlay Filesystem erhalten?
