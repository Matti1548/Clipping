"""Profielen per videotype: highlight-criteria, layout, tempo en caption-stijl."""
import copy

from .config import _merge

PROFILES = {
    "podcast": {
        "criteria": "a bold or controversial claim, a surprising story, a strong opinion, a punchy "
                    "one-liner, an emotional or funny moment, advice that stands on its own",
        "video": {"layout": "crop", "face_tracking": True, "max_pause": 0.45, "zoom": 0.06},
        "captions": {"words_per_line": 3},
    },
    "interview": {
        "criteria": "a revealing answer, a surprising fact, a heated or funny exchange, a quotable line",
        "video": {"layout": "crop", "face_tracking": True, "max_pause": 0.45, "zoom": 0.06},
        "captions": {"words_per_line": 3},
    },
    "gaming": {
        "criteria": "a clutch play, a big reaction (shouting, laughing, rage), a funny fail, an "
                    "unexpected twist, a high-energy moment; the streamer's reaction matters as much as the action",
        "video": {"layout": "fit_blur", "face_tracking": False, "max_pause": 0.8, "zoom": 0.0},
        "captions": {"words_per_line": 2, "size": 96},
        "energy_weight": 3.0,
    },
    "vlog": {
        "criteria": "a funny or emotional moment, a relatable observation, a surprising reveal, a story with a punchline",
        "video": {"layout": "crop", "face_tracking": True, "max_pause": 0.5, "zoom": 0.05},
        "captions": {"words_per_line": 3},
    },
    "educational": {
        "criteria": "one actionable tip, a myth being busted, a clear explanation of a hard concept, "
                    "a numbered list, a 'most people get this wrong' moment",
        "video": {"layout": "crop", "face_tracking": True, "max_pause": 0.5, "zoom": 0.04},
        "captions": {"words_per_line": 3},
    },
    "general": {
        "criteria": "a strong hook, a self-contained idea, emotion or humor, a surprising insight",
        "video": {"layout": "crop", "face_tracking": True, "max_pause": 0.5, "zoom": 0.05},
        "captions": {"words_per_line": 3},
    },
}


def apply_profile(cfg: dict, content_type: str) -> dict:
    """Profiel als basis; eigen `profiles:`-sectie in config.yaml wint daarvan."""
    ctype = content_type if content_type in PROFILES else "general"
    prof = _merge(PROFILES[ctype], (cfg.get("profiles") or {}).get(ctype, {}))
    out = _merge(cfg, {k: v for k, v in prof.items() if k != "criteria"})
    out["content_type"] = ctype
    out["criteria"] = prof["criteria"]
    return out


def classify(transcript: str, cfg: dict) -> str:
    """Raad het videotype uit het transcript (LLM), anders 'general'."""
    import os
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return "general"
    try:
        import anthropic
        r = anthropic.Anthropic().messages.create(
            model=cfg["llm"]["model"], max_tokens=10,
            messages=[{"role": "user", "content":
                       f"Classify this video transcript as one of: {', '.join(k for k in PROFILES if k != 'general')}, "
                       f"general. Answer with the single word only.\n\n{transcript[:3000]}"}])
        word = r.content[0].text.strip().lower()
        return word if word in PROFILES else "general"
    except Exception:
        return "general"
