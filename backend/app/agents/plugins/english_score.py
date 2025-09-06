from __future__ import annotations

from typing import Annotated

from semantic_kernel.functions import kernel_function


class EnglishScorePlugin:
    """Hard comparison plugin for deterministic score evaluation.

    This plugin should be called by the English evaluation agent when it needs
    to convert numeric test results into a normalized 0-10 score based on the
    level rule that applies (e.g., UCL Level 2 for IELTS).
    """

    @kernel_function(description="Score IELTS overall band for Level 2 policy.")
    def score_ielts_level2(
        self,
        overall: Annotated[float, "IELTS overall band"],
    ) -> Annotated[int, "Score from 0 to 10"]:
        # Example mapping provided by product spec for Level 2
        if overall >= 8.0:
            return 10
        if overall >= 7.5:
            return 7
        if overall >= 7.0:
            return 5
        if overall >= 6.5:
            return 0
        return 0

    @kernel_function(description="Compare numeric thresholds for overall and components.")
    def meets_thresholds(
        self,
        overall: Annotated[float, "Observed overall or -1 if N/A"] = -1.0,
        min_overall: Annotated[float, "Required overall or -1 if N/A"] = -1.0,
        reading: Annotated[float, "Observed reading or -1 if N/A"] = -1.0,
        min_reading: Annotated[float, "Required reading or -1 if N/A"] = -1.0,
        writing: Annotated[float, "Observed writing or -1 if N/A"] = -1.0,
        min_writing: Annotated[float, "Required writing or -1 if N/A"] = -1.0,
        speaking: Annotated[float, "Observed speaking or -1 if N/A"] = -1.0,
        min_speaking: Annotated[float, "Required speaking or -1 if N/A"] = -1.0,
        listening: Annotated[float, "Observed listening or -1 if N/A"] = -1.0,
        min_listening: Annotated[float, "Required listening or -1 if N/A"] = -1.0,
    ) -> Annotated[bool, "True if all provided observed values meet or exceed required minimums"]:
        if min_overall >= 0 and overall >= 0 and overall < min_overall:
            return False
        if min_reading >= 0 and reading >= 0 and reading < min_reading:
            return False
        if min_writing >= 0 and writing >= 0 and writing < min_writing:
            return False
        if min_speaking >= 0 and speaking >= 0 and speaking < min_speaking:
            return False
        if min_listening >= 0 and listening >= 0 and listening < min_listening:
            return False
        return True
