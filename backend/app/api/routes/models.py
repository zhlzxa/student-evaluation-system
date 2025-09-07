from __future__ import annotations

from typing import Dict, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.model_config import (
    get_model_config,
    get_supported_models,
    get_agent_types,
    update_agent_model,
)

router = APIRouter()


class ModelConfigResponse(BaseModel):
    """Response model for model configuration."""
    agent_models: Dict[str, str]
    default_model: str
    supported_models: List[str]
    agent_types: List[str]


class UpdateAgentModelRequest(BaseModel):
    """Request model for updating agent model."""
    agent_type: str
    model: str


class UpdateDefaultModelRequest(BaseModel):
    """Request model for updating default model."""
    model: str


@router.get("/config", response_model=ModelConfigResponse)
async def get_model_configuration():
    """Get current model configuration for all agents."""
    model_config = get_model_config()
    
    return ModelConfigResponse(
        agent_models=model_config.get_all_models(),
        default_model=model_config.default_model,
        supported_models=get_supported_models(),
        agent_types=get_agent_types(),
    )


@router.put("/agent/{agent_type}")
async def update_agent_model_config(agent_type: str, request: UpdateAgentModelRequest):
    """Update the model for a specific agent type."""
    try:
        if agent_type != request.agent_type:
            raise HTTPException(status_code=400, detail="Agent type in path and body must match")
        
        update_agent_model(request.agent_type, request.model)
        
        return {"message": f"Model updated for agent '{agent_type}' to '{request.model}'"}
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/default")
async def update_default_model_config(request: UpdateDefaultModelRequest):
    """Update the default model for all agents."""
    try:
        model_config = get_model_config()
        model_config.set_default_model(request.model)
        
        return {"message": f"Default model updated to '{request.model}'"}
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reset")
async def reset_to_default():
    """Reset all agent models to the default model."""
    model_config = get_model_config()
    model_config.reset_to_default()
    
    return {"message": "All agent models reset to default"}


@router.get("/supported")
async def get_supported_models_list():
    """Get list of supported models."""
    return {"models": get_supported_models()}


@router.get("/agents")
async def get_agent_types_list():
    """Get list of available agent types."""
    return {"agent_types": get_agent_types()}