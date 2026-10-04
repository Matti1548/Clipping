"""Pauzes en opvulwoorden wegknippen en de tijdlijn opnieuw berekenen."""
import re

from .models import Word

FILLERS = {"um", "umm", "uh", "uhh", "uhm", "er", "erm", "hmm", "mm", "mmm", "ah", "eh", "huh"}


def is_filler(w: Word) -> bool:
    return re.sub(r"[^a-z]", "", w.text.lower()) in FILLERS


def keep_segments(words: list[Word], start: float, end: float, max_gap: float = 0.5,
                  pad: float = 0.1, drop_fillers: bool = True) -> list[tuple[float, float]]:
    """Segmenten (bronvideo-tijd) die blijven; pauzes > max_gap en opvulwoorden worden weggeknipt."""
    segs, cur = [], None
    for w in words:
        if drop_fillers and is_filler(w):
            if cur:
                segs.append(cur)
            cur = None
            continue
        if cur and w.start - cur[1] <= max_gap:
            cur = (cur[0], w.end)
        else:
            if cur:
                segs.append(cur)
            cur = (w.start, w.end)
    if cur:
        segs.append(cur)
    if not segs:
        return [(start, end)]
    padded = [(max(start, a - pad), min(end, b + pad)) for a, b in segs]
    merged = [padded[0]]
    for a, b in padded[1:]:
        if a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return merged


def remap_time(t: float, segs: list[tuple[float, float]]) -> float:
    """Bronvideo-tijd -> tijd in de ingekorte clip (valt t in een knip, dan het volgende segment)."""
    acc = 0.0
    for a, b in segs:
        if t < a:
            return acc
        if t <= b:
            return acc + (t - a)
        acc += b - a
    return acc


def remap_words(words: list[Word], segs: list[tuple[float, float]], drop_fillers: bool = True) -> list[Word]:
    out = []
    for w in words:
        if drop_fillers and is_filler(w):
            continue
        for a, b in segs:
            if a - 1e-6 <= w.start and w.end <= b + 1e-6:
                out.append(Word(w.text, remap_time(w.start, segs), remap_time(w.end, segs)))
                break
    return out
