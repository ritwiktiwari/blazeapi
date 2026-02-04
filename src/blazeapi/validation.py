"""Handler signature validation for strict mode."""

from __future__ import annotations

import inspect
import re
from typing import Any, get_type_hints

from pydantic import BaseModel

from blazeapi.response import Response

_PATH_PARAM_RE = re.compile(r"\{(\w+)(?::\w+)?\}")


def _is_basemodel(tp: Any) -> bool:
    """Return True if *tp* is a BaseModel subclass."""
    return isinstance(tp, type) and issubclass(tp, BaseModel)


def validate_handler_signature(func: Any, path: str, method: str) -> None:
    """Validate a handler's type annotations at route registration time.

    Raises :class:`TypeError` with an actionable message when the handler
    violates strict-mode typing rules.
    """
    name = getattr(func, "__name__", repr(func))
    hints = get_type_hints(func)
    sig = inspect.signature(func)
    path_param_names = set(_PATH_PARAM_RE.findall(path))

    # --- Rule 1: Return type annotation must exist ---
    ret = hints.get("return")
    if ret is None:
        raise TypeError(
            f"\n\nStrict-mode violation in handler '{name}' "
            f"[{method} {path}]\n"
            f"  Problem: Missing return type annotation.\n"
            f"  Fix:     Add a return type, e.g. -> JSONResponse or -> YourModel.\n"
            f"  Rules:   Return type must be a Response subclass or BaseModel subclass.\n"
        )

    # --- Rule 2: Return type must be structured ---
    is_response = isinstance(ret, type) and issubclass(ret, Response)
    is_model = _is_basemodel(ret)
    if not (is_response or is_model):
        raise TypeError(
            f"\n\nStrict-mode violation in handler '{name}' "
            f"[{method} {path}]\n"
            f"  Current: -> {ret.__name__ if isinstance(ret, type) else ret!r}\n"
            f"  Problem: Return type must be a Response subclass or BaseModel subclass.\n"
            f"  Fix:     Use -> JSONResponse, -> Response, or -> YourModel(BaseModel).\n"
            f"  Rejected types: dict, list, str, int, and other primitives.\n"
        )

    # --- Validate parameters ---
    for param_name, _ in sig.parameters.items():
        # Skip 'request' (framework-internal)
        if param_name == "request":
            continue

        hint = hints.get(param_name)

        # --- Rule 3: All params must be typed ---
        if hint is None:
            raise TypeError(
                f"\n\nStrict-mode violation in handler '{name}' "
                f"[{method} {path}]\n"
                f"  Problem: Parameter '{param_name}' has no type annotation.\n"
                f"  Fix:     Add a type annotation, e.g. {param_name}: int "
                f"or {param_name}: YourModel.\n"
            )

        # Path params — primitives are OK, just need the annotation (Rule 3 above)
        if param_name in path_param_names:
            continue

        # --- Rule 4 & 5: Non-path params must be BaseModel subclass ---
        if not _is_basemodel(hint):
            type_label = hint.__name__ if isinstance(hint, type) else repr(hint)
            raise TypeError(
                f"\n\nStrict-mode violation in handler '{name}' "
                f"[{method} {path}]\n"
                f"  Current: {param_name}: {type_label}\n"
                f"  Problem: Non-path parameter '{param_name}' must be a "
                f"BaseModel subclass.\n"
                f"  Fix:     Wrap '{param_name}' fields in a Pydantic model, "
                f"e.g. {param_name}: {param_name.title()}Model.\n"
                f"  Rejected types: dict, list, str, int, and other primitives.\n"
            )
