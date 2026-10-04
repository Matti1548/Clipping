import copy
from pathlib import Path

import yaml

DEFAULTS = {
    "language": "en",
    "content_type": "auto",
    "profiles": {},
    "whisper_model": "small",
    "clips": 5,
    "min_duration": 15,
    "max_duration": 60,
    "platform": "tiktok",
    "llm": {"model": "claude-sonnet-5-5"},
    "video": {"width": 1080, "height": 1920, "fps": 30, "face_tracking": True,
              "tighten_pauses": True, "max_pause": 0.5,
              "remove_fillers": True, "layout": "crop", "zoom": 0.05, "progress_bar": True},
    "captions": {
        "font": "Arial",
        "size": 84,
        "primary_color": "#FFFFFF",
        "highlight_color": "#FFE600",
        "outline_color": "#000000",
        "outline": 6,
        "words_per_line": 3,
        "margin_bottom": 420,
        "uppercase": True,
    },
}


def _merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path: str | None = None, overrides: dict | None = None) -> dict:
    cfg = copy.deepcopy(DEFAULTS)
    if path and Path(path).exists():
        cfg = _merge(cfg, yaml.safe_load(Path(path).read_text()) or {})
    return _merge(cfg, {k: v for k, v in (overrides or {}).items() if v is not None})
