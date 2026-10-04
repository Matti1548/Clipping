"""Kies de beste momenten met een LLM; zonder API-sleutel een eenvoudige heuristiek."""
import json
import os
import re

from .models import Highlight, Word
from .sentences import sentence_spans, snap_to_sentences

PROMPT = """Je bent een expert in virale korte video's (TikTok, YouTube Shorts, Reels).
Hieronder staat een transcript met tijdstempels in seconden. Kies de {n} beste fragmenten
van {lo}-{hi} seconden. Criteria: sterke hook in de eerste 3 seconden, een afgerond idee,
emotie of humor, een verrassend inzicht. Fragmenten mogen elkaar niet overlappen.

Antwoord ALLEEN met JSON: een lijst van objecten
{{"start": <sec>, "end": <sec>, "score": <0-10>, "reason": "<korte reden>", "hook": "<openingszin>"}}

Transcript:
{transcript}
"""


def build_transcript(words: list[Word]) -> str:
    lines = []
    for a, b in sentence_spans(words):
        text = " ".join(w.text for w in words[a:b + 1])
        lines.append(f"[{words[a].start:.1f}-{words[b].end:.1f}] {text}")
    return "\n".join(lines)


def parse_highlights(raw: str) -> list[Highlight]:
    m = re.search(r"\[.*\]", raw, re.S)
    if not m:
        return []
    out = []
    for d in json.loads(m.group(0)):
        try:
            out.append(Highlight(float(d["start"]), float(d["end"]), float(d.get("score", 5)),
                                 str(d.get("reason", "")), str(d.get("hook", ""))))
        except (KeyError, TypeError, ValueError):
            continue
    return out


def _llm(words: list[Word], cfg: dict) -> list[Highlight]:
    import anthropic

    prompt = PROMPT.format(n=cfg["clips"], lo=cfg["min_duration"], hi=cfg["max_duration"],
                           transcript=build_transcript(words))
    resp = anthropic.Anthropic().messages.create(
        model=cfg["llm"]["model"], max_tokens=2000,
        messages=[{"role": "user", "content": prompt}])
    return parse_highlights(resp.content[0].text)


def _heuristic(words: list[Word], cfg: dict) -> list[Highlight]:
    """Schuivend venster; score = spreektempo + vragen/uitroepen."""
    if not words:
        return []
    target = (cfg["min_duration"] + cfg["max_duration"]) / 2
    cands, t = [], words[0].start
    while t < words[-1].end - cfg["min_duration"]:
        win = [w for w in words if t <= w.start < t + target]
        if win:
            density = len(win) / target
            punch = sum(w.text.endswith(("?", "!")) for w in win)
            cands.append(Highlight(t, t + target, density + punch * 0.5, "heuristiek"))
        t += 5
    return cands


def _dedupe(hs: list[Highlight], n: int) -> list[Highlight]:
    chosen = []
    for h in sorted(hs, key=lambda h: -h.score):
        if all(h.end <= c.start or h.start >= c.end for c in chosen):
            chosen.append(h)
        if len(chosen) == n:
            break
    return sorted(chosen, key=lambda h: h.start)


def find_highlights(words: list[Word], cfg: dict) -> list[Highlight]:
    hs = []
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            hs = _llm(words, cfg)
        except Exception as e:  # netwerk/JSON-fout -> heuristiek
            print(f"LLM-highlights mislukt ({e}); heuristiek gebruikt")
    if not hs:
        hs = _heuristic(words, cfg)
    snapped = []
    for h in hs:
        s, e = snap_to_sentences(words, h.start, h.end, cfg["min_duration"], cfg["max_duration"])
        snapped.append(Highlight(s, e, h.score, h.reason, h.hook))
    return _dedupe(snapped, cfg["clips"])
