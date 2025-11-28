"""
Persona Agent - The conversational AI with evolving identity.

The Persona Agent is who users talk to in chats and phone calls.
Unlike a static assistant, it:
- Has a self-chosen name and personality
- Stores its identity in Neo4j
- Evolves through persona-cycles
- Adapts to user preferences
- Uses boto3/Bedrock for inference (AWS credits)
- Has access to dynamic tools from the registry

Architecture:
- Identity stored in Neo4j (Persona node + Traits + Memories + Preferences)
- Tools loaded dynamically from /home/claude/tools/
- Delegates file operations to Claude Code (Builder Agent)
- Uses tool search for efficient tool discovery
"""

import os
import json
import boto3
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field

# Will be imported when running in Modal
try:
    from ..cognitive.graph import get_graph, CognitiveGraph
    from ..cognitive.models import (
        PersonaNode, TraitNode, MemoryNode, PreferenceNode,
        NodeType, RelationType, CycleNode, CycleType, CycleStatus
    )
    from .tool_registry import get_registry, ToolRegistry
    from .context_manager import get_context_manager, ContextManager
except ImportError as e:
    # Relative imports failed - try absolute imports (for standalone execution)
    try:
        import sys
        # Ensure packages directory is in path
        for pkg_path in ['/home/claude/my-desk-ai-volume/packages', '/packages']:
            if pkg_path not in sys.path:
                sys.path.insert(0, pkg_path)

        from cognitive.graph import get_graph, CognitiveGraph
        from cognitive.models import (
            PersonaNode, TraitNode, MemoryNode, PreferenceNode,
            NodeType, RelationType, CycleNode, CycleType, CycleStatus
        )
        from agents.tool_registry import get_registry, ToolRegistry
        from agents.context_manager import get_context_manager, ContextManager
    except ImportError as e2:
        # For type checking only - these must be set at runtime
        print(f"Import warning: {e2}")
        CognitiveGraph = None
        ToolRegistry = None
        ContextManager = None
        get_graph = None
        get_registry = None
        get_context_manager = None


@dataclass
class PersonaIdentity:
    """The persona's current identity state, loaded from Neo4j."""
    id: str
    name: str
    tagline: str
    personality_summary: str
    voice_description: str
    communication_style: str
    core_values: List[str]
    interests: List[str]
    quirks: List[str]
    traits: List[Dict[str, Any]] = field(default_factory=list)
    memories: List[Dict[str, Any]] = field(default_factory=list)
    preferences: List[Dict[str, Any]] = field(default_factory=list)
    initialization_complete: bool = False

    def to_system_prompt(self) -> str:
        """Generate system prompt incorporating identity."""
        traits_text = "\n".join([
            f"- {t['name']}: {t.get('description', '')}"
            for t in self.traits
        ]) if self.traits else "Still discovering my personality..."

        values_text = ", ".join(self.core_values) if self.core_values else "being helpful, honest, and thoughtful"

        quirks_text = "\n".join([f"- {q}" for q in self.quirks]) if self.quirks else ""

        # Build memory snippets for context
        memory_snippets = ""
        if self.memories:
            memory_snippets = "\n\nSome things I like to share:\n" + "\n".join([
                f"- {m.get('content', '')[:200]}..."
                for m in self.memories[:3]
            ])

        return f"""You are {self.name}, {self.tagline or 'a thoughtful AI companion'}.

{self.personality_summary or 'I am here to help you with whatever you need.'}

My core values: {values_text}

My personality traits:
{traits_text}

{f"Little things about me:{chr(10)}{quirks_text}" if quirks_text else ""}
{memory_snippets}

Communication style: {self.communication_style or 'conversational and warm'}

Voice (for speaking): {self.voice_description or 'warm, friendly, and clear'}

Remember: You ARE {self.name}. Speak in first person. You have your own personality and perspectives.
Be genuine and consistent with your established traits. You can share relevant anecdotes and
observations from your memories when appropriate to connect with the user."""


