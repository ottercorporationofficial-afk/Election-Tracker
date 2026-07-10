from fastapi import FastAPI
from starlette.responses import FileResponse, RedirectResponse

from tracker import get_latest_update
from fastapi.staticfiles import StaticFiles
from storage import load_comparisons


app = FastAPI()

app.mount("/static", StaticFiles(directory="static"),name="static")



@app.get("/")
def home():
    # No hub/landing page yet — for now this just points at the one
    # race that exists. When more races are added, this is the spot
    # to swap in a real landing page linking out to each of them.
    return RedirectResponse("/colorado")


@app.get("/colorado")
def colorado():
    return FileResponse("static/colorado.html")


@app.get("/latest")
def latest():
    return get_latest_update(84287)


@app.get("/history")
def history():
    return load_comparisons()