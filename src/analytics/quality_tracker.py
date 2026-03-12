"""Quality tracker — per-dimension trend analysis and regression detection."""

from pathlib import Path

from src.models import AdRecord

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class QualityTracker:
    """Tracks per-dimension quality trends across cycles."""

    def track(self, records: list[AdRecord]) -> dict:
        """Compute per-dimension averages, per-cycle trends, and pass rates.

        Args:
            records: All AdRecords (may span multiple cycles).

        Returns:
            Dict with keys: per_dimension, per_cycle, pass_rate, avg_score.
        """
        if not records:
            return {
                "per_dimension": {},
                "per_cycle": {},
                "pass_rate": 0.0,
                "avg_score": 0.0,
            }

        # Per-dimension averages
        dim_totals: dict[str, list[float]] = {}
        for r in records:
            if r.evaluation:
                for ds in r.evaluation.dimension_scores:
                    dim_totals.setdefault(ds.dimension, []).append(ds.score)

        per_dimension = {
            dim: round(sum(scores) / len(scores), 2)
            for dim, scores in dim_totals.items()
        }

        # Per-cycle breakdown
        cycle_groups: dict[int, list[AdRecord]] = {}
        for r in records:
            cycle_groups.setdefault(r.cycle, []).append(r)

        per_cycle = {}
        for cycle, cycle_records in sorted(cycle_groups.items()):
            cycle_dim: dict[str, list[float]] = {}
            for r in cycle_records:
                if r.evaluation:
                    for ds in r.evaluation.dimension_scores:
                        cycle_dim.setdefault(ds.dimension, []).append(ds.score)

            cycle_avg = {}
            for dim, scores in cycle_dim.items():
                cycle_avg[dim] = round(sum(scores) / len(scores), 2)

            scored = [r for r in cycle_records if r.evaluation]
            overall = (
                sum(r.evaluation.aggregate_score for r in scored) / len(scored)
                if scored else 0.0
            )
            per_cycle[cycle] = {
                "dimensions": cycle_avg,
                "avg_score": round(overall, 2),
                "count": len(cycle_records),
                "approved": sum(
                    1 for r in cycle_records if r.status == "approved"
                ),
            }

        # Overall stats
        total = len(records)
        approved = sum(1 for r in records if r.status == "approved")
        pass_rate = approved / total if total else 0.0

        scored = [r for r in records if r.evaluation]
        avg_score = (
            sum(r.evaluation.aggregate_score for r in scored) / len(scored)
            if scored else 0.0
        )

        return {
            "per_dimension": per_dimension,
            "per_cycle": per_cycle,
            "pass_rate": round(pass_rate, 3),
            "avg_score": round(avg_score, 2),
        }

    @staticmethod
    def detect_regressions(trends: dict) -> list[dict]:
        """Detect dimensions that dropped > 0.5 points between consecutive cycles.

        Returns list of {dimension, previous_avg, current_avg, drop}.
        """
        per_cycle = trends.get("per_cycle", {})
        cycles = sorted(per_cycle.keys())
        if len(cycles) < 2:
            return []

        regressions = []
        prev_cycle = cycles[-2]
        curr_cycle = cycles[-1]
        prev_dims = per_cycle[prev_cycle].get("dimensions", {})
        curr_dims = per_cycle[curr_cycle].get("dimensions", {})

        for dim in prev_dims:
            if dim in curr_dims:
                drop = prev_dims[dim] - curr_dims[dim]
                if drop > 0.5:
                    regressions.append({
                        "dimension": dim,
                        "previous_avg": prev_dims[dim],
                        "current_avg": curr_dims[dim],
                        "drop": round(drop, 2),
                    })

        return regressions

    @staticmethod
    def plot_trends(trends: dict, output_path: str | None = None) -> str:
        """Generate quality trends chart. Returns path to saved PNG."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        if output_path is None:
            output_path = str(
                PROJECT_ROOT / "output" / "quality_trends.png"
            )

        per_cycle = trends.get("per_cycle", {})
        if not per_cycle:
            return output_path

        cycles = sorted(per_cycle.keys())
        all_dims = set()
        for c in cycles:
            all_dims.update(per_cycle[c].get("dimensions", {}).keys())

        fig, ax = plt.subplots(figsize=(10, 6))
        for dim in sorted(all_dims):
            values = [
                per_cycle[c].get("dimensions", {}).get(dim, 0)
                for c in cycles
            ]
            ax.plot(cycles, values, marker="o", label=dim)

        # Overall avg
        avg_values = [per_cycle[c].get("avg_score", 0) for c in cycles]
        ax.plot(
            cycles, avg_values, marker="s", linewidth=2,
            color="black", label="Overall Avg",
        )

        ax.set_xlabel("Cycle")
        ax.set_ylabel("Score")
        ax.set_title("Quality Trends by Dimension")
        ax.legend(loc="lower right", fontsize=8)
        ax.set_ylim(0, 10)
        ax.grid(True, alpha=0.3)

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return output_path
