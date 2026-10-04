"""Pauzes inkorten: houd alleen spraak-segmenten over en herbereken de tijdlijn."""
from .models import Word


def keep_segments(words: list[Word], start: float, end: float,
                  max_gap: float = 0.5, pad: float = 0.1) -> list[tuple[float, float]]:
    """Segmenten (in bronvideo-tijd) die behouden blijven; pauzes > max_gap worden weggeknipt."""
    if not words:
        return [(start, end)]
    segs = []
    s, e = words[0].start, words[0].end
    for w in words[1:]:
        if w.start - e > max_gap:
            segs.append((s, e))
            s = w.start
        e = w.end
    segs.append((s, e))
    out = [(max(start, a - pad), min(end, b + pad)) for a, b in segs]
    merged = [out[0]]
    for a, b in out[1:]:
        if a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return merged


def remap_words(words: list[Word], segs: list[tuple[float, float]]) -> list[Word]:
    """Zet woordtijden om naar de nieuwe, ingekorte tijdlijn."""
    offsets, acc = [], 0.0
    for a, b in segs:
        offsets.append(acc - a)
        acc += b - a
    out = []
    for w in words:
        for (a, b), off in zip(segs, offsets):
            if a - 1e-6 <= w.start and w.end <= b + 1e-6:
                out.append(Word(w.text, w.start + off, w.end + off))
                break
    return out
