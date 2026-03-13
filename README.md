# Realtime Speech Transcription + Translation

## Demo Video

[![Watch the demo](https://img.youtube.com/vi/eWEqhg1yfn4/maxresdefault.jpg)](https://www.youtube.com/watch?v=eWEqhg1yfn4&hd=1)

Low-latency realtime speech transcription and translation system built with Python and the OpenAI Realtime API.

A realtime speech transcription and translation tool built with Python and OpenAI Realtime API.

This application captures system audio (Stereo Mix or microphone), performs realtime speech recognition, and generates natural translations in another language.

It is designed for meetings, live subtitles, language learning, and realtime communication.

---

# Features

- Realtime speech transcription
- Natural language translation
- Sentence-level translation using punctuation detection
- Auto translation mode
- Manual translation button
- Raw audio recording (WAV)
- Stereo Mix audio capture (system audio)
- Desktop UI
- Low latency streaming

---

# Multi-Language Support

The system is language-agnostic.

By adjusting the transcription and translation settings, it can support any language supported by the API.

Examples:

- English → Japanese
- Japanese → English
- English → Spanish
- Chinese → English
- Korean → Japanese
- French → English

or any other language combination.

---

# Translation Modes

The application provides multiple translation modes.

### Auto Mode
Translation happens automatically when:

- punctuation is detected
- short silence is detected

### Manual Mode
A translation button allows the user to translate the current accumulated speech.

### Meaning-Based Translation

The system does not perform word-by-word translation.

Instead it generates a **natural explanation of the spoken sentence**, making it easier to understand spoken language.

---

# Audio Recording

The application can optionally record raw audio.

Features:

- full session recording
- WAV format
- useful for meeting logs
- useful for later transcription

---

# Architecture


Audio Input
   ↓
Realtime Audio Streaming
   ↓
Speech Recognition
   ↓
Sentence Detection
   ↓
Translation
   ↓
UI Display


---

# Tech Stack

Python

Libraries

- sounddevice
- websockets
- numpy
- python-dotenv

AI

- OpenAI Realtime API
- speech transcription models
- language generation models

---

# Installation

Clone repository


git clone git clone https://github.com/HAYATOKudo/realtime-transcription-translator


Install dependencies


pip install -r requirements.txt


Create `.env`


OPENAI_API_KEY=your_api_key_here


Run application


python app.py


---

# Example Use Cases

Realtime meeting translation

Online meeting subtitles

Podcast transcription

Language learning

Interview transcription

International communication

---

# Future Improvements

- speaker detection
- subtitle export
- OBS integration
- meeting summary generation
- translation history
- multilingual UI

---

# Author

Python developer focused on:

- automation tools
- realtime systems
- AI integrations
- trading infrastructure