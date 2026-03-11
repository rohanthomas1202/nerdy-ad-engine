"""Tests for Pipeline orchestrator — end-to-end generate → evaluate flow."""

import json
import os
import tempfile
from unittest.mock import MagicMock

from src.main import Pipeline
from src.models import AdCopy, AdRecord, Brief, LLMUsage


def _make_mock_pipeline():
    """Create a Pipeline with all LLM calls mocked."""
    mock_client = MagicMock()

    # Mock ad generation (generate_structured returns AdCopy)
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
    mock_client.generate_structured.return_value = (mock_ad, gen_usage)

    # Mock evaluation (generate returns JSON scores)
    scores_data = [
        {"dimension": "clarity", "score": 8.0,
         "rationale": "Clear", "confidence": 0.9},
        {"dimension": "value_proposition", "score": 7.5,
         "rationale": "Good", "confidence": 0.85},
        {"dimension": "call_to_action", "score": 7.0,
         "rationale": "OK", "confidence": 0.8},
        {"dimension": "brand_voice", "score": 8.5,
         "rationale": "On-brand", "confidence": 0.9},
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

    pipeline = Pipeline(client=mock_client)
    return pipeline


class TestPipeline:
    def test_run_single_brief_produces_three_records(self):
        """run_single_brief should return 3 AdRecords (one per variant)."""
        pipeline = _make_mock_pipeline()
        brief = Brief(
            id="test-brief", audience_segment="parents_anxious",
            product="SAT", campaign_goal="conversion",
        )
        records = pipeline.run_single_brief(brief)
        assert len(records) == 3
        assert all(isinstance(r, AdRecord) for r in records)

    def test_each_record_has_evaluation(self):
        """Each AdRecord should have an evaluation attached."""
        pipeline = _make_mock_pipeline()
        brief = Brief(
            id="test-brief", audience_segment="parents_anxious",
            product="SAT", campaign_goal="conversion",
        )
        records = pipeline.run_single_brief(brief)
        for r in records:
            assert r.evaluation is not None
            assert r.evaluation.aggregate_score > 0
            assert len(r.evaluation.dimension_scores) == 5

    def test_status_set_correctly(self):
        """Ads scoring >= 7.0 should be approved."""
        pipeline = _make_mock_pipeline()
        brief = Brief(
            id="test-brief", audience_segment="parents_anxious",
            product="SAT", campaign_goal="conversion",
        )
        records = pipeline.run_single_brief(brief)
        # Our mock scores average ~7.6, all should be approved
        for r in records:
            assert r.status == "approved"

    def test_save_results_produces_json(self):
        """save_results should write ad_library.json and failed_ads.json."""
        pipeline = _make_mock_pipeline()
        brief = Brief(
            id="test-brief", audience_segment="parents_anxious",
            product="SAT", campaign_goal="conversion",
        )
        records = pipeline.run_single_brief(brief)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Monkey-patch PROJECT_ROOT for this test
            import src.main as main_mod
            original_root = main_mod.PROJECT_ROOT
            main_mod.PROJECT_ROOT = type(original_root)(tmpdir)
            try:
                pipeline.save_results(records)
                lib_path = os.path.join(tmpdir, "output", "ad_library.json")
                failed_path = os.path.join(tmpdir, "output", "failed_ads.json")
                assert os.path.exists(lib_path)
                assert os.path.exists(failed_path)

                with open(lib_path) as f:
                    approved = json.load(f)
                assert len(approved) == 3  # all approved in our mock
            finally:
                main_mod.PROJECT_ROOT = original_root
