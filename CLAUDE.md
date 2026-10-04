# Clipping – werkwijze

Doel: uit een brontvideo + brief korte verticale clips (9:16, 1080x1920) maken voor TikTok, Reels en YouTube Shorts. Antwoord altijd in het Nederlands.

## Mappenstructuur
- `campaigns/<campagnenaam>/brief.md` – de opdracht
- `campaigns/<campagnenaam>/transcript.txt|json` – Whisper-transcriptie
- `campaigns/<campagnenaam>/clips.json` – gekozen momenten (start, einde, crop-x, titel)
- `campaigns/<campagnenaam>/clips/` – de eindclips (.mp4)
- `campaigns/<campagnenaam>/captions.txt` – titel + post-caption per clip
- `tools/transcribe.py` – `python3 tools/transcribe.py x <audio.wav> <transcript.json>`
- `tools/make_clips.py` – `python3 tools/make_clips.py campaigns/<naam>`

## Stappen voor een nieuwe campagne
1. Maak `campaigns/<naam>/` en zet de brief in `brief.md`.
2. Download de bron buiten de repo (`gdown`), extraheer audio (`ffmpeg -ac 1 -ar 16000`), transcribeer met faster-whisper (model komt van HuggingFace; vereist `*.hf.co` in de netwerkpolicy).
3. Kies 5-8 momenten van >15 s met sterke hook, beginnend en eindigend op een zin. Vul `clips.json`.
4. Draai `tools/make_clips.py`, controleer enkele frames, commit en push naar de aangewezen branch.

## Leren van resultaten
- Lees voor het kiezen van momenten en het schrijven van titels altijd `LEERPUNTEN.md`.
- Na het posten: synchroniseer de cijfers (Clip Studio, tabblad Statistieken, of via de Metricool-connector) en werk `LEERPUNTEN.md` bij.
- Titel per clip: concrete bewering of vraag uit de clip, in het Engels als de bron Engels is. Zet titel en post-caption in `captions.txt`.

## Waar staat wat
Zie `README.md` (hoofdindex) voor alle links: repo, Clip Studio-site, TikTok-account en Metricool.
