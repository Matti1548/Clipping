import json
import tempfile
from dataclasses import asdict
from pathlib import Path

from .captions import build_ass
from .highlights import find_highlights
from .metadata import make_metadata
from .reframe import face_center_x
from .jumpcut import keep_segments, remap_words
from .render import download, render_clip
from .sentences import words_between
from .transcribe import transcribe


def make_clip(video: str, words: list, h, out: Path, name: str, cfg: dict) -> Path:
    """Render \u00e9\u00e9n clip + metadata-JSON. Los aanroepbaar met een bestaand transcript."""
    cw = words_between(words, h.start, h.end)
    vcfg = cfg["video"]
    if vcfg.get("tighten_pauses", True):
        segs = keep_segments(cw, h.start, h.end, vcfg.get("max_pause", 0.5))
    else:
        segs = [(h.start, h.end)]
    new_words = remap_words(cw, segs)
    ass = out / f"{name}.ass"
    ass.write_text(build_ass(new_words, 0.0, cfg["captions"], vcfg, hook=h.hook), encoding="utf-8")
    fx = face_center_x(video, h.start, h.end) if vcfg["face_tracking"] else 0.5
    mp4 = out / f"{name}.mp4"
    render_clip(video, segs, str(ass), str(mp4), fx, vcfg)
    ass.unlink()
    meta = make_metadata(" ".join(w.text for w in cw), h, cfg)
    (out / f"{name}.json").write_text(json.dumps({
        "title": meta.title, "caption": meta.caption, "hashtags": meta.hashtags,
        "score": h.score, "reason": h.reason, "start": h.start, "end": h.end,
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
        print("2/4 Highlights zoeken...")
        highlights = find_highlights(words, cfg)
        results = []
        for i, h in enumerate(highlights, 1):
            print(f"3/4 Clip {i}/{len(highlights)} renderen ({h.start:.0f}s-{h.end:.0f}s)...")
            results.append(make_clip(video, words, h, out, f"clip_{i:02d}", cfg))
        print(f"4/4 Klaar: {len(results)} clips in {out}/")
        return results
