#!/usr/bin/env python3
"""Gebruik: python clip.py input.mp4 --clips 5 --duration 30"""
import argparse

from autoclip.config import load_config
from autoclip.pipeline import run


def main() -> None:
    p = argparse.ArgumentParser(description="Maak automatisch korte clips met captions.")
    p.add_argument("source", help="videobestand of URL")
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--out", default="output")
    p.add_argument("--clips", type=int)
    p.add_argument("--duration", type=int, help="gewenste clipduur in seconden (max = duur, min = 60%%)")
    p.add_argument("--language", help="standaard en")
    p.add_argument("--type", dest="content_type",
                   choices=["auto", "podcast", "interview", "gaming", "vlog", "educational", "general"])
    p.add_argument("--platform", choices=["tiktok", "youtube", "instagram"])
    p.add_argument("--rules", help="campagne-regels (pdf/docx/md/txt)")
    p.add_argument("--music-dir")
    p.add_argument("--backgrounds-dir")
    p.add_argument("--no-background", action="store_true", help="nooit muziek/achtergrond toevoegen")
    a = p.parse_args()
    over = {"clips": a.clips, "language": a.language, "platform": a.platform, "content_type": a.content_type}
    if a.duration:
        over.update(max_duration=a.duration, min_duration=int(a.duration * 0.6))
    cfg = load_config(a.config, over)
    if a.rules:
        cfg["rules_file"] = a.rules
    if a.music_dir:
        cfg["background"]["music_dir"] = a.music_dir
    if a.backgrounds_dir:
        cfg["background"]["video_dir"] = a.backgrounds_dir
    if a.no_background:
        cfg["background"]["enabled"] = False
    run(a.source, a.out, cfg)


if __name__ == "__main__":
    main()
