from __future__ import annotations

from typing import Annotated

from semantic_kernel.functions import kernel_function


class DegreeScorePlugin:
    """Deterministic helpers for degree thresholds and simple scoring.

    These functions are intentionally minimal; semantic interpretation of
    scales and policies should be done by the agent prior to calling them.
    """

    @kernel_function(description="Check if observed percentage meets a required minimum percentage.")
    def meets_percent_threshold(
        self,
        observed_percent: Annotated[float, "Observed overall percent (0-100)"],
        min_required_percent: Annotated[float, "Minimum required overall percent (0-100)"],
    ) -> Annotated[bool, "True if observed >= required"]:
        return float(observed_percent) >= float(min_required_percent)

    @kernel_function(description="Map percent scale to a 0-10 score using a simple policy.")
    def percent_to_score(
        self,
        observed_percent: Annotated[float, "Observed overall percent (0-100)"],
    ) -> Annotated[int, "Score from 0 to 10"]:
        p = float(observed_percent)
        if p >= 95:
            return 10
        if p >= 90:
            return 6
        if p >= 85:
            return 4
        return 0

