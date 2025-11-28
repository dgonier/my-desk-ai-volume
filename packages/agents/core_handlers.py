"""
Core Tool Handlers for the Persona Agent.

These handlers implement the core tools that are always available:
- get_cognitive_context: Retrieve context from Neo4j graph
- update_cognitive_tree: Update the graph with new information
- delegate_to_builder: Delegate tasks to Claude Code
- refresh_tools: Reload the tool registry
- list_available_tools: List all available tools
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

# Lazy imports to avoid circular dependencies
_graph = None
_registry = None


def _get_graph():
    global _graph
    if _graph is None:
        from ..cognitive.graph import get_graph
        _graph = get_graph()
    return _graph


def _get_registry():
    global _registry
    if _registry is None:
        from .tool_registry import get_registry
        _registry = get_registry()
    return _registry


def get_cognitive_context(
    context_type: str = "full",
    project_name: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Retrieve context from the cognitive tree.

    Args:
        context_type: Type of context - "full", "user", "projects", "people", "recent"
        project_name: Optional specific project to get context for
        limit: Maximum items to return

    Returns:
        Dictionary with requested context
    """
    graph = _get_graph()
    result = {}

    try:
        if context_type in ["full", "user"]:
            user = graph.get_user()
            if user:
                result["user"] = {
                    "id": user.get("id"),
                    "name": user.get("name"),
                    "email": user.get("email"),
                    "first_name": user.get("first_name"),
                    "last_name": user.get("last_name")
                }

        if context_type in ["full", "projects"]:
            if project_name:
                # Search for specific project
                projects = graph.raw_query(
                    """MATCH (p:Project)
                       WHERE toLower(p.name) CONTAINS toLower($name)
                       RETURN p, elementId(p) as id
                       LIMIT $limit""",
                    {"name": project_name, "limit": limit}
                )
                result["projects"] = projects
            else:
                projects = graph.get_user_projects(limit=limit)
                result["projects"] = projects

        if context_type in ["full", "people"]:
            from ..cognitive.models import NodeType
            people = graph.find_nodes(NodeType.PERSON, limit=limit)
            result["people"] = people

        if context_type in ["full", "recent"]:
            recent = graph.raw_query(
                """MATCH (n)
                   WHERE n.created_at IS NOT NULL
                   AND labels(n)[0] IN ['Insight', 'Task', 'Cycle', 'Memory']
                   RETURN n, labels(n) as labels, elementId(n) as id
                   ORDER BY n.created_at DESC
                   LIMIT $limit""",
                {"limit": limit}
            )
            result["recent_activity"] = recent

        # Get persona info
        if context_type == "full":
            persona = graph.raw_query(
                """MATCH (p:Persona)
                   OPTIONAL MATCH (p)-[:HAS_TRAIT]->(t:Trait)
                   RETURN p, elementId(p) as id, collect(t.name) as traits
                   LIMIT 1""",
                {}
            )
            if persona:
                result["persona"] = persona[0] if persona else None

    except Exception as e:
        result["error"] = str(e)

    return result


