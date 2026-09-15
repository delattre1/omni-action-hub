"""Bounded signed Plow downloads into the gateway user's private cache."""
import asyncio
import logging
import os
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from .models import Problem

log = logging.getLogger("omni")


def signed_url(base, value):
    if base not in ("https://api.plow.co", "https://api.plow.dev"):
        raise Problem("media_origin", "Origem de anexo não permitida.")
    if not isinstance(value, str) or any(ord(c) < 32 for c in value) or "\\" in value:
        raise Problem("media_url", "Endereço de anexo inválido.")
    u = urlsplit(value)
    if u.scheme or u.netloc or not value.startswith("/v1/") or value.startswith("//"):
        raise Problem("media_origin", "Origem de anexo não permitida.")
    return base + value


class MediaResolver:
    def __init__(self, base, directory, client, limit=10 * 1024 * 1024):
        self.base, self.directory, self.client, self.limit = base, Path(directory), client, limit
        self.slots = asyncio.Semaphore(2)

    async def fetch(self, item):
        url = signed_url(self.base, item.get("url"))
        size = item.get("size_bytes")
        if isinstance(size, int) and size > self.limit:
            raise Problem("media_size", "A imagem ultrapassa 10 MB.")
        async with self.slots:
            for attempt in range(3):
                path = None
                try:
                    async with self.client.stream("GET", url, headers={}, follow_redirects=False, timeout=20) as response:
                        if response.status_code in (408, 429) or response.status_code >= 500:
                            raise httpx.ReadError("retryable media status")
                        if not response.is_success:
                            raise Problem("media_http", "Anexo indisponível no Plow.")
                        length = response.headers.get("content-length")
                        if length and int(length) > self.limit:
                            raise Problem("media_size", "A imagem ultrapassa 10 MB.")
                        fd, name = tempfile.mkstemp(prefix="media-", dir=self.directory)
                        path = Path(name)
                        total = 0
                        with os.fdopen(fd, "wb") as output:
                            async for chunk in response.aiter_bytes(chunk_size=65536):
                                total += len(chunk)
                                if total > self.limit:
                                    raise Problem("media_size", "A imagem ultrapassa 10 MB.")
                                output.write(chunk)
                            output.flush()
                            os.fsync(output.fileno())
                        log.info("media_downloaded bytes=%d attempt=%d", total, attempt + 1)
                        return str(path)
                except (httpx.HTTPError, OSError, Problem, ValueError, asyncio.CancelledError) as exc:
                    if path:
                        path.unlink(missing_ok=True)
                    if isinstance(exc, asyncio.CancelledError):
                        raise
                    if not isinstance(exc, (httpx.TimeoutException, httpx.NetworkError)) or attempt == 2:
                        raise
                    log.warning("media_retry attempt=%d", attempt + 1)
                    await asyncio.sleep(2 ** attempt)
        raise Problem("media_http", "Anexo indisponível no Plow.")

    async def resolve(self, msg):
        body = msg.get("body") or ""
        attachments = msg.get("attachments") or []
        reply = msg.get("reply_to") or {}
        if not attachments and reply:
            attachments = (reply.get("message") or {}).get("attachments") or []
            index = reply.get("part_index")
            selected = [a for a in attachments if index is not None and a.get("part_index") == index]
            if len(selected) == 1:
                attachments = selected
        if not attachments:
            return [], [], body
        # Apple's object-replacement character is a media placeholder, not speech.
        body = body.replace("\ufffc", "").strip()
        if len(attachments) != 1:
            return [], [], body + "\n[attachment: multiple images]"
        item = attachments[0]
        kind = (item.get("content_type") or "").split(";")[0].strip().lower()
        if kind not in ("image/png", "image/jpeg", "image/webp"):
            return [], [], body + "\n[attachment: unsupported media]"
        try:
            async with asyncio.timeout(60):
                path = await self.fetch(item)
            return [path], [kind], body
        except (httpx.HTTPError, OSError, Problem, ValueError, TimeoutError) as exc:
            code = exc.code if isinstance(exc, Problem) else type(exc).__name__
            log.warning("media_unavailable code=%s", code)
            return [], [], body + "\n[attachment: image unavailable]"
