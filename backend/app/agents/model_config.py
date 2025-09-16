from __future__ import annotations

from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from app.config import get_settings


class AgentType(Enum):
    """Enum for different agent types in the system."""
    ENGLISH = "english"
    DEGREE = "degree"
    EXPERIENCE = "experience"
    PS_RL = "ps_rl"
    ACADEMIC = "academic"
    COMPARE = "compare"
    CLASSIFIER = "classifier"
    BATCH_CLASSIFIER = "batch_classifier"
    URL_RULES_EXTRACTOR = "url_rules_extractor"


@dataclass
class ModelConfig:
    """Configuration for AI models per agent type."""
    agent_models: Dict[AgentType, str] = field(default_factory=dict)
    default_model: str = "gpt-4.1"
    
    def __post_init__(self):
        settings = get_settings()
        self.default_model = settings.DEFAULT_MODEL
        
        # Initialize all agents with default model if not specified
        for agent_type in AgentType:
            if agent_type not in self.agent_models:
                self.agent_models[agent_type] = self.default_model
    
    def get_model_for_agent(self, agent_type: AgentType) -> str:
        """Get the model configured for a specific agent type."""
        return self.agent_models.get(agent_type, self.default_model)
    
    def set_model_for_agent(self, agent_type: AgentType, model: str):
        """Set the model for a specific agent type."""
        settings = get_settings()
        if model in settings.supported_models:
            self.agent_models[agent_type] = model
        else:
            raise ValueError(f"Model '{model}' not supported. Available models: {settings.supported_models}")
    
    def set_default_model(self, model: str):
        """Set the default model for all agents."""
        settings = get_settings()
        if model in settings.supported_models:
            self.default_model = model
        else:
            raise ValueError(f"Model '{model}' not supported. Available models: {settings.supported_models}")
    
    def get_all_models(self) -> Dict[str, str]:
        """Get all agent model configurations."""
        return {agent_type.value: model for agent_type, model in self.agent_models.items()}
    
    def reset_to_default(self):
        """Reset all agents to use the default model."""
        for agent_type in AgentType:
            self.agent_models[agent_type] = self.default_model


# Global model configuration instance
_model_config = ModelConfig()


def get_model_config() -> ModelConfig:
    """Get the global model configuration instance."""
    return _model_config


def get_model_for_agent(agent_name: str) -> str:
    """Get the model configured for a specific agent by name."""
    try:
        agent_type = AgentType(agent_name.lower())
        return _model_config.get_model_for_agent(agent_type)
    except ValueError:
        # If agent type not found, return default model
        return _model_config.default_model


def update_agent_model(agent_name: str, model: str):
    """Update the model for a specific agent."""
    try:
        agent_type = AgentType(agent_name.lower())
        _model_config.set_model_for_agent(agent_type, model)
    except ValueError as e:
        raise ValueError(f"Invalid agent type '{agent_name}' or model '{model}': {e}")


def get_supported_models() -> list[str]:
    """Get list of supported models."""
    settings = get_settings()
    return settings.supported_models


def get_agent_types() -> list[str]:
    """Get list of available agent types."""
    return [agent_type.value for agent_type in AgentType]