def update_cognitive_tree(
    operation: str,
    node_type: str,
    data: Dict[str, Any],
    link_to: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update the cognitive tree with new information.

    Args:
        operation: "create", "update", or "link"
        node_type: Type of node - "Project", "Person", "Task", "Insight", "Goal"
        data: Node data (name, description, etc.)
        link_to: Node ID to link to (for link operation)

    Returns:
        Result of the operation
    """
    graph = _get_graph()
    now = datetime.utcnow().isoformat()

    try:
        if operation == "create":
            if node_type == "Project":
                from ..cognitive.models import ProjectCategory
                category = data.get("category", "general")
                if isinstance(category, str):
                    try:
                        category = ProjectCategory(category)
                    except ValueError:
                        category = ProjectCategory.GENERAL

                project = graph.create_project(
                    name=data.get("name", "Unnamed Project"),
                    description=data.get("description", ""),
                    category=category
                )
                return {
                    "success": True,
                    "operation": "create",
                    "node_type": "Project",
                    "id": project.get("id"),
                    "name": project.get("name")
                }

            elif node_type == "Person":
                query = """
                CREATE (p:Person {
                    name: $name,
                    email: $email,
                    phone: $phone,
                    relationship: $relationship,
                    notes: $notes,
                    created_at: $now
                })
                RETURN p, elementId(p) as id
                """
                with graph.session() as session:
                    result = session.run(
                        query,
                        name=data.get("name"),
                        email=data.get("email"),
                        phone=data.get("phone"),
                        relationship=data.get("relationship"),
                        notes=data.get("notes") or data.get("context"),
                        now=now
                    )
                    record = result.single()
                    if record:
                        return {
                            "success": True,
                            "operation": "create",
                            "node_type": "Person",
                            "id": record["id"],
                            "name": data.get("name")
                        }

            elif node_type == "Task":
                cycle_id = data.get("cycle_id")
                if cycle_id:
                    task = graph.add_task_to_cycle(
                        cycle_id=cycle_id,
                        description=data.get("description", ""),
                        priority=data.get("priority", 5)
                    )
                    return {
                        "success": True,
                        "operation": "create",
                        "node_type": "Task",
                        "id": task.get("id")
                    }
                else:
                    # Create standalone task
                    query = """
                    CREATE (t:Task {
                        name: $name,
                        description: $description,
                        status: $status,
                        priority: $priority,
                        created_at: $now
                    })
                    RETURN t, elementId(t) as id
                    """
                    with graph.session() as session:
                        result = session.run(
                            query,
                            name=data.get("description", "")[:100],
                            description=data.get("description", ""),
                            status=data.get("status", "pending"),
                            priority=data.get("priority", 5),
                            now=now
                        )
                        record = result.single()
                        if record:
                            return {
                                "success": True,
                                "operation": "create",
                                "node_type": "Task",
                                "id": record["id"]
                            }

            elif node_type == "Insight":
                from ..cognitive.models import InsightNode
                insight = InsightNode.create(
                    insight=data.get("insight", data.get("content", "")),
                    source_type=data.get("source_type", "conversation"),
                    confidence=data.get("confidence", 0.7)
                )
                insight_id = graph.create_node(insight)
                return {
                    "success": True,
                    "operation": "create",
                    "node_type": "Insight",
                    "id": insight_id
                }

            elif node_type == "Goal":
                goal = graph.create_goal(
                    name=data.get("name", ""),
                    description=data.get("description", ""),
                    timeframe=data.get("timeframe")
                )
                return {
                    "success": True,
                    "operation": "create",
                    "node_type": "Goal",
                    "id": goal.get("id"),
                    "name": goal.get("name")
                }

        elif operation == "update":
            node_id = data.get("id")
            if not node_id:
                return {"success": False, "error": "Node ID required for update"}

            properties = {k: v for k, v in data.items() if k != "id"}
            success = graph.update_node(node_id, properties)
            return {
                "success": success,
                "operation": "update",
                "id": node_id
            }

        elif operation == "link":
            from_id = data.get("from_id") or data.get("id")
            to_id = link_to or data.get("to_id")

            if not from_id or not to_id:
                return {"success": False, "error": "Both from_id and to_id required"}

            from ..cognitive.models import RelationType
            rel_type_str = data.get("relationship", "RELATED_TO")

            # Try to match relationship type
            try:
                rel_type = RelationType(rel_type_str)
            except ValueError:
                rel_type = RelationType.RELATED_TO

            success = graph.create_relationship(from_id, to_id, rel_type)
            return {
                "success": success,
                "operation": "link",
                "from": from_id,
                "to": to_id,
                "relationship": rel_type.value
            }

        return {"success": False, "error": f"Unknown operation: {operation}"}

    except Exception as e:
        return {"success": False, "error": str(e)}


def delegate_to_builder(
    task: str,
    task_type: str,
    context: Optional[str] = None,
    files: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Delegate a task to Claude Code (Builder Agent).

    Args:
        task: Detailed description of what to do
        task_type: Type of task - "file_operation", "create_tool", "run_code", "research"
        context: Additional context for the task
        files: Relevant file paths

    Returns:
        Delegation result with ID and status
    """
    delegation_path = "/home/claude/delegations"
    os.makedirs(delegation_path, exist_ok=True)

    delegation_id = f"del_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
    delegation_file = os.path.join(delegation_path, f"{delegation_id}.json")

    delegation_data = {
        "id": delegation_id,
        "task": task,
        "task_type": task_type,
        "context": context or "",
        "files": files or [],
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        "created_by": "PersonaAgent"
    }

    try:
        with open(delegation_file, "w") as f:
            json.dump(delegation_data, f, indent=2)

        return {
            "success": True,
            "delegation_id": delegation_id,
            "status": "pending",
            "message": f"Task delegated to Builder Agent. The task will be processed asynchronously.",
            "file": delegation_file
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def refresh_tools() -> Dict[str, Any]:
    """
    Refresh the tool registry to load new tools.

    Returns:
        Summary of changes (added, updated, removed tools)
    """
    registry = _get_registry()
    changes = registry.refresh_tools()

    return {
        "success": True,
        "changes": changes,
        "total_tools": len(registry.list_tools()),
        "message": f"Registry refreshed. Added: {len(changes.get('added', []))}, Updated: {len(changes.get('updated', []))}, Removed: {len(changes.get('removed', []))}"
    }


def list_available_tools(
    category: Optional[str] = None,
    include_disabled: bool = False
) -> List[Dict[str, Any]]:
    """
    List all available tools.

    Args:
        category: Optional category filter
        include_disabled: Include disabled tools

    Returns:
        List of tools with name, description, category
    """
    registry = _get_registry()
    tools = registry.list_tools(
        category=category,
        enabled_only=not include_disabled
    )

    return [
        {
            "name": tool.name,
            "description": tool.description[:300] + "..." if len(tool.description) > 300 else tool.description,
            "category": tool.category,
            "tier": tool.tier,
            "enabled": tool.enabled
        }
        for tool in tools
    ]


# Additional utility handlers

def search_graph(
    query: str,
    node_types: Optional[List[str]] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Search the cognitive graph for matching nodes.

    Args:
        query: Search text
        node_types: Optional list of node types to search
        limit: Maximum results

    Returns:
        List of matching nodes
    """
    graph = _get_graph()

    if node_types:
        type_filter = "AND labels(n)[0] IN $types"
        params = {"search": query, "types": node_types, "limit": limit}
    else:
        type_filter = ""
        params = {"search": query, "limit": limit}

    cypher = f"""
    MATCH (n)
    WHERE (n.name IS NOT NULL AND toLower(n.name) CONTAINS toLower($search))
       OR (n.description IS NOT NULL AND toLower(n.description) CONTAINS toLower($search))
       OR (n.content IS NOT NULL AND toLower(n.content) CONTAINS toLower($search))
    {type_filter}
    RETURN n, labels(n) as labels, elementId(n) as id
    ORDER BY n.created_at DESC
    LIMIT $limit
    """

    return graph.raw_query(cypher, params)


def get_persona_info() -> Dict[str, Any]:
    """
    Get current persona information.

    Returns:
        Persona details including name, traits, memories
    """
    graph = _get_graph()

    result = graph.raw_query(
        """MATCH (p:Persona)
           OPTIONAL MATCH (p)-[:HAS_TRAIT]->(t:Trait)
           OPTIONAL MATCH (p)-[:HAS_MEMORY]->(m:Memory)
           OPTIONAL MATCH (p)-[:LEARNED_PREFERENCE]->(pref:Preference)
           RETURN p, elementId(p) as id,
                  collect(DISTINCT {name: t.name, description: t.description, type: t.trait_type}) as traits,
                  collect(DISTINCT {title: m.name, content: m.content, type: m.memory_type}) as memories,
                  collect(DISTINCT {name: pref.name, value: pref.value, category: pref.category}) as preferences
           LIMIT 1""",
        {}
    )

    if result:
        persona = result[0]
        return {
            "name": persona.get("p", {}).get("name"),
            "tagline": persona.get("p", {}).get("tagline"),
            "personality_summary": persona.get("p", {}).get("personality_summary"),
            "voice_description": persona.get("p", {}).get("voice_description"),
            "core_values": persona.get("p", {}).get("core_values", []),
            "traits": persona.get("traits", []),
            "memories": persona.get("memories", []),
            "preferences": persona.get("preferences", []),
            "conversation_count": persona.get("p", {}).get("conversation_count", 0)
        }

    return {"error": "No persona found. Run initialization first."}
