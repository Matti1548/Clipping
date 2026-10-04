import subprocess
from pathlib import Path

from .jumpcut import remap_time


def _esc_filter_path(p: str) -> str:
    return p.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def pan_expr(keys: list[tuple[float, float]]) -> str:
    """Lineair interpolerende ffmpeg-expressie voor de crop-positie (0..1) over de tijd."""
    if not keys:
        return "0.5"
    pts = [keys[0]]
    for t, x in keys[1:]:
        if t > pts[-1][0] + 0.05:
            pts.append((t, x))
    expr = f"{pts[0][1]:.4f}"
    for (t0, x0), (t1, x1) in zip(pts, pts[1:]):
        if abs(x1 - x0) > 1e-4:
            expr += f"+({x1 - x0:.4f})*clip((t-{t0:.3f})/{t1 - t0:.3f},0,1)"
    return expr


def zoom_expr(segs: list[tuple[float, float]], amount: float) -> str:
    """Om-en-om inzoomen per segment (jump-cut punch-in), in de tijdlijn van de ingekorte clip."""
    acc, terms = 0.0, []
    for i, (a, b) in enumerate(segs):
        d = b - a
        if i % 2 == 1:
            terms.append(f"between(t,{acc:.3f},{acc + d:.3f})")
        acc += d
    return f"(1+{amount}*({'+'.join(terms)}))" if terms and amount else "1"


def build_filter(segs, ass_path, track, vcfg) -> str:
    w, h, fps = vcfg["width"], vcfg["height"], vcfg["fps"]
    dur = sum(b - a for a, b in segs)
    parts, labels = [], ""
    for i, (a, b) in enumerate(segs):
        parts.append(f"[0:v]trim={a:.3f}:{b:.3f},setpts=PTS-STARTPTS[v{i}]")
        parts.append(f"[0:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS[a{i}]")
        labels += f"[v{i}][a{i}]"
    parts.append(f"{labels}concat=n={len(segs)}:v=1:a=1[cv][ca]")

    if vcfg.get("layout") == "fit_blur":  # gameplay/landscape: scherp in het midden, wazige achtergrond
        parts.append(f"[cv]split[bg][fg];"
                     f"[bg]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},boxblur=30:5[b];"
                     f"[fg]scale={w}:-2[f];[b][f]overlay=(W-w)/2:(H-h)/2,setsar=1,fps={fps}[framed]")
    else:  # 9:16 crop, optioneel dynamisch rond het gezicht
        fx = pan_expr(track)
        parts.append(f"[cv]crop=w='min(iw,ih*{w}/{h})':h=ih:x='max(0,min(iw-ow,({fx})*iw-ow/2))':y=0,"
                     f"scale={w}:{h}:flags=lanczos,setsar=1,fps={fps}[framed]")

    last = "framed"
    z = zoom_expr(segs, vcfg.get("zoom", 0))
    if z != "1":
        parts.append(f"[{last}]scale=w='trunc({w}*{z}/2)*2':h='trunc({h}*{z}/2)*2':eval=frame,crop={w}:{h}[zoomed]")
        last = "zoomed"
    if vcfg.get("progress_bar", True):
        parts.append(f"[{last}]drawbox=x=0:y=ih-14:w='iw*t/{dur:.3f}':h=14:color=white@0.9:t=fill[bar]")
        last = "bar"
    parts.append(f"[{last}]ass='{_esc_filter_path(ass_path)}'[vout]")
    parts.append("[ca]loudnorm=I=-14:TP=-1.5:LRA=11[aout]")
    return ";".join(parts)


def render_clip(video: str, segs, ass_path: str, out: str, track, vcfg: dict) -> None:
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", video,
           "-filter_complex", build_filter(segs, ass_path, track, vcfg),
           "-map", "[vout]", "-map", "[aout]", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
           "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)


def download(url: str, dest_dir: str) -> str:
    """Download een URL met yt-dlp en geef het bestandspad terug."""
    out = str(Path(dest_dir) / "source.%(ext)s")
    subprocess.run(["yt-dlp", "-f", "bv*[height<=1080]+ba/b", "--merge-output-format", "mp4",
                    "-o", out, url], check=True)
    return str(next(Path(dest_dir).glob("source.*")))
