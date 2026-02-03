"""URL routing with typed path parameters."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

_PARAM_RE = re.compile(r"\{(\w+)(?::(\w+))?\}")

_PARAM_TYPES: dict[str, tuple[str, Callable[[str], Any]]] = {
    "str": (r"[^/]+", str),
    "int": (r"-?\d+", int),
    "float": (r"-?\d+(?:\.\d+)?", float),
    "uuid": (
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        str,
    ),
    "path": (r".+", str),
}


class Route:
    """A single route mapping a method + path pattern to a handler."""

    __slots__ = ("_converters", "_pattern", "handler", "method", "path")

    def __init__(
        self,
        method: str,
        path: str,
        handler: Callable[..., Any],
    ) -> None:
        self.method = method.upper()
        self.path = path
        self.handler = handler
        self._pattern, self._converters = _compile_pattern(path)

    def match(self, path: str) -> dict[str, Any] | None:
        """Return converted path params if *path* matches, else ``None``."""
        m = self._pattern.match(path)
        if m is None:
            return None
        return {name: self._converters[name](value) for name, value in m.groupdict().items()}

    def __repr__(self) -> str:
        return f"Route({self.method!r}, {self.path!r})"


class Router:
    """Ordered collection of routes with first-match-wins lookup."""

    __slots__ = ("routes",)

    def __init__(self) -> None:
        self.routes: list[Route] = []

    def add_route(
        self,
        method: str,
        path: str,
        handler: Callable[..., Any],
    ) -> Route:
        route = Route(method, path, handler)
        self.routes.append(route)
        return route

    def match(
        self,
        method: str,
        path: str,
    ) -> tuple[Route, dict[str, Any]] | None:
        """Return ``(route, params)`` for the first match, or ``None``."""
        method = method.upper()
        for route in self.routes:
            if route.method != method:
                continue
            params = route.match(path)
            if params is not None:
                return route, params
        return None


def _compile_pattern(
    path: str,
) -> tuple[re.Pattern[str], dict[str, Callable[[str], Any]]]:
    """Compile ``/users/{id:int}`` into a regex + converter dict."""
    converters: dict[str, Callable[[str], Any]] = {}
    parts: list[str] = []
    last_end = 0

    for m in _PARAM_RE.finditer(path):
        parts.append(re.escape(path[last_end : m.start()]))
        name = m.group(1)
        type_name = m.group(2) or "str"

        if type_name not in _PARAM_TYPES:
            msg = f"Unknown path parameter type: {type_name!r}"
            raise ValueError(msg)

        regex, converter = _PARAM_TYPES[type_name]
        parts.append(f"(?P<{name}>{regex})")
        converters[name] = converter
        last_end = m.end()

    parts.append(re.escape(path[last_end:]))
    return re.compile("^" + "".join(parts) + "$"), converters
