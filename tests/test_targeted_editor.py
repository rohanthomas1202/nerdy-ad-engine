"""Tests for TargetedEditor — surgical ad copy rewrites."""

from unittest.mock import MagicMock

from src.iterate.targeted_editor import TargetedEditor
from src.models import AdCopy, Diagnosis, LLMUsage


def _make_mock_editor():
    """Create a TargetedEditor with mocked LLM."""
    mock_client = MagicMock()
    edited_ad = AdCopy(
        primary_text=(
            "Watching your child stress over practice tests? You're not alone. "
            "Our expert SAT tutors build confidence — not just scores. "
            "Personalized 1-on-1 plans matched to how your child learns best."
        ),
        headline="SAT Prep That Builds Confidence",
        description="Expert 1-on-1 tutoring. Free first session.",
        cta="Try Free",
    )
    mock_usage = LLMUsage(
        model="gemini-2.5-pro", input_tokens=700, output_tokens=200,
        cost_usd=0.004, call_type="editing",
    )
    mock_client.generate_structured.return_value = (edited_ad, mock_usage)
    return TargetedEditor(mock_client), mock_client


def _sample_diagnosis():
    """A sample diagnosis for emotional_resonance."""
    return Diagnosis(
        weakest_dimension="emotional_resonance",
        score=5.5,
        problem_description="Ad uses only rational arguments without emotional hooks.",
        suggested_fix="Add parent-perspective opening about test stress.",
        preserve_dimensions=["clarity", "brand_voice", "value_proposition"],
    )


class TestTargetedEditor:
    def test_edit_returns_valid_ad_copy(self, sample_ad_copy):
        """edit() should return a valid AdCopy."""
        editor, _ = _make_mock_editor()
        diagnosis = _sample_diagnosis()
        edited, usage = editor.edit(sample_ad_copy, diagnosis)
        assert isinstance(edited, AdCopy)
        assert len(edited.primary_text) <= 500

    def test_edit_tracks_usage(self, sample_ad_copy):
        """edit() should return LLMUsage with cost."""
        editor, _ = _make_mock_editor()
        diagnosis = _sample_diagnosis()
        _, usage = editor.edit(sample_ad_copy, diagnosis)
        assert isinstance(usage, LLMUsage)
        assert usage.call_type == "editing"
        assert usage.cost_usd > 0

    def test_edit_prompt_includes_diagnosis(self, sample_ad_copy):
        """The editing prompt should contain the diagnosis details."""
        editor, mock_client = _make_mock_editor()
        diagnosis = _sample_diagnosis()
        editor.edit(sample_ad_copy, diagnosis)
        call_kwargs = mock_client.generate_structured.call_args.kwargs
        prompt = call_kwargs.get("prompt") or mock_client.generate_structured.call_args.args[0]
        assert "emotional_resonance" in prompt
        assert "rational arguments" in prompt

    def test_edit_prompt_includes_preservation(self, sample_ad_copy):
        """The editing prompt should list dimensions to preserve."""
        editor, mock_client = _make_mock_editor()
        diagnosis = _sample_diagnosis()
        editor.edit(sample_ad_copy, diagnosis)
        call_kwargs = mock_client.generate_structured.call_args.kwargs
        prompt = call_kwargs.get("prompt") or mock_client.generate_structured.call_args.args[0]
        assert "clarity" in prompt
        assert "brand_voice" in prompt

    def test_edit_uses_pro_model(self, sample_ad_copy):
        """Editing should use Gemini Pro, not Flash."""
        editor, mock_client = _make_mock_editor()
        diagnosis = _sample_diagnosis()
        editor.edit(sample_ad_copy, diagnosis)
        call_kwargs = mock_client.generate_structured.call_args.kwargs
        assert call_kwargs.get("model_type") == "pro"
