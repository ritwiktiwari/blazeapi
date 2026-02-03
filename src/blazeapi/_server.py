import sys
from typing import Any


def serve(
    target: str,
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
    dev: bool = False,
    reload: bool | None = None,
    workers: int = 1,
    log_level: str = "info",
    log_access: bool = False,
    granian_kwargs: dict[str, Any] | None = None,
) -> None:
    """Start a Granian server for the given *target* import path.

    Parameters
    ----------
    target:
        ``"module:var"`` import path understood by Granian.
    dev:
        When ``True``, applies dev-friendly defaults (reload, debug logs,
        access logs) unless explicitly overridden.
    reload:
        Enable auto-reload.  ``None`` means follow *dev* flag.
    """
    from granian import Granian

    # Dev-mode defaults
    if dev:
        if reload is None:
            reload = True
        log_level = "debug"
        log_access = True

    if reload is None:
        reload = False

    _print_banner(target, host=host, port=port, workers=workers, reload=reload, dev=dev)

    kw: dict[str, Any] = granian_kwargs or {}
    server = Granian(
        target=target,
        address=host,
        port=port,
        interface="asgi",
        workers=workers,
        reload=reload,
        log_level=log_level,
        log_access=log_access,
        **kw,
    )
    server.serve()


# ------------------------------------------------------------------
# Startup banner
# ------------------------------------------------------------------

_CYAN = "\033[36m"
_GREEN = "\033[32m"
_BOLD = "\033[1m"
_RESET = "\033[0m"


def _print_banner(
    target: str,
    *,
    host: str,
    port: int,
    workers: int,
    reload: bool,
    dev: bool,
) -> None:
    color = sys.stdout.isatty()

    def c(code: str, text: str) -> str:
        return f"{code}{text}{_RESET}" if color else text

    mode = "development" if dev else "production"
    lines = [
        f"{c(_BOLD + _CYAN, 'BlazeAPI')}   Starting {mode} server",
        "",
        f"{c(_GREEN, 'app')}        {target}",
        f"{c(_GREEN, 'server')}     Granian on http://{host}:{port}",
        f"{c(_GREEN, 'workers')}    {workers}",
        f"{c(_GREEN, 'reload')}     {'enabled' if reload else 'disabled'}",
        "",
    ]
    print("\n".join(lines), flush=True)
