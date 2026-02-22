"""Minimal web UI for AI assistant."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


def _load_template(name: str) -> str:
    root = Path(__file__).resolve().parent / "templates" / name
    return root.read_text(encoding="utf-8")


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def web_index() -> HTMLResponse:
    """Serve simple single-page UI to chat with AI parser."""

    html = _load_template("index.html")
    return HTMLResponse(content=html)
