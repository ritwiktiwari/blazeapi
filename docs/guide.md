# User Guide

## Routing

Register handlers with decorator methods on the `BlazeAPI` app. All standard HTTP methods are supported: `get`, `post`, `put`, `delete`, `patch`, `options`, `head`.

```python
from blazeapi import BlazeAPI, Request, JSONResponse

app = BlazeAPI()

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
from blazeapi import Response

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
from blazeapi import JSONResponse

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

Enable strict mode to get comprehensive handler signature validation at route registration time. This catches type errors early -- at import time rather than at request time.

```python
app = BlazeAPI(strict=True)
```

### What gets validated

Strict mode enforces five rules when a handler is registered:

| Rule | Requirement | Allowed | Rejected |
|------|-------------|---------|----------|
| 1 | Return type annotation exists | Any annotation | Missing annotation |
| 2 | Return type is structured | `BaseModel` subclass, `Response` subclass | `dict`, `list`, primitives |
| 3 | All parameters are typed | Any type annotation | Missing annotation |
| 4 | Non-path parameters are models | `BaseModel` subclass | `dict`, `list`, primitives |
| 5 | Path parameters have types | Primitives OK (`int`, `str`, etc.) | Missing annotation |

### Examples

```python
from pydantic import BaseModel
from blazeapi import BlazeAPI, Request, JSONResponse

app = BlazeAPI(strict=True)

class CreateItemRequest(BaseModel):
    name: str
    price: float

class QueryParams(BaseModel):
    page: int
    size: int
```

**Return types** -- must be `Response`/`JSONResponse` or a `BaseModel` subclass:

```python
# TypeError -- dict is not allowed
@app.get("/bad")
def bad(request: Request) -> dict:
    return {}

# OK -- JSONResponse is a Response subclass
@app.get("/good")
def good(request: Request) -> JSONResponse:
    return JSONResponse({})

# OK -- BaseModel subclass as return type
@app.get("/also-good")
def also_good(request: Request) -> CreateItemRequest:
    return CreateItemRequest(name="Widget", price=9.99)
```

**Path parameters** -- just need a type annotation, primitives are fine:

```python
# OK -- user_id matches {user_id} in the path, so int is allowed
@app.get("/users/{user_id:int}")
async def get_user(request: Request, user_id: int) -> JSONResponse:
    return JSONResponse({"id": user_id})
```

**Non-path parameters** -- must be `BaseModel` subclasses:

```python
# TypeError -- page: int is not in the path, so it must be a BaseModel
@app.get("/items")
async def list_items(request: Request, page: int) -> JSONResponse:
    ...

# OK -- wrap query params in a model
@app.get("/items")
async def list_items(request: Request, query: QueryParams) -> JSONResponse:
    return JSONResponse({"page": query.page})

# OK -- body parameter as a model
@app.post("/items")
async def create_item(request: Request, item: CreateItemRequest) -> JSONResponse:
    return JSONResponse(item)
```

### Error messages

Strict mode errors are detailed and actionable:

```
Strict-mode violation in handler 'list_items' [GET /items]
  Current: page: int
  Problem: Non-path parameter 'page' must be a BaseModel subclass.
  Fix:     Wrap 'page' fields in a Pydantic model, e.g. page: PageModel.
  Rejected types: dict, list, str, int, and other primitives.
```

## Debug Mode

Enable debug mode to include tracebacks in 500 error responses:

```python
app = BlazeAPI(debug=True)
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

BlazeAPI provides a CLI with two commands: `blazeapi dev` for development and `blazeapi run` for production. Both are powered by [Granian](https://github.com/emmett-framework/granian).

### Development

```bash
blazeapi dev main.py
```

This starts the server on `http://127.0.0.1:8000` with auto-reload, debug-level logging, and access logs enabled. The server automatically restarts when you change your code.

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

#### `blazeapi run` options

| Option | Default | Description |
|--------|---------|-------------|
| `PATH` | `main.py` | Python file or `module:var` target |
| `--host` | `127.0.0.1` | Bind address. Use `0.0.0.0` to accept external connections. |
| `--port` | `8000` | Bind port |
| `--workers` | `1` | Number of worker processes |

For full control over threading, TLS, backpressure, and other Granian options, use Granian directly:

```bash
granian --interface asgi --host 0.0.0.0 --port 8000 --workers 4 app:app
```

### Target resolution

The `PATH` argument accepts two forms:

- **File path** -- `main.py`, `app.py`, etc. BlazeAPI auto-discovers the app instance by looking for variables named `app` or `application`, then falls back to any `BlazeAPI` instance found in the module.
- **Module:var** -- `myapp:app`, `server:application`, etc. Used directly as the Granian target.

### Programmatic usage

You can also start the server from Python with `app.run()`:

```python
if __name__ == "__main__":
    app.run(dev=True)
```

`app.run()` accepts the same options: `host`, `port`, `dev`, `reload`, `workers`, `log_level`, and any extra keyword arguments are passed through to Granian.
