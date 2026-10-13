"""Small, deterministic normalization helpers shared by ingestion and DSA modules."""
from __future__ import annotations

import math
import re
from collections.abc import Iterable
from numbers import Real
from typing import Any

import pandas as pd

MISSING_TEXT = {"", "n/a", "null", "none", "nan"}
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


def is_missing(value: Any) -> bool:
    """Recognize blank cells and scalar missing values, not entire collections."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() in MISSING_TEXT
    if isinstance(value, (list, tuple, set, frozenset, dict)):
        return False
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def normalize_skills(value: str | Iterable[str] | None) -> frozenset[str]:
    """Trim, lowercase and deduplicate skills using a hash set.

    Commas, semicolons, pipes and newlines delimit skills; spaces within a skill
    are preserved (e.g. 'machine learning'). No fuzzy matching is performed.
    """
    if is_missing(value):
        return frozenset()
    if isinstance(value, str):
        tokens = re.split(r"[,;|\n]", value)
    elif isinstance(value, (list, tuple, set, frozenset)):
        tokens = list(value)
        if any(not isinstance(item, str) for item in tokens):
            raise ValueError("Skill collections must contain only strings.")
    else:
        raise ValueError("Skills must be text or a collection of text values.")
    return frozenset(
        " ".join(token.strip().lower().split())
        for token in tokens if not is_missing(token)
    )


def skill_text(value: str | Iterable[str] | None) -> str:
    """Return a reproducible, alphabetically ordered skill-cell representation."""
    return "; ".join(sorted(normalize_skills(value)))


def normalize_education(value: Any) -> str | None:
    """Normalize exact-match education labels; missing education remains None."""
    if is_missing(value):
        return None
    if not isinstance(value, str):
        raise ValueError("Education must be text, or an empty cell.")
    return " ".join(value.strip().lower().split())


def normalize_identifier(value: Any) -> str:
    """Preserve textual IDs (including leading zeros); validate a safe ID syntax."""
    if is_missing(value) or isinstance(value, bool):
        raise ValueError("Identifier is missing or has an invalid type.")
    if isinstance(value, str):
        identifier = value.strip()
    elif isinstance(value, Real) and math.isfinite(float(value)) and float(value).is_integer():
        identifier = str(int(value))
    else:
        raise ValueError("Identifier must be text or a whole number.")
    if not ID_PATTERN.fullmatch(identifier):
        raise ValueError("Use 1–64 letters, digits, dots, underscores or hyphens; start with a letter/digit.")
    return identifier
