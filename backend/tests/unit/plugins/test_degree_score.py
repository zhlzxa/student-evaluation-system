import pytest
from app.agents.plugins.degree_score import DegreeScorePlugin


class TestDegreeScorePlugin:
    """Test cases for DegreeScorePlugin functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.plugin = DegreeScorePlugin()

    def test_meets_percent_threshold_exactly_meets(self):
        """Test when observed percentage exactly meets required threshold."""
        result = self.plugin.meets_percent_threshold(85.0, 85.0)
        assert result is True

    def test_meets_percent_threshold_exceeds(self):
        """Test when observed percentage exceeds required threshold."""
        result = self.plugin.meets_percent_threshold(90.0, 85.0)
        assert result is True

    def test_meets_percent_threshold_below(self):
        """Test when observed percentage is below required threshold."""
        result = self.plugin.meets_percent_threshold(80.0, 85.0)
        assert result is False

    def test_meets_percent_threshold_edge_cases(self):
        """Test edge cases for percentage threshold checking."""
        # Test with zero values
        assert self.plugin.meets_percent_threshold(0.0, 0.0) is True
        assert self.plugin.meets_percent_threshold(1.0, 0.0) is True
        assert self.plugin.meets_percent_threshold(0.0, 1.0) is False

        # Test with maximum values
        assert self.plugin.meets_percent_threshold(100.0, 100.0) is True
        assert self.plugin.meets_percent_threshold(100.0, 99.0) is True
        assert self.plugin.meets_percent_threshold(99.0, 100.0) is False

    def test_meets_percent_threshold_decimal_precision(self):
        """Test threshold checking with decimal precision."""
        # Test very close values
        assert self.plugin.meets_percent_threshold(85.01, 85.0) is True
        assert self.plugin.meets_percent_threshold(84.99, 85.0) is False

        # Test high precision decimals
        assert self.plugin.meets_percent_threshold(85.123456, 85.123455) is True
        assert self.plugin.meets_percent_threshold(85.123454, 85.123455) is False

    def test_meets_percent_threshold_type_conversion(self):
        """Test that function properly handles type conversion."""
        # Test with integer inputs
        assert self.plugin.meets_percent_threshold(85, 80) is True
        assert self.plugin.meets_percent_threshold(75, 80) is False

        # Test with string inputs that can be converted to float
        assert self.plugin.meets_percent_threshold("85.5", "85.0") is True
        assert self.plugin.meets_percent_threshold("84.5", "85.0") is False

    def test_meets_percent_threshold_invalid_inputs(self):
        """Test behavior with invalid inputs."""
        with pytest.raises(ValueError):
            self.plugin.meets_percent_threshold("invalid", 85.0)

        with pytest.raises(ValueError):
            self.plugin.meets_percent_threshold(85.0, "invalid")

        with pytest.raises(TypeError):
            self.plugin.meets_percent_threshold(None, 85.0)

        with pytest.raises(TypeError):
            self.plugin.meets_percent_threshold(85.0, None)