# Clipping – auto-clip tool

Geef een lange video (bestand of URL) en krijg korte, 9:16 clips met geanimeerde captions, titel en hashtags – klaar voor TikTok, YouTube Shorts en Reels.

## Pipeline
transcriptie (faster-whisper) → highlight-detectie (Claude, of heuristiek zonder API-sleutel) → knippen op zinsgrenzen → 9:16 met gezichtstracking → captions met woord-highlighting → metadata → export.

## Videotypes
`--type auto` (standaard) laat Claude het type raden; of kies `podcast`, `interview`, `gaming`, `vlog`, `educational`, `general`. Elk profiel stelt highlight-criteria, layout (gezichtstracking-crop of `fit_blur` voor gameplay), pauzelengte, zoom en captionstijl in. Gaming weegt audio-energie (schreeuwen, actie) zwaarder mee. Eigen aanpassingen: sectie `profiles:` in `config.yaml`.

## Editing
Pauzes en opvulwoorden (um/uh) worden weggeknipt, dynamische gezichtstracking, punch-in zoom per knip, voortgangsbalk, hook-titel, loudnorm. Standaardtaal is Engels (`--language`).

## Campagneregels
Geef het regeldocument mee (pdf, docx, md of txt):

    python clip.py video.mp4 --rules brief.pdf

Het document wordt omgezet naar gestructureerde regels (Claude, of zonder API-sleutel een regex-parser voor standaardformuleringen; zie `examples/campaign_novafit.md`). Controleer altijd `output/rules_parsed.json`. Daarna:
- **Duur** blijft binnen de toegestane min/max (ook na het inkorten van pauzes).
- **Verboden woorden:** de zin waarin ze worden uitgesproken wordt uit de clip geknipt en uit titel/caption/hashtags gehaald.
- **Verplicht:** hashtags, vermeldingen, caption-tekst en tekst in beeld (bv. `#ad`) worden toegevoegd; max. aantal hashtags wordt bewaakt.
- **Rapport per clip** in `clip_XX.json` (`compliance`): ✓ gehaald, ✗ overtreden, ? handmatig controleren (regels die niet automatisch te toetsen zijn, zoals toon of "geen medische claims").

## Achtergrond (muziek en beeld)
Alleen als de regels het niet verbieden **en** het de clip beter maakt (Claude beslist; spraakgedreven content zoals podcasts krijgt geen muziek). Muziek ligt zacht onder de stem en zakt automatisch als er gesproken wordt. Achtergrondbeeld wordt alleen gebruikt bij de `fit_blur`-layout. Zet je eigen, rechtenvrije bestanden in `assets/music/` en `assets/backgrounds/` (of `--music-dir`, `--backgrounds-dir`); `--no-background` zet het uit.

## Installeren
Alle commando's draai je vanuit deze map (`cd clipping`).
Vereist Python 3.10+ en `ffmpeg`.

    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=...   # optioneel, voor betere highlights en metadata

## Gebruik

    python clip.py input.mp4 --clips 5 --duration 30
    python clip.py "https://youtube.com/watch?v=..." --language nl

Output in `output/`: `clip_01.mp4` + `clip_01.json` (titel, caption, hashtags, score, timestamps). Stijl en instellingen staan in `config.yaml`.

## Tests

    pytest
    python demo.py   # demo zonder Whisper/API
