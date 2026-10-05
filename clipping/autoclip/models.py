from dataclasses import dataclass, field


@dataclass
class Word:
    text: str
    start: float
    end: float


@dataclass
class Highlight:
    start: float
    end: float
    score: float
    reason: str = ""
    hook: str = ""


@dataclass
class ClipMeta:
    title: str
    caption: str
    hashtags: list[str] = field(default_factory=list)
