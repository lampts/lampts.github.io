#!/usr/bin/env python3
"""
talk.py — Speech-to-speech terminal agent via Gemini Live API.

The Unix pipe for voice:
    mic → [WebSocket] → Gemini Native Audio → [WebSocket] → speaker

One model. No STT→LLM→TTS chain. Audio in, audio out, natively.

Usage:
    export GEMINI_API_KEY=your_key
    python talk.py
    python talk.py --system "You are a Vietnamese banking assistant for Cake digital bank"
    python talk.py --system-file prompts/card_delivery.txt
    python talk.py --model gemini-2.5-flash-native-audio-preview-12-2025

Requirements:
    pip install google-genai pyaudio
"""

import asyncio
import argparse
import os
import sys
import signal
from pathlib import Path

try:
    from google import genai
except ImportError:
    print("pip install google-genai")
    sys.exit(1)

try:
    import pyaudio
except ImportError:
    print("pip install pyaudio")
    print("  macOS: brew install portaudio && pip install pyaudio")
    print("  Ubuntu: sudo apt-get install portaudio19-dev && pip install pyaudio")
    sys.exit(1)


# ── Audio Config ──────────────────────────────────────────────
FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_RATE = 16000      # mic: 16kHz PCM mono
RECV_RATE = 24000      # speaker: 24kHz PCM mono
CHUNK = 1024

# ── Default Model ─────────────────────────────────────────────
DEFAULT_MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"
DEFAULT_SYSTEM = "You are a helpful and friendly AI assistant."


