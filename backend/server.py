from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.tracker import get_latest_update
from backend.storage import load_comparisons

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

    @app.get("/arizona")
    def arizona():
        return FileResponse(STATIC / "arizona.html")


# API endpoints
@app.get("/latest")
def latest(race: str = "co_governor_primary"):
    return get_latest_update(race)


@app.get("/history")
def history(race: str = "co_governor_primary"):
    return load_comparisons(race)
