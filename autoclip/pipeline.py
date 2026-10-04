import json
import tempfile
from dataclasses import asdict
from pathlib import Path

from .captions import build_ass
from .highlights import find_highlights
from .metadata import make_metadata
from .reframe import face_center_x
from .render import download, render_clip
from .sentences import words_between
from .transcribe import transcribe


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
            cw = words_between(words, h.start, h.end)
            name = f"clip_{i:02d}"
            ass = out / f"{name}.ass"
            ass.write_text(build_ass(cw, h.start, cfg["captions"], cfg["video"]), encoding="utf-8")
            fx = face_center_x(video, h.start, h.end) if cfg["video"]["face_tracking"] else 0.5
            mp4 = out / f"{name}.mp4"
            render_clip(video, h.start, h.end, str(ass), str(mp4), fx, cfg["video"])
            ass.unlink()
            meta = make_metadata(" ".join(w.text for w in cw), h, cfg)
            (out / f"{name}.json").write_text(json.dumps({
                "title": meta.title, "caption": meta.caption, "hashtags": meta.hashtags,
                "score": h.score, "reason": h.reason, "start": h.start, "end": h.end,
            }, ensure_ascii=False, indent=2), encoding="utf-8")
            results.append(mp4)
        print(f"4/4 Klaar: {len(results)} clips in {out}/")
        return results
