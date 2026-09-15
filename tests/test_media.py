import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest

from omni.media import MediaResolver, signed_url
from omni.models import Problem


def msg(**overrides):
    result = {"body": "", "attachments": [{"url": "/v1/media/test?signature=private", "content_type": "image/png", "size_bytes": 12}]}
    result.update(overrides)
    return result


async def test_real_stream_to_private_cache(store, picture):
    def handler(req):
        assert not any(h in req.headers for h in ("authorization", "x-goog-api-key", "cookie"))
        return httpx.Response(200, content=picture.read_bytes())
    store.check_downloads()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        paths, types, body = await MediaResolver("https://api.plow.co", store.downloads, client).resolve(msg(body="\ufffc"))
    p = Path(paths[0])
    assert p.parent == store.downloads
    assert p.stat().st_mode & 0o777 == 0o600
    assert p.read_bytes() == picture.read_bytes()
    assert types == ["image/png"] and body == ""


@pytest.mark.parametrize("url", ["https://evil.example/p", "//evil.example/p", "/v1/hello\r\nsecret", "file:///etc/passwd", "/other", "/v1/\\evil"])
def test_media_origin_restriction(url):
    with pytest.raises(Problem):
        signed_url("https://api.plow.co", url)


@pytest.mark.parametrize("status", [302, 401, 403, 404])
async def test_reject_redirect_and_permanent_errors(store, status, caplog):
    handler = AsyncMock(return_value=httpx.Response(status, headers={"Location": "https://evil.example/secret"}))
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        paths, _, text = await MediaResolver("https://api.plow.co", store.downloads, client).resolve(msg())
    assert not paths and "[attachment:" in text
    assert handler.await_count == 1
    assert "signature" not in caplog.text and "evil.example" not in caplog.text


@pytest.mark.parametrize("header", [True, False])
async def test_oversized_stream_cleaned(store, header):
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b"x" * 120
    headers = {"Content-Length": "120"} if header else {}
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, headers=headers, stream=Stream()))) as client:
        paths, _, _ = await MediaResolver("https://api.plow.co", store.downloads, client, limit=100).resolve(msg())
    assert not paths
    assert not list(store.downloads.iterdir())


async def test_download_network_failure_retries_and_cleans(store, picture, monkeypatch):
    sleep = AsyncMock()
    monkeypatch.setattr(asyncio, "sleep", sleep)
    calls = []
    def handler(req):
        calls.append(req)
        if len(calls) < 3:
            raise httpx.ConnectError("signed-secret")
        return httpx.Response(200, content=picture.read_bytes())
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        paths, _, _ = await MediaResolver("https://api.plow.co", store.downloads, client).resolve(msg())
    assert len(paths) == 1 and len(calls) == 3
    assert [c.args[0] for c in sleep.call_args_list] == [1, 2]


async def test_multiple_media_not_downloaded(store):
    handler = AsyncMock()
    value = msg()
    value["attachments"] *= 2
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        paths, _, text = await MediaResolver("https://api.plow.co", store.downloads, client).resolve(value)
    assert not paths and "multiple" in text
    handler.assert_not_called()


async def test_native_reply_part_selection(store, picture):
    selected = []
    def handler(req):
        selected.append(req.url.path)
        return httpx.Response(200, content=picture.read_bytes())
    value = msg(body="Registra esse bug", attachments=[], reply_to={"part_index": 8, "message": {"attachments": [
        {"part_index": 4, "url": "/v1/media/a", "content_type": "image/png"},
        {"part_index": 8, "url": "/v1/media/b", "content_type": "image/png"}]}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        paths, _, text = await MediaResolver("https://api.plow.co", store.downloads, client).resolve(value)
    assert len(paths) == 1 and selected == ["/v1/media/b"]
    assert text == "Registra esse bug"


async def test_interrupted_body_removes_partial_file(store, monkeypatch):
    class Broken(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b"x" * 65536
            raise httpx.ReadError("private-signed-url")
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, stream=Broken()))) as client:
        paths, _, _ = await MediaResolver("https://api.plow.co", store.downloads, client).resolve(msg())
    assert not paths
    assert not list(store.downloads.iterdir())


def test_store_rejects_symlink_cache(tmp_path):
    from omni.store import Store
    root = tmp_path / "state"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "downloads").symlink_to(outside)
    with pytest.raises(ValueError):
        Store(root)
    assert not list(outside.iterdir())
