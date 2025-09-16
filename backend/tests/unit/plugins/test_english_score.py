import pytest
from app.agents.plugins.english_score import EnglishScorePlugin


class TestEnglishScorePlugin:
    """Test cases for EnglishScorePlugin functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.plugin = EnglishScorePlugin()

    def test_score_ielts_level2_excellent(self):
        """Test IELTS Level 2 scoring for excellent scores (8.0+)."""
        assert self.plugin.score_ielts_level2(8.0) == 10
        assert self.plugin.score_ielts_level2(8.5) == 10
        assert self.plugin.score_ielts_level2(9.0) == 10

    def test_score_ielts_level2_good(self):
        """Test IELTS Level 2 scoring for good scores (7.5-7.9)."""
        assert self.plugin.score_ielts_level2(7.5) == 7
        assert self.plugin.score_ielts_level2(7.9) == 7

    def test_score_ielts_level2_acceptable(self):
        """Test IELTS Level 2 scoring for acceptable scores (7.0-7.4)."""
        assert self.plugin.score_ielts_level2(7.0) == 5
        assert self.plugin.score_ielts_level2(7.4) == 5

    def test_score_ielts_level2_minimum(self):
        """Test IELTS Level 2 scoring for minimum scores (6.5-6.9)."""
        assert self.plugin.score_ielts_level2(6.5) == 0
        assert self.plugin.score_ielts_level2(6.9) == 0

    def test_score_ielts_level2_below_minimum(self):
        """Test IELTS Level 2 scoring for below minimum scores (<6.5)."""
        assert self.plugin.score_ielts_level2(6.0) == 0
        assert self.plugin.score_ielts_level2(5.5) == 0
        assert self.plugin.score_ielts_level2(0.0) == 0

    def test_score_ielts_level2_edge_cases(self):
        """Test IELTS Level 2 scoring edge cases."""
        # Test boundary values
        assert self.plugin.score_ielts_level2(7.999) == 7
        assert self.plugin.score_ielts_level2(8.001) == 10
        assert self.plugin.score_ielts_level2(6.999) == 0  # Below 7.0 threshold
        assert self.plugin.score_ielts_level2(7.001) == 5

    def test_score_exemption_various_reasons(self):
        """Test exemption scoring with various exemption reasons."""
        assert self.plugin.score_exemption("British nationality") == 10
        assert self.plugin.score_exemption("UK degree") == 10
        assert self.plugin.score_exemption("Canadian university") == 10
        assert self.plugin.score_exemption("US education") == 10
        assert self.plugin.score_exemption("") == 10  # Empty reason still gets 10

    def test_meets_thresholds_all_pass(self):
        """Test threshold checking when all components pass."""
        result = self.plugin.meets_thresholds(
            overall=7.5, min_overall=7.0,
            reading=7.0, min_reading=6.5,
            writing=7.0, min_writing=6.5,
            speaking=7.0, min_speaking=6.5,
            listening=7.0, min_listening=6.5
        )
        assert result is True

    def test_meets_thresholds_overall_fail(self):
        """Test threshold checking when overall score fails."""
        result = self.plugin.meets_thresholds(
            overall=6.5, min_overall=7.0,
            reading=7.0, min_reading=6.5,
            writing=7.0, min_writing=6.5,
            speaking=7.0, min_speaking=6.5,
            listening=7.0, min_listening=6.5
        )
        assert result is False

    def test_meets_thresholds_component_fail(self):
        """Test threshold checking when one component fails."""
        result = self.plugin.meets_thresholds(
            overall=7.5, min_overall=7.0,
            reading=6.0, min_reading=6.5,  # Reading fails
            writing=7.0, min_writing=6.5,
            speaking=7.0, min_speaking=6.5,
            listening=7.0, min_listening=6.5
        )
        assert result is False

    def test_meets_thresholds_no_requirements(self):
        """Test threshold checking when no requirements are set."""
        result = self.plugin.meets_thresholds()
        assert result is True

    def test_meets_thresholds_partial_data(self):
        """Test threshold checking with partial data (some -1 values)."""
        # Only overall and reading are provided
        result = self.plugin.meets_thresholds(
            overall=7.5, min_overall=7.0,
            reading=7.0, min_reading=6.5,
            writing=-1, min_writing=-1,
            speaking=-1, min_speaking=-1,
            listening=-1, min_listening=-1
        )
        assert result is True

    def test_meets_thresholds_mixed_scenarios(self):
        """Test various mixed scenarios for threshold checking."""
        # Some components not required (-1 min values)
        result = self.plugin.meets_thresholds(
            overall=7.5, min_overall=7.0,
            reading=6.0, min_reading=-1,  # Reading not required
            writing=7.0, min_writing=6.5,
            speaking=-1, min_speaking=6.5,  # Speaking not provided
            listening=7.0, min_listening=6.5
        )
        assert result is True

    def test_meets_thresholds_edge_values(self):
        """Test threshold checking with exact boundary values."""
        # Exact matches should pass
        result = self.plugin.meets_thresholds(
            overall=7.0, min_overall=7.0,
            reading=6.5, min_reading=6.5,
            writing=6.5, min_writing=6.5,
            speaking=6.5, min_speaking=6.5,
            listening=6.5, min_listening=6.5
        )
        assert result is True

        # Just below threshold should fail
        result = self.plugin.meets_thresholds(
            overall=6.9, min_overall=7.0,
            reading=6.5, min_reading=6.5,
            writing=6.5, min_writing=6.5,
            speaking=6.5, min_speaking=6.5,
            listening=6.5, min_listening=6.5
        )
        assert result is False