from .models import Word


def transcribe(video: str, model_size: str = "small", language: str | None = None) -> list[Word]:
    """Spraak -> woorden met timestamps (faster-whisper)."""
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, compute_type="int8")
    segments, _ = model.transcribe(video, language=language, word_timestamps=True, vad_filter=True)
    words = []
    for seg in segments:
        for w in seg.words or []:
            text = w.word.strip()
            if text:
                words.append(Word(text, float(w.start), float(w.end)))
    return words
