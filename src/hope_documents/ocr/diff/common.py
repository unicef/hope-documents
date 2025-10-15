from dataclasses import dataclass


@dataclass
class Match:
    text: str
    distance: float

    def __repr__(self) -> str:
        return f"Match(text={self.text}, distance={self.distance})"


HOMOGLYPH_GROUPS = [
    ["0", "O", "o"],
    ["1", "I", "l", "L", "i"],
    ["5", "S", "$", "s"],
    ["2", "Z", "z"],
    ["8", "B", "b"],
    ["A", "@", "a"],
    ["-", "/", "."],
]

# Build a map: every variant -> canonical uppercase representative (first element uppercased)
HOMOGLYPH_MAP = {ch: group[0].upper() for group in HOMOGLYPH_GROUPS for ch in group}


def _normalize_homoglyphs(s: str) -> str:
    """Normalize characters using HOMOGLYPH_MAP; fallback to uppercase for unmapped chars."""
    return "".join(HOMOGLYPH_MAP.get(ch, ch.upper()) for ch in s)
