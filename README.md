# The Signoff

A weekly show about AI in chip design, with a regular stop in verification.
Researched and written by Claude, voiced with synthetic speech.

**Subscribe:** in your podcast app, choose "Follow a show by URL" (or "Add by
URL") and paste:

```
https://marshallversteeg-cloud.github.io/the-signoff/feed.xml
```

Or listen in a browser at https://marshallversteeg-cloud.github.io/the-signoff/

## How it's made

- `PRODUCTION.md`: the weekly runbook, from research to publishing.
- `tools/render.py`: turns a two-host script into an MP3 with the Kokoro speech model.
- `tools/g2p.py` and `tools/lexicon.json`: turn text into phonemes, using
  [misaki](https://github.com/hexgrad/misaki)'s pronunciation dictionaries
  plus a custom list of names and jargon.
- `tools/feed.py`: builds `feed.xml` and `index.html` from `episodes.json`.
- `tools/cover.py`: draws `cover.png`.
- `episodes/NNN/`: each episode's script and audio.
