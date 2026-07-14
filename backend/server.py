from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from tracker import get_latest_update
from storage import load_comparisons

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

# Local frontend directory
ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "frontend" / "static"
print("ROOT =", ROOT)
print("STATIC =", STATIC)
print("STATIC exists =", STATIC.exists())
print("style.css exists =", (STATIC / "css" / "style.css").exists())
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