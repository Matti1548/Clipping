"""Zinsgrenzen en het snappen van clips daarop."""
from .models import Word

_END = (".", "?", "!", "…")


def sentence_spans(words: list[Word], gap: float = 0.7) -> list[tuple[int, int]]:
    """Index-bereiken (start, eind inclusief) van zinnen. Een zin eindigt op leesteken of lange pauze."""
    spans, start = [], 0
    for i, w in enumerate(words):
        nxt = words[i + 1] if i + 1 < len(words) else None
        if w.text.endswith(_END) or nxt is None or nxt.start - w.end > gap:
            spans.append((start, i))
            start = i + 1
    return spans


def snap_to_sentences(words: list[Word], start: float, end: float,
                      min_dur: float, max_dur: float) -> tuple[float, float]:
    """Schuif start/eind naar zinsgrenzen binnen [min_dur, max_dur]."""
    spans = sentence_spans(words)
    if not spans:
        return start, min(end, start + max_dur)
    starts = [words[a].start for a, _ in spans]
    ends = [words[b].end for _, b in spans]
    s = min(starts, key=lambda t: abs(t - start))
    # kies het laatste zinseinde dat binnen de duurgrenzen valt, het dichtst bij `end`
    cands = [e for e in ends if min_dur <= e - s <= max_dur]
    if cands:
        return s, min(cands, key=lambda t: abs(t - end))
    later = [e for e in ends if e - s > min_dur]
    return s, min(min(later) if later else ends[-1], s + max_dur)


def words_between(words: list[Word], start: float, end: float) -> list[Word]:
    return [w for w in words if w.start >= start - 0.01 and w.end <= end + 0.01]
