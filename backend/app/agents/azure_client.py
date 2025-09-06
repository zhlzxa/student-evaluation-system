from __future__ import annotations

import asyncio
from typing import Optional, Callable, Awaitable

from azure.identity.aio import DefaultAzureCredential
from semantic_kernel.agents import AzureAIAgent, AzureAIAgentSettings, AzureAIAgentThread
from semantic_kernel.contents.chat_message_content import ChatMessageContent

from app.config import get_settings


async def run_single_turn(
    name: str,
    instructions: str,
    message: str,
    tools: Optional[object] = None,
    with_bing_grounding: bool = False,
    plugins: Optional[list[object]] = None,
    on_intermediate: Optional[Callable[[ChatMessageContent], Awaitable[None]]] = None,
) -> str:
    """Create a temporary agent, send one message, return final text.

    Ensures client/thread lifecycle are correctly managed within the call.
    """
    import logging
    import time
    logger = logging.getLogger(__name__)
    
    start_time = time.time()
    logger.info(f"[{name}] Starting Azure AI call")
    logger.info(f"[{name}] Instructions length: {len(instructions)} chars")
    logger.info(f"[{name}] Message: {message[:100]}...")
    logger.info(f"[{name}] With Bing: {with_bing_grounding}")
    logger.info(f"[{name}] Plugins: {[type(p).__name__ for p in (plugins or [])]}")
    
    # Add debug logging for materials evaluation agent calls
    logger.info(f"[MATERIALS-AGENT-REQUEST] Agent: {name}")
    logger.info(f"[MATERIALS-AGENT-REQUEST] Instructions: {instructions}")
    logger.info(f"[MATERIALS-AGENT-REQUEST] Message: {message}")
    logger.info(f"[MATERIALS-AGENT-REQUEST] Plugins: {[type(p).__name__ for p in (plugins or [])]}")
    logger.info(f"[MATERIALS-AGENT-REQUEST] With Bing: {with_bing_grounding}")
    settings = get_settings()
    # Resolve endpoint and deployment name from our settings first, then fall back to SK settings
    endpoint: Optional[str] = settings.AZURE_AI_AGENT_ENDPOINT
    deployment: Optional[str] = settings.AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME
    sk_settings: Optional[AzureAIAgentSettings] = None
    if not endpoint or not deployment:
        try:
            sk_settings = AzureAIAgentSettings()
        except Exception:
            sk_settings = None
    if not endpoint and sk_settings and getattr(sk_settings, "endpoint", None):
        endpoint = sk_settings.endpoint
    if not deployment and sk_settings and getattr(sk_settings, "model_deployment_name", None):
        deployment = sk_settings.model_deployment_name
    if not deployment:
        raise RuntimeError("Azure AI Agent model deployment name is not configured. Set AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME or SDK settings.")

    async with (
        DefaultAzureCredential() as creds,
        AzureAIAgent.create_client(credential=creds, endpoint=endpoint) as client,
    ):
        tool_defs = []
        tool_resources = []

        if tools is not None:
            defs = getattr(tools, "definitions", None)
            res = getattr(tools, "resources", None)
            if defs:
                tool_defs += defs
            if res:
                tool_resources += res

        if with_bing_grounding and settings.bing_connection_name:
            try:
                from azure.ai.agents.models import BingGroundingTool  # type: ignore
                import logging

                bing_connection = await client.connections.get(name=settings.bing_connection_name)
                conn_id = bing_connection.id
                bing_tool = BingGroundingTool(connection_id=conn_id)
                tool_defs += bing_tool.definitions
                tool_resources += bing_tool.resources
                logging.info(f"Successfully configured Bing Grounding with connection {settings.bing_connection_name}")
            except Exception as e:
                # Log the actual error instead of silently failing
                import logging
                logging.error(f"Failed to configure Bing Grounding: {e}")
                print(f"WARNING: Bing Grounding failed to initialize: {e}")
                # Continue without Bing
        agent_definition = await client.agents.create_agent(
            model=deployment,
            name=name,
            instructions=instructions,
            tools=tool_defs or None,
            tool_resources=tool_resources or None,
        )
        agent = AzureAIAgent(client=client, definition=agent_definition, plugins=plugins or [])

        thread: AzureAIAgentThread | None = None
        final = ""
        try:
            async for response in agent.invoke(messages=message, thread=thread, on_intermediate_message=on_intermediate):
                final = str(response)
                thread = response.thread
        finally:
            await thread.delete() if thread else None
        
        # Clean Unicode characters that cause encoding issues
        try:
            final = final.encode('utf-8', errors='ignore').decode('utf-8')
            # Remove common problematic Unicode characters
            final = final.replace('\u2020', '').replace('\u2021', '').replace('\u2022', '•')
        except:
            pass
        
        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"[{name}] Completed in {duration:.1f}s")
        logger.info(f"[{name}] Response length: {len(final)} chars")
        logger.info(f"[{name}] Response preview: {final[:200]}...")
        
        # Add debug logging for materials evaluation agent responses
        response_preview = final[:200] if len(final) > 200 else final
        logger.info(f"[MATERIALS-AGENT-RESPONSE] Agent: {name}")
        logger.info(f"[MATERIALS-AGENT-RESPONSE] Duration: {duration:.1f}s")
        logger.info(f"[MATERIALS-AGENT-RESPONSE] Response: {response_preview}")
        
        return final


def run_single_turn_blocking(
    name: str,
    instructions: str,
    message: str,
    tools: Optional[object] = None,
    with_bing_grounding: bool = False,
    plugins: Optional[list[object]] = None,
) -> str:
    return asyncio.run(
        run_single_turn(
            name=name,
            instructions=instructions,
            message=message,
            tools=tools,
            with_bing_grounding=with_bing_grounding,
            plugins=plugins,
        )
    )
