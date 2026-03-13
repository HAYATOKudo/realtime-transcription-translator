import queue
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText


class AppUI:
    def __init__(self, title: str):
        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry("1200x760")

        self._queue = queue.Queue()
        self._start_callback = None
        self._stop_callback = None
        self._translate_now_callback = None

        self.status_var = tk.StringVar(value="Stopped")
        self.auto_translate_var = tk.BooleanVar(value=True)

        self._build_layout()
        self.root.after(50, self._drain_queue)

    def _build_layout(self) -> None:
        top = ttk.Frame(self.root, padding=8)
        top.pack(fill="x")

        self.start_button = ttk.Button(top, text="Start", command=self._on_start_clicked)
        self.start_button.pack(side="left", padx=(0, 8))

        self.stop_button = ttk.Button(top, text="Stop", command=self._on_stop_clicked)
        self.stop_button.pack(side="left", padx=(0, 8))

        self.translate_button = ttk.Button(top, text="Translate Now", command=self._on_translate_now_clicked)
        self.translate_button.pack(side="left", padx=(0, 8))

        self.clear_button = ttk.Button(top, text="Clear", command=self.clear_all)
        self.clear_button.pack(side="left", padx=(0, 8))

        self.auto_check = ttk.Checkbutton(
            top,
            text="Auto Translate",
            variable=self.auto_translate_var,
        )
        self.auto_check.pack(side="left", padx=(8, 8))

        ttk.Label(top, textvariable=self.status_var).pack(side="right")

        body = ttk.Frame(self.root, padding=8)
        body.pack(fill="both", expand=True)

        left = ttk.Frame(body)
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))

        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True, padx=(6, 0))

        ttk.Label(left, text="English").pack(anchor="w")
        self.english_box = ScrolledText(left, wrap="word", font=("Yu Gothic UI", 11))
        self.english_box.pack(fill="both", expand=True)

        ttk.Label(right, text="日本語").pack(anchor="w")
        self.japanese_box = ScrolledText(right, wrap="word", font=("Yu Gothic UI", 11))
        self.japanese_box.pack(fill="both", expand=True)

    def set_start_callback(self, callback):
        self._start_callback = callback

    def set_stop_callback(self, callback):
        self._stop_callback = callback

    def set_translate_now_callback(self, callback):
        self._translate_now_callback = callback

    def is_auto_translate_enabled(self) -> bool:
        return bool(self.auto_translate_var.get())

    def append_english(self, text: str) -> None:
        self._queue.put(("append_english", text))

    def append_japanese(self, text: str) -> None:
        self._queue.put(("append_japanese", text))

    def set_status(self, text: str) -> None:
        self._queue.put(("status", text))

    def clear_all(self) -> None:
        self.english_box.delete("1.0", tk.END)
        self.japanese_box.delete("1.0", tk.END)

    def run(self) -> None:
        self.root.mainloop()

    def on_close(self, callback) -> None:
        self.root.protocol("WM_DELETE_WINDOW", callback)

    def _on_start_clicked(self) -> None:
        if self._start_callback:
            self._start_callback()

    def _on_stop_clicked(self) -> None:
        if self._stop_callback:
            self._stop_callback()

    def _on_translate_now_clicked(self) -> None:
        if self._translate_now_callback:
            self._translate_now_callback()

    def _drain_queue(self) -> None:
        while True:
            try:
                kind, payload = self._queue.get_nowait()
            except queue.Empty:
                break

            if kind == "append_english":
                self.english_box.insert(tk.END, payload + "\n\n")
                self.english_box.see(tk.END)
            elif kind == "append_japanese":
                self.japanese_box.insert(tk.END, payload + "\n\n")
                self.japanese_box.see(tk.END)
            elif kind == "status":
                self.status_var.set(payload)

        self.root.after(50, self._drain_queue)