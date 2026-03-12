"""Quality ratchet — auto-raises quality gate threshold when performance improves."""


class QualityRatchet:
    """Monotonically raises the quality threshold when sustained improvement detected."""

    def __init__(self, current_threshold: float = 7.0):
        self._threshold = current_threshold

    @property
    def threshold(self) -> float:
        return self._threshold

    def check_ratchet(self, trends: dict) -> tuple[float, bool]:
        """Check if threshold should ratchet up.

        Rule: raise by 0.5 only when the last 3 cycles have
        avg_score > threshold + 1.0. Threshold NEVER decreases.

        Returns (new_threshold, did_ratchet).
        """
        per_cycle = trends.get("per_cycle", {})
        cycles = sorted(per_cycle.keys())

        if len(cycles) < 3:
            return self._threshold, False

        # Check last 3 cycles
        last_3 = cycles[-3:]
        avg_scores = [
            per_cycle[c].get("avg_score", 0.0) for c in last_3
        ]

        # All 3 must be > threshold + 1.0
        target = self._threshold + 1.0
        if all(s > target for s in avg_scores):
            new_threshold = self._threshold + 0.5
            self._threshold = new_threshold
            return new_threshold, True

        return self._threshold, False
