from fastapi import FastAPI
from starlette.responses import FileResponse

from tracker import get_latest_update
from fastapi.staticfiles import StaticFiles
app = FastAPI()

app.mount("/static", StaticFiles(directory="static"),name="static")



@app.get("/")
def home():
    return FileResponse("static/index.html")
@app.get("/latest")
def latest():
    return get_latest_update(84287)