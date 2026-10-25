"""English text to Kokoro phonemes, using misaki's pronunciation dictionaries.

A small dictionary-based converter: it looks words up in misaki's US "gold"
and "silver" dictionaries (data files from https://github.com/hexgrad/misaki,
Apache-2.0), applies the usual -s / -ed / -ing endings, spells hyphenated
single letters as an initialism (R-T-L), and checks tools/lexicon.json first
for names and jargon. Words it can't pronounce are reported, never guessed.
"""
import json
import re
from pathlib import Path

PRIMARY, SECONDARY = "ˈ", "ˌ"
STRESSES = PRIMARY + SECONDARY
VOWELS = set("AIOQWYaiuæɑɒɔəɛɜɪʊʌᵻ")
CONSONANTS = set("bdfhjklmnpstvwzðŋɡɹɾʃʒʤʧθ")
US_TAUS = set("AIOWYiuæɑəɛɪɹʊʌ")
PUNCT = set(';:,.!?—…"()“”')


def apply_stress(ps, stress):
    """misaki's stress adjustment: None leaves it, -1 removes, 0/0.5 demotes, 2 promotes."""
    if ps is None or stress is None:
        return ps

    def restress(p):
        ips = list(enumerate(p))
        marks = {}
        for i, c in ips:
            if c in STRESSES:
                j = next((k for k, v in ips[i:] if v in VOWELS), None)
                if j is not None:
                    marks[i] = j
        if not marks:
            return p
        out = [(float(i), c) for i, c in ips]
        for i, j in marks.items():
            out[i] = (j - 0.5, out[i][1])
        return "".join(c for _, c in sorted(out))

    if stress < -1:
        return ps.replace(PRIMARY, "").replace(SECONDARY, "")
    if stress == -1 or (stress in (0, -0.5) and PRIMARY in ps):
        return ps.replace(SECONDARY, "").replace(PRIMARY, SECONDARY)
    if stress in (0, 0.5, 1) and not any(s in ps for s in STRESSES):
        return ps if not any(v in ps for v in VOWELS) else restress(SECONDARY + ps)
    if stress >= 1 and PRIMARY not in ps and SECONDARY in ps:
        return ps.replace(SECONDARY, PRIMARY)
    if stress > 1 and not any(s in ps for s in STRESSES):
        return ps if not any(v in ps for v in VOWELS) else restress(PRIMARY + ps)
    return ps


def _grow(d):
    e = {}
    for k, v in d.items():
        if len(k) < 2:
            continue
        if k == k.lower() and k != k.capitalize():
            e[k.capitalize()] = v
        elif k == k.lower().capitalize():
            e[k.lower()] = v
    return {**e, **d}


