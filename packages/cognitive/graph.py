"""
Neo4j Graph Database Connection and Operations.

This module provides the CognitiveGraph class for interacting with
the Neo4j database that stores the cognitive tree.

Supports both:
- Neo4j Aura (neo4j+s://) - cloud hosted
- Self-hosted Neo4j (bolt://) - local or AWS

Features:
- Core graph operations (CRUD for nodes and relationships)
- Vector search using Neo4j 5.11+ vector indexes
- Cycle management for autonomous agent work
- Graph initialization with User + Assistant nodes
"""

import os
import ssl
from datetime import datetime
from typing import Optional, List, Dict, Any, Type, TypeVar, Tuple
from contextlib import contextmanager
from neo4j import GraphDatabase, Driver, Session

# Try to import TrustAll for Aura, but don't fail if not available
try:
    from neo4j import TrustAll
except ImportError:
    TrustAll = None

try:
    import certifi
except ImportError:
    certifi = None

from neo4j.exceptions import ServiceUnavailable, AuthError

from .models import (
    Node, Relationship, NodeType, RelationType,
    CycleNode, CycleStatus, CycleType,
    TaskNode, GoalNode, InsightNode,
    ChunkNode, EntityNode, DocumentNode, ProjectNode
)


T = TypeVar('T', bound=Node)

# Singleton graph instance
_graph_instance: Optional["CognitiveGraph"] = None


def get_graph() -> "CognitiveGraph":
    """Get the singleton CognitiveGraph instance."""
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = CognitiveGraph()
    return _graph_instance


