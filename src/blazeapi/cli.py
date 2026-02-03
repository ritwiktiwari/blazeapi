"""BlazeAPI command-line interface powered by Typer."""

import importlib
import sys
from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(name="blazeapi", add_completion=False, no_args_is_help=True)


# ------------------------------------------------------------------
# Target resolution
# ------------------------------------------------------------------


def _resolve_cli_target(path: str) -> str:
    """Turn a CLI *path* argument into a ``"module:var"`` string.

    Accepted forms:
    - ``module:var``   → returned as-is
    - ``file.py``      → imports ``file``, scans for a BlazeAPI instance
    """
    if ":" in path:
        return path

    # Treat as a Python file
    file = Path(path)
    if not file.exists():
        typer.echo(f"Error: file {path!r} not found.", err=True)
        raise typer.Exit(1)

    module_name = file.stem

    # Ensure the file's directory is on sys.path so we can import it.
    parent = str(file.resolve().parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)

    try:
        mod = importlib.import_module(module_name)
    except Exception as exc:
        typer.echo(f"Error importing {module_name!r}: {exc}", err=True)
        raise typer.Exit(1) from exc

    var_name = _find_blazeapi_var(mod)
    if var_name is None:
        typer.echo(
            f"Error: no BlazeAPI instance found in {path!r}. Provide an explicit target, e.g. main:app",
            err=True,
        )
        raise typer.Exit(1)

    return f"{module_name}:{var_name}"


def _find_blazeapi_var(mod: object) -> str | None:
    """Scan a module for a ``BlazeAPI`` instance.

    Checks ``app`` and ``application`` first, then falls back to any attribute.
    """
    from blazeapi.app import BlazeAPI

    for name in ("app", "application"):
        val = getattr(mod, name, None)
        if isinstance(val, BlazeAPI):
            return name

    for name in dir(mod):
        if name.startswith("_"):
            continue
        if isinstance(getattr(mod, name, None), BlazeAPI):
            return name

    return None


# ------------------------------------------------------------------
# Commands
# ------------------------------------------------------------------


@app.command()
def dev(
    path: Annotated[str, typer.Argument(help="Python file or module:var target.")] = "main.py",
    host: Annotated[str, typer.Option(help="Bind address.")] = "127.0.0.1",
    port: Annotated[int, typer.Option(help="Bind port.")] = 8000,
    reload: Annotated[bool | None, typer.Option("--reload/--no-reload", help="Auto-reload on code changes.")] = None,
) -> None:
    """Start a development server with auto-reload and debug logging."""
    from blazeapi._server import serve

    target = _resolve_cli_target(path)
    serve(target, host=host, port=port, dev=True, reload=reload)


@app.command()
def run(
    path: Annotated[str, typer.Argument(help="Python file or module:var target.")] = "main.py",
    host: Annotated[str, typer.Option(help="Bind address.")] = "127.0.0.1",
    port: Annotated[int, typer.Option(help="Bind port.")] = 8000,
    workers: Annotated[int, typer.Option(help="Number of worker processes.")] = 1,
) -> None:
    """Start a production server."""
    from blazeapi._server import serve

    target = _resolve_cli_target(path)
    serve(target, host=host, port=port, workers=workers)
