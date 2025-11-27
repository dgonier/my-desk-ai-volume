"""
Voice call functionality via Twilio.

Provides functions for outbound calls and handling incoming calls.
For TTS during calls, integrates with Supertonic TTS.
"""

import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any, List

# Add packages to path
sys.path.insert(0, '/packages')

from cognitive import get_graph, NodeType, RelationType


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


def initiate_call(
    to_number: str,
    twiml_url: Optional[str] = None,
    message: Optional[str] = None,
    from_number: Optional[str] = None,
    webhook_url: Optional[str] = None,
    record: bool = True,
    log_to_graph: bool = True
) -> Dict[str, Any]:
    """
    Initiate an outbound voice call.

    The call can either:
    1. Use a TwiML URL for dynamic call flow
    2. Speak a simple message using Twilio's TTS

    Args:
        to_number: Phone number to call
        twiml_url: URL returning TwiML for call handling
        message: Simple message to speak (if no twiml_url)
        from_number: Twilio phone number (default from env)
        webhook_url: Status callback URL
        record: Whether to record the call
        log_to_graph: Whether to log to Neo4j

    Returns:
        Dict with call SID and status
    """
    client = get_twilio_client()

    if not client:
        return {
            "success": False,
            "error": "Twilio client not configured"
        }

    from_number = from_number or os.environ.get("TWILIO_PHONE_NUMBER")

    if not from_number:
        return {
            "success": False,
            "error": "TWILIO_PHONE_NUMBER not set"
        }

    try:
        call_params = {
            "to": to_number,
            "from_": from_number,
            "record": record,
        }

        if twiml_url:
            call_params["url"] = twiml_url
        elif message:
            # Use TwiML for simple message
            from twilio.twiml.voice_response import VoiceResponse
            response = VoiceResponse()
            response.say(message, voice="Polly.Matthew")
            call_params["twiml"] = str(response)
        else:
            return {
                "success": False,
                "error": "Must provide either twiml_url or message"
            }

        if webhook_url:
            call_params["status_callback"] = webhook_url
            call_params["status_callback_event"] = ["initiated", "ringing", "answered", "completed"]

        call = client.calls.create(**call_params)

        result = {
            "success": True,
            "call_sid": call.sid,
            "status": call.status,
            "to": to_number,
            "from": from_number,
        }

        # Log to graph
        if log_to_graph:
            _log_call("outgoing", to_number, call.sid)

        return result

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def initiate_call_with_agent(
    to_number: str,
    agent_prompt: str,
    from_number: Optional[str] = None,
    voice_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Initiate a call that connects to an AI voice agent.

    This sets up a call that, when answered, connects to a
    voice agent endpoint for interactive conversation.

    Args:
        to_number: Phone number to call
        agent_prompt: System prompt for the voice agent
        from_number: Twilio phone number
        voice_id: TTS voice to use

    Returns:
        Dict with call SID and status
    """
    # The TwiML URL should point to your voice agent WebSocket handler
    # This is typically set up in your Modal app
    agent_url = os.environ.get("VOICE_AGENT_URL")

    if not agent_url:
        return {
            "success": False,
            "error": "VOICE_AGENT_URL not configured. Set up voice agent endpoint first."
        }

    # Add agent config as query params
    import urllib.parse
    params = {
        "prompt": agent_prompt[:500],  # Truncate long prompts
    }
    if voice_id:
        params["voice_id"] = voice_id

    twiml_url = f"{agent_url}?{urllib.parse.urlencode(params)}"

    return initiate_call(
        to_number=to_number,
        twiml_url=twiml_url,
        from_number=from_number,
        log_to_graph=True
    )


def handle_incoming_call(
    from_number: str,
    call_sid: str,
    caller_name: Optional[str] = None
) -> str:
    """
    Log an incoming call to the cognitive graph.

    Args:
        from_number: Caller's phone number
        call_sid: Twilio call SID
        caller_name: Caller name if available

    Returns:
        Neo4j element ID of the call node
    """
    return _log_call("incoming", from_number, call_sid, caller_name)


def get_call_history(
    direction: Optional[str] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Get call history from the cognitive graph.

    Args:
        direction: Filter by "incoming" or "outgoing"
        limit: Maximum calls to return

    Returns:
        List of call dicts
    """
    graph = get_graph()

    where_clause = "true"
    params = {"limit": limit}

    if direction:
        where_clause = "c.direction = $direction"
        params["direction"] = direction

    query = f"""
    MATCH (c:Call)
    WHERE {where_clause}
    RETURN c, elementId(c) as id
    ORDER BY c.created_at DESC
    LIMIT $limit
    """

    calls = []
    with graph.session() as session:
        result = session.run(query, **params)
        for record in result:
            call_data = dict(record["c"])
            call_data["id"] = record["id"]
            calls.append(call_data)

    return calls


def get_call_recording(call_sid: str) -> Optional[str]:
    """
    Get the recording URL for a call.

    Args:
        call_sid: Twilio call SID

    Returns:
        Recording URL or None
    """
    client = get_twilio_client()

    if not client:
        return None

    try:
        recordings = client.recordings.list(call_sid=call_sid, limit=1)
        if recordings:
            return f"https://api.twilio.com{recordings[0].uri.replace('.json', '.mp3')}"
    except Exception as e:
        print(f"Error getting recording: {e}")

    return None


def _log_call(
    direction: str,
    participant: str,
    call_sid: str,
    participant_name: Optional[str] = None
) -> str:
    """Log a call to the cognitive graph."""
    graph = get_graph()

    props = {
        "name": f"Call with {participant_name or participant} at {datetime.utcnow().isoformat()}",
        "direction": direction,
        "participant": participant,
        "participant_name": participant_name,
        "call_sid": call_sid,
        "status": "initiated",
        "created_at": datetime.utcnow().isoformat(),
    }

    query = """
    CREATE (c:Call $props)
    RETURN elementId(c) as id
    """

    with graph.session() as session:
        result = session.run(query, props=props)
        call_id = result.single()["id"]

    # Link to user
    user = graph.get_user()
    if user:
        rel_type = RelationType.RECEIVED if direction == "incoming" else RelationType.SENT
        graph.create_relationship(user["id"], call_id, rel_type)

    return call_id


def update_call_status(
    call_sid: str,
    status: str,
    duration: Optional[int] = None,
    recording_url: Optional[str] = None
) -> bool:
    """
    Update call status in the graph.

    Args:
        call_sid: Twilio call SID
        status: New status (ringing, in-progress, completed, etc.)
        duration: Call duration in seconds
        recording_url: Recording URL if available

    Returns:
        True if updated successfully
    """
    graph = get_graph()

    props = {
        "status": status,
        "updated_at": datetime.utcnow().isoformat(),
    }
    if duration is not None:
        props["duration"] = duration
    if recording_url:
        props["recording_url"] = recording_url

    query = """
    MATCH (c:Call {call_sid: $call_sid})
    SET c += $props
    RETURN c
    """

    with graph.session() as session:
        result = session.run(query, call_sid=call_sid, props=props)
        return result.single() is not None
