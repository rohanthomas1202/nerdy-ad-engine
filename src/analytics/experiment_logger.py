"""Experiment logger — persists structured experiment history."""

import json
from pathlib import Path

from src.models import ExperimentEntry

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_LOG_PATH = PROJECT_ROOT / "output" / "experiment_log.json"


class ExperimentLogger:
    """Logs experiments to a JSON file for audit and analysis."""

    def __init__(self, log_path: Path | None = None):
        self._path = log_path or DEFAULT_LOG_PATH
        self._entries: list[ExperimentEntry] = []
        self._load()

    def _load(self) -> None:
        """Load existing experiments from disk."""
        if self._path.exists():
            with open(self._path) as f:
                raw = json.load(f)
            self._entries = [ExperimentEntry.model_validate(e) for e in raw]

    def _save(self) -> None:
        """Persist experiments to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = [e.model_dump(mode="json") for e in self._entries]
        with open(self._path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def log_experiment(self, entry: ExperimentEntry) -> None:
        """Add an experiment entry and save."""
        self._entries.append(entry)
        self._save()

    def get_experiments(self) -> list[ExperimentEntry]:
        """Return all logged experiments."""
        return list(self._entries)

    def summary(self) -> str:
        """Return a human-readable summary of all experiments."""
        if not self._entries:
            return "No experiments logged."

        lines = [f"Experiment Log ({len(self._entries)} entries)"]
        lines.append("=" * 50)
        for e in self._entries:
            lines.append(f"\n[{e.id}] {e.timestamp.strftime('%Y-%m-%d %H:%M')}")
            lines.append(f"  Hypothesis: {e.hypothesis}")
            lines.append(f"  Change: {e.change}")
            lines.append(f"  Result: {e.result}")
            if e.metrics_before:
                lines.append(f"  Before: {e.metrics_before}")
            if e.metrics_after:
                lines.append(f"  After:  {e.metrics_after}")
        return "\n".join(lines)
