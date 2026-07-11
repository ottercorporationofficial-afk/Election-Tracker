from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from tracker import get_latest_update
from storage import load_comparisons

app = FastAPI()

# Allow your Cloudflare Pages site to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://election-tracker.jper19223.workers.dev/",  # Replace with Cloudflare Pages URL
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Local frontend directory
ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "frontend" / "static"

# Only serve the frontend if it exists (local development)
if STATIC.exists():

    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    @app.get("/")
    def home():
        return RedirectResponse("/colorado")

    @app.get("/colorado")
    def colorado():
        return FileResponse(STATIC / "colorado.html")

    @app.get("/arizona")
    def arizona():
        return FileResponse(STATIC / "arizona.html")


# API endpoints (always available)
@app.get("/latest")
def latest():
    return get_latest_update(84287)


@app.get("/history")
def history():
    return load_comparisons()