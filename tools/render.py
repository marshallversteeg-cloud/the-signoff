"""Render a two-host script to a podcast MP3.

Usage: python3 render.py SCRIPT OUT.mp3 MODEL.onnx VOICES.bin

Script lines look like "MAYA: text". Each line is spoken by that host's voice,
with a short pause between turns. The result is loudness-normalized for
podcasts (-16 LUFS) and encoded as mono MP3.
"""
import re
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np
from kokoro_onnx import Kokoro

VOICES = {"MAYA": "af_heart", "THEO": "am_michael"}
SPEED = {"MAYA": 1.02, "THEO": 1.0}
PAUSE_BETWEEN_TURNS = 0.35  # seconds
PAUSE_BETWEEN_SENTENCES = 0.12

# Words the speech engine tends to mispronounce, rewritten for the ear.
SAY = {
    "Synopsys": "Sinopsis",
    "Nemotron": "Neemotron",
    "Socionext": "Sohsheeoh-next",
    "Kokoro": "Kohkohroh",
}


def say(text: str) -> str:
    for word, spoken in SAY.items():
        text = re.sub(rf"\b{re.escape(word)}\b", spoken, text)
    return text


def sentences(text: str):
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p]


def main(script_path, out_mp3, model, voices):
    tts = Kokoro(model, voices)
    lines = []
    for raw in Path(script_path).read_text().splitlines():
        m = re.match(r"^(MAYA|THEO):\s*(.+)$", raw.strip())
        if m:
            lines.append((m.group(1), m.group(2)))
    if not lines:
        sys.exit("no speaker lines found")

    rate = None
    chunks = []
    for i, (who, text) in enumerate(lines):
        for s in sentences(say(text)):
            audio, rate = tts.create(s, voice=VOICES[who], speed=SPEED[who], lang="en-us")
            chunks.append(np.asarray(audio, dtype=np.float32))
            chunks.append(np.zeros(int(rate * PAUSE_BETWEEN_SENTENCES), dtype=np.float32))
        chunks.append(np.zeros(int(rate * PAUSE_BETWEEN_TURNS), dtype=np.float32))
        print(f"line {i + 1}/{len(lines)}", file=sys.stderr, flush=True)

    audio = np.concatenate(chunks)
    pcm = (np.clip(audio, -1, 1) * 32767).astype(np.int16)
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "raw.wav"
        with wave.open(str(wav), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(pcm.tobytes())
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav),
             "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ac", "1", "-ar", "44100",
             "-codec:a", "libmp3lame", "-b:a", "64k", out_mp3],
            check=True,
        )
    print(f"wrote {out_mp3} ({len(audio) / rate / 60:.1f} min)")


if __name__ == "__main__":
    main(*sys.argv[1:5])
