"""Achtergrond toevoegen (muziek en/of achtergrondbeeld) -- alleen als het mag en de clip er beter van wordt."""
import hashlib
import json
import os
import re
from pathlib import Path

AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm"}
# Stem-gedreven content: muziek leidt af. Alleen 'lichte' types krijgen standaard muziek (zonder LLM).
MUSIC_FRIENDLY = {"vlog", "educational", "general"}


def list_assets(directory: str | None, exts: set[str]) -> list[str]:
    if not directory or not Path(directory).is_dir():
        return []
    return sorted(str(p) for p in Path(directory).iterdir() if p.suffix.lower() in exts)


def decide(transcript: str, ctype: str, layout: str, rules: dict | None, cfg: dict) -> dict:
    """Geeft {"music": pad|None, "background": pad|None, "reason": str}."""
    bcfg = cfg.get("background", {})
    music_files = list_assets(bcfg.get("music_dir"), AUDIO_EXT) if bcfg.get("enabled", True) else []
    bg_files = list_assets(bcfg.get("video_dir"), VIDEO_EXT) if bcfg.get("enabled", True) else []
    r = rules or {}
    notes = []
    if music_files and r.get("allow_music") is False:
        music_files, notes = [], notes + ["muziek niet toegestaan volgens de regels"]
    if bg_files and r.get("allow_background") is False:
        bg_files, notes = [], notes + ["achtergrondbeeld niet toegestaan volgens de regels"]
    if bg_files and layout != "fit_blur":
        bg_files = []  # bij een volledige 9:16-crop is er geen achtergrond zichtbaar
    if not music_files and not bg_files:
        return {"music": None, "background": None, "reason": "; ".join(notes) or "geen assets/niet nodig"}

    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            import anthropic
            opts = {"music": [Path(f).name for f in music_files], "background": [Path(f).name for f in bg_files]}
            prompt = (
                f"You edit short-form video. Decide whether adding background elements would genuinely "
                f"IMPROVE this clip. Default to adding nothing: skip music when speech carries emotion, "
                f"seriousness or needs full attention; skip background footage if the main picture already "
                f"engages. Content type: {ctype}. Rules: {json.dumps(notes + (r.get('notes') or []))}\n"
                f"Available files: {json.dumps(opts)}\n"
                'Reply ONLY with JSON {"music": "<filename or null>", "background": "<filename or null>", '
                '"reason": "<one sentence>"}\n\nTranscript:\n' + transcript[:2500])
            resp = anthropic.Anthropic().messages.create(
                model=cfg["llm"]["model"], max_tokens=200, messages=[{"role": "user", "content": prompt}])
            d = json.loads(re.search(r"\{.*\}", resp.content[0].text, re.S).group(0))
            pick = lambda name, files: next((f for f in files if Path(f).name == name), None)
            return {"music": pick(d.get("music"), music_files), "background": pick(d.get("background"), bg_files),
                    "reason": str(d.get("reason", ""))}
        except Exception as e:
            print(f"LLM-achtergrondkeuze mislukt ({e}); vaste regels gebruikt")

    # Fallback zonder LLM: voorzichtig. Alleen muziek, alleen voor lichte content-types, nooit beeld.
    if music_files and ctype in MUSIC_FRIENDLY:
        i = int(hashlib.md5(transcript.encode()).hexdigest(), 16) % len(music_files)
        return {"music": music_files[i], "background": None, "reason": f"zachte muziek past bij {ctype}"}
    return {"music": None, "background": None, "reason": f"{ctype}: stem staat centraal, niets toegevoegd"}
