# BlazeAPI

[![CI](https://github.com/ritwiktiwari/blazeapi/actions/workflows/ci.yml/badge.svg)](https://github.com/ritwiktiwari/blazeapi/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/blazeapi)](https://pypi.org/project/blazeapi/)
[![codecov](https://codecov.io/gh/ritwiktiwari/blazeapi/branch/main/graph/badge.svg)](https://codecov.io/gh/ritwiktiwari/blazeapi)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![ty](https://img.shields.io/badge/type--checked-ty-blue?labelColor=orange)](https://github.com/astral-sh/ty)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-yellow.svg)](https://github.com/ritwiktiwari/blazeapi/blob/main/LICENSE)

**BlazeAPI** — Typed-first Python web framework for blazingly fast, stable APIs. Built on [Granian](https://github.com/emmett-framework/granian) and [Pydantic](https://docs.pydantic.dev/).

> **Alpha** -- BlazeAPI is under active development. APIs may change between releases. Not recommended for production use yet.

## Quick Start

```bash
uv add blazeapi
```

```python
from blazeapi import BlazeAPI, Request, JSONResponse

app = BlazeAPI()

@app.get("/")
async def index(request: Request) -> JSONResponse:
    return JSONResponse({"message": "hello, world"})

@app.get("/users/{user_id:int}")
async def get_user(request: Request, user_id: int) -> JSONResponse:
    return JSONResponse({"id": user_id})
```

## Features

- **Typed path parameters** -- `{id:int}`, `{slug:str}`, `{amount:float}`, `{uid:uuid}`, `{filepath:path}`
- **Pydantic serialization** -- return Pydantic models directly from `JSONResponse`
- **Sync and async handlers** -- sync handlers run in a thread executor automatically
- **Strict mode** -- comprehensive handler signature validation at registration time
- **Middleware** -- standard ASGI middleware wrapping
- **CLI** -- `blazeapi dev` and `blazeapi run` commands powered by [Granian](https://github.com/emmett-framework/granian)

## Handlers

Handlers receive a `Request` object and any matched path parameters as keyword arguments:

```python
@app.post("/items")
async def create_item(request: Request) -> JSONResponse:
    data = await request.json()
    return JSONResponse(data, status_code=201)
```

Sync handlers work too -- they're offloaded to a thread pool so they don't block the event loop:

```python
@app.get("/sync")
def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})
```

Return dicts or lists directly and they'll be serialized as JSON:

```python
@app.get("/simple")
async def simple(request: Request) -> dict:
    return {"works": True}
```

## Strict Mode

Catch handler signature mistakes at import time instead of at request time:

```python
from pydantic import BaseModel

app = BlazeAPI(strict=True)

class Item(BaseModel):
    name: str
    price: float

# Return type must be Response/JSONResponse or a BaseModel subclass
@app.get("/x")
def bad(request: Request) -> dict:  # TypeError
    return {}

# Non-path parameters must be BaseModel subclasses
@app.post("/items")
async def create(request: Request, item: Item) -> JSONResponse:  # OK
    return JSONResponse(item)

# Path parameters just need a type annotation
@app.get("/users/{user_id:int}")
async def get_user(request: Request, user_id: int) -> JSONResponse:  # OK
    return JSONResponse({"id": user_id})
```

Strict mode validates at route registration time:

1. Every handler must have a return type annotation
2. Return type must be a `Response` subclass or `BaseModel` subclass (not `dict`, `list`, or primitives)
3. All parameters must have type annotations
4. Non-path parameters must be `BaseModel` subclasses (not `dict`, `list`, or bare primitives)
5. Path parameters (matching `{name}` in the route) may use primitive types like `int` or `str`

## Running the App

BlazeAPI provides a CLI with two commands: `dev` for development and `run` for production.

### Development

```bash
blazeapi dev main.py
```

This starts the server on `http://127.0.0.1:8000` with auto-reload, debug logging, and access logs enabled.

```bash
# Custom host and port
blazeapi dev main.py --host 0.0.0.0 --port 3000

# Disable auto-reload
blazeapi dev main.py --no-reload
```

#### `blazeapi dev` options

| Option | Default | Description |
|--------|---------|-------------|
| `PATH` | `main.py` | Python file or `module:var` target |
| `--host` | `127.0.0.1` | Bind address |
| `--port` | `8000` | Bind port |
| `--reload` / `--no-reload` | `--reload` | Auto-reload on code changes |

Dev mode automatically sets debug-level logging and enables access logs.

### Production

```bash
blazeapi run main.py --host 0.0.0.0 --port 8000 --workers 4
```

Or use Granian directly for full control over threading, TLS, and other options:

```bash
granian --interface asgi --host 0.0.0.0 --port 8000 --workers 4 app:app
```

#### `blazeapi run` options

| Option | Default | Description |
|--------|---------|-------------|
| `PATH` | `main.py` | Python file or `module:var` target |
| `--host` | `127.0.0.1` | Bind address |
| `--port` | `8000` | Bind port |
| `--workers` | `1` | Number of worker processes |

### Target resolution

The `PATH` argument accepts two forms:

- **File path** -- `main.py`, `app.py`, etc. BlazeAPI auto-discovers the app instance by looking for variables named `app` or `application`, then falls back to any `BlazeAPI` instance.
- **Module:var** -- `myapp:app`, `server:application`, etc. Used directly.

## Middleware

Standard ASGI middleware pattern -- a function that takes an app and returns an app:

```python
def add_cors(inner_app):
    async def middleware(scope, receive, send):
        async def custom_send(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"access-control-allow-origin", b"*"))
                message = {**message, "headers": headers}
            await send(message)
        await inner_app(scope, receive, custom_send)
    return middleware

app.add_middleware(add_cors)
```

## Contributing

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) for package management

### Setup

```bash
git clone https://github.com/ritwiktiwari/blazeapi.git
cd blazeapi
make install
```

### Running Tests

```bash
make test

# With coverage
make test-cov

# Across all Python versions
make test-matrix
```

### Code Quality

```bash
# Run all checks (lint, format, type-check)
make verify

# Auto-fix lint and format issues
make fix
```

### Documentation

```bash
make docs-serve
```

## License

This project is licensed under the Apache-2.0 License - see the [LICENSE](LICENSE) file for details.
