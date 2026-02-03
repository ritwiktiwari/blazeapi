"""ASGI response types."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

if TYPE_CHECKING:
    from blazeapi._types import Send


class Response:
    """Plain HTTP response."""

    __slots__ = ("body", "headers", "status_code")

    def __init__(
        self,
        body: bytes = b"",
        *,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        content_type: str = "text/plain; charset=utf-8",
    ) -> None:
        self.status_code = status_code
        self.body = body
        self.headers = headers or {}
        self.headers.setdefault("content-type", content_type)
        self.headers.setdefault("content-length", str(len(body)))

    async def send(self, _send: Send) -> None:
        """Write this response over the ASGI *send* callable."""
        await _send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": [(k.encode("latin-1"), v.encode("latin-1")) for k, v in self.headers.items()],
            }
        )
        await _send({"type": "http.response.body", "body": self.body})


class JSONResponse(Response):
    """JSON response that serializes dicts, lists, and Pydantic models."""

    def __init__(
        self,
        data: Any = None,
        *,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        if isinstance(data, BaseModel):
            raw = data.model_dump_json()
            body = raw if isinstance(raw, bytes) else raw.encode("utf-8")
        else:
            body = json.dumps(data, default=str).encode("utf-8")

        super().__init__(
            body=body,
            status_code=status_code,
            headers=headers,
            content_type="application/json",
        )
