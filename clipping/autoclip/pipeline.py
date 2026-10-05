import json
import tempfile
from pathlib import Path

from .audio import energy_per_second
from .background import decide
from .captions import build_ass
from .highlights import find_highlights
from .jumpcut import keep_segments, remap_time, remap_words
from .metadata import make_metadata
from .profiles import apply_profile, classify
from .reframe import face_track
from .render import download, render_clip
from .rules import apply_to_config, banned_hits, check_compliance, enforce_metadata, load_rules
from .sentences import sentence_spans, words_between
from .transcribe import transcribe


def banned_sentence_words(cw, rules):
    """Woorden (op identiteit) van zinnen waarin een verboden woord wordt uitgesproken."""
    ids = set()
    if rules and rules["banned_words"]:
        for a, b in sentence_spans(cw):
            if banned_hits(" ".join(w.text for w in cw[a:b + 1]), rules):
                ids.update(id(w) for w in cw[a:b + 1])
    return ids


def _segments(cw, h, vcfg, min_dur, drop=None):
    """Knip pauzes/opvulwoorden/verboden zinnen, maar blijf boven de minimale duur (versoepel stapsgewijs)."""
    fill = vcfg.get("remove_fillers", True)
    gap = vcfg.get("max_pause", 0.5)
    if vcfg.get("tighten_pauses", True):
        for g in (gap, gap * 2, gap * 4):
            segs = keep_segments(cw, h.start, h.end, g, drop_fillers=fill, drop=drop)
            if sum(b - a for a, b in segs) >= min_dur:
                return segs
    if drop:  # alleen de verboden zinnen eruit, de rest ongemoeid
        return keep_segments(cw, h.start, h.end, 1e9, drop_fillers=False, drop=drop)
    return [(h.start, h.end)]


def make_clip(video: str, words: list, h, out: Path, name: str, cfg: dict) -> Path:
    """Render een clip + JSON (metadata, achtergrondkeuze, compliance). Los aanroepbaar met een transcript."""
    rules = cfg.get("rules")
    cw = words_between(words, h.start, h.end)
    vcfg = cfg["video"]
    fill = vcfg.get("remove_fillers", True)
    ban_ids = banned_sentence_words(cw, rules)
    drop = (lambda w: id(w) in ban_ids) if ban_ids else None
    segs = _segments(cw, h, vcfg, cfg["min_duration"], drop)
    new_words = remap_words(cw, segs, drop_fillers=fill, drop=drop)
    cw = [w for w in cw if id(w) not in ban_ids]
    on_screen = list(rules["on_screen_text"]) if rules else []
    ass = out / f"{name}.ass"
    ass.write_text(build_ass(new_words, 0.0, cfg["captions"], vcfg, hook=h.hook, tag=" ".join(on_screen)),
                   encoding="utf-8")
    track = []
    if vcfg["face_tracking"] and vcfg.get("layout") == "crop":
        track = [(remap_time(t, segs), x) for t, x in face_track(video, h.start, h.end)]
    spoken = " ".join(w.text for w in cw)
    bg = decide(spoken, cfg.get("content_type", "general"), vcfg.get("layout", "crop"), rules, cfg)
    mp4 = out / f"{name}.mp4"
    render_clip(video, segs, str(ass), str(mp4), track, vcfg, bg["music"], bg["background"],
                cfg.get("background", {}).get("music_volume", 0.12))
    ass.unlink()
    meta = enforce_metadata(make_metadata(spoken, h, cfg), rules)
    duration = sum(b - a for a, b in segs)
    report = check_compliance(rules, duration=duration, spoken=spoken, meta=meta, music=bg["music"],
                              background=bg["background"], on_screen=on_screen)
    (out / f"{name}.json").write_text(json.dumps({
        "title": meta.title, "caption": meta.caption, "hashtags": meta.hashtags,
        "score": h.score, "reason": h.reason, "start": h.start, "end": h.end,
        "content_type": cfg.get("content_type"), "duration": round(duration, 2),
        "background": {k: (Path(v).name if v and k != "reason" else v) for k, v in bg.items()},
        "compliance": report,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return mp4


def run(source: str, out_dir: str, cfg: dict) -> list[Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rules = load_rules(cfg.get("rules_file"), cfg)
    if rules:
        (out / "rules_parsed.json").write_text(json.dumps(rules, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"0/4 Campagneregels ingelezen ({cfg['rules_file']}) -> controleer {out}/rules_parsed.json")
    with tempfile.TemporaryDirectory() as tmp:
        video = download(source, tmp) if source.startswith(("http://", "https://")) else source
        if not Path(video).exists():
            raise FileNotFoundError(video)
        cfg = apply_to_config(cfg, rules)
        print("1/4 Transcriberen...")
        words = transcribe(video, cfg["whisper_model"], cfg["language"])
        if not words:
            raise RuntimeError("Geen spraak gevonden in de video.")
        ctype = cfg["content_type"]
        if ctype == "auto":
            ctype = classify(" ".join(w.text for w in words), cfg)
        cfg = apply_profile(cfg, ctype)  # raakt de duurlimieten uit de regels niet aan
        print(f"2/4 Highlights zoeken (videotype: {cfg['content_type']})...")
        highlights = find_highlights(words, cfg, energy_per_second(video))
        results = []
        for i, h in enumerate(highlights, 1):
            print(f"3/4 Clip {i}/{len(highlights)} renderen ({h.start:.0f}s-{h.end:.0f}s)...")
            mp4 = make_clip(video, words, h, out, f"clip_{i:02d}", cfg)
            rep = json.loads(mp4.with_suffix(".json").read_text())["compliance"]
            bad = [c["check"] for c in rep["checks"] if c["ok"] is False]
            print("   regels: " + ("OK" if not bad else "NIET OK -> " + ", ".join(bad)))
            results.append(mp4)
        print(f"4/4 Klaar: {len(results)} clips in {out}/")
        return results
