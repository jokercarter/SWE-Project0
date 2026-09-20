"""Public-only entry point for Neon Rift Arena.

This intentionally excludes the private Workbench API, database and Codex
integration. It serves only the game files and multiplayer WebSocket rooms.
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .arena import router as arena_router

ROOT = Path(__file__).resolve().parents[1]
app = FastAPI(title='Neon Rift Arena')
app.include_router(arena_router)

@app.get('/')
def home():
    return RedirectResponse('/arena/')

@app.get('/health')
def health():
    return {'status': 'ok', 'service': 'neon-rift-arena'}

app.mount('/arena', StaticFiles(directory=ROOT / 'dist' / 'arena', html=True), name='arena')
