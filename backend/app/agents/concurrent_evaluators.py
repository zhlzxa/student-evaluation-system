from __future__ import annotations

import asyncio
from typing import Any


async def run_concurrent_evaluation(
    applicant_id: int,
    run_id: int,
    english_level_hint: str | None = None,
    english_policy: dict | None = None,
    target_degree_class: str = "UPPER_SECOND",
    degree_checklists: list[str] | None = None,
    experience_checklists: list[str] | None = None,
    ps_rl_checklists: list[str] | None = None,
    academic_checklists: list[str] | None = None,
    special_context: str | None = None,
    detected_country_iso3: str | None = None,
    agent_models: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run all 5 evaluation agents concurrently using simple asyncio.gather()."""
    
    import logging
    logger = logging.getLogger(__name__)
    
    # Log the checklists received for debugging
    logger.info(f"Concurrent evaluator received checklists for applicant {applicant_id}:")
    logger.info(f"  - degree_checklists: {degree_checklists}")
    logger.info(f"  - experience_checklists: {experience_checklists}") 
    logger.info(f"  - ps_rl_checklists: {ps_rl_checklists}")
    logger.info(f"  - academic_checklists: {academic_checklists}")
    
    # Import the actual agent functions directly
    from app.agents.evaluators import (
        english_agent,
        degree_agent,
        experience_agent,
        ps_rl_agent,
        academic_agent,
    )
    
    # Resolve optional per-agent model overrides
    agent_models = agent_models or {}
    def m(name: str) -> str | None:
        return agent_models.get(name)

    # Create concurrent tasks for all 5 agents
    tasks = {}
    
    # English Agent
    tasks["english"] = english_agent(
        applicant_id=applicant_id,
        run_id=run_id,
        level_hint=english_level_hint,
        policy=english_policy,
        model_override=m("english"),
    )
    
    # Degree Agent
    tasks["degree"] = degree_agent(
        applicant_id=applicant_id,
        run_id=run_id,
        target_class=target_degree_class,
        checklists=degree_checklists,
        special_context=special_context,
        detected_country_iso3=detected_country_iso3,
        model_override=m("degree"),
    )
    
    # Experience Agent
    tasks["experience"] = experience_agent(
        applicant_id=applicant_id,
        run_id=run_id,
        checklist=experience_checklists,
        model_override=m("experience"),
    )
    
    # PS/RL Agent
    tasks["ps_rl"] = ps_rl_agent(
        applicant_id=applicant_id,
        run_id=run_id,
        checklist=ps_rl_checklists,
        model_override=m("ps_rl"),
    )
    
    # Academic Agent
    tasks["academic"] = academic_agent(
        applicant_id=applicant_id,
        run_id=run_id,
        checklist=academic_checklists,
        model_override=m("academic"),
    )
    
    # Run all agents concurrently with timeout
    try:
        # Execute all tasks concurrently with 2-minute timeout
        results = await asyncio.wait_for(
            asyncio.gather(
                *tasks.values(),
                return_exceptions=True  # Don't fail if one agent fails
            ),
            timeout=120.0
        )
        
        # Map results back to agent names
        agent_results = {}
        agent_names = list(tasks.keys())
        
        for i, result in enumerate(results):
            agent_name = agent_names[i]
            
            if isinstance(result, Exception):
                # Handle individual agent failures
                agent_results[agent_name] = {
                    "error": f"Agent execution failed: {str(result)}",
                    "exception_type": type(result).__name__
                }
            else:
                # Successful result
                agent_results[agent_name] = result
        
        return agent_results
        
    except asyncio.TimeoutError:
        # Handle timeout
        agent_results = {}
        for agent_name in tasks.keys():
            agent_results[agent_name] = {
                "error": "Agent execution timed out after 2 minutes"
            }
        return agent_results
        
    except Exception as e:
        # Handle unexpected errors
        agent_results = {}
        for agent_name in tasks.keys():
            agent_results[agent_name] = {
                "error": f"Concurrent execution failed: {str(e)}"
            }
        return agent_results
