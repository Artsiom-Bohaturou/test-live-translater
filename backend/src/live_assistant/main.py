"""Command-line entrypoint for the backend."""

from __future__ import annotations

from aiohttp import web

from .config import settings
from .server import create_app


def main() -> None:
    web.run_app(create_app(settings), host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
