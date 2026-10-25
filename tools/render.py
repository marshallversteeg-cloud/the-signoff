"""Render a two-host script to a podcast MP3 with the Kokoro speech model.

Usage:
  python3 tools/render.py SCRIPT OUT.mp3 --model M.onnx --voices V.bin --misaki DATA_DIR
  python3 tools/render.py --check SCRIPT --misaki DATA_DIR   # list unpronounceable words only

Script lines look like "MAYA: text". Each line is spoken by that host's voice,
with a short pause between turns. Output is loudness-normalized for podcasts
(-16 LUFS) and encoded as 64 kbps mono MP3.

Needs only numpy, onnxruntime and ffmpeg. Text becomes phonemes through
tools/g2p.py, which uses misaki's pronunciation dictionaries plus
tools/lexicon.json. Unknown words stop the render, so add them to the lexicon.
"""
import argparse
import re
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from g2p import G2P  # noqa: E402

HERE = Path(__file__).parent
SAMPLE_RATE = 24000
VOICES = {"MAYA": "af_heart", "THEO": "am_michael"}
SPEED = {"MAYA": 1.0, "THEO": 1.0}
PAUSE_TURN = 0.45
PAUSE_SENTENCE = 0.28
PAUSE_CLAUSE = 0.0
MAX_PHONEMES = 500


def script_lines(path):
    lines = []
    for raw in Path(path).read_text().splitlines():
        m = re.match(r"^(MAYA|THEO):\s*(.+)$", raw.strip())
        if m:
            lines.append((m.group(1), m.group(2)))
    if not lines:
        sys.exit("no MAYA:/THEO: lines found")
    return lines


def sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]


def chunks(ps):
    """Split a phoneme string at punctuation, then spaces, to fit the model."""
    if len(ps) <= MAX_PHONEMES:
        return [ps]
    cut = max(ps.rfind(m, 0, MAX_PHONEMES) for m in ",;:—")
    if cut < MAX_PHONEMES // 3:
        cut = ps.rfind(" ", 0, MAX_PHONEMES)
    return [ps[: cut + 1].strip()] + chunks(ps[cut + 1 :].strip())


def trim(audio, threshold=0.012, margin=0.03):
    idx = np.where(np.abs(audio) > threshold)[0]
    if not len(idx):
        return audio[:0]
    pad = int(margin * SAMPLE_RATE)
    return audio[max(0, idx[0] - pad) : idx[-1] + pad]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--model")
    ap.add_argument("--voices")
    ap.add_argument("--misaki", required=True, help="misaki/data directory with us_gold.json")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    g2p = G2P(a.misaki, HERE / "lexicon.json")
    lines = script_lines(a.script)
    plan = [(who, [g2p.phonemize(s) for s in sentences(text)]) for who, text in lines]
    if g2p.unknown:
        sys.exit("Add these to tools/lexicon.json before rendering: " + ", ".join(sorted(g2p.unknown)))
    if a.check:
        print(f"{len(lines)} lines, all words pronounceable")
        return

    import onnxruntime as rt

    vocab = __import__("json").loads((HERE / "kokoro_vocab.json").read_text())
    sess = rt.InferenceSession(a.model, providers=["CPUExecutionProvider"])
    voices = np.load(a.voices)

    def speak(ps, who):
        ids = [vocab[c] for c in ps if c in vocab]
        style = voices[VOICES[who]][min(len(ids), 510) - 1]
        out = sess.run(None, {
            "tokens": np.array([[0, *ids, 0]], dtype=np.int64),
            "style": style.astype(np.float32),
            "speed": np.array([SPEED[who]], dtype=np.float32),
        })[0]
        return trim(np.asarray(out, dtype=np.float32).ravel())

    parts = []
    for n, (who, sents) in enumerate(plan, 1):
        for ps in sents:
            for c in chunks(ps):
                parts.append(speak(c, who))
                parts.append(np.zeros(int(PAUSE_SENTENCE * SAMPLE_RATE), np.float32))
        parts.append(np.zeros(int(PAUSE_TURN * SAMPLE_RATE), np.float32))
        print(f"line {n}/{len(plan)}", file=sys.stderr, flush=True)

    audio = np.concatenate(parts)
    pcm = (np.clip(audio, -1, 1) * 32767).astype(np.int16)
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "raw.wav"
        with wave.open(str(wav), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SAMPLE_RATE)
            w.writeframes(pcm.tobytes())
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav),
             "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ac", "1", "-ar", "44100",
             "-codec:a", "libmp3lame", "-b:a", "64k", a.out],
            check=True,
        )
    print(f"wrote {a.out} ({len(audio) / SAMPLE_RATE / 60:.1f} min)")


if __name__ == "__main__":
    main()
