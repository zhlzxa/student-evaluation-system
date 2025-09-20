#!/usr/bin/env python3
"""
Compare results from GPT-4.1 and o3-mini URL extraction tests.
This script loads both test results and provides detailed comparison
including performance metrics, token usage, and output quality analysis.
"""

import json
import sys
from typing import Dict, Any, List
from pprint import pprint

def load_test_results(filename: str) -> Dict[str, Any]:
    """Load test results from JSON file."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Results file {filename} not found.")
        print("Please run the individual test scripts first:")
        print("  python test_gpt41.py")
        print("  python test_o3mini.py")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {filename}")
        sys.exit(1)

def calculate_cost_comparison(gpt41_results: Dict, o3mini_results: Dict) -> None:
    """Calculate and display cost comparison between models."""
    gpt41_cost = gpt41_results['test_summary']['total_cost']
    o3mini_cost = o3mini_results['test_summary']['total_cost']

    cost_difference = gpt41_cost - o3mini_cost
    cost_ratio = gpt41_cost / o3mini_cost if o3mini_cost > 0 else float('inf')

    print("COST ANALYSIS")
    print("-" * 50)
    print(f"GPT-4.1 total cost:   ${gpt41_cost:.4f}")
    print(f"o3-mini total cost:   ${o3mini_cost:.4f}")
    print(f"Cost difference:      ${cost_difference:.4f}")
    print(f"Cost ratio (4.1/mini): {cost_ratio:.2f}x")

    if cost_difference > 0:
        savings_percent = (cost_difference / gpt41_cost) * 100
        print(f"o3-mini saves:        {savings_percent:.1f}%")
    else:
        extra_percent = (abs(cost_difference) / o3mini_cost) * 100
        print(f"GPT-4.1 saves:       {extra_percent:.1f}%")

def calculate_performance_comparison(gpt41_results: Dict, o3mini_results: Dict) -> None:
    """Calculate and display performance comparison between models."""
    gpt41_time = gpt41_results['test_summary']['average_execution_time']
    o3mini_time = o3mini_results['test_summary']['average_execution_time']

    time_difference = gpt41_time - o3mini_time

    print("\nPERFORMANCE ANALYSIS")
    print("-" * 50)
    print(f"GPT-4.1 avg time:     {gpt41_time:.2f} seconds")
    print(f"o3-mini avg time:     {o3mini_time:.2f} seconds")
    print(f"Time difference:      {time_difference:+.2f} seconds")

    if abs(time_difference) > 0.1:
        faster_model = "o3-mini" if time_difference > 0 else "GPT-4.1"
        speedup = abs(time_difference) / max(gpt41_time, o3mini_time) * 100
        print(f"{faster_model} is faster by: {speedup:.1f}%")

def compare_success_rates(gpt41_results: Dict, o3mini_results: Dict) -> None:
    """Compare success rates between models."""
    gpt41_success = gpt41_results['test_summary']['successful_tests']
    gpt41_total = gpt41_results['test_summary']['total_tests']
    gpt41_rate = (gpt41_success / gpt41_total) * 100 if gpt41_total > 0 else 0

    o3mini_success = o3mini_results['test_summary']['successful_tests']
    o3mini_total = o3mini_results['test_summary']['total_tests']
    o3mini_rate = (o3mini_success / o3mini_total) * 100 if o3mini_total > 0 else 0

    print("\nSUCCESS RATE ANALYSIS")
    print("-" * 50)
    print(f"GPT-4.1 success:      {gpt41_success}/{gpt41_total} ({gpt41_rate:.1f}%)")
    print(f"o3-mini success:      {o3mini_success}/{o3mini_total} ({o3mini_rate:.1f}%)")

    rate_difference = gpt41_rate - o3mini_rate
    if abs(rate_difference) > 1:
        better_model = "GPT-4.1" if rate_difference > 0 else "o3-mini"
        print(f"{better_model} has better success rate by {abs(rate_difference):.1f}%")
    else:
        print("Success rates are comparable")

def display_detailed_comparison(gpt41_results: Dict, o3mini_results: Dict) -> None:
    """Display detailed output comparison for each URL."""
    gpt41_details = gpt41_results['detailed_results']
    o3mini_details = o3mini_results['detailed_results']

    # Group results by URL
    gpt41_by_url = {}
    for result in gpt41_details:
        url = result['url']
        if url not in gpt41_by_url:
            gpt41_by_url[url] = []
        gpt41_by_url[url].append(result)

    o3mini_by_url = {}
    for result in o3mini_details:
        url = result['url']
        if url not in o3mini_by_url:
            o3mini_by_url[url] = []
        o3mini_by_url[url].append(result)

    print("\nDETAILED OUTPUT COMPARISON")
    print("=" * 80)

    for url in sorted(set(gpt41_by_url.keys()) | set(o3mini_by_url.keys())):
        print(f"\nURL: {url}")
        print("-" * 80)

        # Compare first successful result from each model
        gpt41_result = None
        o3mini_result = None

        for result in gpt41_by_url.get(url, []):
            if result.get('success', False):
                gpt41_result = result
                break

        for result in o3mini_by_url.get(url, []):
            if result.get('success', False):
                o3mini_result = result
                break

        if gpt41_result and o3mini_result:
            # Compare requirements count
            gpt41_reqs = gpt41_result['result'].get('checklists', {})
            o3mini_reqs = o3mini_result['result'].get('checklists', {})

            print(f"Requirements extracted:")
            for agent in ['english_agent', 'degree_agent', 'experience_agent', 'ps_rl_agent', 'academic_agent']:
                gpt41_count = len(gpt41_reqs.get(agent, []))
                o3mini_count = len(o3mini_reqs.get(agent, []))
                print(f"  {agent}: GPT-4.1({gpt41_count}) vs o3-mini({o3mini_count})")

            # Show execution details
            print(f"Execution time: GPT-4.1({gpt41_result['execution_time']:.2f}s) vs o3-mini({o3mini_result['execution_time']:.2f}s)")
            print(f"Estimated cost: GPT-4.1(${gpt41_result['estimated_cost']:.4f}) vs o3-mini(${o3mini_result['estimated_cost']:.4f})")

        elif gpt41_result:
            print("Only GPT-4.1 succeeded")
        elif o3mini_result:
            print("Only o3-mini succeeded")
        else:
            print("Both models failed")

def display_raw_outputs(gpt41_results: Dict, o3mini_results: Dict, url_index: int = 0) -> None:
    """Display raw JSON outputs for comparison."""
    print(f"\nRAW OUTPUT COMPARISON (URL {url_index + 1})")
    print("=" * 80)

    gpt41_details = gpt41_results['detailed_results']
    o3mini_details = o3mini_results['detailed_results']

    # Find first successful result for each model
    gpt41_output = None
    o3mini_output = None

    for result in gpt41_details:
        if result.get('success', False):
            gpt41_output = result['result']
            break

    for result in o3mini_details:
        if result.get('success', False):
            o3mini_output = result['result']
            break

    if gpt41_output:
        print("\nGPT-4.1 OUTPUT:")
        print("-" * 40)
        pprint(gpt41_output, width=120, depth=4)

    if o3mini_output:
        print("\no3-mini OUTPUT:")
        print("-" * 40)
        pprint(o3mini_output, width=120, depth=4)

def main():
    """Main comparison function."""
    print("URL RULES EXTRACTOR MODEL COMPARISON")
    print("=" * 80)

    # Load test results
    gpt41_results = load_test_results("gpt41_url_extractor_results.json")
    o3mini_results = load_test_results("o3mini_url_extractor_results.json")

    # Display high-level comparisons
    calculate_cost_comparison(gpt41_results, o3mini_results)
    calculate_performance_comparison(gpt41_results, o3mini_results)
    compare_success_rates(gpt41_results, o3mini_results)

    # Display detailed comparison
    display_detailed_comparison(gpt41_results, o3mini_results)

    # Ask user if they want to see raw outputs
    try:
        response = input("\nShow raw JSON outputs for comparison? (y/n): ").lower().strip()
        if response == 'y' or response == 'yes':
            display_raw_outputs(gpt41_results, o3mini_results)
    except KeyboardInterrupt:
        print("\nComparison completed.")

if __name__ == "__main__":
    main()