import asyncio
import base64
import json
import os
import threading
import wave
from datetime import datetime
from typing import Callable, Optional

import numpy as np
import sounddevice as sd
import websockets

from config import AppConfig


class RealtimeTranscriptionClient:
    def __init__(self, config: AppConfig):
        self.config = config
        self.ws = None
        self.loop = None
        self.thread = None
        self.running = False

        self.on_final_transcript: Optional[Callable[[str], None]] = None
        self.on_status: Optional[Callable[[str], None]] = None

        self._audio_stream = None
        self._audio_queue: Optional[asyncio.Queue] = None
        self._recv_task = None
        self._send_task = None

        self._wav_file = None
        self._wav_path = None
        self._wav_lock = threading.Lock()

    def set_final_transcript_callback(self, callback: Callable[[str], None]) -> None:
        self.on_final_transcript = callback

    def set_status_callback(self, callback: Callable[[str], None]) -> None:
        self.on_status = callback

    def start(self) -> None:
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        if not self.running:
            return

        self.running = False

        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self._shutdown(), self.loop)

    def _run_loop(self) -> None:
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._main())

    async def _main(self) -> None:
        url = f"wss://api.openai.com/v1/realtime?model={self.config.realtime_model}"

        headers = {
            "Authorization": f"Bearer {self.config.openai_api_key}",
            "OpenAI-Beta": "realtime=v1",
        }

        self._set_status("Connecting...")

        try:
            async with websockets.connect(
                url,
                additional_headers=headers,
                max_size=20 * 1024 * 1024,
                ping_interval=20,
                ping_timeout=20,
            ) as ws:
                self.ws = ws
                self._audio_queue = asyncio.Queue()

                await self._send_session_update()
                self._set_status("Connected")

                self._start_microphone()

                self._recv_task = asyncio.create_task(self._receive_loop())
                self._send_task = asyncio.create_task(self._send_audio_loop())

                done, pending = await asyncio.wait(
                    [self._recv_task, self._send_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )

                for task in pending:
                    task.cancel()

                for task in done:
                    try:
                        exc = task.exception()
                        if exc:
                            self._set_status(f"Error: {exc}")
                    except asyncio.CancelledError:
                        pass

        except Exception as e:
            self._set_status(f"Error: {e}")
        finally:
            await self._shutdown()
            self._set_status("Stopped")

    async def _shutdown(self) -> None:
        self._stop_microphone()

        # 番兵値を入れて _send_audio_loop のブロックを解除する
        if self._audio_queue is not None:
            try:
                self._audio_queue.put_nowait(None)
            except Exception:
                pass

        if self.ws is not None:
            try:
                await self.ws.close()
            except Exception:
                pass
            self.ws = None

        self._close_raw_audio_file()

    async def _send_session_update(self) -> None:
        event = {
            "type": "session.update",
            "session": {
                "input_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": self.config.transcribe_model,
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": self.config.vad_threshold,
                    "prefix_padding_ms": self.config.vad_prefix_padding_ms,
                    "silence_duration_ms": self.config.vad_silence_duration_ms,
                },
            },
        }

        await self.ws.send(json.dumps(event))

    def _start_microphone(self) -> None:
        blocksize = int(self.config.sample_rate * self.config.chunk_ms / 1000)

        device_value = self.config.stereo_mix_device
        if device_value:
            if device_value.isdigit():
                device_value = int(device_value)
        else:
            device_value = None

        if self.config.save_raw_audio:
            self._open_raw_audio_file()

        def callback(indata, frames, time_info, status):
            if status:
                self._set_status(f"Mic warning: {status}")

            if not self.running or not self.loop or self._audio_queue is None:
                return

            pcm16 = self._float32_to_pcm16(indata[:, 0])

            if self.config.save_raw_audio:
                self._write_raw_audio(pcm16)

            payload = base64.b64encode(pcm16).decode("ascii")

            try:
                asyncio.run_coroutine_threadsafe(
                    self._audio_queue.put(payload),
                    self.loop,
                )
            except Exception as e:
                self._set_status(f"Audio queue error: {e}")

        self._audio_stream = sd.InputStream(
            device=device_value,
            samplerate=self.config.sample_rate,
            channels=self.config.channels,
            dtype="float32",
            blocksize=blocksize,
            callback=callback,
        )

        self._audio_stream.start()

        if self._wav_path:
            self._set_status(f"Listening... REC {self._wav_path}")
        else:
            self._set_status("Listening...")

    def _stop_microphone(self) -> None:
        if self._audio_stream is not None:
            try:
                self._audio_stream.stop()
                self._audio_stream.close()
            except Exception:
                pass
            self._audio_stream = None

    async def _send_audio_loop(self) -> None:
        while self.running and self.ws is not None and self._audio_queue is not None:
            try:
                # タイムアウト付きで取得し、stop()後に確実に抜けられるようにする
                try:
                    payload = await asyncio.wait_for(self._audio_queue.get(), timeout=0.5)
                except asyncio.TimeoutError:
                    continue

                # 番兵値が入ったらループ終了
                if payload is None:
                    break

                event = {
                    "type": "input_audio_buffer.append",
                    "audio": payload,
                }
                await self.ws.send(json.dumps(event))
            except Exception as e:
                self._set_status(f"Send error: {e}")
                break

    async def _receive_loop(self) -> None:
        partials = {}

        try:
            async for message in self.ws:
                event = json.loads(message)
                event_type = event.get("type", "")

                if event_type == "session.created":
                    self._set_status("Session created")

                elif event_type == "session.updated":
                    if self._wav_path:
                        self._set_status(f"Listening... REC {self._wav_path}")
                    else:
                        self._set_status("Listening...")

                elif event_type == "input_audio_buffer.speech_started":
                    self._set_status("Speaking...")

                elif event_type == "input_audio_buffer.speech_stopped":
                    self._set_status("Transcribing...")

                elif event_type == "conversation.item.input_audio_transcription.delta":
                    item_id = event.get("item_id", "")
                    delta = event.get("delta", "")
                    if item_id:
                        partials[item_id] = partials.get(item_id, "") + delta

                elif event_type == "conversation.item.input_audio_transcription.completed":
                    transcript = (event.get("transcript") or "").strip()
                    item_id = event.get("item_id", "")

                    if not transcript and item_id in partials:
                        transcript = partials[item_id].strip()

                    if item_id in partials:
                        partials.pop(item_id, None)

                    if transcript and self.on_final_transcript:
                        self.on_final_transcript(transcript)

                    if self._wav_path:
                        self._set_status(f"Listening... REC {self._wav_path}")
                    else:
                        self._set_status("Listening...")

                elif event_type == "error":
                    error = event.get("error", {})
                    msg = error.get("message", "Unknown error")
                    self._set_status(f"Error: {msg}")

        except Exception as e:
            self._set_status(f"Receive error: {e}")

    def _open_raw_audio_file(self) -> None:
        os.makedirs(self.config.raw_audio_dir, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._wav_path = os.path.join(self.config.raw_audio_dir, f"raw_{ts}.wav")

        with self._wav_lock:
            self._wav_file = wave.open(self._wav_path, "wb")
            self._wav_file.setnchannels(self.config.channels)
            self._wav_file.setsampwidth(2)
            self._wav_file.setframerate(self.config.sample_rate)

    def _write_raw_audio(self, pcm16: bytes) -> None:
        with self._wav_lock:
            if self._wav_file is not None:
                self._wav_file.writeframes(pcm16)

    def _close_raw_audio_file(self) -> None:
        with self._wav_lock:
            if self._wav_file is not None:
                try:
                    self._wav_file.close()
                except Exception:
                    pass
                self._wav_file = None

    @staticmethod
    def _float32_to_pcm16(audio: np.ndarray) -> bytes:
        clipped = np.clip(audio, -1.0, 1.0)
        pcm = (clipped * 32767.0).astype(np.int16)
        return pcm.tobytes()

    def _set_status(self, text: str) -> None:
        if self.on_status:
            self.on_status(text)