import regex


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


def find_similar(pattern: str, text: str, max_errors: int = 2) -> list[dict[str, str | int]]:
    """
    Find all occurrences of a pattern in a text using fuzzy matching.

    This function allows for a specified number of errors (insertions,
    deletions, or substitutions) when searching for the pattern.

    Args:
        pattern (str): The string pattern to search for.
        text (str): The text to search within.
        max_errors (int): The maximum number of errors allowed for a match.
                          Defaults to 2. A value of 0 means an exact match.

    Returns:
        A list of dictionaries, where each dictionary contains:
        - 'end': The ending index of the match in the text.
        - 'distance': The number of errors in the match (distance).
        - 'similarity': The Levenshtein distance between the matches

    """
    if not pattern:
        return []

    # The fuzzy pattern looks for the `pattern` string with a maximum
    # number of errors specified by `max_errors`.
    # {e<=N} is the syntax for "at most N errors".
    fuzzy_pattern = f"({pattern}){{e<={max_errors}}}"

    results = []
    for match in regex.finditer(fuzzy_pattern, text, regex.BESTMATCH):
        # The regex.BESTMATCH flag ensures we get the best possible match
        # at a given position, minimizing the number of errors.
        matched_text = match.group(0)

        # The `fuzzy_counts` attribute is a tuple of (substitutions, insertions, deletions)
        total_errors = sum(match.fuzzy_counts)

        results.append(
            {
                "match": matched_text,
                "distance": total_errors,
                "similarity": levenshtein_distance(pattern, matched_text),
            }
        )

    return results
