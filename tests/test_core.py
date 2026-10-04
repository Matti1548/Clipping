from autoclip.captions import build_ass
from autoclip.config import load_config
from autoclip.highlights import _dedupe, parse_highlights
from autoclip.models import Highlight, Word
from autoclip.sentences import sentence_spans, snap_to_sentences


def make_words():
    # 3 zinnen van ~10s elk
    words, t = [], 0.0
    for s in range(3):
        for i in range(10):
            txt = f"woord{s}{i}" + ("." if i == 9 else "")
            words.append(Word(txt, t, t + 0.9))
            t += 1.0
    return words


def test_sentence_spans():
    assert sentence_spans(make_words()) == [(0, 9), (10, 19), (20, 29)]


def test_snap_to_sentence_boundaries():
    s, e = snap_to_sentences(make_words(), 0.4, 19.0, 15, 40)
    assert s == 0.0 and abs(e - 19.9) < 1e-6


def test_snap_respects_max():
    s, e = snap_to_sentences(make_words(), 0, 29, 5, 12)
    assert e - s <= 12


def test_parse_highlights_tolerates_noise():
    raw = 'hier is het: [{"start": 1, "end": 20, "score": 9, "reason": "x"}, {"bad": 1}] klaar'
    hs = parse_highlights(raw)
    assert len(hs) == 1 and hs[0].score == 9


def test_dedupe_no_overlap():
    hs = [Highlight(0, 30, 9), Highlight(10, 40, 8), Highlight(40, 70, 5)]
    out = _dedupe(hs, 3)
    assert [(h.start, h.end) for h in out] == [(0, 30), (40, 70)]


def test_ass_highlights_current_word():
    cfg = load_config()
    ass = build_ass(make_words()[:3], 0.0, cfg["captions"], cfg["video"])
    assert ass.count("Dialogue:") == 3
    assert "&H0000E6FF" in ass  # highlightkleur #FFE600 in BGR
    assert "WOORD00" in ass


def test_config_override():
    assert load_config(None, {"clips": 3, "language": None})["clips"] == 3


def test_ass_dialogue_matches_event_format():
    cfg = load_config()
    ass = build_ass(make_words()[:3], 0.0, cfg["captions"], cfg["video"])
    fmt = next(l for l in ass.splitlines() if l.startswith("Format: Layer"))
    n_fields = len(fmt.split(":", 1)[1].split(","))
    for line in (l for l in ass.splitlines() if l.startswith("Dialogue:")):
        assert len(line.split(":", 1)[1].split(",", n_fields - 1)) == n_fields
        assert not line.split(",", n_fields - 1)[-1].startswith("0,")


def test_keep_segments_cuts_long_pauses():
    from autoclip.jumpcut import keep_segments, remap_words
    ws = [Word("a", 0, 1), Word("b", 1.1, 2), Word("c", 5, 6)]  # pauze van 3s voor "c"
    segs = keep_segments(ws, 0, 6, max_gap=0.5, pad=0.1)
    assert len(segs) == 2
    total = sum(b - a for a, b in segs)
    assert total < 4.5  # was 6s
    new = remap_words(ws, segs)
    assert len(new) == 3 and new[2].start < 3.0 and new[2].start >= new[1].end


def test_fillers_are_cut_and_dropped():
    from autoclip.jumpcut import is_filler, keep_segments, remap_words
    ws = [Word("So", 0, 0.3), Word("um", 0.35, 0.8), Word("this", 0.85, 1.2), Word("works.", 1.2, 1.8)]
    assert is_filler(ws[1]) and not is_filler(ws[0])
    segs = keep_segments(ws, 0, 2, max_gap=0.5, pad=0.02)
    assert len(segs) == 2  # "So" | "this works."
    assert [w.text for w in remap_words(ws, segs)] == ["So", "this", "works."]


def test_remap_time():
    from autoclip.jumpcut import remap_time
    segs = [(0, 2), (5, 7)]
    assert remap_time(1, segs) == 1 and remap_time(6, segs) == 3 and remap_time(3, segs) == 2


def test_smooth_track_fills_gaps_and_ignores_jitter():
    from autoclip.reframe import smooth_track
    s = [(i * 0.4, x) for i, x in enumerate([0.5, 0.51, None, 0.49, 0.52, 0.5, 0.9, 0.9, 0.9, 0.9])]
    keys = smooth_track(s)
    assert all(abs(x - 0.5) < 0.06 for _, x in keys[:3])  # geen getril
    assert keys[-1][1] > 0.8  # volgt de echte beweging
    assert smooth_track([(0, None), (1, None)]) == []


def test_pan_expr_is_valid_and_interpolates():
    from autoclip.render import pan_expr
    e = pan_expr([(0, 0.2), (2, 0.8)])
    assert e.startswith("0.2000") and "clip((t-0.000)/2.000,0,1)" in e
    assert pan_expr([]) == "0.5"


def test_profiles():
    from autoclip.profiles import apply_profile
    cfg = apply_profile(load_config(), "gaming")
    assert cfg["video"]["layout"] == "fit_blur" and cfg["captions"]["words_per_line"] == 2
    assert apply_profile(load_config(), "nonsense")["content_type"] == "general"
    cfg = apply_profile(load_config(None, {"profiles": {"gaming": {"captions": {"size": 120}}}}), "gaming")
    assert cfg["captions"]["size"] == 120


def test_english_default():
    assert load_config()["language"] == "en"


def test_ass_wraps_long_hook():
    cfg = load_config()
    ass = build_ass(make_words()[:3], 0.0, cfg["captions"], cfg["video"], hook="a very long hook text " * 3)
    assert "WrapStyle: 0" in ass  # smart wrap, zodat de hook niet buiten beeld valt


