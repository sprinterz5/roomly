from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .routers import admin, auth, bot_admin, calendar, clubs, rooms

app = FastAPI(title="Roomly API")
BASE_DIR = Path(__file__).resolve().parents[2]

app.mount("/assets", StaticFiles(directory=BASE_DIR / "assets"), name="assets")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(calendar.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(bot_admin.router, prefix="/api")
app.include_router(clubs.router, prefix="/api")
app.include_router(rooms.router, prefix="/api")


@app.get("/")
def root_index():
    return FileResponse(BASE_DIR / "index.html")


@app.get("/style.css")
def root_styles():
    return FileResponse(BASE_DIR / "style.css")


@app.get("/script.js")
def root_script():
    return FileResponse(BASE_DIR / "script.js")
