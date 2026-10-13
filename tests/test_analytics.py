"""All numeric applicants, especially exact 100 scores, must appear in charts."""
import pytest
from core.analytics import score_distribution


def test_bins_count_boundaries_and_maximum():
    data = score_distribution([0, 9.9999, 10, 89.999, 90, 99.99, 100, 100])
    assert data.applicants.sum() == 8
    assert data.applicants.iloc[0] == 2
    assert data.applicants.iloc[1] == 1
    assert data.applicants.iloc[-1] == 4


def test_empty_distribution():
    assert score_distribution([]).applicants.sum() == 0


@pytest.mark.parametrize('score', [-1, 101, float('nan'), float('inf')])
def test_out_of_range_rejected(score):
    with pytest.raises(ValueError):
        score_distribution([score])
