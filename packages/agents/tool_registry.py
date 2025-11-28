"""
Dynamic Tool Registry for Persona Agent

Tools are stored as JSON files that Claude Code (Builder Agent) can create/modify.
The registry watches for changes and reloads tools dynamically.

Tool storage structure:
/home/claude/tools/
├── core/           # Always-loaded tools (tier 0-1)
│   ├── cognitive.json
│   ├── delegation.json
│   └── meta.json
├── builtin/        # Deferred tools (tier 2)
│   ├── research.json
│   ├── calendar.json
│   └── email.json
└── generated/      # Claude Code created tools (tier 3)
    └── *.json
"""

import os
import json
import hashlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Literal
from datetime import datetime

# Default tools directory
TOOLS_DIR = Path("/home/claude/tools")

# Singleton registry instance
_registry_instance: Optional["ToolRegistry"] = None


@dataclass
class ToolDef:
    """Definition of a tool available to the Persona Agent."""
    name: str
    description: str
    input_schema: dict
    tier: Literal[0, 1, 2, 3] = 2
    handler_module: Optional[str] = None  # Python module path for handler
    handler_function: Optional[str] = None  # Function name in module
    input_examples: List[dict] = field(default_factory=list)
    category: str = "general"
    enabled: bool = True
    created_at: Optional[str] = None
    created_by: str = "system"  # "system", "builder", "user"

    def to_api_schema(self) -> dict:
        """Convert to Bedrock/Anthropic API tool schema."""
        # Standard Anthropic/Bedrock tool format
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema
        }

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON storage."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "tier": self.tier,
            "handler_module": self.handler_module,
            "handler_function": self.handler_function,
            "input_examples": self.input_examples,
            "category": self.category,
            "enabled": self.enabled,
            "created_at": self.created_at or datetime.utcnow().isoformat(),
            "created_by": self.created_by
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ToolDef":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            description=data["description"],
            input_schema=data["input_schema"],
            tier=data.get("tier", 2),
            handler_module=data.get("handler_module"),
            handler_function=data.get("handler_function"),
            input_examples=data.get("input_examples", []),
            category=data.get("category", "general"),
            enabled=data.get("enabled", True),
            created_at=data.get("created_at"),
            created_by=data.get("created_by", "system")
        )


