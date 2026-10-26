from typing import TYPE_CHECKING

from hope_documents.ocr.diff.common import Match, _normalize_homoglyphs

if TYPE_CHECKING:
    from collections.abc import Sequence


def levenshtein_distance(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row: Sequence[int] = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def find_similar(pattern: str, text: str, max_distance: int = 0) -> Match | None:
    if not pattern:
        return None

    # 1. Normalize pattern: remove spaces and separators, then apply homoglyphs
    pattern_norm = "".join(c for c in pattern if c not in " -./")
    pattern_norm = _normalize_homoglyphs(pattern_norm)

    # 2. Create a "clean" version of the text (no spaces/separators) and an index map
    text_clean = []
    original_indices = []
    for i, char in enumerate(text):
        if char not in " -./":
            text_clean.append(char)
            original_indices.append(i)

    text_clean_norm = _normalize_homoglyphs("".join(text_clean))

    # 3. Find the best match using Levenshtein on the clean strings
    best_match: Match | None = None
    min_distance = float("inf")
    best_window_size = float("inf")
    pattern_len = len(pattern_norm)

    # The window size can vary from pattern_len - max_distance to pattern_len + max_distance
    for window_size in range(max(1, pattern_len - max_distance), pattern_len + max_distance + 1):
        for i in range(len(text_clean_norm) - window_size + 1):
            substring_clean_norm = text_clean_norm[i : i + window_size]
            distance = levenshtein_distance(pattern_norm, substring_clean_norm)

            if distance <= max_distance and (
                best_match is None
                or distance < min_distance
                or (distance == min_distance and abs(window_size - pattern_len) < abs(best_window_size - pattern_len))
            ):
                min_distance = distance
                best_window_size = window_size

                start_original_index = original_indices[i]
                end_original_index_in_clean = i + window_size - 1
                end_original_index = original_indices[end_original_index_in_clean]
                matched_text = text[start_original_index : end_original_index + 1]

                best_match = Match(text=matched_text, distance=distance)

                if distance == 0:
                    return best_match

    return best_match
