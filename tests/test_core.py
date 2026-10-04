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
