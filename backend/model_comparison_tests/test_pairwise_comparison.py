#!/usr/bin/env python3
"""
Test script for Pairwise Comparison Agent using GPT-4.1 vs o3-mini model comparison.
This script tests the complex decision-making capabilities of models when comparing
applicants with similar weighted scores but different strength patterns.
"""

import asyncio
import json
import time
from typing import Any, Dict, List
import logging
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TokenCounter:
    """Token counter for cost estimation."""

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Rough token estimation: ~4 characters per token."""
        return len(text) // 4

    @staticmethod
    def calculate_cost_gpt41(input_tokens: int, output_tokens: int) -> float:
        """Calculate estimated cost for GPT-4.1: $2.00 input, $8.00 output per 1M tokens."""
        input_cost_per_1k = 0.002   # $2.00 per 1M tokens = $0.002 per 1K
        output_cost_per_1k = 0.008  # $8.00 per 1M tokens = $0.008 per 1K

        input_cost = (input_tokens / 1000) * input_cost_per_1k
        output_cost = (output_tokens / 1000) * output_cost_per_1k
        return input_cost + output_cost

    @staticmethod
    def calculate_cost_o3mini(input_tokens: int, output_tokens: int) -> float:
        """Calculate estimated cost for o3-mini: $1.10 input, $4.40 output per 1M tokens."""
        input_cost_per_1k = 0.0011   # $1.10 per 1M tokens = $0.0011 per 1K
        output_cost_per_1k = 0.0044  # $4.40 per 1M tokens = $0.0044 per 1K

        input_cost = (input_tokens / 1000) * input_cost_per_1k
        output_cost = (output_tokens / 1000) * output_cost_per_1k
        return input_cost + output_cost

def load_test_cases() -> Dict[str, Any]:
    """Load test cases configuration."""
    test_data_dir = os.path.join(os.path.dirname(__file__), "test_data", "pairwise_samples")
    config_path = os.path.join(test_data_dir, "test_cases.json")

    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_applicant_data(case_id: str, applicant: str) -> Dict[str, Any]:
    """Load applicant evaluation data."""
    test_data_dir = os.path.join(os.path.dirname(__file__), "test_data", "pairwise_samples")
    # Extract case number from case_id (e.g., "case_1_mid_tier_comparison" -> "case_1")
    case_number = case_id.split('_')[0] + '_' + case_id.split('_')[1]
    file_path = os.path.join(test_data_dir, f"{case_number}_applicant_{applicant}.json")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data["evaluation_data"]

def build_pairwise_instructions() -> str:
    """Build the exact Pairwise Comparison Agent instructions from the production system."""
    return (
        "You are performing detailed pairwise comparison for applicants with similar overall scores to refine their ranking in the admissions process. "
        "These applicants have already passed initial scoring and have comparable weighted scores that require nuanced analysis to determine final ranking order. "
        "Your task is to conduct holistic admissions decisions beyond simple score comparison, considering qualitative factors, evidence strength, and programme-specific requirements. "
        "Use the provided structured scores and evidence from multiple agents (english, degree, academic, experience, ps_rl) as baseline reference, "
        "but focus on determining which applicant would be a better overall fit for the UCL programme based on the weights (english 10%, degree 50%, academic 15%, experience 15%, ps_rl 10%). \n\n"
        "MANDATORY OUTPUT FORMAT: Return ONLY valid JSON with no additional text, explanations, or formatting.\n"
        "Do not use markdown code fences or backticks. Start with { and end with }.\n"
        "Return strict JSON: {winner: 'A'|'B'|'tie', reason: string}."
    )

def build_pairwise_content(app_a: Dict[str, Any], app_b: Dict[str, Any]) -> str:
    """Build the comparison content exactly as done in pipeline."""
    content_data = {"A": app_a, "B": app_b}
    return json.dumps(content_data)

async def test_single_comparison(case_id: str, applicant_a_data: Dict[str, Any],
                                applicant_b_data: Dict[str, Any], model: str) -> Dict[str, Any]:
    """Test pairwise comparison for a single case with specified model."""
    logger.info(f"Testing case {case_id} with model {model}")

    start_time = time.time()

    try:
        # Create Azure AI Project client
        project = AIProjectClient(
            credential=DefaultAzureCredential(),
            endpoint="https://forthefirsttry-project-resource.services.ai.azure.com/api/projects/forthefirsttry-project"
        )

        # Create agent with appropriate model
        agent = project.agents.create_agent(
            model=model,
            name=f"Pairwise-Comparison-{model.replace('.', '-')}",
            instructions=build_pairwise_instructions()
        )
        logger.info(f"Created {model} agent: {agent.id}")

        # Create thread
        thread = project.agents.threads.create()
        logger.info(f"Created thread: {thread.id}")

        # Send comparison content
        content = build_pairwise_content(applicant_a_data, applicant_b_data)
        message = project.agents.messages.create(
            thread_id=thread.id,
            role="user",
            content=content
        )

        # Run comparison
        run = project.agents.runs.create_and_process(
            thread_id=thread.id,
            agent_id=agent.id
        )

        execution_time = time.time() - start_time

        # Get token usage statistics
        actual_input_tokens = None
        actual_output_tokens = None
        try:
            if hasattr(run, 'usage') and run.usage:
                actual_input_tokens = run.usage.prompt_tokens if hasattr(run.usage, 'prompt_tokens') else None
                actual_output_tokens = run.usage.completion_tokens if hasattr(run.usage, 'completion_tokens') else None
                logger.info(f"Azure usage stats - Input: {actual_input_tokens}, Output: {actual_output_tokens}")
        except Exception as e:
            logger.warning(f"Failed to extract usage statistics: {e}")

        if run.status == "failed":
            error_msg = f"Run failed: {run.last_error}"
            logger.error(error_msg)
            return {
                "case_id": case_id,
                "model": model,
                "success": False,
                "execution_time": execution_time,
                "error": error_msg,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }

        # Extract response
        from azure.ai.agents.models import ListSortOrder
        messages = project.agents.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING)

        response_text = ""
        for msg in messages:
            if msg.role == "assistant" and msg.text_messages:
                response_text = msg.text_messages[-1].text.value
                break

        if not response_text:
            raise Exception("No response from agent")

        # Parse JSON response
        try:
            cleaned_response = response_text.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response.replace("```json", "").replace("```", "").strip()

            parsed_result = json.loads(cleaned_response)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            logger.error(f"Raw response: {response_text[:500]}")
            raise Exception(f"Invalid JSON response: {e}")

        # Calculate costs
        if actual_input_tokens is not None and actual_output_tokens is not None:
            input_tokens = actual_input_tokens
            output_tokens = actual_output_tokens
        else:
            # Fallback to estimation
            input_tokens = TokenCounter.estimate_tokens(content)
            output_tokens = TokenCounter.estimate_tokens(response_text)

        if model == "gpt-4.1":
            estimated_cost = TokenCounter.calculate_cost_gpt41(input_tokens, output_tokens)
        else:  # o3-mini
            estimated_cost = TokenCounter.calculate_cost_o3mini(input_tokens, output_tokens)

        # Extract comparison result
        winner = parsed_result.get("winner")
        reason = parsed_result.get("reason", "")

        # Validate winner value
        if winner not in {"A", "B", "tie"}:
            logger.warning(f"Invalid winner value: {winner}")

        # Cleanup
        try:
            project.agents.delete_agent(agent.id)
            logger.info(f"Deleted agent: {agent.id}")
        except:
            pass

        return {
            "case_id": case_id,
            "model": model,
            "success": True,
            "execution_time": execution_time,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost": estimated_cost,
            "winner": winner,
            "reason": reason,
            "result": parsed_result,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "raw_response": response_text[:1000],  # First 1000 chars for analysis
            "token_source": "azure_actual" if actual_input_tokens is not None else "estimated"
        }

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"Error testing case {case_id} with {model}: {str(e)}")

        return {
            "case_id": case_id,
            "model": model,
            "success": False,
            "execution_time": execution_time,
            "error": str(e),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

async def run_comparison_test() -> List[Dict[str, Any]]:
    """Run Pairwise Comparison Agent test between GPT-4.1 and o3-mini."""
    logger.info("Starting Pairwise Comparison Agent test")

    # Load test configuration
    test_config = load_test_cases()
    all_results = []

    for test_case in test_config["test_cases"]:
        case_id = test_case["case_id"]

        logger.info(f"Processing {case_id}")

        # Load applicant data
        applicant_a_data = load_applicant_data(case_id, "A")
        applicant_b_data = load_applicant_data(case_id, "B")

        # Test with GPT-4.1
        gpt41_result = await test_single_comparison(case_id, applicant_a_data, applicant_b_data, "gpt-4.1")
        all_results.append(gpt41_result)

        # Delay between model tests
        await asyncio.sleep(3)

        # Test with o3-mini
        o3mini_result = await test_single_comparison(case_id, applicant_a_data, applicant_b_data, "o3-mini")
        all_results.append(o3mini_result)

        # Delay between cases
        await asyncio.sleep(3)

    return all_results

def save_results(results: List[Dict[str, Any]]) -> None:
    """Save test results to JSON file with summary analysis."""
    output_file = "pairwise_comparison_results.json"

    # Separate results by model
    gpt41_results = [r for r in results if r.get("model") == "gpt-4.1"]
    o3mini_results = [r for r in results if r.get("model") == "o3-mini"]

    # Calculate summary statistics
    def calculate_model_stats(model_results):
        successful = [r for r in model_results if r.get("success", False)]
        if not successful:
            return {
                "total_tests": len(model_results),
                "successful_tests": 0,
                "failed_tests": len(model_results),
                "average_execution_time": 0,
                "total_cost": 0,
                "winner_distribution": {}
            }

        # Calculate winner distribution
        winner_counts = {}
        for r in successful:
            winner = r.get("winner", "unknown")
            winner_counts[winner] = winner_counts.get(winner, 0) + 1

        return {
            "total_tests": len(model_results),
            "successful_tests": len(successful),
            "failed_tests": len(model_results) - len(successful),
            "average_execution_time": sum(r.get("execution_time", 0) for r in successful) / len(successful),
            "total_cost": sum(r.get("estimated_cost", 0) for r in successful),
            "winner_distribution": winner_counts
        }

    summary = {
        "test_summary": {
            "test_type": "Pairwise Comparison Agent Model Comparison",
            "models_compared": ["gpt-4.1", "o3-mini"],
            "test_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "gpt41_summary": calculate_model_stats(gpt41_results),
            "o3mini_summary": calculate_model_stats(o3mini_results)
        },
        "detailed_results": results
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    logger.info(f"Results saved to {output_file}")

    # Print summary
    print("\n" + "="*70)
    print("PAIRWISE COMPARISON AGENT MODEL COMPARISON TEST SUMMARY")
    print("="*70)

    gpt41_stats = summary["test_summary"]["gpt41_summary"]
    o3mini_stats = summary["test_summary"]["o3mini_summary"]

    print(f"GPT-4.1 Results:")
    print(f"  Successful tests: {gpt41_stats['successful_tests']}/{gpt41_stats['total_tests']}")
    print(f"  Average execution time: {gpt41_stats['average_execution_time']:.2f} seconds")
    print(f"  Total cost: ${gpt41_stats['total_cost']:.4f}")
    print(f"  Winner distribution: {gpt41_stats['winner_distribution']}")

    print(f"\no3-mini Results:")
    print(f"  Successful tests: {o3mini_stats['successful_tests']}/{o3mini_stats['total_tests']}")
    print(f"  Average execution time: {o3mini_stats['average_execution_time']:.2f} seconds")
    print(f"  Total cost: ${o3mini_stats['total_cost']:.4f}")
    print(f"  Winner distribution: {o3mini_stats['winner_distribution']}")

    if gpt41_stats['total_cost'] > 0 and o3mini_stats['total_cost'] > 0:
        cost_ratio = o3mini_stats['total_cost'] / gpt41_stats['total_cost']
        print(f"\nCost Comparison:")
        print(f"  o3-mini vs GPT-4.1 cost ratio: {cost_ratio:.2f}x")

    print("="*70)

async def main():
    """Main test execution function."""
    try:
        results = await run_comparison_test()
        save_results(results)

    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test execution failed: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())