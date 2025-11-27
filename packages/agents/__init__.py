"""
Agents package for my-desk.ai

Contains:
- PersonaAgent: The conversational AI with personality
- ToolRegistry: Dynamic tool management
- ContextManager: Efficient context retrieval for conversations
"""

from .persona_agent import PersonaAgent, get_persona_agent
from .tool_registry import ToolRegistry, ToolDef, get_registry
from .context_manager import ContextManager, get_context_manager, RetrievedContext

__all__ = [
    # Persona Agent
    "PersonaAgent",
    "get_persona_agent",
    # Tool Registry
    "ToolRegistry",
    "ToolDef",
    "get_registry",
    # Context Manager
    "ContextManager",
    "get_context_manager",
    "RetrievedContext",
]