def parse_args():
    p = argparse.ArgumentParser(
        description="Speech-to-speech terminal agent via Gemini Live API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic conversation
  python talk.py

  # Custom system prompt
  python talk.py --system "You are a Cake bank customer support agent. Speak Vietnamese."

  # Load prompt from file (like Unix: cat prompt.txt | ...)
  python talk.py --system-file prompts/card_delivery.txt

  # With thinking enabled
  python talk.py --thinking 1024

  # Specific voice
  python talk.py --voice Kore
        """,
    )
    p.add_argument("--model", default=DEFAULT_MODEL, help="Gemini model ID")
    p.add_argument("--system", default=DEFAULT_SYSTEM, help="System instruction")
    p.add_argument("--system-file", type=Path, help="Read system instruction from file")
    p.add_argument("--voice", default=None, help="Voice name (e.g., Kore, Puck, Charon, Fenrir)")
    p.add_argument("--thinking", type=int, default=0, help="Thinking budget tokens (0=off)")
    p.add_argument("--transcribe", action="store_true", help="Print transcriptions to terminal")
    return p.parse_args()


class VoiceAgent:
    """Minimal speech-to-speech agent. Mic → Gemini → Speaker."""

    def __init__(self, args):
        self.args = args
        self.pya = pyaudio.PyAudio()
        self.mic_stream = None
        self.speaker_stream = None

        # Queues: the pipes between async tasks
        self.mic_queue = asyncio.Queue(maxsize=5)
        self.speaker_queue = asyncio.Queue()

        # System prompt: from file or argument
        if args.system_file and args.system_file.exists():
            self.system_prompt = args.system_file.read_text().strip()
        else:
            self.system_prompt = args.system

        # Build config
        self.config = {
            "response_modalities": ["AUDIO"],
            "system_instruction": self.system_prompt,
        }

        # Voice selection
        if args.voice:
            self.config["speech_config"] = {
                "voice_config": {
                    "prebuilt_voice_config": {
                        "voice_name": args.voice,
                    }
                }
            }

        # Thinking budget
        if args.thinking > 0:
            self.config["thinking_config"] = {
                "thinking_budget": args.thinking,
            }

        # Transcription
        if args.transcribe:
            self.config["input_audio_transcription"] = {}
            self.config["output_audio_transcription"] = {}

        # Client
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("ERROR: export GEMINI_API_KEY=your_key")
            sys.exit(1)
        self.client = genai.Client(api_key=api_key)

    # ── listen: mic → queue ───────────────────────────────────
    async def listen(self):
        """Capture mic audio into queue. The 'listen' pipe."""
        mic_info = self.pya.get_default_input_device_info()
        self.mic_stream = await asyncio.to_thread(
            self.pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=SEND_RATE,
            input=True,
            input_device_index=mic_info["index"],
            frames_per_buffer=CHUNK,
        )
        while True:
            data = await asyncio.to_thread(
                self.mic_stream.read, CHUNK, exception_on_overflow=False
            )
            await self.mic_queue.put({"data": data, "mime_type": "audio/pcm"})

    # ── send: queue → Gemini ──────────────────────────────────
    async def send(self, session):
        """Send mic audio to Gemini. The upstream pipe."""
        while True:
            msg = await self.mic_queue.get()
            await session.send_realtime_input(audio=msg)

    # ── receive: Gemini → queue ───────────────────────────────
    async def receive(self, session):
        """Receive Gemini responses into speaker queue. The downstream pipe."""
        while True:
            turn = session.receive()
            async for response in turn:
                sc = response.server_content
                if sc and sc.model_turn:
                    for part in sc.model_turn.parts:
                        if part.inline_data and isinstance(part.inline_data.data, bytes):
                            self.speaker_queue.put_nowait(part.inline_data.data)

                # Print transcriptions if enabled
                if self.args.transcribe and sc:
                    if hasattr(sc, "input_transcription") and sc.input_transcription:
                        print(f"\r🎤 {sc.input_transcription.text}", end="", flush=True)
                    if hasattr(sc, "output_transcription") and sc.output_transcription:
                        print(f"\r🤖 {sc.output_transcription.text}", flush=True)

            # Interrupted — flush speaker queue
            while not self.speaker_queue.empty():
                self.speaker_queue.get_nowait()

    # ── respond: queue → speaker ──────────────────────────────
    async def respond(self):
        """Play audio from speaker queue. The 'respond' pipe."""
        self.speaker_stream = await asyncio.to_thread(
            self.pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=RECV_RATE,
            output=True,
        )
        while True:
            audio_bytes = await self.speaker_queue.get()
            await asyncio.to_thread(self.speaker_stream.write, audio_bytes)

    # ── run: the main pipe ────────────────────────────────────
    async def run(self):
        """
        The full pipe:
            listen | send → [Gemini Live API] → receive | respond
        """
        print(f"─── Gemini Voice Agent ───")
        print(f"  Model:  {self.args.model}")
        print(f"  System: {self.system_prompt[:80]}...")
        if self.args.voice:
            print(f"  Voice:  {self.args.voice}")
        if self.args.thinking:
            print(f"  Think:  {self.args.thinking} tokens")
        print(f"  Use headphones to prevent echo.")
        print(f"  Ctrl+C to quit.\n")

        try:
            async with self.client.aio.live.connect(
                model=self.args.model, config=self.config
            ) as session:
                print("✓ Connected. Start speaking!\n")
                async with asyncio.TaskGroup() as tg:
                    tg.create_task(self.listen())      # mic → queue
                    tg.create_task(self.send(session))  # queue → gemini
                    tg.create_task(self.receive(session))  # gemini → queue
                    tg.create_task(self.respond())      # queue → speaker
        except asyncio.CancelledError:
            pass
        finally:
            self.cleanup()

    def cleanup(self):
        if self.mic_stream:
            self.mic_stream.close()
        if self.speaker_stream:
            self.speaker_stream.close()
        self.pya.terminate()
        print("\n✓ Disconnected.")


def main():
    args = parse_args()
    agent = VoiceAgent(args)

    # Graceful shutdown on Ctrl+C
    loop = asyncio.new_event_loop()

    def shutdown(sig, frame):
        print("\nShutting down...")
        for task in asyncio.all_tasks(loop):
            task.cancel()

    signal.signal(signal.SIGINT, shutdown)

    try:
        loop.run_until_complete(agent.run())
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        loop.close()


if __name__ == "__main__":
    main()
