import sys
from typing import TypedDict

import regex

# Define homoglyph groups (each inner list = equivalent characters)
HOMOGLYPH_GROUPS = [
    ["0", "O", "o"],
    ["1", "I", "l", "L", "i"],
    ["5", "S", "$", "s"],
    ["2", "Z", "z"],
    ["8", "B", "b"],
    ["A", "@", "a"],  # Fixed: 'A' is now canonical
    # add more groups if you want (including Unicode confusables)
]

# Build a map: every variant -> canonical uppercase representative (first element uppercased)
HOMOGLYPH_MAP = {ch: group[0].upper() for group in HOMOGLYPH_GROUPS for ch in group}


IGNORE_CHARS = " -/"


class Match(TypedDict):
    match: str
    distance: float


def levenshtein_distance(s1: str, s2: str) -> int:
    """Return the Levenshtein distance between two strings."""
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,  # Deletion
                dp[i][j - 1] + 1,  # Insertion
                dp[i - 1][j - 1] + cost,
            )  # Substitution

    return dp[m][n]


def numeric_string_similarity(s1: str, s2: str) -> float:
    """Return the similarity between two numeric strings as a percentage."""
    distance = levenshtein_distance(s1, s2)
    max_len = max(len(s1), len(s2))

    if max_len == 0:
        return 1.0  # Both strings are empty, so they are 100% similar

    return 1.0 - (distance / max_len)


def _normalize_homoglyphs(s: str) -> str:
    """Normalize characters using HOMOGLYPH_MAP; fallback to uppercase for unmapped chars."""
    return "".join(HOMOGLYPH_MAP.get(ch, ch.upper()) for ch in s)


def find_similar1(pattern: str, text: str, max_errors: int = 5) -> Match | None:
    """Find all occurrences of a pattern in a text using fuzzy matching.

    This function allows for a specified number of errors (insertions,
    deletions, or substitutions) when searching for the pattern.
    Differences in characters defined in `IGNORE_CHARS` are not considered.

    Args:
        pattern (str): The string pattern to search for.
        text (str): The text to search within.
        max_errors (int): The maximum number of errors allowed for a match.
                          Defaults to 5.

    Returns:
        A list of dictionaries, where each dictionary contains:
        - 'match': The matched substring from the original text.
        - 'distance': The weighted distance.

    """
    if not pattern:
        return None

    # Create a translation table to remove ignored characters
    translation_table = str.maketrans("", "", IGNORE_CHARS)

    pattern_no_ignored = pattern.translate(translation_table)
    text_no_ignored = text.translate(translation_table)

    # Create a map from indices in the text with ignored characters removed back to the original text.
    original_indices = [i for i, char in enumerate(text) if char not in IGNORE_CHARS]

    # The fuzzy pattern looks for the `pattern` string with a maximum
    # number of errors specified by `max_errors`.
    # {e<=N} is the syntax for "at most N errors".
    fuzzy_pattern = f"({pattern_no_ignored}){{e<={max_errors}}}"
    best_distance = sys.maxsize
    result: Match | None = None
    for match in regex.finditer(fuzzy_pattern, text_no_ignored, regex.BESTMATCH):
        # The regex.BESTMATCH flag ensures we get the best possible match
        # at a given position, minimizing the number of errors.
        start, end = match.span()

        if start >= len(original_indices) or end > len(original_indices) or end == 0:
            continue

        original_start = original_indices[start]
        original_end = original_indices[end - 1] + 1
        matched_original = text[original_start:original_end]

        # Calculate the base errors from the fuzzy match on the strings with ignored characters removed.
        total_distance = sum(match.fuzzy_counts)
        if total_distance < best_distance:
            best_distance = total_distance
            result = {"match": matched_original, "distance": float(total_distance)}

    return result


def find_similar2(pattern: str, text: str, max_errors: int = 5) -> Match | None:
    """Find all occurrences of a pattern in a text.

    It allows up to `max_errors` edits, taking into account homoglyph equivalences defined in HOMOGLYPH_GROUPS,
    and special handling for characters in `IGNORE_CHARS`.
    This version normalizes both the pattern and text, then uses fuzzy regex
    for a robust search.

    Args:
        pattern (str): The string pattern to search for.
        text (str): The text to search within.
        max_errors (int): The maximum number of errors allowed for a match.
                          Defaults to 5.

    Returns a list of dicts with keys:
      - 'match': the original substring from `text` that matched
      - 'distance': the weighted edit distance between the found match and the pattern.

    """
    if not pattern:
        return None
    best_distance = float(sys.maxsize)

    norm_pattern = _normalize_homoglyphs(pattern)
    # assumption: _normalize_homoglyphs is length-preserving, so we can map spans
    # from norm_text back to the original text.
    norm_text = _normalize_homoglyphs(text)

    # Create a translation table to remove ignored characters
    translation_table = str.maketrans("", "", IGNORE_CHARS)

    pattern_no_ignored = norm_pattern.translate(translation_table)
    text_no_ignored = norm_text.translate(translation_table)

    # Map indices from the no-ignored, normalized text back to the original text
    original_indices = [i for i, char in enumerate(norm_text) if char not in IGNORE_CHARS]

    # {e<=N} is the syntax for "at most N errors".
    fuzzy_pattern = f"({pattern_no_ignored}){{e<={max_errors}}}"

    result: Match | None = None
    for match in regex.finditer(fuzzy_pattern, text_no_ignored, regex.BESTMATCH):
        # The regex.BESTMATCH flag ensures we get the best possible match
        # at a given position, minimizing the number of errors.
        start, end = match.span()

        if start >= len(original_indices) or end > len(original_indices) or end == 0:
            continue

        original_start = original_indices[start]
        original_end = original_indices[end - 1] + 1
        matched_original = text[original_start:original_end]

        # Calculate the base errors from the fuzzy match on the no-hyphen strings.
        total_distance = sum(match.fuzzy_counts)

        if total_distance <= max_errors and total_distance < best_distance:
            best_distance = float(total_distance)
            result = {"match": matched_original, "distance": float(total_distance)}
    return result


find_similar = find_similar2
