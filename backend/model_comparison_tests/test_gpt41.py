#!/usr/bin/env python3
"""
Test script for URLRulesExtractor using GPT-4.1 model with Azure SDK.
This script tests the URL rules extraction agent with GPT-4.1 model
and saves results with performance metrics including token usage.
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
from azure.ai.agents.models import ListSortOrder
from app.services.url_extractor import extract_full_page_text, extract_programme_title_from_text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test URLs - UCL programme criteria pages
TEST_URLS = [
    "https://www.ucl.ac.uk/prospective-students/graduate/taught-degrees/computer-graphics-vision-and-imaging-msc",
    "https://www.ucl.ac.uk/prospective-students/graduate/taught-degrees/education-ma",
    "https://www.ucl.ac.uk/prospective-students/graduate/taught-degrees/finance-msc",
]

class TokenCounter:
    """Mock token counter for cost estimation."""

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Rough token estimation: ~4 characters per token."""
        return len(text) // 4

    @staticmethod
    def calculate_cost(input_tokens: int, output_tokens: int, model: str) -> float:
        """Calculate estimated cost based on token usage."""
        # GPT-4.1 pricing: $2.00 input, $8.00 output per 1M tokens
        input_cost_per_1k = 0.002   # $2.00 per 1M tokens = $0.002 per 1K
        output_cost_per_1k = 0.008  # $8.00 per 1M tokens = $0.008 per 1K

        input_cost = (input_tokens / 1000) * input_cost_per_1k
        output_cost = (output_tokens / 1000) * output_cost_per_1k
        return input_cost + output_cost

def build_parsing_prompt(page_text: str, custom_requirements: list = None) -> str:
    """Build the exact same prompt as URLRulesExtractor uses."""
    return (
        "You are a JSON extraction specialist. Your task is to analyze UCL programme webpage content and extract admission requirements "
        "into appropriate evaluation agent categories.\n\n"
        f"Programme Webpage Content:\n{page_text}\n\n"
        f"Custom Requirements to Include: {custom_requirements or []}\n\n"
        "AGENT CATEGORIES:\n"
        "- english_agent: English language requirements (IELTS, TOEFL, language proficiency, exemptions)\n"
        "- degree_agent: Academic degree requirements (GPA, classification, subject prerequisites, academic background)\n"
        "- experience_agent: Work experience, internships, professional projects, industry experience\n"
        "- ps_rl_agent: Personal statement, reference letters, motivation letters, recommendation requirements\n"
        "- academic_agent: Research publications, academic achievements, scholarly work\n\n"
        "CRITICAL INSTRUCTIONS:\n"
        "- You MUST return ONLY valid JSON, nothing else\n"
        "- NO explanatory text before or after the JSON\n"
        "- NO markdown code fences or backticks\n"
        "- NO comments or additional formatting\n"
        "- The response must start with { and end with }\n"
        "- Assign each requirement to the MOST appropriate single category\n"
        "- If a requirement spans multiple categories, choose the primary/dominant one\n\n"
        "Required JSON structure (return exactly this format):\n"
        "{\n"
        '  "checklists": {\n'
        '    "english_agent": ["requirement 1", "requirement 2"],\n'
        '    "degree_agent": ["requirement 1", "requirement 2"],\n'
        '    "experience_agent": ["requirement if any"],\n'
        '    "ps_rl_agent": ["requirement if any"],\n'
        '    "academic_agent": ["requirement if any"]\n'
        '  },\n'
        '  "english_level": "level1/level2/level3/level4/level5 or null",\n'
        '  "degree_requirement_class": "FIRST/UPPER_SECOND/LOWER_SECOND or null"\n'
        "}\n\n"
        "START YOUR RESPONSE WITH THE JSON OBJECT NOW:"
    )