class ToolRegistry:
    """
    Dynamic tool registry that loads tools from JSON files.

    Claude Code (Builder Agent) can add new tools by:
    1. Creating a .json file in /home/claude/tools/generated/
    2. Calling refresh_tools() or the agent's refresh_tools tool

    Tools are organized by tier:
    - Tier 0: Tool search (always loaded, required for defer_loading)
    - Tier 1: Core tools (always loaded - cognitive tree, delegation)
    - Tier 2: Built-in tools (deferred - research, calendar, email)
    - Tier 3: Generated tools (deferred - created by Builder Agent)
    """

    def __init__(self, tools_dir: Path = TOOLS_DIR):
        self.tools_dir = tools_dir
        self._tools: Dict[str, ToolDef] = {}
        self._file_hashes: Dict[str, str] = {}
        self._handlers: Dict[str, Callable] = {}
        self._last_refresh: Optional[datetime] = None

        # Ensure directories exist
        self._ensure_directories()

        # Load all tools
        self.refresh_tools()

    def _ensure_directories(self):
        """Create tool directories if they don't exist."""
        for subdir in ["core", "builtin", "generated"]:
            (self.tools_dir / subdir).mkdir(parents=True, exist_ok=True)

    def _file_hash(self, path: Path) -> str:
        """Get hash of file contents for change detection."""
        if not path.exists():
            return ""
        return hashlib.md5(path.read_bytes()).hexdigest()

    def refresh_tools(self) -> Dict[str, Any]:
        """
        Reload all tools from disk.

        Returns summary of changes.
        """
        changes = {"added": [], "updated": [], "removed": [], "errors": []}
        seen_tools = set()

        # Scan all tool directories
        for subdir in ["core", "builtin", "generated"]:
            dir_path = self.tools_dir / subdir
            if not dir_path.exists():
                continue

            for json_file in dir_path.glob("*.json"):
                try:
                    file_hash = self._file_hash(json_file)
                    old_hash = self._file_hashes.get(str(json_file))

                    # Load if new or changed
                    if file_hash != old_hash:
                        with open(json_file) as f:
                            data = json.load(f)

                        # Handle single tool or list of tools
                        tools_data = data if isinstance(data, list) else [data]

                        for tool_data in tools_data:
                            tool = ToolDef.from_dict(tool_data)

                            if tool.name in self._tools:
                                changes["updated"].append(tool.name)
                            else:
                                changes["added"].append(tool.name)

                            self._tools[tool.name] = tool
                            seen_tools.add(tool.name)

                        self._file_hashes[str(json_file)] = file_hash
                    else:
                        # File unchanged, just mark tools as seen
                        with open(json_file) as f:
                            data = json.load(f)
                        tools_data = data if isinstance(data, list) else [data]
                        for tool_data in tools_data:
                            seen_tools.add(tool_data["name"])

                except Exception as e:
                    changes["errors"].append(f"{json_file.name}: {str(e)}")

        # Remove tools from deleted files
        for tool_name in list(self._tools.keys()):
            if tool_name not in seen_tools:
                del self._tools[tool_name]
                changes["removed"].append(tool_name)

        self._last_refresh = datetime.utcnow()
        return changes

    def get_tool(self, name: str) -> Optional[ToolDef]:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self,
                   tier: Optional[int] = None,
                   category: Optional[str] = None,
                   enabled_only: bool = True) -> List[ToolDef]:
        """List tools with optional filtering."""
        tools = list(self._tools.values())

        if tier is not None:
            tools = [t for t in tools if t.tier == tier]
        if category:
            tools = [t for t in tools if t.category == category]
        if enabled_only:
            tools = [t for t in tools if t.enabled]

        return tools

    def get_tools_for_api(self) -> List[dict]:
        """
        Get all tools formatted for Bedrock API.

        Returns tools in the format required by Bedrock's invoke_model.
        """
        tools = []

        # Add all enabled tools
        for tool in self.list_tools(enabled_only=True):
            tools.append(tool.to_api_schema())

        return tools

    def get_core_tools_for_api(self) -> List[dict]:
        """Get only tier 0-1 tools (always loaded)."""
        tools = []

        for tool in self.list_tools(enabled_only=True):
            if tool.tier <= 1:
                tools.append(tool.to_api_schema())

        return tools

    def register_tool(self, tool: ToolDef, save: bool = True) -> bool:
        """
        Register a new tool.

        Args:
            tool: Tool definition
            save: If True, save to disk in generated/ directory

        Returns:
            True if successful
        """
        self._tools[tool.name] = tool

        if save:
            # Save to generated directory
            file_path = self.tools_dir / "generated" / f"{tool.name}.json"
            with open(file_path, "w") as f:
                json.dump(tool.to_dict(), f, indent=2)
            self._file_hashes[str(file_path)] = self._file_hash(file_path)

        return True

    def unregister_tool(self, name: str, delete_file: bool = False) -> bool:
        """Remove a tool from the registry."""
        if name not in self._tools:
            return False

        tool = self._tools[name]
        del self._tools[name]

        if delete_file:
            # Try to find and delete the file
            for subdir in ["generated", "builtin", "core"]:
                file_path = self.tools_dir / subdir / f"{name}.json"
                if file_path.exists():
                    file_path.unlink()
                    if str(file_path) in self._file_hashes:
                        del self._file_hashes[str(file_path)]
                    break

        return True

    def register_handler(self, tool_name: str, handler: Callable):
        """Register a Python handler for a tool."""
        self._handlers[tool_name] = handler

    def get_handler(self, tool_name: str) -> Optional[Callable]:
        """Get the handler for a tool."""
        # First check registered handlers
        if tool_name in self._handlers:
            return self._handlers[tool_name]

        # Then try to load from module path
        tool = self._tools.get(tool_name)
        if tool and tool.handler_module and tool.handler_function:
            try:
                import importlib
                module = importlib.import_module(tool.handler_module)
                handler = getattr(module, tool.handler_function)
                self._handlers[tool_name] = handler
                return handler
            except Exception as e:
                print(f"Failed to load handler for {tool_name}: {e}")

        return None

    def execute_tool(self, name: str, input_data: dict) -> Any:
        """
        Execute a tool by name.

        Args:
            name: Tool name
            input_data: Tool input parameters

        Returns:
            Tool execution result
        """
        handler = self.get_handler(name)
        if not handler:
            raise ValueError(f"No handler registered for tool: {name}")

        return handler(**input_data)

    def get_stats(self) -> dict:
        """Get registry statistics."""
        tools = list(self._tools.values())
        return {
            "total_tools": len(tools),
            "by_tier": {
                0: len([t for t in tools if t.tier == 0]),
                1: len([t for t in tools if t.tier == 1]),
                2: len([t for t in tools if t.tier == 2]),
                3: len([t for t in tools if t.tier == 3]),
            },
            "by_category": {},
            "enabled": len([t for t in tools if t.enabled]),
            "disabled": len([t for t in tools if not t.enabled]),
            "last_refresh": self._last_refresh.isoformat() if self._last_refresh else None
        }


