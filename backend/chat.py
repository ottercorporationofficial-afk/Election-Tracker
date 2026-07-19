"""
Chat orchestration
------------------
Runs the tool-calling loop against the real google-genai SDK
(client.chats.create() / chat.send_message()).

Supports multiple named conversations per browser (like ChatGPT/Claude's
sidebar), identified by a browser_id the frontend generates once and
never changes, plus a conversation_id per individual chat thread.
"""

import os
import json
import logging
import time
import uuid
from pathlib import Path

from google import genai
from google.genai import types

from backend import ai_tools
from backend.registry import RACES

logger = logging.getLogger(__name__)

MODEL = "gemini-3.1-flash-lite"
MAX_TOOL_TURNS = 6  # hard cap so a confused model can't loop forever

STORE_PATH = Path(__file__).resolve().parent / "data" / "chat_conversations.json"
_CONVERSATION_TTL_SECONDS = 60 * 60 * 24 * 90  # keep conversations 90 days

_cache = None  # whole store, loaded lazily; small enough for a chat widget to keep fully in memory


def _load_all():
    global _cache

    if _cache is not None:
        return _cache

    if not STORE_PATH.exists():
        _cache = {}
        return _cache

    try:
        with open(STORE_PATH) as f:
            _cache = json.load(f)
    except (json.JSONDecodeError, OSError):
        logger.exception("Failed to read chat_conversations.json, starting fresh")
        _cache = {}

    return _cache


def _save_all():
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STORE_PATH, "w") as f:
        json.dump(_cache, f)


def _prune_expired():
    cutoff = time.time() - _CONVERSATION_TTL_SECONDS
    all_data = _load_all()
    expired = [cid for cid, entry in all_data.items() if entry.get("last_used", 0) < cutoff]
    for cid in expired:
        del all_data[cid]
    if expired:
        _save_all()


def _make_title(first_message):
    title = first_message.strip().replace("\n", " ")
    if len(title) > 48:
        title = title[:45].rstrip() + "..."
    return title or "New chat"


def list_conversations(browser_id):
    """
    All conversations belonging to one browser_id, newest first --
    powers the sidebar list. Returns metadata only (id, title, last_used),
    not full message content.
    """
    _prune_expired()
    all_data = _load_all()

    conversations = [
        {
            "conversation_id": cid,
            "title": entry.get("title", "New chat"),
            "last_used": entry.get("last_used")
        }
        for cid, entry in all_data.items()
        if entry.get("browser_id") == browser_id
    ]

    conversations.sort(key=lambda c: c["last_used"], reverse=True)
    return conversations


def get_display_messages(conversation_id, browser_id):
    """
    The visible message bubbles for one conversation (role + text only,
    no tool-call internals) -- used to repopulate the chat window when
    switching to/reopening a conversation.
    """
    all_data = _load_all()
    entry = all_data.get(conversation_id)

    if entry is None or entry.get("browser_id") != browser_id:
        return None

    return entry.get("display_messages", [])


def delete_conversation(conversation_id, browser_id):
    all_data = _load_all()
    entry = all_data.get(conversation_id)

    if entry is None or entry.get("browser_id") != browser_id:
        return False

    del all_data[conversation_id]
    _save_all()
    return True


def _get_entry(conversation_id):
    all_data = _load_all()
    return all_data.get(conversation_id)


def _get_sdk_history(conversation_id):
    entry = _get_entry(conversation_id)

    if entry is None:
        return None

    try:
        return [types.Content.model_validate(item) for item in entry["history"]]
    except Exception:
        logger.exception("Stored history for conversation '%s' failed to deserialize -- starting fresh", conversation_id)
        return None


def _save_conversation(conversation_id, browser_id, title, sdk_history, display_messages):
    all_data = _load_all()

    all_data[conversation_id] = {
        "browser_id": browser_id,
        "title": title,
        "history": [content.model_dump(mode="json") for content in sdk_history],
        "display_messages": display_messages,
        "last_used": time.time()
    }

    _save_all()


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


def chat(message, browser_id, conversation_id=None):
    """
    Returns (response_text, conversation_id, title) -- conversation_id is
    generated fresh if this is a new conversation, so the caller can hand
    it back to the frontend to remember for subsequent messages in the
    same thread.
    """

    client = _get_client()

    is_new_conversation = conversation_id is None

    if is_new_conversation:
        conversation_id = str(uuid.uuid4())
        sdk_history = None
        display_messages = []
        title = _make_title(message)
    else:
        sdk_history = _get_sdk_history(conversation_id)
        entry = _get_entry(conversation_id)
        display_messages = (entry or {}).get("display_messages", [])
        title = (entry or {}).get("title") or _make_title(message)
        if sdk_history is None:
            is_new_conversation = True  # couldn't restore -- treat as fresh

    create_kwargs = dict(
        model=MODEL,
        config=types.GenerateContentConfig(tools=_build_tools())
    )

    if sdk_history:
        create_kwargs["history"] = sdk_history

    chat_session = client.chats.create(**create_kwargs)

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

    final_text = response.text or "I wasn't able to fully answer that -- could you try rephrasing?"

    display_messages = display_messages + [
        {"role": "user", "text": message},
        {"role": "ai", "text": final_text}
    ]

    _save_conversation(
        conversation_id,
        browser_id,
        title,
        chat_session.get_history(),
        display_messages
    )

    return final_text, conversation_id, title
