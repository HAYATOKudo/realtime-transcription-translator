import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class AppConfig:
    openai_api_key: str
    realtime_model: str
    transcribe_model: str
    text_model: str
    app_title: str
    sample_rate: int
    channels: int
    chunk_ms: int
    vad_threshold: float
    vad_prefix_padding_ms: int
    vad_silence_duration_ms: int
    stereo_mix_device: str
    save_raw_audio: bool
    raw_audio_dir: str


def load_config() -> AppConfig:
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY が設定されていません。")

    return AppConfig(
        openai_api_key=api_key,
        realtime_model=os.getenv("REALTIME_MODEL", "gpt-4o-realtime-preview"),
        transcribe_model=os.getenv("TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe"),
        text_model=os.getenv("TEXT_MODEL", "gpt-4o-mini"),
        app_title=os.getenv("APP_TITLE", "Realtime EN/JA Transcriber"),
        sample_rate=int(os.getenv("SAMPLE_RATE", "24000")),
        channels=int(os.getenv("CHANNELS", "1")),
        chunk_ms=int(os.getenv("CHUNK_MS", "200")),
        vad_threshold=float(os.getenv("VAD_THRESHOLD", "0.5")),
        vad_prefix_padding_ms=int(os.getenv("VAD_PREFIX_PADDING_MS", "300")),
        vad_silence_duration_ms=int(os.getenv("VAD_SILENCE_DURATION_MS", "300")),
        stereo_mix_device=os.getenv("STEREO_MIX_DEVICE", "").strip(),
        save_raw_audio=os.getenv("SAVE_RAW_AUDIO", "1").strip() in {"1", "true", "True", "yes", "on"},
        raw_audio_dir=os.getenv("RAW_AUDIO_DIR", "recordings").strip(),
    )