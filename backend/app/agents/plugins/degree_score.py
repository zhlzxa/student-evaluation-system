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