async def test_single_url_azure_sdk(url: str, run_number: int = 1) -> Dict[str, Any]:
    """Test URL extraction with GPT-4.1 using Azure SDK."""
    logger.info(f"Testing URL {run_number}: {url}")

    start_time = time.time()

    try:
        # Step 1: Extract page content
        page_data = await extract_full_page_text(url)
        if page_data.get("status") != "success":
            raise Exception(f"Failed to fetch URL: {page_data}")

        page_text = page_data.get("text", "")
        if len(page_text) < 100:
            raise Exception(f"Page text too short: {len(page_text)} chars")

        # Step 2: Create Azure AI Project client
        project = AIProjectClient(
            credential=DefaultAzureCredential(),
            endpoint="https://forthefirsttry-project-resource.services.ai.azure.com/api/projects/forthefirsttry-project"
        )

        # Step 3: Create or get GPT-4.1 agent
        try:
            # Try to create a new agent with GPT-4.1
            agent = project.agents.create_agent(
                model="gpt-4.1",
                name="URL-Rules-Extractor-GPT41-Test",
                instructions="You are a JSON extraction specialist. You must return ONLY valid JSON with no additional text, explanations, or formatting. Follow the user's format requirements exactly."
            )
            logger.info(f"Created new GPT-4.1 agent: {agent.id}")
        except Exception as e:
            logger.error(f"Failed to create GPT-4.1 agent: {e}")
            raise

        # Step 4: Create thread and process
        thread = project.agents.threads.create()
        logger.info(f"Created thread: {thread.id}")

        # Step 5: Send message
        prompt = build_parsing_prompt(page_text)
        message = project.agents.messages.create(
            thread_id=thread.id,
            role="user",
            content=prompt
        )

        # Step 6: Run and get response
        run = project.agents.runs.create_and_process(
            thread_id=thread.id,
            agent_id=agent.id
        )

        execution_time = time.time() - start_time

        # Try to get usage statistics from the run
        actual_input_tokens = None
        actual_output_tokens = None
        try:
            # Check if run has usage information
            if hasattr(run, 'usage') and run.usage:
                actual_input_tokens = run.usage.prompt_tokens if hasattr(run.usage, 'prompt_tokens') else None
                actual_output_tokens = run.usage.completion_tokens if hasattr(run.usage, 'completion_tokens') else None
                logger.info(f"Azure usage stats - Input: {actual_input_tokens}, Output: {actual_output_tokens}")
            elif hasattr(run, 'metadata') and run.metadata:
                # Sometimes usage is in metadata
                usage_data = run.metadata.get('usage', {})
                actual_input_tokens = usage_data.get('prompt_tokens')
                actual_output_tokens = usage_data.get('completion_tokens')
                logger.info(f"Azure metadata usage - Input: {actual_input_tokens}, Output: {actual_output_tokens}")
            else:
                logger.warning("No usage statistics available from Azure run")
        except Exception as e:
            logger.warning(f"Failed to extract usage statistics: {e}")

        if run.status == "failed":
            error_msg = f"Run failed: {run.last_error}"
            logger.error(error_msg)
            return {
                "url": url,
                "model": "gpt-4.1",
                "run_number": run_number,
                "success": False,
                "execution_time": execution_time,
                "error": error_msg,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }

        # Step 7: Extract response
        messages = project.agents.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING)

        response_text = ""
        for msg in messages:
            if msg.role == "assistant" and msg.text_messages:
                response_text = msg.text_messages[-1].text.value
                break

        if not response_text:
            raise Exception("No response from agent")

        # Step 8: Parse JSON response
        try:
            # Clean and parse JSON
            cleaned_response = response_text.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response.replace("```json", "").replace("```", "").strip()

            parsed_result = json.loads(cleaned_response)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            logger.error(f"Raw response: {response_text[:500]}")
            raise Exception(f"Invalid JSON response: {e}")

        # Step 9: Calculate metrics - use actual Azure stats if available
        if actual_input_tokens is not None and actual_output_tokens is not None:
            input_tokens = actual_input_tokens
            output_tokens = actual_output_tokens
            logger.info(f"Using actual Azure token counts: {input_tokens} + {output_tokens}")
        else:
            # Fallback to estimation
            input_tokens = TokenCounter.estimate_tokens(prompt)
            output_tokens = TokenCounter.estimate_tokens(response_text)
            logger.warning(f"Using estimated token counts: {input_tokens} + {output_tokens}")

        estimated_cost = TokenCounter.calculate_cost(input_tokens, output_tokens, "gpt-4.1")

        # Step 10: Format result like URLRulesExtractor
        final_result = {
            "checklists": parsed_result.get("checklists", {}),
            "english_level": parsed_result.get("english_level"),
            "degree_requirement_class": parsed_result.get("degree_requirement_class"),
            "programme_title": extract_programme_title_from_text(page_text, url),
            "rule_set_url": url,
            "text_length": len(page_text)
        }

        # Step 11: Cleanup
        try:
            project.agents.delete_agent(agent.id)
            logger.info(f"Deleted agent: {agent.id}")
        except:
            pass  # Ignore cleanup errors

        return {
            "url": url,
            "model": "gpt-4.1",
            "run_number": run_number,
            "success": True,
            "execution_time": execution_time,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost": estimated_cost,
            "result": final_result,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "raw_response": response_text[:500],  # For debugging
            "token_source": "azure_actual" if actual_input_tokens is not None else "estimated"
        }

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"Error testing URL {url}: {str(e)}")

        return {
            "url": url,
            "model": "gpt-4.1",
            "run_number": run_number,
            "success": False,
            "execution_time": execution_time,
            "error": str(e),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

async def run_all_tests() -> List[Dict[str, Any]]:
    """Run tests on all URLs with multiple iterations for consistency check."""
    all_results = []

    logger.info(f"Starting GPT-4.1 URL extraction tests on {len(TEST_URLS)} URLs")

    for i, url in enumerate(TEST_URLS, 1):
        logger.info(f"Processing URL {i}/{len(TEST_URLS)}: {url}")

        # Run each URL 2 times to check consistency
        for run in range(1, 3):
            result = await test_single_url_azure_sdk(url, run)
            all_results.append(result)

            # Small delay between runs
            await asyncio.sleep(2)

    return all_results

def save_results(results: List[Dict[str, Any]]) -> None:
    """Save test results to JSON file."""
    output_file = "gpt41_url_extractor_results.json"

    summary = {
        "test_summary": {
            "model": "gpt-4.1",
            "total_tests": len(results),
            "successful_tests": len([r for r in results if r.get("success", False)]),
            "failed_tests": len([r for r in results if not r.get("success", False)]),
            "total_cost": sum(r.get("estimated_cost", 0) for r in results),
            "average_execution_time": sum(r.get("execution_time", 0) for r in results) / len(results) if results else 0,
            "test_timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        },
        "detailed_results": results
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    logger.info(f"Results saved to {output_file}")

    # Print summary
    print("\n" + "="*60)
    print("GPT-4.1 URL EXTRACTOR TEST SUMMARY")
    print("="*60)
    print(f"Total tests: {summary['test_summary']['total_tests']}")
    print(f"Successful: {summary['test_summary']['successful_tests']}")
    print(f"Failed: {summary['test_summary']['failed_tests']}")
    print(f"Total estimated cost: ${summary['test_summary']['total_cost']:.4f}")
    print(f"Average execution time: {summary['test_summary']['average_execution_time']:.2f} seconds")
    print("="*60)

async def main():
    """Main test execution function."""
    try:
        results = await run_all_tests()
        save_results(results)

    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test execution failed: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())