# ---------- campagneregels & achtergrond ----------
SAMPLE = open("examples/campaign_novafit.md").read()


def test_parse_rules_regex():
    from autoclip.rules import parse_rules_regex
    r = parse_rules_regex(SAMPLE)
    assert (r["min_duration"], r["max_duration"], r["max_hashtags"]) == (20, 45, 5)
    assert r["required_hashtags"] == ["#NovaFitPartner", "#ad"] and r["required_mentions"] == ["@novafit"]
    assert set(r["banned_words"]) == {"fitbrand", "gympro"}
    assert r["allow_music"] is None  # 'copyrighted music' gaat over rechten, niet over muziek verbieden
    assert r["allow_background"] is True
    from autoclip.rules import parse_rules_regex as p
    assert p("- No music allowed in the video.")["allow_music"] is False


def test_read_docx(tmp_path):
    import zipfile
    from autoclip.rules import read_document
    f = tmp_path / "brief.docx"
    with zipfile.ZipFile(f, "w") as z:
        z.writestr("word/document.xml", "<w:p><w:r><w:t>Max 30 seconds</w:t></w:r></w:p><w:p><w:r><w:t>No music</w:t></w:r></w:p>")
    assert read_document(str(f)).splitlines()[:2] == ["Max 30 seconds", "No music"]


def test_apply_to_config_clamps_duration():
    from autoclip.rules import apply_to_config, parse_rules_regex
    cfg = apply_to_config(load_config(), parse_rules_regex(SAMPLE))
    assert (cfg["min_duration"], cfg["max_duration"]) == (20, 45)
    c2 = apply_to_config(load_config(), parse_rules_regex("- Clips under 12 seconds"))
    assert c2["max_duration"] == 12 and c2["min_duration"] < 12


def test_enforce_metadata_and_compliance():
    from autoclip.models import ClipMeta
    from autoclip.rules import check_compliance, enforce_metadata, parse_rules_regex
    r = parse_rules_regex(SAMPLE)
    m = enforce_metadata(ClipMeta("Why FitBrand fails", "Better than GymPro!", ["#fyp", "#gym", "#a", "#b", "#c", "#d"]), r)
    assert "fitbrand" not in m.title.lower() and "gympro" not in m.caption.lower()
    assert m.hashtags[:2] == ["#NovaFitPartner", "#ad"] and len(m.hashtags) == 5
    assert "@novafit" in m.caption
    rep = check_compliance(r, duration=30, spoken="hello", meta=m, music=None, background=None, on_screen=["#ad"])
    assert rep["compliant"] and any(c["ok"] is None for c in rep["checks"])  # notes = handmatig
    bad = check_compliance(r, duration=60, spoken="try fitbrand", meta=m, music=None, background=None, on_screen=[])
    assert not bad["compliant"]


def test_banned_sentence_is_cut_out_of_the_clip():
    from autoclip.jumpcut import keep_segments, remap_words
    from autoclip.pipeline import banned_sentence_words
    from autoclip.rules import parse_rules_regex
    ws = make_words()
    ws[15] = Word("FitBrand", ws[15].start, ws[15].end)  # verboden woord in zin 2 (10-20s)
    rules = parse_rules_regex("- Do not say FitBrand.")
    ids = banned_sentence_words(ws, rules)
    assert len(ids) == 10
    drop = lambda w: id(w) in ids
    segs = keep_segments(ws, 0, 30, max_gap=0.5, drop=drop)
    assert len(segs) == 2 and segs[0][1] <= 10.0 and segs[1][0] >= 19.9  # zin 2 volledig weg, ook de padding
    kept = remap_words(ws, segs, drop=drop)
    assert len(kept) == 20 and all(w.text != "FitBrand" for w in kept)


def test_background_decision_respects_rules(tmp_path, monkeypatch):
    from autoclip.background import decide
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    (tmp_path / "m.mp3").write_bytes(b"x")
    cfg = load_config(None, {"background": {"music_dir": str(tmp_path), "video_dir": str(tmp_path)}})
    allowed = decide("hello there", "vlog", "crop", None, cfg)
    assert allowed["music"] and allowed["background"] is None
    forbidden = decide("hello there", "vlog", "crop", {"allow_music": False, "allow_background": None, "notes": []}, cfg)
    assert forbidden["music"] is None and "niet toegestaan" in forbidden["reason"]
    assert decide("hello", "podcast", "crop", None, cfg)["music"] is None  # stem staat centraal
    off = load_config(None, {"background": {"enabled": False, "music_dir": str(tmp_path)}})
    assert decide("hello", "vlog", "crop", None, off)["music"] is None


def test_filter_graph_music_and_background():
    from autoclip.render import build_filter
    v = dict(load_config()["video"], layout="fit_blur")
    g = build_filter([(0, 5), (7, 10)], "x.ass", [], v, music_idx=2, bg_idx=1)
    assert "sidechaincompress" in g and "[1:v]" in g and "[2:a]" in g
    assert "boxblur" in build_filter([(0, 5)], "x.ass", [], v)


def test_on_screen_text_rule_is_parsed_and_rendered():
    from autoclip.rules import parse_rules_regex
    r = parse_rules_regex('- Show "#ad" on screen during the whole clip.')
    assert r["on_screen_text"] == ["#ad"] and r["notes"]
    cfg = load_config()
    ass = build_ass(make_words()[:3], 0.0, cfg["captions"], cfg["video"], tag="#ad")
    assert "Tag,,0,0,0,,#ad" in ass
