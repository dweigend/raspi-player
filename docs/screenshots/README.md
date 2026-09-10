# Screenshot provenance

The original PNGs were captured from the actual Tk/macOS UI with Computer Use.
The start window comes from the PyInstaller app. The selection window uses
`uv run python scripts/preview_gui.py`, which supplies an example card and blocks
all card writing. These images are documentation, not hardware-test evidence.

The annotated versions were edited with the built-in Image Gen tool on
2026-09-10. Original UI labels and the targeted controls were visually compared
with the captures. Image editing may resample the screenshot; originals are retained.

## Start window

- Input: `start-original.png`
- Output: `start-annotated.png`

```text
Use case: precise-object-edit. Asset type: annotated screenshot for a German beginner README. Input image is the EDIT TARGET: the actual Raspi Player macOS app start window. Keep the entire original screenshot, dimensions ratio 660x398, all controls, text, positions and colors unchanged. Do not redesign or invent controls. Add only orange annotation overlays matching an instructional screenshot: (1) a thin bright orange oval around the 'Refresh cards' button at x=510..635 y=160..182, with an arrow pointing to it from the empty center area around x=360 y=230 and the label 'Kartenliste aktualisieren' in clean white lettering near x=255 y=245; (2) a thin bright orange oval around the bottom-left status text 'Choose a card.' at x=25..140 y=338, with a short left-pointing orange arrow from x=360 y=350 and label 'Status der App' around x=400 y=350. Keep all existing UI text including Choose video..., Create card..., and title exactly unchanged, unobscured and readable. Keep full window border, title bar, empty card dropdown and progress bar visible. No extra text besides the two specified labels. Output one high-resolution annotated screenshot with the same original aspect ratio. Use clean sparse annotations.
```

## Example selection

- Input: `selection-original.png`
- Output: `selection-annotated.png`

```text
Use case: precise-object-edit. Asset type: annotated screenshot for a beginner German README. Input image is the EDIT TARGET, an actual Raspi Player macOS window. Preserve the full screenshot and ALL original UI text, layout, colors, controls and example values exactly. Do not redesign, translate, add controls, invent icons or remove anything. Add only crisp bright orange annotation overlays: thin oval around the full SD card dropdown at y=138, thin oval around Choose video button at y=205, thin oval around Create card button at y=277. Add short orange arrows from the unused RIGHT HALF of the window pointing to those three controls. Put small white or pale orange numbered German labels in the unused right-side space: '1 Karte auswählen' around x=390 y=195; '2 Video wählen' around x=390 y=240; '3 Karte erstellen' around x=390 y=285. The arrow to the card dropdown should point upward without covering the Refresh cards button or text. Keep every original text legible, including example card info and example video path. Keep full window border and title bar visible; no cropping. Output a single high-resolution annotated screenshot, same aspect ratio as the original 660x398.
```

