"""Provide a small native card/video/start window; workers never touch Tk widgets."""

import os
import queue
import sys
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from raspi_player.devices import list_devices
from raspi_player.models import Device, WriteRequest
from raspi_player.settings import offline_directory
from raspi_player.workflow import create_card


class PlayerWindow:
    """Own selection widgets and marshal worker status onto the UI thread."""

    def __init__(self, root: tk.Tk, assets: Path) -> None:
        self.root, self.assets = root, assets
        self.devices: list[Device] = []
        self.video = tk.StringVar()
        self.status = tk.StringVar(value="Choose an SD card and a video.")
        self.events: queue.Queue[tuple[str, str]] = queue.Queue()
        self.scan_results: queue.Queue[list[Device] | Exception] = queue.Queue()
        self.scanning = False
        self.busy = False
        root.title("Raspi Player")
        root.geometry("660x370")
        root.minsize(560, 370)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.build_widgets()
        root.after(100, self.poll)
        self.refresh()

    def build_widgets(self) -> None:
        frame = ttk.Frame(self.root, padding=24)
        frame.pack(fill="both", expand=True)
        ttk.Label(
            frame, text="Create a Raspberry Pi video player", font=("", 17, "bold")
        ).pack(anchor="w")
        ttk.Label(frame, text="Offline · Raspberry Pi 5 · One video on repeat").pack(
            anchor="w", pady=(4, 18)
        )
        self.card = ttk.Combobox(frame, state="readonly")
        self.card.pack(fill="x")
        self.refresh_button = ttk.Button(
            frame, text="Refresh cards", command=self.refresh
        )
        self.refresh_button.pack(anchor="e", pady=6)
        self.video_button = ttk.Button(
            frame, text="Choose video…", command=self.choose_video
        )
        self.video_button.pack(anchor="w")
        ttk.Label(frame, textvariable=self.video, wraplength=590).pack(
            anchor="w", pady=6
        )
        self.start_button = ttk.Button(frame, text="Create card…", command=self.start)
        self.start_button.pack(anchor="w", pady=12)
        self.progress = ttk.Progressbar(frame, mode="indeterminate")
        self.progress.pack(fill="x")
        ttk.Label(frame, textvariable=self.status, wraplength=590).pack(
            anchor="w", pady=10
        )

    def refresh(self) -> None:
        """Query native devices off-thread so a slow reader cannot freeze startup."""
        if self.busy or self.scanning:
            return
        self.devices = []
        self.card.configure(values=())
        self.card.set("")
        self.set_scanning(True)
        self.status.set("Looking for SD cards…")
        threading.Thread(target=self.scan_cards, daemon=True).start()

    def set_scanning(self, scanning: bool) -> None:
        self.scanning = scanning
        self.card.configure(state="disabled" if scanning else "readonly")
        for button in (self.refresh_button, self.start_button):
            button.configure(state="disabled" if scanning else "normal")

    def scan_cards(self) -> None:
        """Return read-only discovery results without accessing any Tk objects."""
        try:
            self.scan_results.put(list_devices())
        except Exception as error:
            self.scan_results.put(error)

    def finish_scan(self, result: list[Device] | Exception) -> None:
        """Apply discovery on the UI thread; never preselect a destructive target."""
        self.set_scanning(False)
        if isinstance(result, Exception):
            self.status.set(f"Could not read SD cards: {result}")
            return
        self.devices = result
        self.card.configure(values=[device.label for device in result])
        self.status.set(
            "Choose a card."
            if result
            else "No writable SD card found. Insert a card and refresh."
        )

    def choose_video(self) -> None:
        filename = filedialog.askopenfilename(
            title="Choose a video",
            filetypes=[
                ("Video files", "*.mp4 *.mkv *.mov *.m4v *.webm *.avi *.ts"),
                ("All files", "*"),
            ],
        )
        if filename:
            self.video.set(filename)

    def start(self) -> None:
        if self.busy or self.scanning:
            return
        index = self.card.current()
        if index < 0 or index >= len(self.devices) or not self.video.get():
            messagebox.showerror(
                "Select inputs", "Choose an SD card and a video first."
            )
            return
        device = self.devices[index]
        if not messagebox.askyesno(
            "Erase selected SD card?",
            (
                f"ALL DATA on this card will be erased:\n\n{device.label}\n\n"
                f"Video: {Path(self.video.get()).name}\n\nCreate the player card?"
            ),
            default=messagebox.NO,
        ):
            return
        request = WriteRequest(
            device, Path(self.video.get()), self.assets, Path(tempfile.gettempdir())
        )
        self.set_busy(True)
        threading.Thread(target=self.work, args=(request,), daemon=False).start()

    def work(self, request: WriteRequest) -> None:
        try:
            create_card(request, lambda text: self.events.put(("progress", text)))
        except Exception as error:
            self.events.put(("error", str(error)))
        else:
            self.events.put(
                ("done", "Ready. Insert the card into your Pi 5 and power it on.")
            )

    def set_busy(self, busy: bool) -> None:
        self.busy = busy
        for button in (self.start_button, self.refresh_button, self.video_button):
            button.configure(state="disabled" if busy else "normal")
        self.card.configure(state="disabled" if busy else "readonly")
        self.progress.start() if busy else self.progress.stop()

    def poll(self) -> None:
        if not self.scan_results.empty():
            self.finish_scan(self.scan_results.get_nowait())
        while not self.events.empty():
            kind, text = self.events.get_nowait()
            self.status.set(text)
            if kind in ("error", "done"):
                self.set_busy(False)
                self.card.set("")
                if kind == "error":
                    messagebox.showerror("Card creation failed", text)
        self.root.after(100, self.poll)

    def close(self) -> None:
        if self.busy:
            messagebox.showinfo(
                "Card creation in progress",
                "Wait until writing and verification have finished.",
            )
            return
        self.root.destroy()


def launch(assets: Path | None = None) -> None:
    """Launch the native UI with the distribution's offline assets."""
    root = create_root()
    PlayerWindow(root, assets or offline_directory())
    root.mainloop()


def create_root() -> tk.Tk:
    """Locate uv's bundled Tcl/Tk scripts when running from a virtual environment."""
    for variable, name in (("TCL_LIBRARY", "tcl"), ("TK_LIBRARY", "tk")):
        version = tk.TclVersion if name == "tcl" else tk.TkVersion
        directory = Path(sys.base_prefix) / "lib" / f"{name}{version}"
        if directory.is_dir():
            os.environ.setdefault(variable, str(directory))
    return tk.Tk()
