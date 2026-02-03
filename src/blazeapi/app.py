"""BlazeAPI ASGI application."""

import asyncio
import inspect
import sys
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any, get_type_hints

from blazeapi._types import ASGIApp, Receive, Scope, Send
from blazeapi.request import Request
from blazeapi.response import JSONResponse, Response
from blazeapi.routing import Router


class _HandlerMeta:
    """Pre-computed handler metadata, built once at registration time."""

    __slots__ = ("handler", "is_coroutine", "param_names", "wants_request")

    def __init__(self, handler: Callable[..., Any]) -> None:
        self.handler = handler
        self.is_coroutine = asyncio.iscoroutinefunction(handler)
        sig = inspect.signature(handler)
        self.wants_request = "request" in sig.parameters
        self.param_names = frozenset(sig.parameters.keys()) - {"request"}


class BlazeAPI:
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
        self._handler_meta: dict[Callable[..., Any], _HandlerMeta] = {}
        self._app: ASGIApp | None = None

    # ------------------------------------------------------------------
    # Route registration
    # ------------------------------------------------------------------

    def _route(self, method: str, path: str) -> Callable[..., Any]:
        def decorator(handler: Callable[..., Any]) -> Callable[..., Any]:
            if self.strict:
                _validate_return_type(handler)
            self.router.add_route(method, path, handler)
            self._handler_meta[handler] = _HandlerMeta(handler)
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
        self._app = None  # invalidate cached chain

    def _build_app(self) -> ASGIApp:
        app: ASGIApp = self._handle
        for mw in reversed(self._middleware):
            app = mw(app)
        return app

    # ------------------------------------------------------------------
    # ASGI interface
    # ------------------------------------------------------------------

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            await _handle_lifespan(receive, send)
            return

        if self._app is None:
            self._app = self._build_app()
        await self._app(scope, receive, send)

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
        meta = self._handler_meta[handler]
        kwargs: dict[str, Any] = {name: path_params[name] for name in meta.param_names if name in path_params}
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
        *,
        dev: bool = False,
        reload: bool | None = None,
        workers: int = 1,
        log_level: str = "info",
        **granian_kwargs: Any,
    ) -> None:
        """Start the app with Granian.

        Parameters
        ----------
        dev:
            When ``True``, enables reload, debug logging, and access logs.
        reload:
            Auto-reload on code changes.  ``None`` follows *dev*.
        workers:
            Number of worker processes.
        log_level:
            Granian log level.
        """
        from blazeapi._server import serve

        target = _resolve_target(self)
        serve(
            target,
            host=host,
            port=port,
            dev=dev,
            reload=reload,
            workers=workers,
            log_level=log_level,
            granian_kwargs=granian_kwargs or None,
        )


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _resolve_target(app: BlazeAPI) -> str:
    """Derive a ``"module:var"`` string for the given app instance.

    Searches ``__main__`` for a module-level variable whose value *is* the
    app.  Falls back to the caller's ``__file__`` stem when running as a
    script (``python main.py``) so Granian workers can import it.
    """
    main = sys.modules.get("__main__")
    if main is None:
        raise RuntimeError(
            "Cannot auto-detect Granian target: __main__ module not found. "
            "Pass an explicit target string, e.g. app.run(target='myapp:app')."
        )

    var_name: str | None = None
    for name, val in vars(main).items():
        if val is app:
            var_name = name
            break

    if var_name is None:
        raise RuntimeError(
            "Cannot auto-detect Granian target: no module-level variable in "
            "__main__ references this BlazeAPI instance. "
            "Pass an explicit target string, e.g. app.run(target='myapp:app')."
        )

    spec = getattr(main, "__spec__", None)
    module_name: str | None = spec.name if spec else None
    if not module_name:
        # Running as a script — use the filename stem so granian can import it.
        main_file = getattr(main, "__file__", None)
        module_name = Path(main_file).stem if main_file else None

    return f"{module_name}:{var_name}"


async def _handle_lifespan(receive: Receive, send: Send) -> None:
    """Minimal lifespan responder — accept startup/shutdown with no-ops."""
    while True:
        message = await receive()
        if message["type"] == "lifespan.startup":
            await send({"type": "lifespan.startup.complete"})
        elif message["type"] == "lifespan.shutdown":
            await send({"type": "lifespan.shutdown.complete"})
            return


def _validate_return_type(handler: Callable[..., Any]) -> None:
    hints = get_type_hints(handler)
    name = getattr(handler, "__name__", repr(handler))
    ret = hints.get("return")
    if ret is None:
        msg = f"Handler {name!r} must have a return type annotation in strict mode"
        raise TypeError(msg)
    if not (isinstance(ret, type) and issubclass(ret, Response)):
        msg = f"Handler {name!r} return type must be Response or a subclass, got {ret!r}"
        raise TypeError(msg)


async def _send_response(response: Any, send: Send) -> None:
    if isinstance(response, Response):
        await response.send(send)
    elif isinstance(response, dict | list):
        await JSONResponse(response).send(send)
    else:
        await Response(str(response).encode("utf-8")).send(send)
