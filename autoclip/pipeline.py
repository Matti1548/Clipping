import json
import tempfile
from dataclasses import asdict
from pathlib import Path

from .captions import build_ass
from .highlights import find_highlights
from .metadata import make_metadata
from .audio import energy_per_second
from .profiles import apply_profile, classify
from .reframe import face_track
from .jumpcut import keep_segments, remap_time, remap_words
from .render import download, render_clip
from .sentences import words_between
from .transcribe import transcribe


def make_clip(video: str, words: list, h, out: Path, name: str, cfg: dict) -> Path:
    """Render \u00e9\u00e9n clip + metadata-JSON. Los aanroepbaar met een bestaand transcript."""
    cw = words_between(words, h.start, h.end)
    vcfg = cfg["video"]
    fill = vcfg.get("remove_fillers", True)
    if vcfg.get("tighten_pauses", True):
        segs = keep_segments(cw, h.start, h.end, vcfg.get("max_pause", 0.5), drop_fillers=fill)
    else:
        segs = [(h.start, h.end)]
    new_words = remap_words(cw, segs, drop_fillers=fill)
    ass = out / f"{name}.ass"
    ass.write_text(build_ass(new_words, 0.0, cfg["captions"], vcfg, hook=h.hook), encoding="utf-8")
    track = []
    if vcfg["face_tracking"] and vcfg.get("layout") == "crop":
        track = [(remap_time(t, segs), x) for t, x in face_track(video, h.start, h.end)]
    mp4 = out / f"{name}.mp4"
    render_clip(video, segs, str(ass), str(mp4), track, vcfg)
    ass.unlink()
    meta = make_metadata(" ".join(w.text for w in cw), h, cfg)
    (out / f"{name}.json").write_text(json.dumps({
        "title": meta.title, "caption": meta.caption, "hashtags": meta.hashtags,
        "score": h.score, "reason": h.reason, "start": h.start, "end": h.end,
        "content_type": cfg.get("content_type"),
        "duration": round(sum(b - a for a, b in segs), 2),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return mp4


def run(source: str, out_dir: str, cfg: dict) -> list[Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        video = download(source, tmp) if source.startswith(("http://", "https://")) else source
        if not Path(video).exists():
            raise FileNotFoundError(video)
        print("1/4 Transcriberen...")
        words = transcribe(video, cfg["whisper_model"], cfg["language"])
        if not words:
            raise RuntimeError("Geen spraak gevonden in de video.")
        ctype = cfg["content_type"]
        if ctype == "auto":
            ctype = classify(" ".join(w.text for w in words), cfg)
        cfg = apply_profile(cfg, ctype)
        print(f"2/4 Highlights zoeken (videotype: {cfg['content_type']})...")
        highlights = find_highlights(words, cfg, energy_per_second(video))
        results = []
        for i, h in enumerate(highlights, 1):
            print(f"3/4 Clip {i}/{len(highlights)} renderen ({h.start:.0f}s-{h.end:.0f}s)...")
            results.append(make_clip(video, words, h, out, f"clip_{i:02d}", cfg))
        print(f"4/4 Klaar: {len(results)} clips in {out}/")
        return results
