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

if __name__ == "__main__":
    app.run()
```

## Features

- **Typed path parameters** -- `{id:int}`, `{slug:str}`, `{amount:float}`, `{uid:uuid}`, `{filepath:path}`
- **Pydantic serialization** -- return Pydantic models directly from `JSONResponse`
- **Sync and async handlers** -- sync handlers run in a thread executor automatically
- **Strict mode** -- validates handler return type annotations at registration time
- **Middleware** -- standard ASGI middleware wrapping
- **Granian server** -- built-in `app.run()` for development, or use Granian directly in production

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
app = BlazeAPI(strict=True)

@app.get("/x")
def bad(request: Request) -> dict:  # TypeError -- must return Response or subclass
    return {}
```

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

## Development

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
