"""aiohttp application for health checks and WebSocket streaming."""

from __future__ import annotations

import json

from aiohttp import WSMsgType, web

from .config import Settings, settings
from .sessions import ClientSession


async def health(_request: web.Request) -> web.Response:
    return web.json_response({"ok": True})


async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse(heartbeat=30)
    await ws.prepare(request)
    client = ClientSession(ws, request.app["settings"])
    try:
        async for message in ws:
            if message.type == WSMsgType.TEXT:
                try:
                    await client.handle_message(json.loads(message.data))
                except json.JSONDecodeError:
                    await ws.send_json({"type": "error", "message": "Invalid JSON message"})
            elif message.type == WSMsgType.ERROR:
                break
    finally:
        await client.close()
    return ws


def create_app(app_settings: Settings = settings) -> web.Application:
    app = web.Application()
    app["settings"] = app_settings
    app.router.add_get("/api/health", health)
    app.router.add_get("/ws", websocket_handler)
    return app
