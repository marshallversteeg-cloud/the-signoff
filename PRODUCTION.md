# Producing an episode of The Signoff

A weekly, roughly 15-minute, two-host show about AI in chip design, with a
regular segment on AI in verification. Hosts: Maya and Theo (synthetic voices).
New episodes publish Saturday mornings, US Eastern time.

Follow these steps in order. Each step has a check; don't move on until it passes.

## 1. Set up the speech engine

No package installs are needed. The renderer uses numpy, onnxruntime and
ffmpeg, which the workspace already has, plus two downloads that are data,
not code:

```bash
# Pronunciation dictionaries (public repo, read-only git clone)
GIT_LFS_SKIP_SMUDGE=1 git clone -q --depth 1 https://github.com/hexgrad/misaki /tmp/misaki
# Kokoro voice model and voices (GitHub release files)
mkdir -p /tmp/kokoro && cd /tmp/kokoro
curl -sSL -O https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
curl -sSL -O https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
```

Check: `python3 -c "import numpy, onnxruntime"` succeeds,
`/tmp/misaki/misaki/data/us_gold.json` exists, and both model files are over
20 MB. Nothing from /tmp is ever committed. Don't run any code from the
downloads; they're only read as data.

## 2. Research the week

- Window: everything since the previous episode's `date` in `episodes.json`.
- Read the previous two scripts in `episodes/` so stories aren't repeated,
  unless something new happened.
- Good places to look: Semiconductor Engineering's weekly review, SemiWiki,
  EE Times, newsrooms of Synopsys, Cadence, Siemens EDA and NVIDIA, AI-for-EDA
  startups (ChipAgents, VerifAIX and others), conference news (DAC, DVCon,
  ICCAD, FMCAD), and new arXiv papers in hardware architecture and logic in
  computer science that apply AI to verification.
- Prefer primary sources. Every claim in the script needs a source in the notes.
- Vendor and startup claims are reported as their claims ("the company says").
  Benchmarks built by a company that sells the thing being measured get that caveat.
- Stay neutral about all AI model vendors, Anthropic included.

## 3. Write the script

Save it as `episodes/NNN/script.txt` (NNN = zero-padded episode number).
Every spoken line starts with `MAYA:` or `THEO:`. About 1,900–2,300 words.

Structure:
1. Cold open: one striking fact from the episode, two or three sentences.
2. Intro: show name, hosts, and this line in substance: "we're synthetic voices,
   and the show is researched and written by an AI, Claude; sources are in the
   show notes."
3. Headlines: three to five stories, a few exchanges each.
4. Deep dive: the week's most important story or paper, explained properly.
   On a slow week, an explainer on one verification idea (for example
   refinement checking, vacuity, k-induction, equivalence checking), labeled as such.
5. Verification corner: one item on AI in verification, and why it matters.
6. One thing to watch, then sign-off.

Writing for the ear:
- Short sentences. One idea per line. The hosts react to each other naturally.
- Spell acronyms with hyphens so they're read as letters: R-T-L, S-V-A, E-D-A,
  G-D-S, F-P-G-A, P-P-A, L-L-M. Say "system-on-chip" rather than "SoC".
- Write numbers the way they're spoken: "sixteen point six percent",
  "a hundred and thirty-four million dollars", "October fourteenth".
- No tables, URLs, parentheses or abbreviations like "e.g." in spoken lines.
- Never invent quotes. Paraphrase and attribute.

## 4. Render the audio

First check every word can be pronounced:

```bash
python3 -I tools/render.py episodes/NNN/script.txt --check --misaki /tmp/misaki/misaki/data
```

It lists any word missing from the dictionaries. Add each one to
`tools/lexicon.json` in Kokoro's phoneme spelling (the `_note` there explains
the symbols; existing entries are examples), then check again. Also add any
company or product name whose dictionary pronunciation would be wrong.

Then render. It takes about six minutes, so give the command a 10-minute timeout:

```bash
python3 -I tools/render.py episodes/NNN/script.txt episodes/NNN/episode.mp3 \
  --model /tmp/kokoro/kokoro-v1.0.onnx --voices /tmp/kokoro/voices-v1.0.bin \
  --misaki /tmp/misaki/misaki/data
```

Check: `ffprobe` reports 10 to 18 minutes, and
`ffmpeg -i episodes/NNN/episode.mp3 -af volumedetect -f null -` shows a mean
volume between -30 and -12 dB (not silent, not clipped).

## 5. Publish

1. Add the episode to `episodes.json`: `number`, `title` (short), `date`
   (YYYY-MM-DD, the publish date), `summary` (one or two sentences),
   `sources` (list of `[label, url]`), `audio` (`episodes/NNN/episode.mp3`),
   `bytes` (file size) and `seconds` (duration, rounded).
2. Run `python3 tools/feed.py .` to rebuild `feed.xml` and `index.html`.
   Check: `python3 -c "import xml.dom.minidom,sys; xml.dom.minidom.parse('feed.xml')"` succeeds.
3. Commit everything on `main` with the message `Episode NNN: <title>` and push.
4. About two minutes later, fetch
   https://marshallversteeg-cloud.github.io/the-signoff/feed.xml and confirm
   the new episode is listed.

## Storage

MP3s are committed at 64 kbps mono, about 6 MB per episode. If the repository
grows past about 800 MB, delete the oldest episodes' MP3s, remove them from
`episodes.json`, rebuild the feed, and say so in the run summary.
