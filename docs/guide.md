# User Guide

## Routing

Register handlers with decorator methods on the `Thrustly` app. All standard HTTP methods are supported: `get`, `post`, `put`, `delete`, `patch`, `options`, `head`.

```python
from thrustly import Thrustly, Request, JSONResponse

app = Thrustly()

@app.get("/items")
async def list_items(request: Request) -> JSONResponse:
    return JSONResponse([{"id": 1}, {"id": 2}])

@app.post("/items")
async def create_item(request: Request) -> JSONResponse:
    data = await request.json()
    return JSONResponse(data, status_code=201)
```

Routes are matched in registration order. The first match wins.

### Path Parameters

Path parameters are declared with `{name}` or `{name:type}` syntax. Supported types:

| Type    | Pattern                  | Python type | Example              |
|---------|--------------------------|-------------|----------------------|
| `str`   | `[^/]+` (default)        | `str`       | `{slug}`             |
| `int`   | `-?\d+`                  | `int`       | `{id:int}`           |
| `float` | `-?\d+(?:\.\d+)?`        | `float`     | `{amount:float}`     |
| `uuid`  | UUID v4 hex pattern      | `str`       | `{uid:uuid}`         |
| `path`  | `.+` (matches slashes)   | `str`       | `{filepath:path}`    |

Parameters are converted to their Python type automatically and passed as keyword arguments:

```python
@app.get("/users/{user_id:int}/posts/{post_id:int}")
async def get_post(request: Request, user_id: int, post_id: int) -> JSONResponse:
    return JSONResponse({"user": user_id, "post": post_id})
```

If the path doesn't match the type constraint (e.g. `/users/abc` for an `int` param), it's treated as a non-match and routing continues.

## Request

The `Request` object wraps the ASGI scope and receive callable.

### Properties

- `request.method` -- HTTP method (`"GET"`, `"POST"`, etc.)
- `request.path` -- URL path
- `request.query_string` -- raw query string as `bytes`
- `request.query_params` -- parsed query params as `dict[str, list[str]]`
- `request.headers` -- headers as a lowercase-keyed `dict[str, str]`
- `request.path_params` -- matched path parameters as a `dict[str, Any]`

### Body

```python
@app.post("/upload")
async def upload(request: Request) -> JSONResponse:
    raw: bytes = await request.body()
    parsed: dict = await request.json()
    return JSONResponse(parsed)
```

The body is read once and cached. Subsequent calls to `body()` or `json()` return the cached result.

## Responses

### `Response`

Plain response with explicit body bytes:

```python
from thrustly import Response

@app.get("/text")
async def text(request: Request) -> Response:
    return Response(b"hello", content_type="text/plain")
```

Constructor parameters:

- `body` -- response body as `bytes` (default: `b""`)
- `status_code` -- HTTP status code (default: `200`)
- `headers` -- dict of response headers
- `content_type` -- content-type header value (default: `"text/plain; charset=utf-8"`)

The `content-length` header is set automatically.

### `JSONResponse`

Serializes dicts, lists, and Pydantic models to JSON:

```python
from pydantic import BaseModel
from thrustly import JSONResponse

class User(BaseModel):
    id: int
    name: str

@app.get("/user")
async def get_user(request: Request) -> JSONResponse:
    return JSONResponse(User(id=1, name="Alice"))
    # -> {"id": 1, "name": "Alice"}
```

Pydantic models are serialized with `model_dump_json()` for performance. Everything else goes through `json.dumps` with `default=str` as a fallback serializer.

### Auto-serialization

If a handler returns a `dict` or `list` instead of a `Response`, it's automatically wrapped in `JSONResponse`:

```python
@app.get("/auto")
async def auto(request: Request) -> dict:
    return {"auto": True}
```

## Sync Handlers

Sync handlers are supported and automatically offloaded to a thread executor so they don't block the event loop:

```python
import time

@app.get("/slow")
def slow(request: Request) -> JSONResponse:
    time.sleep(1)  # won't block other requests
    return JSONResponse({"done": True})
```

## Strict Mode

Enable strict mode to validate handler return type annotations at registration time:

```python
app = Thrustly(strict=True)

# This raises TypeError immediately at decoration time:
@app.get("/bad")
def bad(request: Request) -> dict:  # not a Response subclass
    return {}

# This is fine:
@app.get("/good")
def good(request: Request) -> JSONResponse:
    return JSONResponse({})
```

Strict mode requires:

1. A return type annotation on every handler
2. The annotation must be `Response` or a subclass (e.g. `JSONResponse`)

## Debug Mode

Enable debug mode to include tracebacks in 500 error responses:

```python
app = Thrustly(debug=True)
```

When `debug=False` (the default), 500 responses only return `{"detail": "Internal Server Error"}` with no traceback information.

## Middleware

Middleware uses the standard ASGI wrapping pattern. A middleware is a function that takes an ASGI app and returns a new ASGI app:

```python
def timing_middleware(inner_app):
    async def middleware(scope, receive, send):
        import time
        start = time.perf_counter()

        async def custom_send(message):
            if message["type"] == "http.response.start":
                elapsed = f"{time.perf_counter() - start:.4f}"
                headers = list(message.get("headers", []))
                headers.append((b"x-response-time", elapsed.encode()))
                message = {**message, "headers": headers}
            await send(message)

        await inner_app(scope, receive, custom_send)
    return middleware

app.add_middleware(timing_middleware)
```

Middleware is applied in reverse registration order (last registered wraps outermost).

## Running

### Development

Use the built-in `run()` method:

```python
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
```

### Production

Use Granian directly for more control over workers, threading, and TLS:

```bash
granian --interface asgi --host 0.0.0.0 --port 8000 --workers 4 app:app
```
