"""Integration tests for the iteration loop in Pipeline."""

import json
from unittest.mock import MagicMock

from src.main import Pipeline
from src.models import AdCopy, Brief, LLMUsage


def _make_iterating_pipeline(
    initial_score=5.5, edited_score=7.5, num_edits_to_pass=1,
):
    """Create a Pipeline that simulates iteration: low score → edit → high score.

    The mock LLM returns:
    - Generation: valid AdCopy
    - Evaluation: initial_score on first call, edited_score after edits
    - Diagnosis: valid JSON
    - Editing: valid AdCopy
    """
    mock_client = MagicMock()

    # Mock ad generation
    mock_ad = AdCopy(
        primary_text="Expert SAT tutoring matched to your child's learning style.",
        headline="SAT Score Boost 200+ Pts",
        description="Personalized 1-on-1 prep. Free first session.",
        cta="Try Free",
    )
    gen_usage = LLMUsage(
        model="gemini-2.5-flash", input_tokens=300, output_tokens=100,
        cost_usd=0.0001, call_type="generation",
    )
    mock_client.generate_structured.return_value = (mock_ad, gen_usage)

    # Mock evaluation — alternate between low and high scores
    call_count = {"eval": 0}

    def _make_scores(score_val):
        return [
            {"dimension": "clarity", "score": score_val,
             "rationale": "Test", "confidence": 0.9},
            {"dimension": "value_proposition", "score": score_val,
             "rationale": "Test", "confidence": 0.85},
            {"dimension": "call_to_action", "score": score_val,
             "rationale": "Test", "confidence": 0.8},
            {"dimension": "brand_voice", "score": score_val,
             "rationale": "Test", "confidence": 0.9},
            {"dimension": "emotional_resonance", "score": score_val - 1.0,
             "rationale": "Weak", "confidence": 0.75},
        ]

    def mock_generate(prompt, model_type="flash", call_type="generation", **kwargs):
        """Route mock responses based on call_type."""
        usage = LLMUsage(
            model="gemini-2.5-pro", input_tokens=500, output_tokens=200,
            cost_usd=0.002, call_type=call_type,
        )

        if call_type == "evaluation":
            call_count["eval"] += 1
            if call_count["eval"] <= 1:
                # First eval: low score
                return json.dumps({"scores": _make_scores(initial_score)}), usage
            else:
                # Subsequent evals: high score
                return json.dumps({"scores": _make_scores(edited_score)}), usage
        elif call_type == "editing":
            # Diagnosis response
            return json.dumps({
                "problem_description": "Lacks emotional hook.",
                "suggested_fix": "Add parent empathy opening.",
            }), usage
        else:
            return json.dumps({"scores": _make_scores(initial_score)}), usage

    mock_client.generate.side_effect = mock_generate
    mock_client.total_cost = 0.01

    pipeline = Pipeline(client=mock_client)
    return pipeline


class TestIterationIntegration:
    def test_ad_rescued_after_edit(self):
        """An ad scoring 5.5 initially should be approved after editing to 7.5."""
        pipeline = _make_iterating_pipeline(
            initial_score=5.5, edited_score=7.5,
        )
        brief = Brief(
            id="test-iter", audience_segment="parents_anxious",
            product="SAT", campaign_goal="conversion",
        )
        records = pipeline.run_single_brief(brief)
        # At least one should be approved via editing
        approved = [r for r in records if r.status == "approved"]
        assert len(approved) >= 1

    def test_iteration_history_has_multiple_entries(self):
        """Edited ads should have iteration_history with > 1 entry."""
        pipeline = _make_iterating_pipeline(
            initial_score=5.5, edited_score=7.5,
        )
        brief = Brief(
            id="test-hist", audience_segment="parents_anxious",
            product="SAT", campaign_goal="conversion",
        )
        records = pipeline.run_single_brief(brief)
        edited = [r for r in records if len(r.iteration_history) > 1]
        assert len(edited) >= 1

    def test_approved_first_try_no_iteration(self):
        """Ads scoring above threshold should not enter iteration loop."""
        pipeline = _make_iterating_pipeline(
            initial_score=7.5, edited_score=8.0,
        )
        brief = Brief(
            id="test-pass", audience_segment="parents_anxious",
            product="SAT", campaign_goal="conversion",
        )
        records = pipeline.run_single_brief(brief)
        for r in records:
            assert r.status == "approved"
            # Should have exactly 1 entry (initial eval, no iterations)
            assert len(r.iteration_history) == 1

    def test_cost_tracking_includes_iterations(self):
        """Total cost should include generation, evaluation, and iteration costs."""
        pipeline = _make_iterating_pipeline(
            initial_score=5.5, edited_score=7.5,
        )
        brief = Brief(
            id="test-cost", audience_segment="parents_anxious",
            product="SAT", campaign_goal="conversion",
        )
        records = pipeline.run_single_brief(brief)
        for r in records:
            assert r.total_cost_usd > 0
            # Edited ads should cost more than just gen + first eval
            if len(r.iteration_history) > 1:
                assert r.total_cost_usd > r.generation_cost_usd + 0.001
