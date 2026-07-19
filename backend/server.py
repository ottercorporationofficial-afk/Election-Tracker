from pathlib import Path
import os
import secrets
import logging

from dotenv import load_dotenv
load_dotenv()  # must run before any os.environ.get() calls below

from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.responses import FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.tracker import get_latest_update
from backend.storage import load_comparisons, load_snapshot
from backend import admin_store
from backend.registry import RACES

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://otterelections.com",
        "https://www.otterelections.com",
        "https://election-tracker.jper19223.workers.dev",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_origin_regex=r"https://([a-zA-Z0-9-]+\.)?otterelections\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "frontend" / "static"

# Serve frontend for local development
if STATIC.exists():

    # Match the paths used by Cloudflare
    app.mount("/css", StaticFiles(directory=STATIC / "css"), name="css")
    app.mount("/js", StaticFiles(directory=STATIC / "js"), name="js")
    app.mount("/images", StaticFiles(directory=STATIC / "images"), name="images")
    app.mount("/data", StaticFiles(directory=STATIC / "data"), name="data")

    @app.get("/")
    def home():
        return RedirectResponse("/colorado")

    @app.get("/colorado")
    def colorado():
        return FileResponse(STATIC / "colorado.html")


    @app.get("/chat")
    def chat():
        return FileResponse(STATIC / "chat.html")

    @app.get("/colorado/governor-primary")
    def colorado_governor_primary():
        return FileResponse(STATIC / "colorado-governor-primary.html")

    @app.get("/arizona")
    def arizona():
        return FileResponse(STATIC / "arizona.html")

    @app.get("/arizona/governor-primary")
    def arizona_governor_primary():
        return FileResponse(STATIC / "arizona-governor-primary.html")


# API endpoints
@app.get("/latest")
def latest(race: str = "co_governor_primary"):
    return get_latest_update(race)


@app.get("/history")
def history(race: str = "co_governor_primary"):
    return load_comparisons(race)


# --------------------
# Chat
# --------------------

class ChatRequest(BaseModel):
    message: str
    browser_id: str
    conversation_id: str | None = None


@app.post("/chat")
def chat_endpoint(payload: ChatRequest):
    from backend import chat as chat_module

    try:
        response_text, conversation_id, title = chat_module.chat(
            payload.message,
            browser_id=payload.browser_id,
            conversation_id=payload.conversation_id
        )
    except Exception as e:
        logging.exception("Chat request failed")
        return {"response": f"Sorry, something went wrong: {e}"}

    return {"response": response_text, "conversation_id": conversation_id, "title": title}


@app.get("/chat/conversations")
def chat_list_conversations(browser_id: str):
    from backend import chat as chat_module
    return {"conversations": chat_module.list_conversations(browser_id)}


@app.get("/chat/conversations/{conversation_id}")
def chat_get_conversation(conversation_id: str, browser_id: str):
    from backend import chat as chat_module

    messages = chat_module.get_display_messages(conversation_id, browser_id)

    if messages is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {"messages": messages}


@app.delete("/chat/conversations/{conversation_id}")
def chat_delete_conversation(conversation_id: str, browser_id: str):
    from backend import chat as chat_module

    deleted = chat_module.delete_conversation(conversation_id, browser_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {"ok": True}


# --------------------
# Admin (password-protected)
# --------------------
# Set ADMIN_USERNAME / ADMIN_PASSWORD as real environment variables in
# Railway (or your local shell) before relying on this -- the fallbacks
# below are NOT safe to leave in place.

security = HTTPBasic()
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "changeme")


def require_admin(credentials: HTTPBasicCredentials = Depends(security)):

    correct_username = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"}
        )

    return True


@app.get("/admin")
def admin_page(_: bool = Depends(require_admin)):
    admin_html = ROOT / "frontend" / "admin.html"
    if admin_html.exists():
        return FileResponse(admin_html)
    return {"error": "admin.html not found -- place it at frontend/admin.html"}


@app.get("/admin/races")
def admin_list_races(_: bool = Depends(require_admin)):
    return {"races": list(RACES.keys())}


@app.get("/admin/races/{race_key}")
def admin_get_race(race_key: str, _: bool = Depends(require_admin)):

    if race_key not in RACES:
        raise HTTPException(status_code=404, detail=f"No such race: {race_key}")

    snapshot = load_snapshot(race_key) or {}

    return {
        "candidates": snapshot.get("candidates", []),
        "overrides": admin_store.get_overrides(race_key)
    }


@app.post("/admin/races/{race_key}/color")
def admin_set_color(race_key: str, name: str, color: str, _: bool = Depends(require_admin)):
    admin_store.set_candidate_color(race_key, name, color)
    return {"ok": True}


@app.delete("/admin/races/{race_key}/color")
def admin_clear_color(race_key: str, name: str, _: bool = Depends(require_admin)):
    admin_store.clear_candidate_color(race_key, name)
    return {"ok": True}


@app.post("/admin/races/{race_key}/alias")
def admin_set_alias(race_key: str, raw_name: str, display_name: str, _: bool = Depends(require_admin)):
    admin_store.set_candidate_alias(race_key, raw_name, display_name)
    return {"ok": True}


@app.delete("/admin/races/{race_key}/alias")
def admin_clear_alias(race_key: str, raw_name: str, _: bool = Depends(require_admin)):
    admin_store.clear_candidate_alias(race_key, raw_name)
    return {"ok": True}


@app.post("/admin/races/{race_key}/projected_winner")
def admin_set_projected_winner(race_key: str, winner: str = None, _: bool = Depends(require_admin)):
    admin_store.set_projected_winner(race_key, winner)
    return {"ok": True}
