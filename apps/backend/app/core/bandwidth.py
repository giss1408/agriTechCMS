"""Low-bandwidth helpers: ETag / 304 on GET JSON, and gzip-compressed request bodies.

Response compression itself is Starlette's GZipMiddleware (see main.py). Order matters: the ETag is
computed on the uncompressed body, so GZip must wrap this middleware (be added after it).
"""

import gzip
import hashlib
import io

from starlette.types import ASGIApp, Message, Receive, Scope, Send

MAX_REQUEST_BODY = 10 * 1024 * 1024  # decompressed; protects against gzip bombs


class ETagMiddleware:
    """Adds a weak ETag to successful GET JSON responses and answers 304 when the client already has it.

    Polling screens (dashboard, pending counter, payment status) then cost a few hundred bytes of headers
    instead of the full body when nothing changed.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] != "GET":
            await self.app(scope, receive, send)
            return
        if_none_match = dict(scope["headers"]).get(b"if-none-match", b"").decode()

        start: Message | None = None
        chunks: list[bytes] = []
        passthrough = False

        async def capture(message: Message) -> None:
            nonlocal start, passthrough
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                cacheable = message["status"] == 200 and headers.get(b"content-type", b"").startswith(b"application/json")
                if not cacheable:
                    passthrough = True
                    await send(message)
                    return
                start = message
                return
            if passthrough:
                await send(message)
                return
            chunks.append(message.get("body", b""))
            if message.get("more_body"):
                return
            body = b"".join(chunks)
            etag = 'W/"' + hashlib.blake2b(body, digest_size=12).hexdigest() + '"'
            headers = [(k, v) for k, v in start["headers"] if k.lower() != b"content-length"]
            headers += [(b"etag", etag.encode()), (b"cache-control", b"private, no-cache")]
            if etag in [t.strip() for t in if_none_match.split(",")]:
                await send({"type": "http.response.start", "status": 304, "headers": [(b"etag", etag.encode())]})
                await send({"type": "http.response.body", "body": b""})
                return
            headers.append((b"content-length", str(len(body)).encode()))
            await send({**start, "headers": headers})
            await send({"type": "http.response.body", "body": body})

        await self.app(scope, receive, capture)


class GzipRequestMiddleware:
    """Accepts `Content-Encoding: gzip` request bodies. The collector app compresses its sync batches:
    a batch of 25 collections shrinks from ~7.7 KB to ~1.3 KB."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope["headers"])
        if headers.get(b"content-encoding", b"").lower() != b"gzip":
            await self.app(scope, receive, send)
            return

        compressed = b""
        while True:
            message = await receive()
            compressed += message.get("body", b"")
            if not message.get("more_body"):
                break
        try:
            body = gzip.GzipFile(fileobj=io.BytesIO(compressed)).read(MAX_REQUEST_BODY + 1)
        except (OSError, EOFError):
            await _plain_error(send, 400, b"Invalid gzip body")
            return
        if len(body) > MAX_REQUEST_BODY:
            await _plain_error(send, 413, b"Request body too large")
            return

        new_headers = [(k, v) for k, v in scope["headers"] if k not in (b"content-encoding", b"content-length")]
        new_headers.append((b"content-length", str(len(body)).encode()))
        sent = False

        async def replay() -> Message:
            nonlocal sent
            if sent:
                return {"type": "http.disconnect"}
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}

        await self.app({**scope, "headers": new_headers}, replay, send)


async def _plain_error(send: Send, status: int, text: bytes) -> None:
    await send({"type": "http.response.start", "status": status, "headers": [(b"content-type", b"text/plain")]})
    await send({"type": "http.response.body", "body": text})
