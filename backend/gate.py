"""Compatibility entry point: uvicorn gate:app now runs Django."""
from config.asgi import application as app
