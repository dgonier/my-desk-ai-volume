"""
Conversation tracking and management.

Tracks all conversations (WhatsApp, voice, SMS) in the cognitive graph
for context and memory across sessions.
"""

import sys
from datetime import datetime
from typing import Optional, Dict, Any, List

# Add packages to path
sys.path.insert(0, '/packages')

from cognitive import get_graph, NodeType, RelationType
from cognitive.models import ConversationNode


def create_conversation(
    channel: str,
    participant: str,
    topic: Optional[str] = None,
    **extra_props
) -> Dict[str, Any]:
    """
    Create a new conversation record.

    Args:
        channel: Communication channel (whatsapp, voice, sms)
        participant: Other party's identifier (phone number, name)
        topic: Optional topic/subject of conversation
        **extra_props: Additional properties

    Returns:
        Dict with conversation ID and details
    """
    graph = get_graph()

    conv = ConversationNode.create(
        channel=channel,
        participant=participant,
    )

    # Add extra properties
    if topic:
        conv.properties["topic"] = topic
    conv.properties.update(extra_props)

    conv_id = graph.create_node(conv)

    # Link to user
    user = graph.get_user()
    if user:
        graph.create_relationship(
            user["id"],
            conv_id,
            RelationType.PARTICIPATED_IN
        )

    # Link to topic if provided
    if topic:
        topic_node = graph.get_or_create_topic(topic)
        graph.create_relationship(
            conv_id,
            topic_node["id"],
            RelationType.DISCUSSED
        )

    return {
        "id": conv_id,
        "channel": channel,
        "participant": participant,
        "topic": topic,
        "started_at": conv.properties.get("started_at"),
    }


def add_message(
    conversation_id: str,
    content: str,
    direction: str,  # "incoming" or "outgoing"
    sender: Optional[str] = None,
) -> str:
    """
    Add a message to an existing conversation.

    Args:
        conversation_id: Neo4j ID of the conversation
        content: Message content
        direction: "incoming" (from participant) or "outgoing" (from agent)
        sender: Sender identifier

    Returns:
        Neo4j element ID of the message node
    """
    graph = get_graph()

    props = {
        "name": f"Message at {datetime.utcnow().isoformat()}",
        "content": content[:2000],  # Truncate very long messages
        "direction": direction,
        "sender": sender,
        "created_at": datetime.utcnow().isoformat(),
    }

    query = """
    CREATE (m:Message $props)
    RETURN elementId(m) as id
    """

    with graph.session() as session:
        result = session.run(query, props=props)
        message_id = result.single()["id"]

    # Link message to conversation
    graph.create_relationship(
        conversation_id,
        message_id,
        RelationType.HAS_NOTE,  # Using HAS_NOTE for messages in conversation
        {"order": datetime.utcnow().timestamp()}
    )

    return message_id


def end_conversation(
    conversation_id: str,
    summary: Optional[str] = None,
    outcome: Optional[str] = None
) -> bool:
    """
    Mark a conversation as ended.

    Args:
        conversation_id: Neo4j ID of the conversation
        summary: Optional summary of the conversation
        outcome: Optional outcome (resolved, pending, followup_needed)

    Returns:
        True if successful
    """
    graph = get_graph()

    props = {
        "ended_at": datetime.utcnow().isoformat(),
        "status": "completed",
    }
    if summary:
        props["summary"] = summary
    if outcome:
        props["outcome"] = outcome

    return graph.update_node(conversation_id, props)


def get_conversation_summary(conversation_id: str) -> Dict[str, Any]:
    """
    Get a summary of a conversation including all messages.

    Args:
        conversation_id: Neo4j ID of the conversation

    Returns:
        Dict with conversation details and messages
    """
    graph = get_graph()

    # Get conversation node
    conv = graph.get_node_by_id(conversation_id)
    if not conv:
        return {"error": "Conversation not found"}

    # Get all messages in the conversation
    query = """
    MATCH (c)-[r:HAS_NOTE]->(m:Message)
    WHERE elementId(c) = $conv_id
    RETURN m, elementId(m) as id
    ORDER BY m.created_at ASC
    """

    messages = []
    with graph.session() as session:
        result = session.run(query, conv_id=conversation_id)
        for record in result:
            msg = dict(record["m"])
            msg["id"] = record["id"]
            messages.append(msg)

    return {
        "conversation": conv,
        "messages": messages,
        "message_count": len(messages),
    }


def get_recent_conversations(
    channel: Optional[str] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Get recent conversations.

    Args:
        channel: Filter by channel (whatsapp, voice, sms)
        limit: Maximum conversations to return

    Returns:
        List of conversation dicts
    """
    graph = get_graph()

    where_clause = "true"
    params = {"limit": limit}

    if channel:
        where_clause = "c.channel = $channel"
        params["channel"] = channel

    query = f"""
    MATCH (c:Conversation)
    WHERE {where_clause}
    OPTIONAL MATCH (c)-[:HAS_NOTE]->(m:Message)
    WITH c, count(m) as message_count
    RETURN c, elementId(c) as id, message_count
    ORDER BY c.created_at DESC
    LIMIT $limit
    """

    conversations = []
    with graph.session() as session:
        result = session.run(query, **params)
        for record in result:
            conv = dict(record["c"])
            conv["id"] = record["id"]
            conv["message_count"] = record["message_count"]
            conversations.append(conv)

    return conversations


def get_conversations_about_topic(topic: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get conversations that discussed a specific topic.

    Args:
        topic: Topic name
        limit: Maximum conversations

    Returns:
        List of conversation dicts
    """
    graph = get_graph()

    query = """
    MATCH (c:Conversation)-[:DISCUSSED]->(t:Topic {name: $topic})
    RETURN c, elementId(c) as id
    ORDER BY c.created_at DESC
    LIMIT $limit
    """

    conversations = []
    with graph.session() as session:
        result = session.run(query, topic=topic, limit=limit)
        for record in result:
            conv = dict(record["c"])
            conv["id"] = record["id"]
            conversations.append(conv)

    return conversations


def search_conversations(
    search_text: str,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Search conversations by message content.

    Args:
        search_text: Text to search for
        limit: Maximum results

    Returns:
        List of conversations containing matching messages
    """
    graph = get_graph()

    query = """
    MATCH (c:Conversation)-[:HAS_NOTE]->(m:Message)
    WHERE toLower(m.content) CONTAINS toLower($search)
    WITH DISTINCT c, elementId(c) as id
    RETURN c, id
    ORDER BY c.created_at DESC
    LIMIT $limit
    """

    conversations = []
    with graph.session() as session:
        result = session.run(query, search=search_text, limit=limit)
        for record in result:
            conv = dict(record["c"])
            conv["id"] = record["id"]
            conversations.append(conv)

    return conversations
