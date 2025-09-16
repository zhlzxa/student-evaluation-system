import pytest
import json
from app.agents.json_utils import parse_agent_json


class TestParseAgentJson:
    """Test cases for parse_agent_json utility function."""

    def test_parse_valid_json(self):
        """Test parsing of valid JSON strings."""
        valid_json = '{"score": 8, "status": "pass"}'
        result = parse_agent_json(valid_json)

        assert result is not None
        assert result["score"] == 8
        assert result["status"] == "pass"

    def test_parse_json_with_code_fences(self):
        """Test parsing JSON wrapped in code fences."""
        json_with_fences = '```json\n{"score": 7, "level": "intermediate"}\n```'
        result = parse_agent_json(json_with_fences)

        assert result is not None
        assert result["score"] == 7
        assert result["level"] == "intermediate"

    def test_parse_json_with_text_prefix(self):
        """Test parsing JSON that has text before the JSON object."""
        response_with_prefix = 'Here is the evaluation result: {"score": 9, "passed": true}'
        result = parse_agent_json(response_with_prefix)

        assert result is not None
        assert result["score"] == 9
        assert result["passed"] is True

    def test_parse_json_with_nested_objects(self):
        """Test parsing nested JSON objects."""
        nested_json = '{"evaluation": {"english": {"score": 8}, "degree": {"score": 7}}}'
        result = parse_agent_json(nested_json)

        assert result is not None
        assert result["evaluation"]["english"]["score"] == 8
        assert result["evaluation"]["degree"]["score"] == 7

    def test_parse_json_with_arrays(self):
        """Test parsing JSON with arrays."""
        json_with_arrays = '{"evidence": ["Good grades", "Strong CV"], "scores": [8, 7, 9]}'
        result = parse_agent_json(json_with_arrays)

        assert result is not None
        assert len(result["evidence"]) == 2
        assert result["evidence"][0] == "Good grades"
        assert result["scores"] == [8, 7, 9]

    def test_parse_empty_string(self):
        """Test parsing empty string."""
        result = parse_agent_json("")
        assert result is None

    def test_parse_none_input(self):
        """Test parsing None input."""
        result = parse_agent_json(None)
        assert result is None

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON."""
        invalid_json = '{"score": 8, "status": incomplete}'  # Missing quotes
        result = parse_agent_json(invalid_json)
        assert result is None

    def test_parse_no_json_in_response(self):
        """Test parsing response with no JSON object."""
        no_json_response = "This is just plain text with no JSON"
        result = parse_agent_json(no_json_response)
        assert result is None

    def test_parse_incomplete_json(self):
        """Test parsing incomplete JSON (missing closing brace)."""
        incomplete_json = '{"score": 8, "status": "pass"'  # Missing closing brace
        result = parse_agent_json(incomplete_json)
        assert result is None

    def test_parse_json_with_trailing_text(self):
        """Test parsing JSON with trailing text fails with current implementation."""
        json_with_suffix = '{"score": 6} This is additional text that should be ignored'
        result = parse_agent_json(json_with_suffix)

        # Current implementation fails when there's trailing text after JSON
        assert result is None

    def test_parse_json_with_special_characters(self):
        """Test parsing JSON with special characters in strings."""
        json_with_special = '{"message": "Score: 85% - Excellent work!", "unicode": "测试中文"}'
        result = parse_agent_json(json_with_special)

        assert result is not None
        assert "85%" in result["message"]
        assert result["unicode"] == "测试中文"

    def test_parse_json_boolean_and_null(self):
        """Test parsing JSON with boolean and null values."""
        json_with_types = '{"passed": true, "failed": false, "pending": null}'
        result = parse_agent_json(json_with_types)

        assert result is not None
        assert result["passed"] is True
        assert result["failed"] is False
        assert result["pending"] is None

    def test_parse_multiple_json_objects(self):
        """Test parsing multiple JSON objects fails with current implementation."""
        multiple_objects = '{"first": 1} {"second": 2}'
        result = parse_agent_json(multiple_objects)

        # Current implementation fails when there are multiple JSON objects
        assert result is None

    def test_parse_json_with_whitespace(self):
        """Test parsing JSON with various whitespace."""
        whitespace_json = '\\n\\t  {"score": 8}  \\n'
        result = parse_agent_json(whitespace_json)

        assert result is not None
        assert result["score"] == 8