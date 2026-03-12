"""Tests for QualityRatchet — monotonic threshold raising."""

from src.analytics.quality_ratchet import QualityRatchet


def _make_trends(cycle_scores: list[float]) -> dict:
    """Build a trends dict from a list of per-cycle avg scores."""
    per_cycle = {}
    for i, score in enumerate(cycle_scores):
        per_cycle[i + 1] = {
            "avg_score": score,
            "dimensions": {"clarity": score},
            "count": 3,
            "approved": 2,
        }
    return {"per_cycle": per_cycle}


class TestQualityRatchet:
    def test_triggers_after_3_cycles_above(self):
        """Should ratchet when last 3 cycles all avg > threshold + 1.0."""
        ratchet = QualityRatchet(current_threshold=7.0)
        # All 3 cycles > 8.0 (threshold + 1.0)
        trends = _make_trends([8.5, 8.3, 8.7])
        new_threshold, did_ratchet = ratchet.check_ratchet(trends)
        assert did_ratchet is True
        assert new_threshold == 7.5

    def test_no_trigger_at_2_cycles(self):
        """Should NOT ratchet with only 2 cycles of data."""
        ratchet = QualityRatchet(current_threshold=7.0)
        trends = _make_trends([8.5, 8.5])
        new_threshold, did_ratchet = ratchet.check_ratchet(trends)
        assert did_ratchet is False
        assert new_threshold == 7.0

    def test_never_decreases(self):
        """Threshold should never decrease, even if scores drop."""
        ratchet = QualityRatchet(current_threshold=7.5)
        # Scores below threshold — should NOT lower
        trends = _make_trends([6.0, 6.0, 6.0])
        new_threshold, did_ratchet = ratchet.check_ratchet(trends)
        assert did_ratchet is False
        assert new_threshold == 7.5  # unchanged, not lowered

    def test_raises_by_exactly_half(self):
        """Ratchet should raise by exactly 0.5."""
        ratchet = QualityRatchet(current_threshold=7.0)
        trends = _make_trends([8.5, 8.5, 8.5])
        new_threshold, _ = ratchet.check_ratchet(trends)
        assert new_threshold == 7.5  # exactly +0.5
