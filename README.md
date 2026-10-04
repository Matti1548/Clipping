# Clipping – auto-clip tool

Geef een lange video (bestand of URL) en krijg korte, 9:16 clips met geanimeerde captions, titel en hashtags – klaar voor TikTok, YouTube Shorts en Reels.

## Pipeline
transcriptie (faster-whisper) → highlight-detectie (Claude, of heuristiek zonder API-sleutel) → knippen op zinsgrenzen → 9:16 met gezichtstracking → captions met woord-highlighting → metadata → export.

## Videotypes
`--type auto` (standaard) laat Claude het type raden; of kies `podcast`, `interview`, `gaming`, `vlog`, `educational`, `general`. Elk profiel stelt highlight-criteria, layout (gezichtstracking-crop of `fit_blur` voor gameplay), pauzelengte, zoom en captionstijl in. Gaming weegt audio-energie (schreeuwen, actie) zwaarder mee. Eigen aanpassingen: sectie `profiles:` in `config.yaml`.

## Editing
Pauzes en opvulwoorden (um/uh) worden weggeknipt, dynamische gezichtstracking, punch-in zoom per knip, voortgangsbalk, hook-titel, loudnorm. Standaardtaal is Engels (`--language`).

## Installeren
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
