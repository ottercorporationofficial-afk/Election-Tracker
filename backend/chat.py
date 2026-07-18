"""
Chat orchestration
------------------
Runs the actual tool-calling loop against Gemini's Interactions API
(google-genai SDK). Handles the model calling zero, one, or multiple
tools -- including calling a tool, getting a result, then calling
another tool based on that (compositional calling) -- before producing
a final natural-language answer.
"""

import os
import json
import logging
import time

from google import genai

from backend import ai_tools
from backend.registry import RACES

logger = logging.getLogger(__name__)

MODEL = "gemini-3.1-flash-lite"
MAX_TOOL_TURNS = 6  # hard cap so a confused model can't loop forever

# In-memory conversation history, keyed by a conversation_id the frontend
# generates once per tab/session and sends with every request. This is
# what makes follow-ups like "what about by margin" resolve correctly --
# without it, every message is a totally isolated request with no idea
# what "it" refers to.
#
# In-memory means history is lost on server restart -- fine for a chat
# widget (not mission-critical state), but if you want it to survive
# restarts/scale across multiple server processes, swap this for a real
# store (redis, a database table) using the same get/append interface.
_conversations = {}
_CONVERSATION_TTL_SECONDS = 60 * 60 * 2  # drop conversations after 2hrs idle


def _get_history(conversation_id):
    entry = _conversations.get(conversation_id)

    if entry is None:
        return []

    if time.time() - entry["last_used"] > _CONVERSATION_TTL_SECONDS:
        del _conversations[conversation_id]
        return []

    return entry["history"]


def _save_history(conversation_id, history):
    _conversations[conversation_id] = {
        "history": history,
        "last_used": time.time()
    }


def _build_system_context():
    # Race list embedded directly here (not left for the model to
    # discover via the list_races tool) so a typical question only needs
    # ONE tool call (get_race_summary/get_county_result), not two
    # (list_races, then the real one) -- saves a full network round-trip
    # on the most common category of question. list_races is still
    # available as a tool for anything unusual (e.g. "what races exist").
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
        "Never show complex math or explain how you got to a answer in a question. do not give an mathematical explanation unless the user asks"
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

    history = _get_history(conversation_id) if conversation_id else []

    # System context only needs to go in ONCE per conversation -- it's
    # part of history from then on, the model doesn't need it repeated
    # every turn. This is also what makes race identity actually stick
    # across follow-ups instead of resetting each message.
    user_text = f"{_build_system_context()}\n\nUser: {message}" if not history else message

    history.append({
        "type": "user_input",
        "content": [{"type": "text", "text": user_text}]
    })

    interaction = client.interactions.create(
        model=MODEL,
        store=False,
        input=history,
        tools=ai_tools.TOOLS
    )

    for step in interaction.steps:
        history.append(step.model_dump())

    for _ in range(MAX_TOOL_TURNS):

        function_call_steps = [s for s in interaction.steps if s.type == "function_call"]

        if not function_call_steps:
            break

        for step in function_call_steps:

            fn = ai_tools.TOOL_FUNCTIONS.get(step.name)

            if fn is None:
                result = {"error": f"Unknown tool '{step.name}'"}
            else:
                try:
                    result = fn(**step.arguments)
                except Exception as e:
                    logger.exception("Tool '%s' raised an exception", step.name)
                    result = {"error": str(e)}

            history.append({
                "type": "function_result",
                "name": step.name,
                "call_id": step.id,
                "result": [{"type": "text", "text": json.dumps(result)}]
            })

        interaction = client.interactions.create(
            model=MODEL,
            store=False,
            input=history,
            tools=ai_tools.TOOLS
        )

        for step in interaction.steps:
            history.append(step.model_dump())

    if conversation_id:
        _save_history(conversation_id, history)

    return interaction.output_text or "I wasn't able to fully answer that -- could you try rephrasing?"
