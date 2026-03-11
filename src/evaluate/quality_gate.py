"""Quality gate — routes ads based on evaluation score."""

from pathlib import Path
from typing import Literal

import yaml

from src.models import EvaluationResult

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class QualityGate:
    """Routes ads to approved, needs_editing, or failed based on score threshold."""

    def __init__(self, threshold: float | None = None, settings_path: str | None = None):
        if threshold is not None:
            self._threshold = threshold
        else:
            if settings_path is None:
                settings_path = str(PROJECT_ROOT / "config" / "settings.yaml")
            with open(settings_path) as f:
                settings = yaml.safe_load(f)
            self._threshold = settings["thresholds"]["quality_gate"]

        if settings_path is None:
            settings_path = str(PROJECT_ROOT / "config" / "settings.yaml")
        with open(settings_path) as f:
            settings = yaml.safe_load(f)
        self._max_attempts = settings["thresholds"]["max_edit_attempts"]

    @property
    def threshold(self) -> float:
        return self._threshold

    def check(
        self,
        evaluation: EvaluationResult,
        attempt: int = 0,
    ) -> Literal["approved", "needs_editing", "failed"]:
        """Route an ad based on its evaluation score and attempt count."""
        if evaluation.aggregate_score >= self._threshold:
            return "approved"
        if attempt >= self._max_attempts:
            return "failed"
        return "needs_editing"
