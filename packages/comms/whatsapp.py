"""
WhatsApp messaging via Twilio.

Provides functions to send messages and log conversations.
"""

import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any

# Add packages to path
sys.path.insert(0, '/packages')

from cognitive import get_graph, NodeType, RelationType
from cognitive.models import ConversationNode


def get_twilio_client():
    """Get Twilio client (lazy import)."""
    try:
        from twilio.rest import Client
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        if account_sid and auth_token:
            return Client(account_sid, auth_token)
    except ImportError:
        pass
    return None


def send_whatsapp(
    to_number: str,
    message: str,
    from_number: Optional[str] = None,
    log_to_graph: bool = True
) -> Dict[str, Any]:
    """
    Send a WhatsApp message via Twilio.

    Args:
        to_number: Recipient phone number (with country code)
        message: Message text
        from_number: Twilio WhatsApp number (default from env)
        log_to_graph: Whether to log this message to Neo4j

    Returns:
        Dict with status and message SID
    """
    client = get_twilio_client()

    if not client:
        return {
            "success": False,
            "error": "Twilio client not configured. Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN."
        }

    from_number = from_number or os.environ.get("TWILIO_WHATSAPP_NUMBER")

    if not from_number:
        return {
            "success": False,
            "error": "TWILIO_WHATSAPP_NUMBER not set"
        }

    # Ensure WhatsApp format
    if not to_number.startswith("whatsapp:"):
        to_number = f"whatsapp:{to_number}"
    if not from_number.startswith("whatsapp:"):
        from_number = f"whatsapp:{from_number}"

    try:
        msg = client.messages.create(
            body=message,
            from_=from_number,
            to=to_number
        )

        result = {
            "success": True,
            "sid": msg.sid,
            "status": msg.status,
            "to": to_number,
        }

        # Log to graph
        if log_to_graph:
            _log_outgoing_message("whatsapp", to_number, message)

        return result

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def send_whatsapp_media(
    to_number: str,
    media_url: str,
    caption: Optional[str] = None,
    from_number: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send a WhatsApp message with media (image, document, etc.).

    Args:
        to_number: Recipient phone number
        media_url: Public URL of the media file
        caption: Optional caption text
        from_number: Twilio WhatsApp number

    Returns:
        Dict with status and message SID
    """
    client = get_twilio_client()

    if not client:
        return {
            "success": False,
            "error": "Twilio client not configured"
        }

    from_number = from_number or os.environ.get("TWILIO_WHATSAPP_NUMBER")

    if not to_number.startswith("whatsapp:"):
        to_number = f"whatsapp:{to_number}"
    if not from_number.startswith("whatsapp:"):
        from_number = f"whatsapp:{from_number}"

    try:
        msg = client.messages.create(
            body=caption or "",
            from_=from_number,
            to=to_number,
            media_url=[media_url]
        )

        return {
            "success": True,
            "sid": msg.sid,
            "status": msg.status,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def log_incoming_message(
    from_number: str,
    message: str,
    message_sid: Optional[str] = None
) -> str:
    """
    Log an incoming WhatsApp message to the cognitive graph.

    Args:
        from_number: Sender's phone number
        message: Message content
        message_sid: Twilio message SID

    Returns:
        Neo4j element ID of the message node
    """
    return _log_message(
        channel="whatsapp",
        direction="incoming",
        participant=from_number,
        content=message,
        external_id=message_sid
    )


def _log_outgoing_message(
    channel: str,
    to: str,
    content: str,
    external_id: Optional[str] = None
) -> str:
    """Log an outgoing message to the graph."""
    return _log_message(
        channel=channel,
        direction="outgoing",
        participant=to,
        content=content,
        external_id=external_id
    )


def _log_message(
    channel: str,
    direction: str,
    participant: str,
    content: str,
    external_id: Optional[str] = None
) -> str:
    """Log a message to the cognitive graph."""
    graph = get_graph()

    props = {
        "name": f"{channel} message at {datetime.utcnow().isoformat()}",
        "channel": channel,
        "direction": direction,
        "participant": participant,
        "content": content[:500],  # Truncate long messages
        "external_id": external_id,
        "created_at": datetime.utcnow().isoformat(),
    }

    query = """
    CREATE (m:Message $props)
    RETURN elementId(m) as id
    """

    with graph.session() as session:
        result = session.run(query, props=props)
        message_id = result.single()["id"]

    # Link to user
    user = graph.get_user()
    if user:
        rel_type = RelationType.RECEIVED if direction == "incoming" else RelationType.SENT
        graph.create_relationship(user["id"], message_id, rel_type)

    return message_id
