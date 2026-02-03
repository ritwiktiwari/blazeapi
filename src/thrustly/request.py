"""ASGI request wrapper."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs

if TYPE_CHECKING:
    from thrustly._types import Receive, Scope


class Request:
    """Thin wrapper around an ASGI *scope* and *receive* callable."""

    __slots__ = ("_body", "_receive", "_scope", "path_params")

    def __init__(
        self,
        scope: Scope,
        receive: Receive,
        path_params: dict[str, Any] | None = None,
    ) -> None:
        self._scope = scope
        self._receive = receive
        self._body: bytes | None = None
        self.path_params: dict[str, Any] = path_params or {}

    @property
    def method(self) -> str:
        return self._scope["method"]

    @property
    def path(self) -> str:
        return self._scope["path"]

    @property
    def query_string(self) -> bytes:
        return self._scope.get("query_string", b"")

    @property
    def query_params(self) -> dict[str, list[str]]:
        return parse_qs(self.query_string.decode("latin-1"))

    @property
    def headers(self) -> dict[str, str]:
        """Headers as a lowercase-keyed dict (last value wins for dupes)."""
        return {k.decode("latin-1"): v.decode("latin-1") for k, v in self._scope.get("headers", [])}

    async def body(self) -> bytes:
        """Read and cache the full request body."""
        if self._body is not None:
            return self._body
        chunks: list[bytes] = []
        while True:
            message = await self._receive()
            chunk = message.get("body", b"")
            if chunk:
                chunks.append(chunk)
            if not message.get("more_body", False):
                break
        self._body = b"".join(chunks)
        return self._body

    async def json(self) -> Any:
        """Parse the request body as JSON."""
        return json.loads(await self.body())
