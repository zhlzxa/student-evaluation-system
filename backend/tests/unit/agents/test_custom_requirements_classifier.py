"""
Unit tests for custom requirements classifier functionality.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.agents.custom_requirements_classifier import (
    classify_custom_requirements,
    merge_classified_requirements_with_checklists
)


class TestMergeClassifiedRequirements:
    """Test cases for merge_classified_requirements_with_checklists function."""

    def test_merge_empty_lists(self):
        """Test merging when both original and classified are empty."""
        original = {
            "english_agent": [],
            "degree_agent": [],
            "experience_agent": [],
            "ps_rl_agent": [],
            "academic_agent": []
        }
        classified = {
            "english_agent": [],
            "degree_agent": [],
            "experience_agent": [],
            "ps_rl_agent": [],
            "academic_agent": []
        }

        result = merge_classified_requirements_with_checklists(original, classified)

        assert all(len(reqs) == 0 for reqs in result.values())
        assert set(result.keys()) == {"english_agent", "degree_agent", "experience_agent", "ps_rl_agent", "academic_agent"}

    def test_merge_only_original_requirements(self):
        """Test merging when only original requirements exist."""
        original = {
            "english_agent": ["IELTS 6.5 minimum"],
            "degree_agent": ["Upper second class degree", "Relevant bachelor's degree"],
            "experience_agent": [],
            "ps_rl_agent": ["Personal statement required"],
            "academic_agent": []
        }
        classified = {
            "english_agent": [],
            "degree_agent": [],
            "experience_agent": [],
            "ps_rl_agent": [],
            "academic_agent": []
        }

        result = merge_classified_requirements_with_checklists(original, classified)

        assert result["english_agent"] == ["IELTS 6.5 minimum"]
        assert result["degree_agent"] == ["Upper second class degree", "Relevant bachelor's degree"]
        assert result["experience_agent"] == []
        assert result["ps_rl_agent"] == ["Personal statement required"]
        assert result["academic_agent"] == []

    def test_merge_only_classified_requirements(self):
        """Test merging when only classified requirements exist."""
        original = {
            "english_agent": [],
            "degree_agent": [],
            "experience_agent": [],
            "ps_rl_agent": [],
            "academic_agent": []
        }
        classified = {
            "english_agent": ["[USER DEFINED] IELTS 7.0 minimum"],
            "degree_agent": ["[USER DEFINED] Minimum GPA 3.5"],
            "experience_agent": ["[USER DEFINED] 2 years work experience"],
            "ps_rl_agent": [],
            "academic_agent": ["[USER DEFINED] At least one publication"]
        }

        result = merge_classified_requirements_with_checklists(original, classified)

        assert result["english_agent"] == ["[USER DEFINED] IELTS 7.0 minimum"]
        assert result["degree_agent"] == ["[USER DEFINED] Minimum GPA 3.5"]
        assert result["experience_agent"] == ["[USER DEFINED] 2 years work experience"]
        assert result["ps_rl_agent"] == []
        assert result["academic_agent"] == ["[USER DEFINED] At least one publication"]

    def test_merge_custom_requirements_come_first(self):
        """Test that custom requirements are placed before original requirements."""
        original = {
            "english_agent": ["IELTS 6.5 minimum", "TOEFL 90 minimum"],
            "degree_agent": ["Upper second class degree"],
            "experience_agent": ["Any relevant experience"],
            "ps_rl_agent": ["Personal statement required"],
            "academic_agent": []
        }
        classified = {
            "english_agent": ["[USER DEFINED] IELTS 7.0 minimum"],
            "degree_agent": ["[USER DEFINED] Minimum GPA 3.5"],
            "experience_agent": ["[USER DEFINED] 2 years work experience"],
            "ps_rl_agent": [],
            "academic_agent": ["[USER DEFINED] At least one publication"]
        }

        result = merge_classified_requirements_with_checklists(original, classified)

        # Check that custom requirements come first
        assert result["english_agent"][0] == "[USER DEFINED] IELTS 7.0 minimum"
        assert result["english_agent"][1] == "IELTS 6.5 minimum"
        assert result["english_agent"][2] == "TOEFL 90 minimum"

        assert result["degree_agent"][0] == "[USER DEFINED] Minimum GPA 3.5"
        assert result["degree_agent"][1] == "Upper second class degree"

        assert result["experience_agent"][0] == "[USER DEFINED] 2 years work experience"
        assert result["experience_agent"][1] == "Any relevant experience"

        # ps_rl_agent has no custom requirements, should only have original
        assert result["ps_rl_agent"] == ["Personal statement required"]

        # academic_agent has no original requirements, should only have custom
        assert result["academic_agent"] == ["[USER DEFINED] At least one publication"]

    def test_merge_handles_missing_agents(self):
        """Test merging handles missing agent keys gracefully."""
        original = {
            "english_agent": ["IELTS 6.5 minimum"],
            "degree_agent": ["Upper second class degree"]
            # Missing other agents
        }
        classified = {
            "experience_agent": ["[USER DEFINED] 2 years work experience"],
            "academic_agent": ["[USER DEFINED] At least one publication"]
            # Missing other agents
        }

        result = merge_classified_requirements_with_checklists(original, classified)

        # Should include all expected agents
        assert set(result.keys()) == {"english_agent", "degree_agent", "experience_agent", "ps_rl_agent", "academic_agent"}

        assert result["english_agent"] == ["IELTS 6.5 minimum"]
        assert result["degree_agent"] == ["Upper second class degree"]
        assert result["experience_agent"] == ["[USER DEFINED] 2 years work experience"]
        assert result["ps_rl_agent"] == []
        assert result["academic_agent"] == ["[USER DEFINED] At least one publication"]


class TestClassifyCustomRequirements:
    """Test cases for classify_custom_requirements function."""

    def test_empty_requirements(self):
        """Test classifying empty requirements list."""
        import asyncio

        async def run_test():
            result = await classify_custom_requirements(
                custom_requirements=[],
                run_id=123
            )

            assert result["classified_checklists"] == {}
            assert result["classification_details"] == []
            assert result["total_classified"] == 0

        asyncio.run(run_test())

    @patch('app.agents.custom_requirements_classifier.run_single_turn')
    @patch('app.agents.custom_requirements_classifier.log_agent_event')
    @patch('app.agents.custom_requirements_classifier.parse_agent_json')
    def test_successful_classification(self, mock_parse_json, mock_log_event, mock_run_single_turn):
        """Test successful classification of custom requirements."""
        import asyncio

        # Mock the agent response
        mock_run_single_turn.return_value = AsyncMock(return_value="mocked_response")

        # Mock the parsed response
        mock_parse_json.return_value = {
            "classifications": [
                {
                    "requirement": "Minimum GPA 3.5",
                    "agent": "degree_agent",
                    "priority": "high",
                    "reasoning": "GPA is related to academic performance"
                },
                {
                    "requirement": "2 years work experience",
                    "agent": "experience_agent",
                    "priority": "normal",
                    "reasoning": "Work experience relates to professional background"
                },
                {
                    "requirement": "IELTS 7.0 minimum",
                    "agent": "english_agent",
                    "priority": "high",
                    "reasoning": "IELTS is an English language test"
                }
            ],
            "summary": {
                "total_requirements": 3,
                "english_agent": 1,
                "degree_agent": 1,
                "experience_agent": 1,
                "ps_rl_agent": 0,
                "academic_agent": 0
            }
        }

        async def run_test():
            result = await classify_custom_requirements(
                custom_requirements=["Minimum GPA 3.5", "2 years work experience", "IELTS 7.0 minimum"],
                run_id=123
            )

            # Check classified checklists
            assert result["classified_checklists"]["degree_agent"] == ["[USER DEFINED] Minimum GPA 3.5"]
            assert result["classified_checklists"]["experience_agent"] == ["[USER DEFINED] 2 years work experience"]
            assert result["classified_checklists"]["english_agent"] == ["[USER DEFINED] IELTS 7.0 minimum"]
            assert result["classified_checklists"]["ps_rl_agent"] == []
            assert result["classified_checklists"]["academic_agent"] == []

            # Check classification details
            assert len(result["classification_details"]) == 3
            assert result["total_classified"] == 3

            # Verify agent was called
            mock_run_single_turn.assert_called_once()

            # Verify logging was called
            assert mock_log_event.call_count >= 2  # start and completed events

        asyncio.run(run_test())

    @patch('app.agents.custom_requirements_classifier.run_single_turn')
    @patch('app.agents.custom_requirements_classifier.log_agent_event')
    def test_classification_failure_fallback(self, mock_log_event, mock_run_single_turn):
        """Test fallback behavior when classification fails."""
        import asyncio

        # Mock the agent to raise an exception
        mock_run_single_turn.side_effect = Exception("Agent failed")

        async def run_test():
            result = await classify_custom_requirements(
                custom_requirements=["Minimum GPA 3.5", "2 years work experience"],
                run_id=123
            )

            # Should fall back to degree_agent for all requirements
            assert result["classified_checklists"]["degree_agent"] == [
                "[USER DEFINED] Minimum GPA 3.5",
                "[USER DEFINED] 2 years work experience"
            ]
            assert result["classified_checklists"]["english_agent"] == []
            assert result["classified_checklists"]["experience_agent"] == []
            assert result["classified_checklists"]["ps_rl_agent"] == []
            assert result["classified_checklists"]["academic_agent"] == []

            # Should indicate fallback was used
            assert result["total_classified"] == 0
            assert result.get("fallback_used") is True

            # Verify error logging
            mock_log_event.assert_called()
            error_calls = [call for call in mock_log_event.call_args_list if "error" in str(call)]
            assert len(error_calls) > 0

        asyncio.run(run_test())

    @patch('app.agents.custom_requirements_classifier.run_single_turn')
    @patch('app.agents.custom_requirements_classifier.log_agent_event')
    @patch('app.agents.custom_requirements_classifier.parse_agent_json')
    def test_invalid_agent_name_handling(self, mock_parse_json, mock_log_event, mock_run_single_turn):
        """Test handling of invalid agent names in classification response."""
        import asyncio

        # Mock the agent response with invalid agent name
        mock_run_single_turn.return_value = AsyncMock(return_value="mocked_response")

        mock_parse_json.return_value = {
            "classifications": [
                {
                    "requirement": "Some requirement",
                    "agent": "invalid_agent",  # Invalid agent name
                    "priority": "normal",
                    "reasoning": "Test reasoning"
                },
                {
                    "requirement": "Valid requirement",
                    "agent": "degree_agent",  # Valid agent name
                    "priority": "normal",
                    "reasoning": "Test reasoning"
                }
            ],
            "summary": {
                "total_requirements": 2,
                "invalid_agent": 1,
                "degree_agent": 1
            }
        }

        async def run_test():
            result = await classify_custom_requirements(
                custom_requirements=["Some requirement", "Valid requirement"],
                run_id=123
            )

            # Only the valid requirement should be classified
            assert result["classified_checklists"]["degree_agent"] == ["[USER DEFINED] Valid requirement"]
            assert result["classified_checklists"]["english_agent"] == []

            # Should have fewer classification details due to invalid agent
            assert len(result["classification_details"]) == 1
            assert result["total_classified"] == 1

        asyncio.run(run_test())


class TestClassificationIntegration:
    """Integration tests for the complete custom requirements classification workflow."""

    def test_user_defined_marker_consistency(self):
        """Test that USER DEFINED markers are consistent throughout the workflow."""
        original = {
            "english_agent": ["Standard IELTS requirement"],
            "degree_agent": ["Standard degree requirement"],
            "experience_agent": [],
            "ps_rl_agent": [],
            "academic_agent": []
        }

        classified = {
            "english_agent": ["[USER DEFINED] IELTS 7.0 minimum"],
            "degree_agent": ["[USER DEFINED] Minimum GPA 3.5"],
            "experience_agent": ["[USER DEFINED] 2 years experience"],
            "ps_rl_agent": [],
            "academic_agent": []
        }

        merged = merge_classified_requirements_with_checklists(original, classified)

        # Check that all custom requirements have the marker
        for agent, requirements in merged.items():
            custom_reqs = [req for req in requirements if "[USER DEFINED]" in req]
            standard_reqs = [req for req in requirements if "[USER DEFINED]" not in req]

            # Custom requirements should come first
            for i, req in enumerate(requirements):
                if "[USER DEFINED]" in req:
                    # All custom requirements should come before any standard requirements
                    remaining_reqs = requirements[i+1:]
                    custom_after = any("[USER DEFINED]" in r for r in remaining_reqs)
                    if not custom_after:
                        # If no more custom requirements after this one,
                        # all remaining should be standard
                        standard_after = all("[USER DEFINED]" not in r for r in remaining_reqs)
                        assert standard_after, f"Found mixed ordering in {agent}: {requirements}"

    def test_all_agent_types_supported(self):
        """Test that all expected agent types are supported in classification."""
        all_agents = {"english_agent", "degree_agent", "experience_agent", "ps_rl_agent", "academic_agent"}

        original = {agent: [] for agent in all_agents}
        classified = {agent: [f"[USER DEFINED] Test requirement for {agent}"] for agent in all_agents}

        merged = merge_classified_requirements_with_checklists(original, classified)

        # All agents should be present in result
        assert set(merged.keys()) == all_agents

        # Each agent should have exactly one custom requirement
        for agent in all_agents:
            assert len(merged[agent]) == 1
            assert merged[agent][0] == f"[USER DEFINED] Test requirement for {agent}"