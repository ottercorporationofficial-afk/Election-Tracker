from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse, RedirectResponse

from tracker import get_latest_update
from storage import load_comparisons

app = FastAPI()

# Election-tracker/
ROOT = Path(__file__).resolve().parent.parent

# Election-tracker/frontend/static
STATIC = ROOT / "frontend" / "static"

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


@app.get("/latest")
def latest():
    return get_latest_update(84287)


@app.get("/history")
def history():
    return load_comparisons()