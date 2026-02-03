# thrustly

Typed-first Python web framework for fast, stable APIs. Built on [Granian](https://github.com/emmett-framework/granian) and [Pydantic](https://docs.pydantic.dev/).

!!! warning "Alpha"
    Thrustly is under active development. APIs may change between releases. Not recommended for production use yet.

## Installation

```bash
uv add thrustly
```

Or with pip:

```bash
pip install thrustly
```

## Quick Start

Create a file called `app.py`:

```python
from thrustly import Thrustly, Request, JSONResponse

app = Thrustly()

@app.get("/")
async def index(request: Request) -> JSONResponse:
    return JSONResponse({"message": "hello, world"})

@app.get("/users/{user_id:int}")
async def get_user(request: Request, user_id: int) -> JSONResponse:
    return JSONResponse({"id": user_id})

if __name__ == "__main__":
    app.run()
```

Run it:

```bash
python app.py
```

The server starts on `http://127.0.0.1:8000`. Hit `GET /users/42` and you'll get `{"id": 42}`.

For production, run with Granian directly:

```bash
granian --interface asgi app:app
```

## What's Next

- [User Guide](guide.md) -- routing, requests, responses, middleware, strict mode
- [API Reference](api.md) -- full class and function documentation
- [Contributing](contributing.md) -- development setup and workflow
