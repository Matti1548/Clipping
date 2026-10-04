"""Geanimeerde TikTok-captions als ASS-ondertitels met woord-highlighting."""
from .models import Word


def _ass_color(hex_rgb: str) -> str:
    h = hex_rgb.lstrip("#")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H00{b}{g}{r}".upper()


def _ts(t: float) -> str:
    t = max(t, 0)
    cs = round(t * 100)
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def _esc(text: str, upper: bool) -> str:
    text = text.upper() if upper else text
    return text.replace("\\", "").replace("{", "(").replace("}", ")")


def build_ass(words: list[Word], clip_start: float, cfg: dict, video: dict,
              hook: str = "", hook_secs: float = 3.0) -> str:
    c = cfg
    primary, hl, outline = (_ass_color(c["primary_color"]), _ass_color(c["highlight_color"]),
                            _ass_color(c["outline_color"]))
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {video['width']}
PlayResY: {video['height']}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hook,{c['font']},{int(c['size']*0.75)},{primary},{primary},{outline},&H99000000,1,0,0,0,100,100,0,0,3,{c['outline']//2},0,8,80,80,260,1
Style: Cap,{c['font']},{c['size']},{primary},{primary},{outline},&H00000000,1,0,0,0,100,100,0,0,1,{c['outline']},2,2,60,60,{c['margin_bottom']},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    n = max(1, c["words_per_line"])
    lines = []
    for i in range(0, len(words), n):
        chunk = words[i:i + n]
        for j, w in enumerate(chunk):
            start = w.start - clip_start
            end = (chunk[j + 1].start if j + 1 < len(chunk) else w.end) - clip_start
            parts = []
            for k, o in enumerate(chunk):
                txt = _esc(o.text, c["uppercase"])
                parts.append(f"{{\\c{hl}}}{txt}{{\\c{primary}}}" if k == j else txt)
            lines.append(f"Dialogue: 0,{_ts(start)},{_ts(end)},Cap,,0,0,0,,{' '.join(parts)}")
    if hook:
        lines.insert(0, f"Dialogue: 1,{_ts(0)},{_ts(hook_secs)},Hook,,0,0,0,,{_esc(hook, c['uppercase'])}")
    return head + "\n".join(lines) + "\n"
