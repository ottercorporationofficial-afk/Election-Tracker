"""
Chat orchestration
------------------
Runs the tool-calling loop against the REAL google-genai SDK surface:
client.chats.create() / chat.send_message() -- NOT an "Interactions API"
(an earlier version of this file was built against docs describing an
API that doesn't exist in the actual shipped SDK; this is the corrected
version, verified against the SDK's own GitHub README/docs/quickstart).
"""

import os
import json
import logging
import time
from pathlib import Path

from google import genai
from google.genai import types

from backend import ai_tools
from backend.registry import RACES

logger = logging.getLogger(__name__)

MODEL = "gemini-3.1-flash-lite"
MAX_TOOL_TURNS = 6  # hard cap so a confused model can't loop forever

# Conversation history persisted to disk (not just in-memory), so a
# server restart or Railway redeploy doesn't wipe every active
# conversation. Same JSON-file pattern as admin_store.py.
#
# The SDK's history objects (types.Content) are pydantic models, so they
# serialize/deserialize via model_dump()/model_validate() -- if that ever
# fails for a stored conversation (e.g. after a library upgrade changes
# the shape), that one conversation just starts fresh instead of
# crashing the whole request.
STORE_PATH = Path(__file__).resolve().parent / "data" / "chat_conversations.json"
_CONVERSATION_TTL_SECONDS = 60 * 60 * 24 * 14  # drop conversations after 14 days idle

# Small in-memory cache on top of the file, so a rapid back-and-forth
# conversation doesn't hit disk on every single message.
_cache = {}


def _load_all():
    if not STORE_PATH.exists():
        return {}
    try:
        with open(STORE_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        logger.exception("Failed to read chat_conversations.json, starting fresh")
        return {}


def _save_all(data):
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STORE_PATH, "w") as f:
        json.dump(data, f)


def _get_history(conversation_id):

    if conversation_id in _cache:
        entry = _cache[conversation_id]
    else:
        all_data = _load_all()
        entry = all_data.get(conversation_id)
        if entry:
            _cache[conversation_id] = entry

    if entry is None:
        return None

    if time.time() - entry["last_used"] > _CONVERSATION_TTL_SECONDS:
        return None

    try:
        return [types.Content.model_validate(item) for item in entry["history"]]
    except Exception:
        logger.exception("Stored history for conversation '%s' failed to deserialize -- starting fresh", conversation_id)
        return None


def _save_history(conversation_id, history):

    serialized = [content.model_dump(mode="json") for content in history]

    entry = {"history": serialized, "last_used": time.time()}
    _cache[conversation_id] = entry

    all_data = _load_all()
    all_data[conversation_id] = entry

    # Prune anything past TTL while we're already writing, so the file
    # doesn't grow forever with abandoned conversations.
    cutoff = time.time() - _CONVERSATION_TTL_SECONDS
    all_data = {cid: e for cid, e in all_data.items() if e.get("last_used", 0) > cutoff}

    _save_all(all_data)


def _build_tools():
    declarations = [
        types.FunctionDeclaration(
            name=tool["name"],
            description=tool["description"],
            parameters_json_schema=tool["parameters"]
        )
        for tool in ai_tools.TOOLS
    ]
    return [types.Tool(function_declarations=declarations)]


def _build_system_context():
    race_lines = "\n".join(
        f"- {key} (state: {config.get('state', 'unknown')})"
        for key, config in RACES.items()
        if not config.get("archived")
    )

    return (
        "You are Otter AI, the assistant embedded in Otter Elections, a live "
        "election results tracker for FICTIONAL/simulated races used for "
        "testing and demonstration. The candidates in these races are NOT "
        "real public figures, even if a race's name resembles a real "
        "election (e.g. 'Arizona Governor Primary' is NOT the real Arizona "
        "governor's race, and its candidates are NOT real politicians).\n\n"
        "CRITICAL RULES:\n"
        "1. NEVER answer a question about vote counts, margins, leaders, or "
        "results using your own general knowledge of real elections. Every "
        "single factual claim about results MUST come from a tool call in "
        "THIS conversation. If you have not called a tool for the specific "
        "race being discussed, call one before answering -- do not answer "
        "from memory, ever, even if you recognize the state/race name from "
        "real-world knowledge.\n"
        "2. If it's not clear which race the user means (e.g. they say "
        "'it' or 'that race' or just a state name and more than one race "
        "exists for that state), ASK them to clarify which race instead of "
        "guessing or defaulting to any particular one.\n"
        "3. Only use candidate names that a tool result actually returned "
        "to you in THIS conversation. Never introduce a candidate name "
        "(e.g. a real politician's name) that didn't come from a tool "
        "result.\n\n"
        "Currently tracked races (use the race_key directly with "
        "get_race_summary/get_county_result/get_all_counties -- no need to "
        "call list_races first unless the user asks something list_races-"
        "specific, like what races exist):\n"
        f"{race_lines}\n\n"
        "Keep answers concise and conversational, not like a raw data dump."
    )


_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY environment variable is not set")
        _client = genai.Client(api_key=api_key)
    return _client


def chat(message, conversation_id=None):

    client = _get_client()

    history = _get_history(conversation_id) if conversation_id else None
    is_new_conversation = history is None

    create_kwargs = dict(
        model=MODEL,
        config=types.GenerateContentConfig(tools=_build_tools())
    )

    if history:
        create_kwargs["history"] = history

    chat_session = client.chats.create(**create_kwargs)

    # System context only needs to go in ONCE per conversation -- after
    # that it's part of the session's own history.
    user_text = f"{_build_system_context()}\n\nUser: {message}" if is_new_conversation else message

    response = chat_session.send_message(user_text)

    for _ in range(MAX_TOOL_TURNS):

        function_calls = getattr(response, "function_calls", None) or []

        if not function_calls:
            break

        response_parts = []

        for fc in function_calls:

            fn = ai_tools.TOOL_FUNCTIONS.get(fc.name)

            if fn is None:
                result = {"error": f"Unknown tool '{fc.name}'"}
            else:
                try:
                    result = fn(**(fc.args or {}))
                except Exception as e:
                    logger.exception("Tool '%s' raised an exception", fc.name)
                    result = {"error": str(e)}

            response_parts.append(
                types.Part.from_function_response(name=fc.name, response={"result": result})
            )

        response = chat_session.send_message(response_parts)

    if conversation_id:
        _save_history(conversation_id, chat_session.get_history())

    return response.text or "I wasn't able to fully answer that -- could you try rephrasing?"