def get_registry(tools_dir: Path = TOOLS_DIR) -> ToolRegistry:
    """Get the singleton ToolRegistry instance."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ToolRegistry(tools_dir)
    return _registry_instance


def create_initial_tools():
    """
    Create the initial tool JSON files if they don't exist.

    Call this once during setup.
    """
    tools_dir = TOOLS_DIR
    tools_dir.mkdir(parents=True, exist_ok=True)

    # Core tools (tier 0-1) - always loaded
    core_tools = [
        {
            "name": "get_cognitive_context",
            "description": """Retrieve context from the cognitive tree (Neo4j graph).

Search terms: memory, context, graph, knowledge, user, projects, people, history
Use when: need user context, project info, relationship data, past conversations
Returns: Structured context including user profile, active projects, recent activity

Retrieves:
- User profile and preferences
- Active projects and their status
- Recent insights and learnings
- Key people and relationships""",
            "input_schema": {
                "type": "object",
                "properties": {
                    "context_type": {
                        "type": "string",
                        "enum": ["full", "user", "projects", "people", "recent"],
                        "description": "Type of context to retrieve"
                    },
                    "project_name": {
                        "type": "string",
                        "description": "Specific project to get context for"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max items to return",
                        "default": 10
                    }
                }
            },
            "tier": 1,
            "handler_module": "packages.agents.core_handlers",
            "handler_function": "get_cognitive_context",
            "category": "cognitive"
        },
        {
            "name": "update_cognitive_tree",
            "description": """Update the cognitive tree with new information.

Search terms: save, store, remember, add, create, update, memory, learn
Use when: learning new info about user, creating projects/tasks/insights
Returns: Confirmation of what was stored

Can create/update:
- Projects (name, description, goals)
- People (name, relationship, context)
- Tasks (description, status, project)
- Insights (learnings, observations)
- Goals (objectives, timeframes)""",
            "input_schema": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["create", "update", "link"],
                        "description": "Operation to perform"
                    },
                    "node_type": {
                        "type": "string",
                        "enum": ["Project", "Person", "Task", "Insight", "Goal"],
                        "description": "Type of node"
                    },
                    "data": {
                        "type": "object",
                        "description": "Node data (name, description, etc.)"
                    },
                    "link_to": {
                        "type": "string",
                        "description": "Node ID to link to (for link operation)"
                    }
                },
                "required": ["operation", "node_type", "data"]
            },
            "tier": 1,
            "handler_module": "packages.agents.core_handlers",
            "handler_function": "update_cognitive_tree",
            "category": "cognitive"
        },
        {
            "name": "delegate_to_builder",
            "description": """Delegate a task to Claude Code (Builder Agent) for file operations or tool creation.

Search terms: file, code, create, build, write, edit, tool, script, automation
Use when: need to create/edit files, build new tools, run code, complex operations
Returns: Result from Claude Code execution

Builder Agent can:
- Create/edit files and code
- Build new tools for the Persona Agent
- Run shell commands
- Access the file system
- Install packages""",
            "input_schema": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "Detailed description of what to do"
                    },
                    "task_type": {
                        "type": "string",
                        "enum": ["file_operation", "create_tool", "run_code", "research"],
                        "description": "Type of task"
                    },
                    "context": {
                        "type": "string",
                        "description": "Additional context for the task"
                    },
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Relevant file paths"
                    }
                },
                "required": ["task", "task_type"]
            },
            "tier": 1,
            "handler_module": "packages.agents.core_handlers",
            "handler_function": "delegate_to_builder",
            "category": "delegation"
        },
        {
            "name": "refresh_tools",
            "description": """Refresh the tool registry to load new tools created by Builder Agent.

