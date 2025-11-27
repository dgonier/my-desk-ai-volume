"""
Comms Package - Communication Functions

This package provides functions for:
- WhatsApp messaging (send/receive)
- Voice calls (outbound/inbound)
- SMS messaging
- Conversation tracking in the cognitive graph

All conversations are logged to Neo4j for context and memory.
"""

from .whatsapp import (
    send_whatsapp,
    send_whatsapp_media,
    log_incoming_message,
)
from .voice import (
    initiate_call,
    handle_incoming_call,
    get_call_history,
)
from .conversations import (
    create_conversation,
    add_message,
    end_conversation,
    get_conversation_summary,
    get_recent_conversations,
)

__all__ = [
    # WhatsApp
    "send_whatsapp",
    "send_whatsapp_media",
    "log_incoming_message",
    # Voice
    "initiate_call",
    "handle_incoming_call",
    "get_call_history",
    # Conversations
    "create_conversation",
    "add_message",
    "end_conversation",
    "get_conversation_summary",
    "get_recent_conversations",
]
