import pytest
from app.services.scoring import weighted_total, is_close, WEIGHTS


class TestWeightedTotal:
    """Test cases for weighted_total scoring function."""

    def test_weighted_total_all_scores_provided(self):
        """Test weighted total calculation with all scores provided."""
        result = weighted_total(
            english=8.0,
            degree=7.0,
            academic=6.0,
            experience=9.0,
            ps_rl=5.0
        )
        # Expected: 0.10*8 + 0.50*7 + 0.15*6 + 0.15*9 + 0.10*5 = 0.8 + 3.5 + 0.9 + 1.35 + 0.5 = 7.05
        expected = 7.05
        assert result == expected

    def test_weighted_total_some_none_values(self):
        """Test weighted total calculation with some None values."""
        result = weighted_total(
            english=8.0,
            degree=7.0,
            academic=None,  # Missing
            experience=9.0,
            ps_rl=None      # Missing
        )
        # Expected: 0.10*8 + 0.50*7 + 0.15*9 = 0.8 + 3.5 + 1.35 = 5.65
        expected = 5.65
        assert result == expected

    def test_weighted_total_all_none_values(self):
        """Test weighted total calculation with all None values."""
        result = weighted_total(
            english=None,
            degree=None,
            academic=None,
            experience=None,
            ps_rl=None
        )
        assert result == 0.0

    def test_weighted_total_clamps_high_values(self):
        """Test that values above 10 are clamped to 10."""
        result = weighted_total(
            english=15.0,  # Should be clamped to 10
            degree=12.0,   # Should be clamped to 10
            academic=8.0,
            experience=11.0,  # Should be clamped to 10
            ps_rl=7.0
        )
        # Expected: 0.10*10 + 0.50*10 + 0.15*8 + 0.15*10 + 0.10*7 = 1.0 + 5.0 + 1.2 + 1.5 + 0.7 = 9.4
        expected = 9.4
        assert result == expected

    def test_weighted_total_clamps_negative_values(self):
        """Test that negative values are clamped to 0."""
        result = weighted_total(
            english=-2.0,  # Should be clamped to 0
            degree=-5.0,   # Should be clamped to 0
            academic=8.0,
            experience=-1.0,  # Should be clamped to 0
            ps_rl=7.0
        )
        # Expected: 0.10*0 + 0.50*0 + 0.15*8 + 0.15*0 + 0.10*7 = 0 + 0 + 1.2 + 0 + 0.7 = 1.9
        expected = 1.9
        assert result == expected

    def test_weighted_total_boundary_values(self):
        """Test weighted total with boundary values (0 and 10)."""
        result = weighted_total(
            english=0.0,
            degree=10.0,
            academic=0.0,
            experience=10.0,
            ps_rl=0.0
        )
        # Expected: 0.10*0 + 0.50*10 + 0.15*0 + 0.15*10 + 0.10*0 = 0 + 5.0 + 0 + 1.5 + 0 = 6.5
        expected = 6.5
        assert result == expected

    def test_weighted_total_precision(self):
        """Test weighted total precision and rounding."""
        result = weighted_total(
            english=7.333,
            degree=8.666,
            academic=5.999,
            experience=4.001,
            ps_rl=9.777
        )
        # Should be rounded to 4 decimal places
        assert isinstance(result, float)
        # Check that result has at most 4 decimal places
        assert len(str(result).split('.')[-1]) <= 4

    def test_weighted_total_weights_sum_correctly(self):
        """Test that weights sum to 1.0 for consistency."""
        total_weight = sum(WEIGHTS.values())
        assert abs(total_weight - 1.0) < 1e-10

    def test_weighted_total_perfect_scores(self):
        """Test weighted total with perfect scores (all 10s)."""
        result = weighted_total(
            english=10.0,
            degree=10.0,
            academic=10.0,
            experience=10.0,
            ps_rl=10.0
        )
        # Should equal 10.0 when all components are perfect
        assert result == 10.0


class TestIsClose:
    """Test cases for is_close proximity function."""

    def test_is_close_within_default_epsilon(self):
        """Test is_close with values within default epsilon (0.3)."""
        assert is_close(5.0, 5.2) is True
        assert is_close(5.0, 4.8) is True
        assert is_close(5.0, 5.3) is True
        assert is_close(5.0, 4.7) is True

    def test_is_close_outside_default_epsilon(self):
        """Test is_close with values outside default epsilon (0.3)."""
        assert is_close(5.0, 5.4) is False
        assert is_close(5.0, 4.6) is False
        assert is_close(5.0, 5.5) is False
        assert is_close(5.0, 4.5) is False

    def test_is_close_exact_match(self):
        """Test is_close with exactly matching values."""
        assert is_close(5.0, 5.0) is True
        assert is_close(0.0, 0.0) is True
        assert is_close(10.0, 10.0) is True

    def test_is_close_custom_epsilon(self):
        """Test is_close with custom epsilon values."""
        # Tighter epsilon
        assert is_close(5.0, 5.05, eps=0.1) is True
        assert is_close(5.0, 5.15, eps=0.1) is False

        # Looser epsilon
        assert is_close(5.0, 6.0, eps=1.5) is True
        assert is_close(5.0, 7.0, eps=1.5) is False

    def test_is_close_negative_values(self):
        """Test is_close with negative values."""
        assert is_close(-5.0, -5.2) is True
        assert is_close(-5.0, -4.8) is True
        assert is_close(-5.0, -5.4) is False

    def test_is_close_mixed_signs(self):
        """Test is_close with mixed positive and negative values."""
        assert is_close(-0.1, 0.1) is True  # Within 0.3
        assert is_close(-0.2, 0.5) is False  # 0.7 difference > 0.3

    def test_is_close_zero_epsilon(self):
        """Test is_close with zero epsilon (exact match required)."""
        assert is_close(5.0, 5.0, eps=0.0) is True
        assert is_close(5.0, 5.001, eps=0.0) is False

    def test_is_close_large_values(self):
        """Test is_close with large values."""
        assert is_close(1000.0, 1000.2) is True
        assert is_close(1000.0, 1000.4) is False