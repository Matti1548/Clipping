"""Titel, caption en hashtags per clip."""
import json
import os
import re
from collections import Counter

from .models import ClipMeta, Highlight

_STOP = set("de het een en van is dat die in te op voor met niet ook maar als dan zo je ik we "
            "the a an and of is that to in it you i for on with this are was be have".split())


def _fallback(transcript: str, h: Highlight) -> ClipMeta:
    words = [w for w in re.findall(r"[\wÀ-ÿ']+", transcript.lower()) if len(w) > 3 and w not in _STOP]
    tags = ["#" + w for w, _ in Counter(words).most_common(5)] + ["#fyp", "#shorts"]
    title = (h.hook or transcript[:60]).strip()[:70]
    return ClipMeta(title=title, caption=f"{title} 👇 Volg voor meer!", hashtags=tags)


def make_metadata(transcript: str, h: Highlight, cfg: dict) -> ClipMeta:
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            import anthropic

            prompt = (f"Schrijf voor een korte video ({cfg['platform']}) in de taal van het transcript "
                      "een pakkende titel (max 70 tekens), een caption met call-to-action en 5-10 "
                      'relevante hashtags. Antwoord ALLEEN met JSON: {"title":"","caption":"","hashtags":[]}\n\n'
                      f"Transcript:\n{transcript}")
            r = anthropic.Anthropic().messages.create(
                model=cfg["llm"]["model"], max_tokens=600,
                messages=[{"role": "user", "content": prompt}])
            d = json.loads(re.search(r"\{.*\}", r.content[0].text, re.S).group(0))
            tags = [t if t.startswith("#") else "#" + t for t in d["hashtags"]]
            return ClipMeta(d["title"], d["caption"], tags)
        except Exception as e:
            print(f"LLM-metadata mislukt ({e}); fallback gebruikt")
    return _fallback(transcript, h)
