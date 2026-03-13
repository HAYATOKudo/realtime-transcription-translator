import re
import threading
from concurrent.futures import ThreadPoolExecutor

from config import load_config
from realtime_client import RealtimeTranscriptionClient
from translator import Translator
from ui import AppUI


SENTENCE_RE = re.compile(r'(.+?[.!?。！？]+(?:["\')\]]+)?)', re.DOTALL)


class TranslationCoordinator:
    def __init__(self, ui: AppUI, translator: Translator):
        self.ui = ui
        self.translator = translator
        self.lock = threading.Lock()
        self.pending_text = ""
        # 翻訳スレッドは最大2並列に制限
        self._executor = ThreadPoolExecutor(max_workers=2)

    def add_transcript(self, text: str) -> None:
        cleaned = self._normalize_join(text)
        if not cleaned:
            self.ui.set_status("Listening...")
            return

        ready_text = ""

        with self.lock:
            self.pending_text = self._join_text(self.pending_text, cleaned)

            if self.ui.is_auto_translate_enabled():
                ready_text, rest = self._extract_ready_text(self.pending_text)
                self.pending_text = rest

        if ready_text:
            self._translate_async(ready_text)
        else:
            self.ui.set_status("Listening... (buffering)")

    def translate_now(self) -> None:
        flush_text = ""

        with self.lock:
            flush_text = self.pending_text.strip()
            self.pending_text = ""

        if not flush_text:
            self.ui.set_status("Nothing to translate")
            return

        self._translate_async(flush_text)

    def _translate_async(self, text: str) -> None:
        self.ui.set_status("Translating...")

        def work():
            try:
                english, japanese = self.translator.translate_pair(text)
                self.ui.append_english(english)
                self.ui.append_japanese(japanese)
                self.ui.set_status("Listening...")
            except Exception as e:
                self.ui.set_status(f"Translate error: {e}")

        self._executor.submit(work)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False)

    @staticmethod
    def _normalize_join(text: str) -> str:
        return " ".join(text.strip().split())

    @staticmethod
    def _join_text(current: str, new_text: str) -> str:
        if not current:
            return new_text
        return f"{current} {new_text}".strip()

    def _extract_ready_text(self, text: str):
        matches = list(SENTENCE_RE.finditer(text))
        if not matches:
            return "", text

        last_end = matches[-1].end()
        ready = text[:last_end].strip()
        rest = text[last_end:].strip()
        return ready, rest


def main() -> None:
    config = load_config()

    ui = AppUI(config.app_title)
    translator = Translator(config)
    client = RealtimeTranscriptionClient(config)
    coordinator = TranslationCoordinator(ui, translator)

    client.set_status_callback(ui.set_status)
    client.set_final_transcript_callback(coordinator.add_transcript)

    def start_app():
        client.start()

    def stop_app():
        client.stop()

    def translate_now():
        coordinator.translate_now()

    def on_close():
        client.stop()
        coordinator.shutdown()
        ui.root.destroy()

    ui.set_start_callback(start_app)
    ui.set_stop_callback(stop_app)
    ui.set_translate_now_callback(translate_now)
    ui.on_close(on_close)
    ui.run()


if __name__ == "__main__":
    main()