Search terms: reload, refresh, tools, update, new tools
Use when: Builder Agent has created new tools, tools seem out of date
Returns: Summary of added/updated/removed tools""",
            "input_schema": {
                "type": "object",
                "properties": {}
            },
            "tier": 1,
            "handler_module": "packages.agents.core_handlers",
            "handler_function": "refresh_tools",
            "category": "meta"
        },
        {
            "name": "list_available_tools",
            "description": """List all available tools with descriptions.

Search terms: tools, capabilities, help, what can you do
Use when: need to know available capabilities, user asks what you can do
Returns: List of tools with names, descriptions, and categories""",
            "input_schema": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Filter by category"
                    },
                    "include_disabled": {
                        "type": "boolean",
                        "description": "Include disabled tools",
                        "default": False
                    }
                }
            },
            "tier": 1,
            "handler_module": "packages.agents.core_handlers",
            "handler_function": "list_available_tools",
            "category": "meta"
        }
    ]

    # Write core tools
    core_file = tools_dir / "core" / "core_tools.json"
    core_file.parent.mkdir(parents=True, exist_ok=True)
    with open(core_file, "w") as f:
        json.dump(core_tools, f, indent=2)

    # Built-in tools (tier 2) - deferred loading
    builtin_tools = [
        {
            "name": "search_emails",
            "description": """Search user's emails for relevant information.

Search terms: email, gmail, messages, inbox, correspondence, communication
Use when: looking for email conversations, finding contact info, tracking discussions
Returns: List of matching emails with sender, subject, date, snippet

Supports:
- Full text search
- Date range filtering
- Sender/recipient filtering""",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Max emails to return",
                        "default": 10
                    },
                    "after_date": {
                        "type": "string",
                        "description": "Only emails after this date (YYYY-MM-DD)"
                    },
                    "before_date": {
                        "type": "string",
                        "description": "Only emails before this date"
                    }
                },
                "required": ["query"]
            },
            "tier": 2,
            "handler_module": "packages.private_services.gmail",
            "handler_function": "search_emails",
            "category": "research"
        },
        {
            "name": "search_calendar",
            "description": """Search user's calendar for events.

Search terms: calendar, events, meetings, schedule, appointments, when
Use when: checking schedule, finding past events, looking for appointments
Returns: List of calendar events with title, date, time, attendees

Supports:
- Text search in event titles/descriptions
- Date range queries
- Recurring event detection""",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search text (optional)"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start of date range (YYYY-MM-DD)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End of date range"
                    },
                    "max_results": {
                        "type": "integer",
                        "default": 20
                    }
                }
            },
            "tier": 2,
            "handler_module": "packages.research.google_services",
            "handler_function": "search_calendar",
            "category": "research"
        },
        {
            "name": "search_contacts",
            "description": """Search user's contacts.

Search terms: contacts, people, phone, address, find person
Use when: looking up contact information, finding people
Returns: Contact details including name, email, phone

Searches across:
- Name
- Email addresses
- Phone numbers
- Organizations""",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Name or email to search"
                    },
                    "max_results": {
                        "type": "integer",
                        "default": 10
                    }
                },
                "required": ["query"]
            },
            "tier": 2,
            "handler_module": "packages.research.google_services",
            "handler_function": "search_contacts",
            "category": "research"
        },
        {
            "name": "web_search",
            "description": """Search the web for information.

Search terms: search, web, google, internet, find, lookup, research
Use when: need current information, researching topics, fact-checking
Returns: Search results with titles, URLs, snippets""",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "num_results": {
                        "type": "integer",
                        "default": 5
                    }
                },
                "required": ["query"]
            },
            "tier": 2,
            "handler_module": "packages.research.articles",
            "handler_function": "web_search",
            "category": "research"
        }
    ]

    # Write builtin tools
    builtin_file = tools_dir / "builtin" / "research_tools.json"
    builtin_file.parent.mkdir(parents=True, exist_ok=True)
    with open(builtin_file, "w") as f:
        json.dump(builtin_tools, f, indent=2)

    # Create empty generated directory
    (tools_dir / "generated").mkdir(parents=True, exist_ok=True)

    print(f"Created initial tools in {tools_dir}")
    return {"core": len(core_tools), "builtin": len(builtin_tools)}
