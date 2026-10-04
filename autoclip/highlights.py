"""Kies de beste momenten met een LLM; zonder API-sleutel een eenvoudige heuristiek."""
import json
import os
import re

from .audio import mean_energy
from .jumpcut import is_filler
from .models import Highlight, Word
from .rules import banned_hits, rules_for_prompt
from .sentences import sentence_spans, snap_to_sentences

PROMPT = """You are an expert editor of viral short-form video (TikTok, YouTube Shorts, Reels).
The source is a {ctype} video. Below is a transcript with timestamps in seconds.

Pick the {n} best clips of {lo}-{hi} seconds. Look for: {criteria}.
Every clip needs a strong hook in the first 3 seconds, must make sense on its own (no missing
context) and must end on a complete thought. Clips must not overlap. Avoid intros, outros,
sponsor reads and filler talk.

Reply with ONLY a JSON list of objects:
{{"start": <sec>, "end": <sec>, "score": <0-10>, "reason": "<short reason>",
  "hook": "<on-screen hook text, max 8 words, written to stop the scroll>"}}

{rules}

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
    # 2x kandidaten opvragen; de beste n blijven over na snappen en ontdubbelen
    import anthropic

    prompt = PROMPT.format(ctype=cfg.get("content_type", "general"), criteria=cfg.get("criteria", ""), rules=rules_for_prompt(cfg.get("rules")),
                           n=cfg["clips"] * 2, lo=cfg["min_duration"], hi=cfg["max_duration"],
                           transcript=build_transcript(words))
    resp = anthropic.Anthropic().messages.create(
        model=cfg["llm"]["model"], max_tokens=4000,
        messages=[{"role": "user", "content": prompt}])
    return parse_highlights(resp.content[0].text)


HOOK_WORDS = {"never", "secret", "crazy", "insane", "actually", "wrong", "mistake", "truth", "why",
              "how", "biggest", "best", "worst", "nobody", "everyone", "always", "free", "wait", "wow",
              "no way", "oh my god", "what"}


def _heuristic(words: list[Word], cfg: dict, energy=None) -> list[Highlight]:
    """Schuivend venster; score = spreektempo, hook-woorden, vragen/uitroepen en audio-energie."""
    if not words:
        return []
    target = (cfg["min_duration"] + cfg["max_duration"]) / 2
    ew = cfg.get("energy_weight", 1.0)
    cands, t = [], words[0].start
    while t < words[-1].end - cfg["min_duration"]:
        win = [w for w in words if t <= w.start < t + target and not is_filler(w)]
        if win:
            density = len(win) / target
            punch = sum(w.text.endswith(("?", "!")) for w in win)
            hooks = sum(w.text.lower().strip(".,!?") in HOOK_WORDS for w in win[:12])  # hook vooraan
            loud = mean_energy(energy, t, t + target) if energy is not None and len(energy) else 0.0
            cands.append(Highlight(t, t + target, density + 0.4 * punch + 0.8 * hooks + ew * 2 * loud,
                                   "heuristic", " ".join(w.text for w in win[:6]).rstrip(".,")))
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


def find_highlights(words: list[Word], cfg: dict, energy=None) -> list[Highlight]:
    hs = []
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            hs = _llm(words, cfg)
        except Exception as e:  # netwerk/JSON-fout -> heuristiek
            print(f"LLM-highlights mislukt ({e}); heuristiek gebruikt")
    if not hs:
        hs = _heuristic(words, cfg, energy)
    snapped = []
    for h in hs:
        s, e = snap_to_sentences(words, h.start, h.end, cfg["min_duration"], cfg["max_duration"])
        snapped.append(Highlight(s, e, h.score, h.reason, h.hook))
    return _dedupe(snapped, cfg["clips"])
