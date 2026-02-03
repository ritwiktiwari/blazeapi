"""Thrustly ASGI application."""

from __future__ import annotations

import asyncio
import inspect
from typing import TYPE_CHECKING, Any, get_type_hints

from thrustly.request import Request
from thrustly.response import JSONResponse, Response
from thrustly.routing import Router

if TYPE_CHECKING:
    from collections.abc import Callable

    from thrustly._types import ASGIApp, Receive, Scope, Send


class _HandlerMeta:
    """Pre-computed handler metadata, built once at registration time."""

    __slots__ = ("handler", "is_coroutine", "param_names", "wants_request")

    def __init__(self, handler: Callable[..., Any]) -> None:
        self.handler = handler
        self.is_coroutine = asyncio.iscoroutinefunction(handler)
        sig = inspect.signature(handler)
        self.wants_request = "request" in sig.parameters
        self.param_names = frozenset(sig.parameters.keys()) - {"request"}


class Thrustly:
    """ASGI 3.0 web application.

    Parameters
    ----------
    strict:
        When ``True``, handler return-type annotations are validated at
        registration time — they must be :class:`Response` or a subclass.
    debug:
        When ``True``, 500 responses include the full traceback.
    """

    def __init__(self, *, strict: bool = False, debug: bool = False) -> None:
        self.router = Router()
        self.strict = strict
        self.debug = debug
        self._middleware: list[Callable[[ASGIApp], ASGIApp]] = []
        self._handler_meta: dict[int, _HandlerMeta] = {}

    # ------------------------------------------------------------------
    # Route registration
    # ------------------------------------------------------------------

    def _route(self, method: str, path: str) -> Callable[..., Any]:
        def decorator(handler: Callable[..., Any]) -> Callable[..., Any]:
            if self.strict:
                _validate_return_type(handler)
            self.router.add_route(method, path, handler)
            self._handler_meta[id(handler)] = _HandlerMeta(handler)
            return handler

        return decorator

    def get(self, path: str) -> Callable[..., Any]:
        return self._route("GET", path)

    def post(self, path: str) -> Callable[..., Any]:
        return self._route("POST", path)

    def put(self, path: str) -> Callable[..., Any]:
        return self._route("PUT", path)

    def delete(self, path: str) -> Callable[..., Any]:
        return self._route("DELETE", path)

    def patch(self, path: str) -> Callable[..., Any]:
        return self._route("PATCH", path)

    def options(self, path: str) -> Callable[..., Any]:
        return self._route("OPTIONS", path)

    def head(self, path: str) -> Callable[..., Any]:
        return self._route("HEAD", path)

    # ------------------------------------------------------------------
    # Middleware
    # ------------------------------------------------------------------

    def add_middleware(self, middleware: Callable[[ASGIApp], ASGIApp]) -> None:
        """Register a middleware that wraps the ASGI app.

        Called as ``middleware(app)`` and must return an ASGI callable.
        """
        self._middleware.append(middleware)

    # ------------------------------------------------------------------
    # ASGI interface
    # ------------------------------------------------------------------

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        app: ASGIApp = self._handle
        for mw in reversed(self._middleware):
            app = mw(app)
        await app(scope, receive, send)

    async def _handle(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return

        result = self.router.match(scope["method"], scope["path"])
        if result is None:
            await JSONResponse({"detail": "Not Found"}, status_code=404).send(send)
            return

        route, path_params = result
        request = Request(scope, receive, path_params)

        try:
            response = await self._invoke(route.handler, request, path_params)
        except Exception:
            body: dict[str, Any] = {"detail": "Internal Server Error"}
            if self.debug:
                import traceback

                body["traceback"] = traceback.format_exc()
            await JSONResponse(body, status_code=500).send(send)
            return

        await _send_response(response, send)

    async def _invoke(
        self,
        handler: Callable[..., Any],
        request: Request,
        path_params: dict[str, Any],
    ) -> Any:
        meta = self._handler_meta[id(handler)]
        kwargs: dict[str, Any] = {
            name: path_params[name] for name in meta.param_names if name in path_params
        }
        if meta.wants_request:
            kwargs["request"] = request

        if meta.is_coroutine:
            return await handler(**kwargs)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: handler(**kwargs))

    # ------------------------------------------------------------------
    # Granian convenience
    # ------------------------------------------------------------------

    def run(
        self,
        host: str = "127.0.0.1",
        port: int = 8000,
        **granian_kwargs: Any,
    ) -> None:
        """Start the app with Granian (convenience for development)."""
        from granian import Granian

        server = Granian(
            target=self,
            address=host,
            port=port,
            interface="asgi",
            **granian_kwargs,
        )
        server.serve()


# ------------------------------------------------------------------
# Module-level helpers (no reason to be methods)
# ------------------------------------------------------------------


def _validate_return_type(handler: Callable[..., Any]) -> None:
    hints = get_type_hints(handler)
    ret = hints.get("return")
    if ret is None:
        msg = (
            f"Handler {handler.__name__!r} must have a return type "
            f"annotation in strict mode"
        )
        raise TypeError(msg)
    if not (isinstance(ret, type) and issubclass(ret, Response)):
        msg = (
            f"Handler {handler.__name__!r} return type must be "
            f"Response or a subclass, got {ret!r}"
        )
        raise TypeError(msg)


async def _send_response(response: Any, send: Send) -> None:
    if isinstance(response, Response):
        await response.send(send)
    elif isinstance(response, dict | list):
        await JSONResponse(response).send(send)
    else:
        await Response(str(response).encode("utf-8")).send(send)
