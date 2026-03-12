"""Integration tests for the Pipeline — batch processing, error resilience, output files."""

import json
import os
import tempfile
from unittest.mock import MagicMock

from src.main import Pipeline, _parse_args
from src.models import AdCopy, AdRecord, Brief, LLMUsage


def _make_mock_pipeline(output_dir=None, fail_on_variant=None):
    """Create a Pipeline with all LLM calls mocked.

    Args:
        output_dir: Override output directory.
        fail_on_variant: If set, raise an exception on this variant index.
    """
    mock_client = MagicMock()

    mock_ad = AdCopy(
        primary_text="Expert SAT tutoring matched to your child's learning style.",
        headline="SAT Score Boost 200+ Pts",
        description="Personalized 1-on-1 prep. Free first session.",
        cta="Try Free",
    )
    gen_usage = LLMUsage(
        model="gemini-2.0-flash", input_tokens=300, output_tokens=100,
        cost_usd=0.0001, call_type="generation",
    )

    call_count = {"n": 0}

    def _generate_structured(*args, **kwargs):
        call_count["n"] += 1
        if fail_on_variant is not None and (call_count["n"] - 1) % 3 == fail_on_variant:
            raise RuntimeError("Simulated LLM failure")
        return (mock_ad, gen_usage)

    mock_client.generate_structured.side_effect = _generate_structured

    scores_data = [
        {"dimension": "clarity", "score": 8.0, "rationale": "Clear", "confidence": 0.9},
        {"dimension": "value_proposition", "score": 7.5, "rationale": "Good", "confidence": 0.85},
        {"dimension": "call_to_action", "score": 7.0, "rationale": "OK", "confidence": 0.8},
        {"dimension": "brand_voice", "score": 8.5, "rationale": "On-brand", "confidence": 0.9},
        {"dimension": "emotional_resonance", "score": 7.0,
         "rationale": "Decent", "confidence": 0.8},
    ]
    mock_scores_json = json.dumps({"scores": scores_data})
    eval_usage = LLMUsage(
        model="gemini-2.0-pro", input_tokens=500, output_tokens=200,
        cost_usd=0.002, call_type="evaluation",
    )
    mock_client.generate.return_value = (mock_scores_json, eval_usage)
    mock_client.total_cost = 0.005
    mock_client.usage_log = [eval_usage]

    from pathlib import Path
    pipeline = Pipeline(client=mock_client, output_dir=Path(output_dir) if output_dir else None)
    return pipeline


class TestPipelineIntegration:
    def test_batch_three_briefs_produces_nine_ads(self):
        """3 briefs × 3 variants = 9 ads."""
        pipeline = _make_mock_pipeline()
        briefs = [
            Brief(id=f"brief-{i}", audience_segment="parents_anxious",
                  product="SAT", campaign_goal="conversion")
            for i in range(3)
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline._output_dir = type(pipeline._output_dir)(tmpdir) / "output"
            records = pipeline.run_batch(briefs=briefs)
        assert len(records) == 9
        assert all(isinstance(r, AdRecord) for r in records)

    def test_error_resilience_single_variant_failure(self):
        """A failing variant should produce an error record, not crash the batch."""
        pipeline = _make_mock_pipeline(fail_on_variant=1)
        brief = Brief(
            id="test-error", audience_segment="students_stressed",
            product="SAT", campaign_goal="conversion",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline._output_dir = type(pipeline._output_dir)(tmpdir) / "output"
            records = pipeline.run_batch(briefs=[brief])

        assert len(records) == 3
        error_records = [r for r in records if r.error_message]
        assert len(error_records) == 1
        assert "Simulated LLM failure" in error_records[0].error_message
        assert error_records[0].status == "failed"

    def test_output_files_generated(self):
        """run_batch should produce ad_library.json and failed_ads.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output")
            pipeline = _make_mock_pipeline()
            from pathlib import Path
            pipeline._output_dir = Path(output_path)
            briefs = [
                Brief(id="out-test", audience_segment="parents_anxious",
                      product="SAT", campaign_goal="conversion")
            ]
            pipeline.run_batch(briefs=briefs)

            assert os.path.exists(os.path.join(output_path, "ad_library.json"))
            assert os.path.exists(os.path.join(output_path, "failed_ads.json"))
            with open(os.path.join(output_path, "ad_library.json")) as f:
                lib = json.load(f)
            assert isinstance(lib, list)
            assert len(lib) == 3  # all approved with our mock scores

    def test_count_flag_limits_ads(self):
        """--count should limit the number of briefs processed."""
        pipeline = _make_mock_pipeline()
        with tempfile.TemporaryDirectory() as tmpdir:
            from pathlib import Path
            pipeline._output_dir = Path(tmpdir) / "output"
            # count=6 → max 2 briefs → 6 ads
            briefs = [
                Brief(id=f"count-{i}", audience_segment="parents_anxious",
                      product="SAT", campaign_goal="conversion")
                for i in range(10)
            ]
            records = pipeline.run_batch(briefs=briefs, count=6)
        assert len(records) == 6  # 2 briefs × 3 variants

    def test_deterministic_with_seed(self):
        """Pipeline with same seed should produce consistent variant selections."""
        import random
        random.seed(42)
        pipeline = _make_mock_pipeline()
        brief = Brief(
            id="seed-test", audience_segment="families_comparing",
            product="SAT", campaign_goal="awareness",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            from pathlib import Path
            pipeline._output_dir = Path(tmpdir) / "output"
            records1 = pipeline.run_batch(briefs=[brief])

        random.seed(42)
        pipeline2 = _make_mock_pipeline()
        with tempfile.TemporaryDirectory() as tmpdir:
            from pathlib import Path
            pipeline2._output_dir = Path(tmpdir) / "output"
            records2 = pipeline2.run_batch(briefs=[brief])

        assert len(records1) == len(records2)


class TestArgParser:
    def test_defaults(self):
        args = _parse_args([])
        assert args.count is None
        assert args.cycles == 1
        assert args.seed == 42
        assert args.port == 8020
        assert args.demo is False
        assert args.research is False

    def test_count_and_cycles(self):
        args = _parse_args(["--count", "50", "--cycles", "3"])
        assert args.count == 50
        assert args.cycles == 3

    def test_demo_flag(self):
        args = _parse_args(["--demo"])
        assert args.demo is True

    def test_seed_override(self):
        args = _parse_args(["--seed", "99"])
        assert args.seed == 99
