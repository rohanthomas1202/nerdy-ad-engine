"""Tests for ExperimentLogger — structured experiment history."""

import tempfile
from pathlib import Path

from src.analytics.experiment_logger import ExperimentLogger
from src.models import ExperimentEntry


class TestExperimentLogger:
    def test_log_adds_entry(self):
        """log_experiment() should add an entry to the log."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "experiments.json"
            logger = ExperimentLogger(log_path)
            entry = ExperimentEntry(
                id="exp-1",
                hypothesis="Higher temperature improves diversity",
                change="Raised temperature from 0.7 to 0.9",
                result="Diversity improved, quality stable",
            )
            logger.log_experiment(entry)
            assert len(logger.get_experiments()) == 1
            assert logger.get_experiments()[0].id == "exp-1"

    def test_save_load_roundtrip(self):
        """Experiments should persist across logger instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "experiments.json"
            logger1 = ExperimentLogger(log_path)
            entry = ExperimentEntry(
                id="exp-rt",
                hypothesis="Test roundtrip",
                change="None",
                result="Success",
                metrics_before={"score": 7.0},
                metrics_after={"score": 7.5},
            )
            logger1.log_experiment(entry)

            # New logger instance should load from disk
            logger2 = ExperimentLogger(log_path)
            assert len(logger2.get_experiments()) == 1
            assert logger2.get_experiments()[0].metrics_after["score"] == 7.5

    def test_summary_readable(self):
        """summary() should return a human-readable string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "experiments.json"
            logger = ExperimentLogger(log_path)
            entry = ExperimentEntry(
                id="exp-s",
                hypothesis="Test summary",
                change="Added patterns",
                result="Score improved",
            )
            logger.log_experiment(entry)
            text = logger.summary()
            assert "exp-s" in text
            assert "Test summary" in text
            assert "1 entries" in text