class G2P:
    def __init__(self, misaki_data_dir, lexicon_path=None):
        data = Path(misaki_data_dir)
        self.gold = _grow(json.loads((data / "us_gold.json").read_text()))
        self.silver = _grow(json.loads((data / "us_silver.json").read_text()))
        self.custom = {}
        if lexicon_path and Path(lexicon_path).exists():
            self.custom = {k: v for k, v in json.loads(Path(lexicon_path).read_text()).items() if not k.startswith("_")}
        self.unknown = set()

    # ---- dictionary lookups -------------------------------------------------
    def _entry(self, word):
        for d in (self.gold, self.silver):
            v = d.get(word)
            if isinstance(v, dict):
                v = v.get("DEFAULT")
            if v:
                return v
        return None

    def letters(self, letters):
        ps = [self.gold.get(c.upper()) for c in letters]
        if None in ps:
            return None
        joined = apply_stress("".join(ps), 0)
        head, _, tail = joined.rpartition(SECONDARY)
        return head + PRIMARY + tail if head or tail else joined

    def known(self, word):
        return word in self.custom or self._entry(word) is not None or self._entry(word.lower()) is not None

    def lookup(self, word):
        if word in self.custom:
            return self.custom[word]
        if word.lower() in self.custom:
            return self.custom[word.lower()]
        ps = self._entry(word)
        if ps is None and word.isupper() and len(word) > 1:
            ps = self._entry(word.lower()) or self.letters(word)
        if ps is None:
            ps = self._entry(word.lower())
        return ps

    def _s(self, stem):
        if not stem:
            return None
        if stem[-1] in "ptkfθ":
            return stem + "s"
        if stem[-1] in "szʃʒʧʤ":
            return stem + "ᵻz"
        return stem + "z"

    def _ed(self, stem):
        if not stem:
            return None
        if stem[-1] in "pkfθʃsʧ":
            return stem + "t"
        if stem[-1] == "d":
            return stem + "ᵻd"
        if stem[-1] != "t":
            return stem + "d"
        if len(stem) > 1 and stem[-2] in US_TAUS:
            return stem[:-1] + "ɾᵻd"
        return stem + "ᵻd"

    def _ing(self, stem):
        if not stem:
            return None
        if len(stem) > 1 and stem[-1] == "t" and stem[-2] in US_TAUS:
            return stem[:-1] + "ɾɪŋ"
        return stem + "ɪŋ"

    def word(self, w):
        w = w.replace("’", "'").replace("‘", "'")
        ps = self.lookup(w)
        if ps:
            return ps
        lw = w.lower()
        if lw.endswith("'s") and self.known(w[:-2]):
            return self._s(self.lookup(w[:-2]))
        if lw.endswith("s'") and self.known(w[:-1]):
            return self._s(self.lookup(w[:-1]))
        if len(w) > 2 and lw.endswith("s") and not lw.endswith("ss") and self.known(w[:-1]):
            return self._s(self.lookup(w[:-1]))
        if len(w) > 4 and lw.endswith("es") and self.known(w[:-2]):
            return self._s(self.lookup(w[:-2]))
        if len(w) > 4 and lw.endswith("ies") and self.known(w[:-3] + "y"):
            return self._s(self.lookup(w[:-3] + "y"))
        if len(w) > 3 and lw.endswith("d") and not lw.endswith("dd") and self.known(w[:-1]):
            return self._ed(self.lookup(w[:-1]))
        if len(w) > 4 and lw.endswith("ed") and self.known(w[:-2]):
            return self._ed(self.lookup(w[:-2]))
        if len(w) > 4 and lw.endswith("ied") and self.known(w[:-3] + "y"):
            return self._ed(self.lookup(w[:-3] + "y"))
        if len(w) > 5 and lw.endswith("ing"):
            for stem in (w[:-3], w[:-3] + "e", w[:-4]):
                if self.known(stem):
                    return self._ing(apply_stress(self.lookup(stem), 0.5))
        self.unknown.add(w)
        return None

    # ---- sentences -----------------------------------------------------------
    TOKEN = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)*(?:-[A-Za-z]+(?:['’][A-Za-z]+)*)*|[;:,.!?—…\"()“”]")

    def _first_sound(self, ps):
        for c in ps or "":
            if c in VOWELS or c == "ɐ":
                return True
            if c in CONSONANTS:
                return False
        return None

    def _token(self, tok, next_vowel):
        if tok in PUNCT:
            return tok
        parts = tok.split("-")
        if len(parts) > 1 and all(len(p) == 1 for p in parts):
            ps = self.letters("".join(parts))
            if ps is None:
                self.unknown.add(tok)
            return ps
        if len(parts) > 1:
            pieces = [self._token(p, None) for p in parts]
            return None if None in pieces else " ".join(pieces)
        w = tok
        lw = w.lower()
        if lw == "the":
            return "ði" if next_vowel else "ðə"
        if lw == "a" and w != "A":
            return "ɐ"
        if w == "A":
            return "ɐ"
        if lw == "an":
            return "ɐn"
        if lw == "to":
            return {None: self.gold["to"], False: "tə", True: "tʊ"}[next_vowel]
        if w == "I":
            return SECONDARY + "I"
        ps = self.word(w)
        if ps and w[0].isupper() and w not in self.custom:
            ps = apply_stress(ps, 2 if (w.isupper() and len(w) > 1) else 0.5)
        return ps

    def phonemize(self, text):
        text = text.replace("–", "—").replace(" - ", " — ")
        toks = self.TOKEN.findall(text)
        out = [None] * len(toks)
        next_vowel = None
        for i in range(len(toks) - 1, -1, -1):
            ps = self._token(toks[i], next_vowel)
            out[i] = ps
            if toks[i] in PUNCT:
                next_vowel = None
            elif ps:
                next_vowel = self._first_sound(ps)
        result = ""
        for tok, ps in zip(toks, out):
            if ps is None:
                continue
            if tok in PUNCT and tok not in "(“\"":
                result = result.rstrip() + ps + " "
            else:
                result += ps + " "
        # Kokoro v1.0 was trained with flaps written as T and glottal stops as t.
        return result.strip().replace("ɾ", "T").replace("ʔ", "t")
