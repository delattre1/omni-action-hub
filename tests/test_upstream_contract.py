"""Execute the two media resolver functions from the pinned upstream source.

This checks actual quoted-part behavior without opening a socket or importing
the whole Hermes runtime. It does not claim a container boot or live iMessage test.
"""
import ast
import asyncio
import logging
from pathlib import Path
from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def upstream():
    path = Path(__file__).resolve().parents[1] / "work/pinned-transport.py"
    if not path.exists():
        pytest.fail("Run python scripts/fetch-transport.py")
    tree = ast.parse(path.read_text())
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
             and n.name in ("_reply_parts", "_resolve_parts")]
    assert len(nodes) == 2
    scope = {"asyncio": asyncio, "log": logging.getLogger("test"),
             "_fetch_attachment": AsyncMock(side_effect=lambda item, kind: "/cache/" + item["uid"])}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), scope)
    return scope


async def test_quoted_image_selected_by_provider_index(upstream):
    a = {"uid": "a", "url": "/signed/a", "content_type": "image/png", "part_index": 4}
    b = {"uid": "b", "url": "/signed/b", "content_type": "image/png", "part_index": 8}
    msg = {"body": "Registra esse bug", "attachments": [],
           "reply_to": {"part_index": 8, "message": {"attachments": [a, b]}}}
    paths, kinds, text = await upstream["_resolve_parts"](msg)
    assert paths == ["/cache/b"]
    assert kinds == ["image/png"]
    assert text == "Registra esse bug"


async def test_unresolved_quote_keeps_all_images_for_clarification(upstream):
    parts = [{"uid": str(i), "url": f"/signed/{i}", "content_type": "image/png", "part_index": i} for i in (2, 3)]
    msg = {"body": "Registra esse bug", "attachments": [],
           "reply_to": {"part_index": None, "message": {"attachments": parts}}}
    paths, _, _ = await upstream["_resolve_parts"](msg)
    assert len(paths) == 2


async def test_unavailable_attachment_is_not_silently_dropped(upstream):
    msg = {"body": "Registra esse bug", "attachments": [
        {"uid": "missing", "url": None, "content_type": "image/png"}]}
    paths, kinds, text = await upstream["_resolve_parts"](msg)
    assert not paths
    assert "[attachment:" in text
