"""Small data-derived dashboard summaries, independent of Streamlit."""
from __future__ import annotations

import math
from collections.abc import Iterable

import pandas as pd


def score_distribution(scores: Iterable[float]) -> pd.DataFrame:
    """Count ten fixed bins; the final 90–100 bin INCLUDES a score of 100.

    Pre-counting avoids a plotting library placing exact 100 scores into
    an invisible 100–110 bin when an axis is limited to [0,100].
    """
    counts = [0] * 10
    for raw_score in scores:
        score = float(raw_score)
        if not math.isfinite(score) or not 0 <= score <= 100:
            raise ValueError("Dashboard matching scores must be finite and within 0–100.")
        counts[min(int(score // 10), 9)] += 1
    return pd.DataFrame([{"bin_center": 5 + position * 10,
                          "score_range": f"{position * 10}–{'100 inclusive' if position == 9 else '<' + str((position + 1) * 10)}",
                          "applicants": count} for position, count in enumerate(counts)])