class CognitiveGraph:
    """
    Neo4j Graph Database interface for the cognitive tree.

    Uses environment variables for connection:
    - NEO4J_URI: Connection URI (neo4j+s://xxx.databases.neo4j.io)
    - NEO4J_USERNAME: Username (default: neo4j)
    - NEO4J_PASSWORD: Password
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        self.uri = uri or os.environ.get("NEO4J_URI")
        self.username = username or os.environ.get("NEO4J_USERNAME", "neo4j")
        self.password = password or os.environ.get("NEO4J_PASSWORD")

        if not self.uri or not self.password:
            raise ValueError(
                "Neo4j connection requires NEO4J_URI and NEO4J_PASSWORD environment variables. "
                "Create a Neo4j Aura free instance at https://console.neo4j.io/"
            )

        self._driver: Optional[Driver] = None

    @property
    def driver(self) -> Driver:
        """Lazy-load the Neo4j driver."""
        if self._driver is None:
            # Convert neo4j+s:// to neo4j+ssc:// for self-signed certs
            # Neo4j Aura cluster routing sometimes returns IPs with self-signed certs
            uri = self.uri
            if uri.startswith("neo4j+s://"):
                # Use +ssc to accept self-signed certificates
                uri = uri.replace("neo4j+s://", "neo4j+ssc://")
                print(f"[Neo4j] Converting to neo4j+ssc for self-signed cert support...")
            elif uri.startswith("bolt+s://"):
                uri = uri.replace("bolt+s://", "bolt+ssc://")
                print(f"[Neo4j] Converting to bolt+ssc for self-signed cert support...")

            print(f"[Neo4j] Connecting to {uri[:50]}...")

            # All connections now go through standard driver creation
            # +ssc handles self-signed certs, +s handles valid certs
            self._driver = GraphDatabase.driver(
                uri,
                auth=(self.username, self.password)
            )
        return self._driver

    def close(self):
        """Close the driver connection."""
        if self._driver:
            self._driver.close()
            self._driver = None

    @contextmanager
    def session(self) -> Session:
        """Context manager for Neo4j sessions."""
        session = self.driver.session()
        try:
            yield session
        finally:
            session.close()

    def verify_connectivity(self) -> bool:
        """Test the database connection."""
        try:
            with self.session() as session:
                result = session.run("RETURN 1 as n")
                return result.single()["n"] == 1
        except (ServiceUnavailable, AuthError) as e:
            print(f"Neo4j connection failed: {e}")
            return False

    # ==================== Node Operations ====================

    def create_node(self, node: Node) -> str:
        """
        Create a node in the graph.

        Returns the Neo4j element ID of the created node.
        """
        props = node.to_cypher_props()
        query = f"""
        CREATE (n:{node.type.value} $props)
        RETURN elementId(n) as id
        """
        with self.session() as session:
            result = session.run(query, props=props)
            record = result.single()
            node.id = record["id"]
            return node.id

    def get_node_by_id(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get a node by its element ID."""
        query = """
        MATCH (n) WHERE elementId(n) = $id
        RETURN n, labels(n) as labels
        """
        with self.session() as session:
            result = session.run(query, id=node_id)
            record = result.single()
            if record:
                node_data = dict(record["n"])
                node_data["id"] = node_id
                node_data["labels"] = record["labels"]
                return node_data
        return None

    def find_nodes(
        self,
        node_type: NodeType,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Find nodes of a given type with optional property filters.

        Example:
            graph.find_nodes(NodeType.ARTICLE, {"source": "Hacker News"})
        """
        where_clauses = []
        params = {"limit": limit}

        if filters:
            for i, (key, value) in enumerate(filters.items()):
                param_name = f"p{i}"
                where_clauses.append(f"n.{key} = ${param_name}")
                params[param_name] = value

        where_str = " AND ".join(where_clauses) if where_clauses else "true"

        query = f"""
        MATCH (n:{node_type.value})
        WHERE {where_str}
        RETURN n, elementId(n) as id
        ORDER BY n.created_at DESC
        LIMIT $limit
        """

        nodes = []
        with self.session() as session:
            result = session.run(query, **params)
            for record in result:
                node_data = dict(record["n"])
                node_data["id"] = record["id"]
                nodes.append(node_data)
        return nodes

    def find_node_by_name(
        self,
        node_type: NodeType,
        name: str
    ) -> Optional[Dict[str, Any]]:
        """Find a node by its name (exact match)."""
        query = f"""
        MATCH (n:{node_type.value} {{name: $name}})
        RETURN n, elementId(n) as id
        LIMIT 1
        """
        with self.session() as session:
            result = session.run(query, name=name)
            record = result.single()
            if record:
                node_data = dict(record["n"])
                node_data["id"] = record["id"]
                return node_data
        return None

    def search_nodes(
        self,
        node_type: NodeType,
        search_text: str,
        property_name: str = "name",
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search nodes using case-insensitive contains.

        Example:
            graph.search_nodes(NodeType.ARTICLE, "LLM", "name")
        """
        query = f"""
        MATCH (n:{node_type.value})
        WHERE toLower(n.{property_name}) CONTAINS toLower($search)
        RETURN n, elementId(n) as id
        ORDER BY n.created_at DESC
        LIMIT $limit
        """
        nodes = []
        with self.session() as session:
            result = session.run(query, search=search_text, limit=limit)
            for record in result:
                node_data = dict(record["n"])
                node_data["id"] = record["id"]
                nodes.append(node_data)
        return nodes

    def update_node(self, node_id: str, properties: Dict[str, Any]) -> bool:
        """Update properties on an existing node."""
        properties["updated_at"] = __import__("datetime").datetime.utcnow().isoformat()
        query = """
        MATCH (n) WHERE elementId(n) = $id
        SET n += $props
        RETURN n
        """
        with self.session() as session:
            result = session.run(query, id=node_id, props=properties)
            return result.single() is not None

    def delete_node(self, node_id: str) -> bool:
        """Delete a node and all its relationships."""
        query = """
        MATCH (n) WHERE elementId(n) = $id
        DETACH DELETE n
        """
        with self.session() as session:
            result = session.run(query, id=node_id)
            return result.consume().counters.nodes_deleted > 0

    # ==================== Relationship Operations ====================

    def create_relationship(
        self,
        from_node_id: str,
        to_node_id: str,
        rel_type: RelationType,
        properties: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Create a relationship between two nodes.

        Example:
            graph.create_relationship(user_id, article_id, RelationType.RESEARCHED)
        """
        props = properties or {}
        props["created_at"] = __import__("datetime").datetime.utcnow().isoformat()

        query = f"""
        MATCH (a) WHERE elementId(a) = $from_id
        MATCH (b) WHERE elementId(b) = $to_id
        CREATE (a)-[r:{rel_type.value} $props]->(b)
        RETURN r
        """
        with self.session() as session:
            result = session.run(query, from_id=from_node_id, to_id=to_node_id, props=props)
            return result.single() is not None

    def get_related_nodes(
        self,
        node_id: str,
        rel_type: Optional[RelationType] = None,
        direction: str = "outgoing",  # outgoing, incoming, both
        target_type: Optional[NodeType] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get nodes related to a given node.

        Example:
            # Get all articles the user has researched
            graph.get_related_nodes(user_id, RelationType.RESEARCHED, target_type=NodeType.ARTICLE)
        """
        rel_pattern = f":{rel_type.value}" if rel_type else ""
        target_pattern = f":{target_type.value}" if target_type else ""

        if direction == "outgoing":
            pattern = f"-[r{rel_pattern}]->(related{target_pattern})"
        elif direction == "incoming":
            pattern = f"<-[r{rel_pattern}]-(related{target_pattern})"
        else:  # both
            pattern = f"-[r{rel_pattern}]-(related{target_pattern})"

        query = f"""
        MATCH (n){pattern}
        WHERE elementId(n) = $node_id
        RETURN related, elementId(related) as id, type(r) as rel_type
        LIMIT $limit
        """
        nodes = []
        with self.session() as session:
            result = session.run(query, node_id=node_id, limit=limit)
            for record in result:
                node_data = dict(record["related"])
                node_data["id"] = record["id"]
                node_data["_rel_type"] = record["rel_type"]
                nodes.append(node_data)
        return nodes

    # ==================== User Operations ====================

    def get_or_create_user(
        self,
        first_name: str,
        last_name: Optional[str] = None,
        **properties
    ) -> Dict[str, Any]:
        """
        Get the primary user node, creating it if it doesn't exist.

        There should only be one User node in the graph.
        """
        query = """
        MERGE (u:User {first_name: $first_name})
        ON CREATE SET u += $props, u.created_at = datetime()
        ON MATCH SET u += $props, u.updated_at = datetime()
        RETURN u, elementId(u) as id
        """
        props = {
            "first_name": first_name,
            "last_name": last_name,
            "name": f"{first_name} {last_name}" if last_name else first_name,
            **properties
        }
        with self.session() as session:
            result = session.run(query, first_name=first_name, props=props)
            record = result.single()
            user_data = dict(record["u"])
            user_data["id"] = record["id"]
            return user_data

    def get_user(self) -> Optional[Dict[str, Any]]:
        """Get the primary user node."""
        query = """
        MATCH (u:User)
        RETURN u, elementId(u) as id
        LIMIT 1
        """
        with self.session() as session:
            result = session.run(query)
            record = result.single()
            if record:
                user_data = dict(record["u"])
                user_data["id"] = record["id"]
                return user_data
        return None

    # ==================== Topic/Knowledge Graph ====================

    def get_or_create_topic(self, name: str, **properties) -> Dict[str, Any]:
        """
        Get or create a topic node.

        Topics are used to categorize and relate articles, jobs, etc.
        """
        query = """
        MERGE (t:Topic {name: $name})
        ON CREATE SET t += $props, t.created_at = datetime()
        RETURN t, elementId(t) as id
        """
        with self.session() as session:
            result = session.run(query, name=name, props=properties)
            record = result.single()
            topic_data = dict(record["t"])
            topic_data["id"] = record["id"]
            return topic_data

    def link_to_topics(
        self,
        node_id: str,
        topics: List[str]
    ) -> int:
        """
        Link a node to multiple topics (creating topics if needed).

        Returns the number of relationships created.
        """
        query = """
        MATCH (n) WHERE elementId(n) = $node_id
        UNWIND $topics as topic_name
        MERGE (t:Topic {name: topic_name})
        MERGE (n)-[r:ABOUT_TOPIC]->(t)
        RETURN count(r) as count
        """
        with self.session() as session:
            result = session.run(query, node_id=node_id, topics=topics)
            return result.single()["count"]

    # ==================== Raw Query & Search ====================

    def raw_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a raw Cypher query.

        Use this for custom queries that don't fit the standard methods.
        The LLM can use this to design its own schema dynamically.

        Example:
            graph.raw_query("MATCH (n:Article) RETURN n LIMIT 10")
        """
        params = params or {}
        results = []
        with self.session() as session:
            result = session.run(query, **params)
            for record in result:
                # Convert record to dict
                row = {}
                for key in record.keys():
                    value = record[key]
                    # Handle Neo4j node objects
                    if hasattr(value, 'items'):
                        row[key] = dict(value)
                    else:
                        row[key] = value
                results.append(row)
        return results

    def search_all(self, search_text: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search across all node types for a text match.

        Searches name, title, summary, and content properties.
        """
        query = """
        MATCH (n)
        WHERE (n.name IS NOT NULL AND toLower(n.name) CONTAINS toLower($search))
           OR (n.title IS NOT NULL AND toLower(n.title) CONTAINS toLower($search))
           OR (n.summary IS NOT NULL AND toLower(n.summary) CONTAINS toLower($search))
           OR (n.content IS NOT NULL AND toLower(n.content) CONTAINS toLower($search))
        RETURN n, labels(n) as labels, elementId(n) as id
        ORDER BY n.created_at DESC
        LIMIT $limit
        """
        nodes = []
        with self.session() as session:
            result = session.run(query, search=search_text, limit=limit)
            for record in result:
                node_data = dict(record["n"])
                node_data["id"] = record["id"]
                node_data["labels"] = record["labels"]
                nodes.append(node_data)
        return nodes

    # ==================== Statistics ====================

    def get_stats(self) -> Dict[str, int]:
        """Get node and relationship counts by type."""
        query = """
        CALL {
            MATCH (n)
            RETURN labels(n)[0] as label, count(*) as count
        }
        RETURN collect({label: label, count: count}) as node_counts
        """
        with self.session() as session:
            result = session.run(query)
            record = result.single()
            return {item["label"]: item["count"] for item in record["node_counts"]}

    # ==================== Graph Initialization ====================

    def initialize_graph(
        self,
        user_first_name: str,
        user_last_name: Optional[str] = None,
        assistant_name: str = "Claude",
        assistant_model: str = "claude-sonnet-4-5-20250929",
        **user_properties
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Initialize the cognitive graph with User and Assistant nodes.

        The graph always starts with these two core nodes connected by ASSISTS.
        This should be called once when setting up a new user's graph.

        Returns:
            Tuple of (user_node, assistant_node)
        """
        # Create or get User node
        user = self.get_or_create_user(
            first_name=user_first_name,
            last_name=user_last_name,
            **user_properties
        )

        # Create or get Assistant node
        assistant = self.get_or_create_assistant(
            name=assistant_name,
            model=assistant_model
        )

        # Create ASSISTS relationship (Assistant -> User)
        # Use MERGE to avoid duplicates
        query = """
        MATCH (a:Assistant), (u:User)
        WHERE elementId(a) = $assistant_id AND elementId(u) = $user_id
        MERGE (a)-[r:ASSISTS]->(u)
        ON CREATE SET r.created_at = datetime()
        RETURN r
        """
        with self.session() as session:
            session.run(query, assistant_id=assistant["id"], user_id=user["id"])

        return user, assistant

    def get_or_create_assistant(
        self,
        name: str = "Claude",
        model: str = "claude-sonnet-4-5-20250929",
        **properties
    ) -> Dict[str, Any]:
        """
        Get or create the Assistant node.

        There should typically be one Assistant node per graph.
        """
        query = """
        MERGE (a:Assistant {name: $name})
        ON CREATE SET a += $props, a.created_at = datetime()
        ON MATCH SET a += $props, a.updated_at = datetime()
        RETURN a, elementId(a) as id
        """
        props = {
            "name": name,
            "model": model,
            "capabilities": properties.get("capabilities", [
                "research", "writing", "analysis",
                "coding", "conversation", "planning"
            ]),
            **properties
        }
        with self.session() as session:
            result = session.run(query, name=name, props=props)
            record = result.single()
            assistant_data = dict(record["a"])
            assistant_data["id"] = record["id"]
            return assistant_data

    def get_assistant(self) -> Optional[Dict[str, Any]]:
        """Get the Assistant node."""
        query = """
        MATCH (a:Assistant)
        RETURN a, elementId(a) as id
        LIMIT 1
        """
        with self.session() as session:
            result = session.run(query)
            record = result.single()
            if record:
                assistant_data = dict(record["a"])
                assistant_data["id"] = record["id"]
                return assistant_data
        return None

    # ==================== Cycle Operations ====================

    def create_cycle(
        self,
        name: str,
        objective: str,
        cycle_type: CycleType = CycleType.RESEARCH,
        priority: int = 5,
        goal_id: Optional[str] = None,
        project_id: Optional[str] = None,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new Cycle (self-assigned task toward a larger goal).

        Cycles are initiated by the Assistant and optionally linked to:
        - A Goal (what the cycle works toward)
        - A Project (broader context)
        """
        cycle = CycleNode.create(
            name=name,
            objective=objective,
            cycle_type=cycle_type,
            status=CycleStatus.PLANNING,
            priority=priority,
            context=context
        )

        # Create the cycle node
        props = cycle.to_cypher_props()
        query = """
        CREATE (c:Cycle $props)
        RETURN c, elementId(c) as id
        """
        with self.session() as session:
            result = session.run(query, props=props)
            record = result.single()
            cycle_data = dict(record["c"])
            cycle_data["id"] = record["id"]

        # Link Assistant -> Cycle (INITIATED)
        assistant = self.get_assistant()
        if assistant:
            self.create_relationship(
                assistant["id"],
                cycle_data["id"],
                RelationType.INITIATED
            )

        # Link Cycle -> Goal (WORKS_TOWARD)
        if goal_id:
            self.create_relationship(
                cycle_data["id"],
                goal_id,
                RelationType.WORKS_TOWARD
            )

        # Link Cycle -> Project (PART_OF)
        if project_id:
            self.create_relationship(
                cycle_data["id"],
                project_id,
                RelationType.PART_OF
            )

        return cycle_data

    def get_active_cycles(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get all active cycles ordered by priority."""
        query = """
        MATCH (c:Cycle)
        WHERE c.status IN ['planning', 'active']
        RETURN c, elementId(c) as id
        ORDER BY c.priority DESC, c.created_at DESC
        LIMIT $limit
        """
        cycles = []
        with self.session() as session:
            result = session.run(query, limit=limit)
            for record in result:
                cycle_data = dict(record["c"])
                cycle_data["id"] = record["id"]
                cycles.append(cycle_data)
        return cycles

    def update_cycle_status(
        self,
        cycle_id: str,
        status: CycleStatus,
        reason: Optional[str] = None
    ) -> bool:
        """Update a cycle's status."""
        props = {
            "status": status.value,
            "updated_at": datetime.utcnow().isoformat()
        }
        if reason:
            props["status_reason"] = reason
        if status == CycleStatus.COMPLETED:
            props["completed_at"] = datetime.utcnow().isoformat()

        return self.update_node(cycle_id, props)

    def add_task_to_cycle(
        self,
        cycle_id: str,
        description: str,
        priority: int = 5,
        estimated_minutes: Optional[int] = None
    ) -> Dict[str, Any]:
        """Add a task to a cycle."""
        task = TaskNode.create(
            description=description,
            priority=priority,
            estimated_minutes=estimated_minutes
        )

        props = task.to_cypher_props()
        query = """
        MATCH (c:Cycle) WHERE elementId(c) = $cycle_id
        CREATE (t:Task $props)
        CREATE (c)-[:CONTAINS]->(t)
        SET c.estimated_tasks = coalesce(c.estimated_tasks, 0) + 1
        RETURN t, elementId(t) as id
        """
        with self.session() as session:
            result = session.run(query, cycle_id=cycle_id, props=props)
            record = result.single()
            if record:
                task_data = dict(record["t"])
                task_data["id"] = record["id"]
                return task_data
        return {}

    def complete_task(self, task_id: str) -> bool:
        """Mark a task as completed and update parent cycle stats."""
        query = """
        MATCH (t:Task) WHERE elementId(t) = $task_id
        OPTIONAL MATCH (c:Cycle)-[:CONTAINS]->(t)
        SET t.status = 'completed',
            t.completed_at = datetime(),
            c.tasks_completed = coalesce(c.tasks_completed, 0) + 1
        RETURN t
        """
        with self.session() as session:
            result = session.run(query, task_id=task_id)
            return result.single() is not None

    def add_insight_to_cycle(
        self,
        cycle_id: str,
        insight: str,
        source_type: str = "research",
        confidence: float = 0.7
    ) -> Dict[str, Any]:
        """Add an insight discovered during a cycle."""
        insight_node = InsightNode.create(
            insight=insight,
            source_type=source_type,
            confidence=confidence
        )

        props = insight_node.to_cypher_props()
        query = """
        MATCH (c:Cycle) WHERE elementId(c) = $cycle_id
        CREATE (i:Insight $props)
        CREATE (i)-[:INFORMS]->(c)
        SET c.insights_count = coalesce(c.insights_count, 0) + 1
        RETURN i, elementId(i) as id
        """
        with self.session() as session:
            result = session.run(query, cycle_id=cycle_id, props=props)
            record = result.single()
            if record:
                insight_data = dict(record["i"])
                insight_data["id"] = record["id"]
                return insight_data
        return {}

    # ==================== Project Operations ====================

    def create_project(
        self,
        name: str,
        description: str,
        category: Optional["ProjectCategory"] = None,
        project_type: Optional[str] = None,
        is_life_area: bool = False
    ) -> Dict[str, Any]:
        """
        Create a new project.

        Args:
            name: Project name
            description: Project description
            category: ProjectCategory enum (WORK, FAMILY, HEALTH, etc.)
            project_type: More specific type within category
            is_life_area: True for permanent life areas (Family, Health)
        """
        from .models import ProjectCategory as PC
        project = ProjectNode.create(
            name=name,
            description=description,
            category=category or PC.GENERAL,
            project_type=project_type,
            is_life_area=is_life_area
        )

        props = project.to_cypher_props()
        query = """
        CREATE (p:Project $props)
        RETURN p, elementId(p) as id
        """
        with self.session() as session:
            result = session.run(query, props=props)
            record = result.single()
            project_data = dict(record["p"])
            project_data["id"] = record["id"]

        # Link User -> Project (OWNS)
        user = self.get_user()
        if user:
            self.create_relationship(
                user["id"],
                project_data["id"],
                RelationType.OWNS
            )

        return project_data

    def create_life_area(
        self,
        name: str,
        category: "ProjectCategory",
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a permanent life area project.

        Life areas are always-active projects representing ongoing
        areas of focus (Family, Health, Finance, etc.)

        Args:
            name: Life area name (e.g., "Family", "Health & Fitness")
            category: ProjectCategory enum
            description: Optional custom description
        """
        from .models import ProjectCategory as PC
        default_descriptions = {
            PC.FAMILY: "Family relationships and activities",
            PC.HEALTH: "Health, fitness, and wellness",
            PC.FINANCE: "Financial planning and goals",
            PC.SOCIAL: "Friendships and community",
            PC.HOBBY: "Hobbies and creative pursuits",
            PC.LEARNING: "Learning and personal development",
            PC.WORK: "Professional career and work",
            PC.HOME: "Home and living space",
        }
        return self.create_project(
            name=name,
            description=description or default_descriptions.get(category, f"{name} life area"),
            category=category,
            is_life_area=True
        )

    def add_person_to_project(
        self,
        person_id: str,
        project_id: str,
        relationship_type: str = "MEMBER_OF",
        role: Optional[str] = None
    ) -> Optional[str]:
        """
        Link a person to a project.

        Args:
            person_id: Person node ID
            project_id: Project node ID
            relationship_type: "MEMBER_OF" or "COLLABORATES_ON"
            role: Optional role description (e.g., "spouse", "contractor")

        Returns:
            Relationship ID or None if failed
        """
        rel_type = RelationType.MEMBER_OF if relationship_type == "MEMBER_OF" else RelationType.COLLABORATES_ON
        return self.create_relationship(
            person_id,
            project_id,
            rel_type,
            properties={"role": role} if role else None
        )

    def add_article_to_project(
        self,
        article_id: str,
        project_id: str,
        relevance: Optional[str] = None
    ) -> Optional[str]:
        """
        Link an article/resource to a project.

        Args:
            article_id: Article node ID
            project_id: Project node ID
            relevance: Optional description of how it's relevant

        Returns:
            Relationship ID or None if failed
        """
        return self.create_relationship(
            project_id,
            article_id,
            RelationType.USES_SOURCE,
            properties={"relevance": relevance} if relevance else None
        )

    def get_project_members(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all people linked to a project."""
        query = """
        MATCH (p:Person)-[r:MEMBER_OF|COLLABORATES_ON]->(proj:Project)
        WHERE elementId(proj) = $project_id
        RETURN p, elementId(p) as id, type(r) as relationship, r.role as role
        """
        members = []
        with self.session() as session:
            result = session.run(query, project_id=project_id)
            for record in result:
                member_data = dict(record["p"])
                member_data["id"] = record["id"]
                member_data["relationship"] = record["relationship"]
                member_data["role"] = record["role"]
                members.append(member_data)
        return members

    def get_project_articles(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all articles/resources linked to a project."""
        query = """
        MATCH (proj:Project)-[r:USES_SOURCE]->(a:Article)
        WHERE elementId(proj) = $project_id
        RETURN a, elementId(a) as id, r.relevance as relevance
        """
        articles = []
        with self.session() as session:
            result = session.run(query, project_id=project_id)
            for record in result:
                article_data = dict(record["a"])
                article_data["id"] = record["id"]
                article_data["relevance"] = record["relevance"]
                articles.append(article_data)
        return articles

    def get_user_projects(self, limit: int = 20, category: Optional[str] = None, life_areas_only: bool = False) -> List[Dict[str, Any]]:
        """
        Get all projects owned by the user.

        Args:
            limit: Max projects to return
            category: Filter by category (e.g., "family", "work")
            life_areas_only: If True, only return life area projects
        """
        where_clauses = []
        params = {"limit": limit}

        if category:
            where_clauses.append("p.category = $category")
            params["category"] = category

        if life_areas_only:
            where_clauses.append("p.is_life_area = true")

        where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        query = f"""
        MATCH (u:User)-[:OWNS]->(p:Project)
        {where_str}
        RETURN p, elementId(p) as id
        ORDER BY p.created_at DESC
        LIMIT $limit
        """
        projects = []
        with self.session() as session:
            result = session.run(query, **params)
            for record in result:
                project_data = dict(record["p"])
                project_data["id"] = record["id"]
                projects.append(project_data)
        return projects

    def get_life_areas(self) -> List[Dict[str, Any]]:
        """Get all life area projects."""
        return self.get_user_projects(life_areas_only=True)

    # ==================== Vector Operations ====================

    def create_vector_indexes(self) -> Dict[str, bool]:
        """
        Create vector indexes for semantic search.

        Requires Neo4j 5.11+ with vector index support.
        Should be called once during graph setup.
        """
        results = {}

        # Chunk embedding index (1536 dims for OpenAI, adjust as needed)
        chunk_index = """
        CREATE VECTOR INDEX chunk_embedding IF NOT EXISTS
        FOR (c:Chunk)
        ON c.embedding
        OPTIONS {
            indexConfig: {
                `vector.dimensions`: 1536,
                `vector.similarity_function`: 'cosine'
            }
        }
        """

        # Entity embedding index
        entity_index = """
        CREATE VECTOR INDEX entity_embedding IF NOT EXISTS
        FOR (e:Entity)
        ON e.embedding
        OPTIONS {
            indexConfig: {
                `vector.dimensions`: 1536,
                `vector.similarity_function`: 'cosine'
            }
        }
        """

        # Full-text indexes for hybrid search
        chunk_text_index = """
        CREATE FULLTEXT INDEX chunk_text IF NOT EXISTS
        FOR (c:Chunk) ON EACH [c.text]
        """

        entity_text_index = """
        CREATE FULLTEXT INDEX entity_text IF NOT EXISTS
        FOR (e:Entity) ON EACH [e.name, e.description]
        """

        with self.session() as session:
            for name, query in [
                ("chunk_embedding", chunk_index),
                ("entity_embedding", entity_index),
                ("chunk_text", chunk_text_index),
                ("entity_text", entity_text_index)
            ]:
                try:
                    session.run(query)
                    results[name] = True
                except Exception as e:
                    print(f"Failed to create index {name}: {e}")
                    results[name] = False

        return results

    def vector_search(
        self,
        embedding: List[float],
        node_type: str = "Chunk",
        limit: int = 10,
        min_score: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search for similar nodes using vector similarity.

        Args:
            embedding: Query embedding vector
            node_type: Type of node to search (Chunk, Entity)
            limit: Maximum results to return
            min_score: Minimum similarity score (0-1)

        Returns:
            List of matching nodes with similarity scores
        """
        index_name = f"{node_type.lower()}_embedding"

        query = f"""
        CALL db.index.vector.queryNodes($index_name, $limit, $embedding)
        YIELD node, score
        WHERE score >= $min_score
        RETURN node, score, elementId(node) as id
        ORDER BY score DESC
        """

        results = []
        with self.session() as session:
            result = session.run(
                query,
                index_name=index_name,
                limit=limit,
                embedding=embedding,
                min_score=min_score
            )
            for record in result:
                node_data = dict(record["node"])
                node_data["id"] = record["id"]
                node_data["_score"] = record["score"]
                results.append(node_data)

        return results

    def hybrid_search(
        self,
        query_text: str,
        embedding: List[float],
        node_type: str = "Chunk",
        limit: int = 10,
        text_weight: float = 0.3,
        vector_weight: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining full-text and vector similarity.

        Args:
            query_text: Text query for full-text search
            embedding: Query embedding for vector search
            node_type: Type of node to search
            limit: Maximum results
            text_weight: Weight for text search score
            vector_weight: Weight for vector similarity score

        Returns:
            List of matching nodes with combined scores
        """
        # First, get vector results
        vector_results = self.vector_search(
            embedding=embedding,
            node_type=node_type,
            limit=limit * 2,  # Get more candidates
            min_score=0.5
        )

        # Then, get full-text results
        text_index = f"{node_type.lower()}_text"
        text_query = f"""
        CALL db.index.fulltext.queryNodes($index_name, $query)
        YIELD node, score
        RETURN node, score, elementId(node) as id
        LIMIT $limit
        """

        text_results = {}
        with self.session() as session:
            result = session.run(
                text_query,
                index_name=text_index,
                query=query_text,
                limit=limit * 2
            )
            for record in result:
                node_id = record["id"]
                text_results[node_id] = {
                    "node": dict(record["node"]),
                    "text_score": record["score"]
                }

        # Combine scores
        combined = {}
        for vr in vector_results:
            node_id = vr["id"]
            vector_score = vr["_score"]
            text_score = text_results.get(node_id, {}).get("text_score", 0)

            combined_score = (vector_weight * vector_score) + (text_weight * text_score)
            combined[node_id] = {
                **vr,
                "_text_score": text_score,
                "_vector_score": vector_score,
                "_combined_score": combined_score
            }

        # Add text-only results
        for node_id, data in text_results.items():
            if node_id not in combined:
                combined[node_id] = {
                    **data["node"],
                    "id": node_id,
                    "_text_score": data["text_score"],
                    "_vector_score": 0,
                    "_combined_score": text_weight * data["text_score"]
                }

        # Sort by combined score and return top results
        sorted_results = sorted(
            combined.values(),
            key=lambda x: x["_combined_score"],
            reverse=True
        )
        return sorted_results[:limit]

    def store_chunk_with_embedding(
        self,
        text: str,
        embedding: List[float],
        source_id: Optional[str] = None,
        chunk_index: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Store a text chunk with its embedding.

        Args:
            text: The text content
            embedding: Vector embedding (e.g., from OpenAI)
            source_id: Optional ID of parent document
            chunk_index: Position in source document
            metadata: Additional properties

        Returns:
            Created chunk node
        """
        props = {
            "text": text,
            "embedding": embedding,
            "source_id": source_id,
            "chunk_index": chunk_index,
            "char_count": len(text),
            "created_at": datetime.utcnow().isoformat(),
            **(metadata or {})
        }

        query = """
        CREATE (c:Chunk $props)
        RETURN c, elementId(c) as id
        """

        with self.session() as session:
            result = session.run(query, props=props)
            record = result.single()
            chunk_data = dict(record["c"])
            chunk_data["id"] = record["id"]

        # Link to source document if provided
        if source_id:
            self.create_relationship(
                source_id,
                chunk_data["id"],
                RelationType.HAS_CHUNK
            )

        return chunk_data

    def store_entity_with_embedding(
        self,
        name: str,
        entity_type: str,
        embedding: List[float],
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Store an entity with its embedding.

        Args:
            name: Entity name
            entity_type: Type (person, org, concept, etc.)
            embedding: Vector embedding
            description: Optional description
            metadata: Additional properties

        Returns:
            Created or updated entity node
        """
        props = {
            "name": name,
            "entity_type": entity_type,
            "embedding": embedding,
            "description": description,
            "updated_at": datetime.utcnow().isoformat(),
            **(metadata or {})
        }

        # Use MERGE to avoid duplicate entities
        query = """
        MERGE (e:Entity {name: $name, entity_type: $entity_type})
        ON CREATE SET e = $props, e.created_at = datetime()
        ON MATCH SET e += $props
        RETURN e, elementId(e) as id
        """

        with self.session() as session:
            result = session.run(
                query,
                name=name,
                entity_type=entity_type,
                props=props
            )
            record = result.single()
            entity_data = dict(record["e"])
            entity_data["id"] = record["id"]

        return entity_data

    # ==================== Goal Operations ====================

    def create_goal(
        self,
        name: str,
        description: str,
        timeframe: Optional[str] = None,
        success_criteria: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create a new goal."""
        goal = GoalNode.create(
            name=name,
            description=description,
            timeframe=timeframe,
            success_criteria=success_criteria
        )

        props = goal.to_cypher_props()
        query = """
        CREATE (g:Goal $props)
        RETURN g, elementId(g) as id
        """
        with self.session() as session:
            result = session.run(query, props=props)
            record = result.single()
            goal_data = dict(record["g"])
            goal_data["id"] = record["id"]

        # Link to User
        user = self.get_user()
        if user:
            self.create_relationship(
                user["id"],
                goal_data["id"],
                RelationType.INTERESTED_IN
            )

        return goal_data

    def get_user_goals(self, timeframe: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all goals for the user."""
        if timeframe:
            query = """
            MATCH (u:User)-[:INTERESTED_IN]->(g:Goal)
            WHERE g.timeframe = $timeframe
            RETURN g, elementId(g) as id
            ORDER BY g.created_at DESC
            """
            params = {"timeframe": timeframe}
        else:
            query = """
            MATCH (u:User)-[:INTERESTED_IN]->(g:Goal)
            RETURN g, elementId(g) as id
            ORDER BY g.created_at DESC
            """
            params = {}

        goals = []
        with self.session() as session:
            result = session.run(query, **params)
            for record in result:
                goal_data = dict(record["g"])
                goal_data["id"] = record["id"]
                goals.append(goal_data)
        return goals
