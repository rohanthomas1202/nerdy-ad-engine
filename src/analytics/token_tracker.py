"""Token tracker — cost analytics and performance-per-token economics."""

from pathlib import Path

from src.models import AdRecord, LLMUsage

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class TokenTracker:
    """Computes cost metrics and quality-per-dollar economics."""

    def summarize(
        self,
        records: list[AdRecord],
        usage_log: list[LLMUsage],
    ) -> dict:
        """Compute cost summary from records and usage log.

        Returns dict with: total_cost, cost_per_ad, cost_per_approved_ad,
        cost_by_call_type, cost_by_model, quality_per_dollar.
        """
        total_cost = sum(u.cost_usd for u in usage_log)
        total_ads = len(records)
        approved_ads = sum(1 for r in records if r.status == "approved")

        # Cost by call type
        cost_by_call_type: dict[str, float] = {}
        for u in usage_log:
            cost_by_call_type[u.call_type] = (
                cost_by_call_type.get(u.call_type, 0.0) + u.cost_usd
            )

        # Cost by model
        cost_by_model: dict[str, float] = {}
        for u in usage_log:
            cost_by_model[u.model] = (
                cost_by_model.get(u.model, 0.0) + u.cost_usd
            )

        # Avg score
        scored = [r for r in records if r.evaluation]
        avg_score = (
            sum(r.evaluation.aggregate_score for r in scored) / len(scored)
            if scored else 0.0
        )

        # Quality per dollar = avg_score / cost_per_ad (higher is better)
        cost_per_ad = total_cost / total_ads if total_ads else 0.0
        quality_per_dollar = (
            avg_score / cost_per_ad if cost_per_ad > 0 else 0.0
        )

        cost_per_approved = (
            total_cost / approved_ads if approved_ads else 0.0
        )

        return {
            "total_cost": round(total_cost, 4),
            "cost_per_ad": round(cost_per_ad, 4),
            "cost_per_approved_ad": round(cost_per_approved, 4),
            "cost_by_call_type": {
                k: round(v, 4) for k, v in cost_by_call_type.items()
            },
            "cost_by_model": {
                k: round(v, 4) for k, v in cost_by_model.items()
            },
            "avg_score": round(avg_score, 2),
            "quality_per_dollar": round(quality_per_dollar, 2),
        }

    @staticmethod
    def plot_cost_dashboard(
        summary: dict, output_path: str | None = None,
    ) -> str:
        """Generate cost dashboard chart. Returns path to saved PNG."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        if output_path is None:
            output_path = str(
                PROJECT_ROOT / "output" / "cost_dashboard.png"
            )

        fig, axes = plt.subplots(1, 2, figsize=(12, 5))

        # Cost by call type (pie)
        cbt = summary.get("cost_by_call_type", {})
        if cbt:
            labels = list(cbt.keys())
            values = list(cbt.values())
            axes[0].pie(values, labels=labels, autopct="%1.1f%%")
            axes[0].set_title("Cost by Call Type")
        else:
            axes[0].text(0.5, 0.5, "No data", ha="center")

        # Key metrics (table)
        metrics = [
            ("Total Cost", f"${summary.get('total_cost', 0):.4f}"),
            ("Cost/Ad", f"${summary.get('cost_per_ad', 0):.4f}"),
            (
                "Cost/Approved",
                f"${summary.get('cost_per_approved_ad', 0):.4f}",
            ),
            ("Avg Score", f"{summary.get('avg_score', 0):.2f}"),
            (
                "Quality/Dollar",
                f"{summary.get('quality_per_dollar', 0):.1f}",
            ),
        ]
        axes[1].axis("off")
        table = axes[1].table(
            cellText=[[m[1]] for m in metrics],
            rowLabels=[m[0] for m in metrics],
            loc="center",
            cellLoc="center",
        )
        table.auto_set_font_size(False)
        table.set_fontsize(11)
        table.scale(1.2, 1.5)
        axes[1].set_title("Cost Metrics")

        fig.suptitle("Cost Dashboard", fontsize=14, fontweight="bold")
        fig.tight_layout()

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return output_path