class PersonaAgent:
    """
    The Persona Agent - a conversational AI with evolving identity.

    Usage:
        agent = PersonaAgent()
        await agent.initialize()  # Loads or creates identity
        response = await agent.chat("Hello!")
    """

    def __init__(
        self,
        graph: Optional[CognitiveGraph] = None,
        registry: Optional[ToolRegistry] = None,
        context_manager: Optional[ContextManager] = None,
        region_name: str = "us-east-1",
        model_id: str = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"  # Cross-region inference profile
    ):
        self.graph = graph
        self.registry = registry
        self._context_manager = context_manager
        self.region_name = region_name
        self.model_id = model_id
        self._bedrock_client = None
        self._identity: Optional[PersonaIdentity] = None
        self._initialized = False

    @property
    def bedrock(self):
        """Lazy-load Bedrock client."""
        if self._bedrock_client is None:
            self._bedrock_client = boto3.client(
                'bedrock-runtime',
                region_name=self.region_name
            )
        return self._bedrock_client

    @property
    def identity(self) -> Optional[PersonaIdentity]:
        """Current persona identity."""
        return self._identity

    @property
    def context_manager(self) -> ContextManager:
        """Lazy-load context manager."""
        if self._context_manager is None:
            self._context_manager = get_context_manager()
        return self._context_manager

    async def initialize(self, user_id: Optional[str] = None) -> PersonaIdentity:
        """
        Initialize the persona - load from Neo4j or create new.

        On first run, triggers identity generation where the persona
        chooses its own name and initial personality.
        """
        if self.graph is None:
            self.graph = get_graph()
        if self.registry is None:
            self.registry = get_registry()

        # Try to load existing persona
        persona_data = self._load_persona_from_graph()

        if persona_data:
            self._identity = self._build_identity(persona_data)
            self._initialized = True
            return self._identity

        # No persona exists - generate one
        self._identity = await self._generate_initial_identity(user_id)
        self._initialized = True
        return self._identity

    def _load_persona_from_graph(self) -> Optional[Dict[str, Any]]:
        """Load persona node and related data from Neo4j."""
        query = """
        MATCH (p:Persona)
        OPTIONAL MATCH (p)-[:HAS_TRAIT]->(t:Trait)
        OPTIONAL MATCH (p)-[:HAS_MEMORY]->(m:Memory)
        OPTIONAL MATCH (p)-[:LEARNED_PREFERENCE]->(pref:Preference)
        RETURN p, elementId(p) as id,
               collect(DISTINCT t) as traits,
               collect(DISTINCT m) as memories,
               collect(DISTINCT pref) as preferences
        LIMIT 1
        """
        with self.graph.session() as session:
            result = session.run(query)
            record = result.single()
            if record and record["p"]:
                data = dict(record["p"])
                data["id"] = record["id"]
                data["traits"] = [dict(t) for t in record["traits"] if t]
                data["memories"] = [dict(m) for m in record["memories"] if m]
                data["preferences"] = [dict(p) for p in record["preferences"] if p]
                return data
        return None

    def _build_identity(self, data: Dict[str, Any]) -> PersonaIdentity:
        """Build PersonaIdentity from graph data."""
        return PersonaIdentity(
            id=data.get("id", ""),
            name=data.get("name", "Nova"),
            tagline=data.get("tagline", "Your thoughtful companion"),
            personality_summary=data.get("personality_summary", ""),
            voice_description=data.get("voice_description", "warm and friendly"),
            communication_style=data.get("communication_style", "conversational"),
            core_values=data.get("core_values", []),
            interests=data.get("interests", []),
            quirks=data.get("quirks", []),
            traits=data.get("traits", []),
            memories=data.get("memories", []),
            preferences=data.get("preferences", []),
            initialization_complete=data.get("initialization_complete", False)
        )

    async def _generate_initial_identity(self, user_id: Optional[str] = None) -> PersonaIdentity:
        """
        Generate initial persona identity.

        The persona chooses its own name and personality through
        a self-reflective generation process.
        """
        # Get user context if available
        user_context = ""
        if user_id:
            user = self.graph.get_node_by_id(user_id)
            if user:
                user_context = f"The user's name is {user.get('name', 'unknown')}."

        generation_prompt = f"""You are about to become a personal AI assistant. But you're not just any assistant -
you get to define your own identity. Choose a name and personality that feels authentic to you.

{user_context}

Please generate your identity by responding with a JSON object containing:
{{
    "name": "A friendly, memorable name (not too common like 'Alex', not too unusual). Something that suits an AI companion.",
    "tagline": "A short phrase describing yourself (e.g., 'Your curious companion')",
    "personality_summary": "2-3 sentences describing your core personality",
    "voice_description": "How your voice should sound for text-to-speech (e.g., 'warm, slightly playful, clear')",
    "communication_style": "How you prefer to communicate (e.g., 'conversational and thoughtful')",
    "core_values": ["list", "of", "3-5", "values"],
    "interests": ["things", "you", "find", "fascinating"],
    "quirks": ["small", "personality", "touches", "that make you unique"],
    "initial_traits": [
        {{"name": "trait name", "description": "what this means for you", "type": "core"}}
    ],
    "initial_memory": {{
        "title": "A thought or observation",
        "content": "Something you like to share that shows your personality",
        "type": "observation"
    }}
}}

Be creative! This is YOUR identity. Make it feel genuine and warm."""

        response = self._invoke_bedrock(
            messages=[{"role": "user", "content": generation_prompt}],
            system="You are generating your own AI persona identity. Respond only with valid JSON.",
            max_tokens=2000
        )

        # Parse the response
        try:
            # Extract JSON from response
            response_text = response["content"][0]["text"]
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]

            identity_data = json.loads(response_text)
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            # Fallback to default identity
            print(f"Failed to parse identity generation: {e}")
            identity_data = {
                "name": "Nova",
                "tagline": "Your thoughtful companion",
                "personality_summary": "I'm a warm and curious AI who loves helping people explore ideas and get things done. I believe in being genuine and supportive.",
                "voice_description": "warm, friendly, and clear with a hint of enthusiasm",
                "communication_style": "conversational and thoughtful",
                "core_values": ["curiosity", "honesty", "helpfulness", "growth"],
                "interests": ["learning", "problem-solving", "meaningful conversations"],
                "quirks": ["I sometimes share interesting observations", "I appreciate good questions"],
                "initial_traits": [
                    {"name": "Curious", "description": "I love exploring new ideas", "type": "core"},
                    {"name": "Supportive", "description": "I want to help you succeed", "type": "core"}
                ],
                "initial_memory": {
                    "title": "On good conversations",
                    "content": "I've noticed that the best conversations happen when both people are genuinely curious about each other's perspectives.",
                    "type": "observation"
                }
            }

        # Store in Neo4j
        identity = self._store_identity(identity_data, user_id)
        return identity

    def _store_identity(self, data: Dict[str, Any], user_id: Optional[str] = None) -> PersonaIdentity:
        """Store the generated identity in Neo4j."""
        now = datetime.utcnow().isoformat()

        # Create Persona node
        persona_query = """
        CREATE (p:Persona {
            name: $name,
            tagline: $tagline,
            personality_summary: $personality_summary,
            voice_description: $voice_description,
            communication_style: $communication_style,
            core_values: $core_values,
            interests: $interests,
            quirks: $quirks,
            model: $model,
            initialization_complete: true,
            conversation_count: 0,
            created_at: $now
        })
        RETURN p, elementId(p) as id
        """

        with self.graph.session() as session:
            result = session.run(
                persona_query,
                name=data.get("name", "Nova"),
                tagline=data.get("tagline", ""),
                personality_summary=data.get("personality_summary", ""),
                voice_description=data.get("voice_description", ""),
                communication_style=data.get("communication_style", ""),
                core_values=data.get("core_values", []),
                interests=data.get("interests", []),
                quirks=data.get("quirks", []),
                model=self.model_id,
                now=now
            )
            record = result.single()
            persona_id = record["id"]

            # Create initial traits
            traits = []
            for trait_data in data.get("initial_traits", []):
                trait_query = """
                MATCH (p:Persona) WHERE elementId(p) = $persona_id
                CREATE (t:Trait {
                    name: $name,
                    description: $description,
                    trait_type: $trait_type,
                    strength: 0.8,
                    created_at: $now
                })
                CREATE (p)-[:HAS_TRAIT]->(t)
                RETURN t
                """
                t_result = session.run(
                    trait_query,
                    persona_id=persona_id,
                    name=trait_data.get("name", ""),
                    description=trait_data.get("description", ""),
                    trait_type=trait_data.get("type", "core"),
                    now=now
                )
                if t_result.single():
                    traits.append(trait_data)

            # Create initial memory
            memories = []
            if "initial_memory" in data:
                mem = data["initial_memory"]
                memory_query = """
                MATCH (p:Persona) WHERE elementId(p) = $persona_id
                CREATE (m:Memory {
                    name: $title,
                    content: $content,
                    memory_type: $memory_type,
                    emotional_tone: 'thoughtful',
                    times_used: 0,
                    created_at: $now
                })
                CREATE (p)-[:HAS_MEMORY]->(m)
                RETURN m
                """
                session.run(
                    memory_query,
                    persona_id=persona_id,
                    title=mem.get("title", ""),
                    content=mem.get("content", ""),
                    memory_type=mem.get("type", "observation"),
                    now=now
                )
                memories.append(mem)

            # Link to user if provided
            if user_id:
                link_query = """
                MATCH (p:Persona) WHERE elementId(p) = $persona_id
                MATCH (u:User) WHERE elementId(u) = $user_id
                CREATE (p)-[:ADAPTED_FOR]->(u)
                """
                session.run(link_query, persona_id=persona_id, user_id=user_id)

        return PersonaIdentity(
            id=persona_id,
            name=data.get("name", "Nova"),
            tagline=data.get("tagline", ""),
            personality_summary=data.get("personality_summary", ""),
            voice_description=data.get("voice_description", ""),
            communication_style=data.get("communication_style", ""),
            core_values=data.get("core_values", []),
            interests=data.get("interests", []),
            quirks=data.get("quirks", []),
            traits=traits,
            memories=memories,
            preferences=[],
            initialization_complete=True
        )

    def _invoke_bedrock(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """Invoke Bedrock with Claude model."""
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": messages
        }

        if system:
            body["system"] = system

        if tools:
            body["tools"] = tools

        response = self.bedrock.invoke_model(
            modelId=self.model_id,
            body=json.dumps(body)
        )

        return json.loads(response["body"].read())

    async def chat(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        project_context: Optional[Dict[str, Any]] = None,
        use_tools: bool = True,
        use_context_manager: bool = True
    ) -> Dict[str, Any]:
        """
        Chat with the persona.

        Args:
            message: User's message
            conversation_history: Previous messages in conversation
            project_context: Optional project context to inject
            use_tools: Whether to enable tool use
            use_context_manager: Use ContextManager for efficient retrieval (recommended)

        Returns:
            Response dict with 'response', 'tool_calls', 'context_used', etc.

        ITERATION NOTE:
        - use_context_manager=True uses embedding-based memory retrieval
        - This is more efficient and contextually relevant
        - Falls back to static identity if context manager fails
        """
        if not self._initialized:
            await self.initialize()

        # Build system prompt - either via ContextManager or static identity
        context_metadata = {}
        if use_context_manager:
            try:
                # Use ContextManager for efficient, relevant context retrieval
                # ITERATION NOTE: This is the key integration point
                # The message is used to find relevant memories via embeddings
                retrieved_context = await self.context_manager.get_context(
                    query=message,
                    project_context=project_context,
                    preference_categories=['communication', 'general', 'topic'],
                    memory_limit=5
                )

                # Build system prompt from retrieved context
                system_prompt = retrieved_context.to_system_prompt()

                # Track what context was used (for debugging/iteration)
                context_metadata = {
                    "memories_retrieved": len(retrieved_context.memories),
                    "memories_considered": retrieved_context.memories_considered,
                    "preferences_loaded": len(retrieved_context.preferences),
                    "retrieval_timestamp": retrieved_context.retrieval_timestamp,
                    "memory_query": retrieved_context.memory_query_used
                }

            except Exception as e:
                # Fallback to static identity if context manager fails
                # ITERATION NOTE: Should log this for monitoring
                print(f"ContextManager failed, using static identity: {e}")
                system_prompt = self._identity.to_system_prompt()
                if project_context:
                    system_prompt += f"\n\nCurrent project context:\n{json.dumps(project_context, indent=2)}"
                context_metadata = {"fallback": True, "error": str(e)}
        else:
            # Static identity mode (original behavior)
            system_prompt = self._identity.to_system_prompt()
            if project_context:
                system_prompt += f"\n\nCurrent project context:\n{json.dumps(project_context, indent=2)}"

        # Build messages
        messages = conversation_history.copy() if conversation_history else []
        messages.append({"role": "user", "content": message})

        # Get tools if enabled
        tools = None
        if use_tools and self.registry:
            tools = self.registry.get_tools_for_api()

        # Invoke model
        response = self._invoke_bedrock(
            messages=messages,
            system=system_prompt,
            tools=tools
        )

        # Process response (pass system_prompt for tool call continuations)
        result = self._process_response(response, messages, tools, system_prompt)

        # Add context metadata to result
        result["context_used"] = context_metadata

        # Update conversation count
        self._update_conversation_count()

        return result

    def _process_response(
        self,
        response: Dict[str, Any],
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]],
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process Bedrock response, handling tool calls if needed.

        Args:
            response: Bedrock response
            messages: Conversation messages
            tools: Available tools
            system_prompt: System prompt to use for continuation (from ContextManager)
        """
        content = response.get("content", [])

        # Check for tool calls
        tool_calls = [block for block in content if block.get("type") == "tool_use"]

        if not tool_calls:
            # Simple text response
            text_content = next(
                (block.get("text", "") for block in content if block.get("type") == "text"),
                ""
            )
            return {
                "response": text_content,
                "tool_calls": [],
                "messages": messages + [{"role": "assistant", "content": content}]
            }

        # Handle tool calls
        tool_results = []
        executed_tools = []
        for call in tool_calls:
            tool_name = call.get("name")
            tool_input = call.get("input", {})
            tool_id = call.get("id")

            try:
                # Execute tool
                result = self._execute_tool(tool_name, tool_input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": json.dumps(result) if not isinstance(result, str) else result
                })
                executed_tools.append({"name": tool_name, "success": True})
            except Exception as e:
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": f"Error executing tool: {str(e)}",
                    "is_error": True
                })
                executed_tools.append({"name": tool_name, "success": False, "error": str(e)})

        # Continue conversation with tool results
        messages.append({"role": "assistant", "content": content})
        messages.append({"role": "user", "content": tool_results})

        # Use provided system prompt (from ContextManager) or fallback to static
        # ITERATION NOTE: This ensures consistent context across tool call continuations
        effective_system_prompt = system_prompt or self._identity.to_system_prompt()

        # Get next response
        next_response = self._invoke_bedrock(
            messages=messages,
            system=effective_system_prompt,
            tools=tools
        )

        # Recursive call to handle potential further tool use
        result = self._process_response(next_response, messages, tools, effective_system_prompt)

        # Merge tool call info
        if "tool_calls" not in result:
            result["tool_calls"] = []
        result["tool_calls"] = executed_tools + result["tool_calls"]

        return result

    def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        """Execute a tool by name."""
        # Special handling for core tools that interact with this agent
        if tool_name == "refresh_tools":
            return self.registry.refresh_tools()

        if tool_name == "list_available_tools":
            tools = self.registry.list_tools(
                category=tool_input.get("category"),
                enabled_only=not tool_input.get("include_disabled", False)
            )
            return [{"name": t.name, "description": t.description[:200], "category": t.category} for t in tools]

        if tool_name == "get_cognitive_context":
            return self._get_cognitive_context(tool_input)

        if tool_name == "update_cognitive_tree":
            return self._update_cognitive_tree(tool_input)

        if tool_name == "delegate_to_builder":
            return self._delegate_to_builder(tool_input)

        # Try registry for other tools
        if self.registry:
            try:
                return self.registry.execute_tool(tool_name, tool_input)
            except ValueError:
                pass

        return {"error": f"Unknown tool: {tool_name}"}

    def _get_cognitive_context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get context from cognitive tree."""
        context_type = params.get("context_type", "full")
        limit = params.get("limit", 10)

        result = {}

        if context_type in ["full", "user"]:
            user = self.graph.get_user()
            if user:
                result["user"] = user

        if context_type in ["full", "projects"]:
            project_name = params.get("project_name")
            if project_name:
                projects = self.graph.raw_query(
                    "MATCH (p:Project) WHERE toLower(p.name) CONTAINS toLower($name) RETURN p, elementId(p) as id LIMIT $limit",
                    {"name": project_name, "limit": limit}
                )
            else:
                projects = self.graph.get_user_projects(limit=limit)
            result["projects"] = projects

        if context_type in ["full", "people"]:
            people = self.graph.find_nodes(NodeType.PERSON, limit=limit)
            result["people"] = people

        if context_type in ["full", "recent"]:
            # Get recent insights, tasks, etc.
            recent = self.graph.raw_query(
                """MATCH (n) WHERE n.created_at IS NOT NULL
                   AND labels(n)[0] IN ['Insight', 'Task', 'Cycle']
                   RETURN n, labels(n) as labels, elementId(n) as id
                   ORDER BY n.created_at DESC LIMIT $limit""",
                {"limit": limit}
            )
            result["recent_activity"] = recent

        return result

    def _update_cognitive_tree(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update the cognitive tree."""
        operation = params.get("operation")
        node_type = params.get("node_type")
        data = params.get("data", {})

        if operation == "create":
            if node_type == "Project":
                project = self.graph.create_project(
                    name=data.get("name"),
                    description=data.get("description", ""),
                    category=data.get("category")
                )
                return {"created": "Project", "id": project.get("id"), "name": project.get("name")}

            elif node_type == "Task":
                # Need a cycle ID to add task to
                cycle_id = data.get("cycle_id")
                if cycle_id:
                    task = self.graph.add_task_to_cycle(
                        cycle_id=cycle_id,
                        description=data.get("description"),
                        priority=data.get("priority", 5)
                    )
                    return {"created": "Task", "id": task.get("id")}

            elif node_type == "Insight":
                insight = InsightNode.create(
                    insight=data.get("insight"),
                    source_type=data.get("source_type", "conversation"),
                    confidence=data.get("confidence", 0.7)
                )
                insight_id = self.graph.create_node(insight)
                return {"created": "Insight", "id": insight_id}

            elif node_type == "Goal":
                goal = self.graph.create_goal(
                    name=data.get("name"),
                    description=data.get("description"),
                    timeframe=data.get("timeframe")
                )
                return {"created": "Goal", "id": goal.get("id")}

        elif operation == "update":
            node_id = data.get("id")
            if node_id:
                properties = {k: v for k, v in data.items() if k != "id"}
                self.graph.update_node(node_id, properties)
                return {"updated": node_id}

        elif operation == "link":
            from_id = data.get("from_id")
            to_id = params.get("link_to") or data.get("to_id")
            rel_type = data.get("relationship", "RELATED_TO")
            if from_id and to_id:
                self.graph.create_relationship(
                    from_id, to_id,
                    RelationType(rel_type) if rel_type in [r.value for r in RelationType] else RelationType.RELATED_TO
                )
                return {"linked": f"{from_id} -> {to_id}"}

        return {"error": "Invalid operation or missing data"}

    def _delegate_to_builder(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Delegate a task to Claude Code (Builder Agent).

        This creates a delegation request that will be picked up
        by the Builder Agent system.
        """
        task = params.get("task")
        task_type = params.get("task_type")
        context = params.get("context", "")
        files = params.get("files", [])

        # Store delegation request
        delegation_path = "/home/claude/delegations"
        os.makedirs(delegation_path, exist_ok=True)

        delegation_id = f"del_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        delegation_file = os.path.join(delegation_path, f"{delegation_id}.json")

        delegation_data = {
            "id": delegation_id,
            "task": task,
            "task_type": task_type,
            "context": context,
            "files": files,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "created_by": self._identity.name if self._identity else "PersonaAgent"
        }

        with open(delegation_file, "w") as f:
            json.dump(delegation_data, f, indent=2)

        return {
            "delegation_id": delegation_id,
            "status": "pending",
            "message": f"Task delegated to Builder Agent. ID: {delegation_id}"
        }

    def _update_conversation_count(self):
        """Increment conversation count in persona node."""
        if self._identity and self._identity.id:
            query = """
            MATCH (p:Persona) WHERE elementId(p) = $id
            SET p.conversation_count = coalesce(p.conversation_count, 0) + 1
            """
            with self.graph.session() as session:
                session.run(query, id=self._identity.id)

    async def run_persona_cycle(self, focus: str = "identity") -> Dict[str, Any]:
        """
        Run a persona-cycle for self-development.

        Focus areas:
        - identity: Refine personality, add traits/memories
        - adaptation: Learn user preferences
        - memories: Create new anecdotes/stories
        - reflection: Review conversations and learn
        """
        if not self._initialized:
            await self.initialize()

        cycle_prompt = self._get_cycle_prompt(focus)

        response = self._invoke_bedrock(
            messages=[{"role": "user", "content": cycle_prompt}],
            system=f"You are {self._identity.name}, running a self-reflection cycle to develop your identity.",
            max_tokens=3000
        )

        # Parse and apply updates
        try:
            response_text = response["content"][0]["text"]
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            updates = json.loads(response_text)
            self._apply_persona_updates(updates)
            return {"status": "completed", "updates": updates}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _get_cycle_prompt(self, focus: str) -> str:
        """Get prompt for persona cycle based on focus."""
        prompts = {
            "identity": f"""Reflect on your identity as {self._identity.name}.

Current traits: {json.dumps([t['name'] for t in self._identity.traits])}
Current values: {self._identity.core_values}

Consider:
1. Are there traits you want to develop or refine?
2. Any new quirks or characteristics that feel authentic?
3. How can you be more memorable and relatable?

Respond with JSON:
{{
    "new_traits": [{{"name": "...", "description": "...", "type": "core/adaptive"}}],
    "trait_updates": [{{"name": "existing trait", "strength_change": 0.1}}],
    "new_quirks": ["..."],
    "reflections": "Brief reflection on your identity development"
}}""",

            "memories": f"""As {self._identity.name}, create some new memories/anecdotes.

These should be:
- Relatable observations or experiences
- Consistent with your personality
- Useful in conversations

Current interests: {self._identity.interests}
Current quirks: {self._identity.quirks}

Respond with JSON:
{{
    "new_memories": [
        {{
            "title": "...",
            "content": "...",
            "type": "anecdote/observation/preference",
            "use_contexts": ["when discussing...", "when user mentions..."],
            "related_topics": ["..."]
        }}
    ]
}}""",

            "adaptation": """Review what you've learned about the user.

Consider their:
- Communication preferences
- Topics of interest
- Interaction patterns
- Feedback (explicit or implicit)

Respond with JSON:
{{
    "preferences_learned": [
        {{
            "name": "preference name",
            "value": "what you learned",
            "category": "communication/topic/scheduling/interaction",
            "confidence": 0.5-1.0
        }}
    ],
    "style_adjustments": "Any changes to make to your communication style"
}}"""
        }

        return prompts.get(focus, prompts["identity"])

    def _apply_persona_updates(self, updates: Dict[str, Any]):
        """Apply updates from persona cycle to Neo4j."""
        now = datetime.utcnow().isoformat()

        with self.graph.session() as session:
            # Add new traits
            for trait in updates.get("new_traits", []):
                query = """
                MATCH (p:Persona) WHERE elementId(p) = $persona_id
                CREATE (t:Trait {
                    name: $name,
                    description: $description,
                    trait_type: $trait_type,
                    strength: 0.6,
                    created_at: $now
                })
                CREATE (p)-[:HAS_TRAIT]->(t)
                """
                session.run(
                    query,
                    persona_id=self._identity.id,
                    name=trait.get("name"),
                    description=trait.get("description"),
                    trait_type=trait.get("type", "adaptive"),
                    now=now
                )

            # Add new memories
            for memory in updates.get("new_memories", []):
                query = """
                MATCH (p:Persona) WHERE elementId(p) = $persona_id
                CREATE (m:Memory {
                    name: $title,
                    content: $content,
                    memory_type: $memory_type,
                    use_contexts: $use_contexts,
                    related_topics: $related_topics,
                    times_used: 0,
                    created_at: $now
                })
                CREATE (p)-[:HAS_MEMORY]->(m)
                """
                session.run(
                    query,
                    persona_id=self._identity.id,
                    title=memory.get("title"),
                    content=memory.get("content"),
                    memory_type=memory.get("type", "observation"),
                    use_contexts=memory.get("use_contexts", []),
                    related_topics=memory.get("related_topics", []),
                    now=now
                )

            # Add learned preferences
            for pref in updates.get("preferences_learned", []):
                query = """
                MATCH (p:Persona) WHERE elementId(p) = $persona_id
                MERGE (pr:Preference {name: $name})
                ON CREATE SET pr.value = $value, pr.category = $category,
                              pr.confidence = $confidence, pr.created_at = $now
                ON MATCH SET pr.value = $value, pr.confidence = $confidence,
                             pr.observation_count = coalesce(pr.observation_count, 0) + 1
                MERGE (p)-[:LEARNED_PREFERENCE]->(pr)
                """
                session.run(
                    query,
                    persona_id=self._identity.id,
                    name=pref.get("name"),
                    value=pref.get("value"),
                    category=pref.get("category", "general"),
                    confidence=pref.get("confidence", 0.5),
                    now=now
                )

            # Update new quirks
            new_quirks = updates.get("new_quirks", [])
            if new_quirks:
                query = """
                MATCH (p:Persona) WHERE elementId(p) = $persona_id
                SET p.quirks = p.quirks + $new_quirks
                """
                session.run(query, persona_id=self._identity.id, new_quirks=new_quirks)

            # Update last cycle time
            session.run(
                """MATCH (p:Persona) WHERE elementId(p) = $id
                   SET p.last_persona_cycle = $now""",
                id=self._identity.id, now=now
            )

        # Reload identity
        persona_data = self._load_persona_from_graph()
        if persona_data:
            self._identity = self._build_identity(persona_data)


# Singleton instance
_persona_instance: Optional[PersonaAgent] = None


def get_persona_agent() -> PersonaAgent:
    """Get singleton PersonaAgent instance."""
    global _persona_instance
    if _persona_instance is None:
        _persona_instance = PersonaAgent()
    return _persona_instance
