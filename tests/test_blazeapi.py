"""Tests for BlazeAPI."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from blazeapi import BlazeAPI, JSONResponse, Request, Response, __version__
from blazeapi.routing import Route, Router

# =====================================================================
# Version
# =====================================================================


def test_version() -> None:
    assert __version__ is not None
    assert isinstance(__version__, str)


# =====================================================================
# Routing — pattern compilation & matching
# =====================================================================


class TestRouteCompilation:
    def test_static_path(self) -> None:
        route = Route("GET", "/health", lambda: None)
        assert route.match("/health") == {}
        assert route.match("/other") is None

    def test_str_param(self) -> None:
        route = Route("GET", "/users/{name}", lambda: None)
        assert route.match("/users/alice") == {"name": "alice"}
        assert route.match("/users/") is None

    def test_int_param(self) -> None:
        route = Route("GET", "/items/{id:int}", lambda: None)
        assert route.match("/items/42") == {"id": 42}
        assert route.match("/items/abc") is None

    def test_float_param(self) -> None:
        route = Route("GET", "/price/{amount:float}", lambda: None)
        assert route.match("/price/9.99") == {"amount": 9.99}
        assert route.match("/price/10") == {"amount": 10.0}
        assert route.match("/price/abc") is None

    def test_uuid_param(self) -> None:
        route = Route("GET", "/obj/{uid:uuid}", lambda: None)
        assert route.match("/obj/550e8400-e29b-41d4-a716-446655440000") == {
            "uid": "550e8400-e29b-41d4-a716-446655440000"
        }
        assert route.match("/obj/not-a-uuid") is None

    def test_path_param(self) -> None:
        route = Route("GET", "/files/{filepath:path}", lambda: None)
        assert route.match("/files/a/b/c.txt") == {"filepath": "a/b/c.txt"}

    def test_multiple_params(self) -> None:
        route = Route("GET", "/users/{user_id:int}/posts/{post_id:int}", lambda: None)
        assert route.match("/users/1/posts/42") == {"user_id": 1, "post_id": 42}

    def test_unknown_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown path parameter type"):
            Route("GET", "/x/{v:bogus}", lambda: None)


class TestRouter:
    def test_match_returns_first_match(self) -> None:
        router = Router()
        router.add_route("GET", "/a", lambda: "first")
        router.add_route("GET", "/a", lambda: "second")
        result = router.match("GET", "/a")
        assert result is not None
        route, _params = result
        assert route.handler() == "first"

    def test_match_filters_by_method(self) -> None:
        router = Router()
        router.add_route("POST", "/x", lambda: None)
        assert router.match("GET", "/x") is None
        assert router.match("POST", "/x") is not None

    def test_match_returns_none_for_unknown(self) -> None:
        router = Router()
        assert router.match("GET", "/nope") is None


# =====================================================================
# ASGI end-to-end
# =====================================================================


def _make_client(app: BlazeAPI) -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    )


@pytest.mark.asyncio
async def test_simple_get() -> None:
    app = BlazeAPI()

    @app.get("/hello")
    async def hello(request: Request) -> JSONResponse:
        return JSONResponse({"msg": "hi"})

    async with _make_client(app) as client:
        resp = await client.get("/hello")
        assert resp.status_code == 200
        assert resp.json() == {"msg": "hi"}


@pytest.mark.asyncio
async def test_path_params() -> None:
    app = BlazeAPI()

    @app.get("/users/{user_id:int}")
    async def get_user(request: Request, user_id: int) -> JSONResponse:
        return JSONResponse({"id": user_id})

    async with _make_client(app) as client:
        resp = await client.get("/users/42")
        assert resp.status_code == 200
        assert resp.json() == {"id": 42}


@pytest.mark.asyncio
async def test_404() -> None:
    app = BlazeAPI()

    async with _make_client(app) as client:
        resp = await client.get("/nope")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Not Found"


@pytest.mark.asyncio
async def test_500_on_handler_error() -> None:
    app = BlazeAPI()

    @app.get("/boom")
    async def boom(request: Request) -> Response:
        raise RuntimeError("kaboom")

    async with _make_client(app) as client:
        resp = await client.get("/boom")
        assert resp.status_code == 500
        assert "Internal Server Error" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_sync_handler() -> None:
    app = BlazeAPI()

    @app.get("/sync")
    def sync_handler(request: Request) -> JSONResponse:
        return JSONResponse({"sync": True})

    async with _make_client(app) as client:
        resp = await client.get("/sync")
        assert resp.status_code == 200
        assert resp.json() == {"sync": True}


@pytest.mark.asyncio
async def test_dict_return_auto_json() -> None:
    app = BlazeAPI()

    @app.get("/auto")
    async def auto(request: Request) -> dict:
        return {"auto": True}

    async with _make_client(app) as client:
        resp = await client.get("/auto")
        assert resp.status_code == 200
        assert resp.json() == {"auto": True}


@pytest.mark.asyncio
async def test_post_with_body() -> None:
    app = BlazeAPI()

    @app.post("/echo")
    async def echo(request: Request) -> JSONResponse:
        data = await request.json()
        return JSONResponse(data)

    async with _make_client(app) as client:
        resp = await client.post("/echo", json={"key": "value"})
        assert resp.status_code == 200
        assert resp.json() == {"key": "value"}


@pytest.mark.asyncio
async def test_pydantic_model_response() -> None:
    class Item(BaseModel):
        name: str
        price: float

    app = BlazeAPI()

    @app.get("/item")
    async def get_item(request: Request) -> JSONResponse:
        return JSONResponse(Item(name="Widget", price=9.99))

    async with _make_client(app) as client:
        resp = await client.get("/item")
        assert resp.status_code == 200
        assert resp.json() == {"name": "Widget", "price": 9.99}


# =====================================================================
# Strict mode
# =====================================================================


def test_strict_mode_rejects_missing_annotation() -> None:
    app = BlazeAPI(strict=True)

    with pytest.raises(TypeError, match="Missing return type annotation"):

        @app.get("/x")
        def no_annotation(request: Request):
            return Response()


def test_strict_mode_rejects_wrong_return_type() -> None:
    app = BlazeAPI(strict=True)

    with pytest.raises(TypeError, match="must be a Response subclass or BaseModel subclass"):

        @app.get("/x")
        def wrong_type(request: Request) -> dict:
            return {}


def test_strict_mode_accepts_response_subclass() -> None:
    app = BlazeAPI(strict=True)

    @app.get("/x")
    def ok(request: Request) -> JSONResponse:
        return JSONResponse({})

    assert len(app.router.routes) == 1


# =====================================================================
# Middleware
# =====================================================================


@pytest.mark.asyncio
async def test_middleware() -> None:
    app = BlazeAPI()

    @app.get("/mw")
    async def handler(request: Request) -> JSONResponse:
        return JSONResponse({"ok": True})

    def add_header_middleware(inner_app):
        async def middleware(scope, receive, send):
            async def custom_send(message):
                if message["type"] == "http.response.start":
                    headers = list(message.get("headers", []))
                    headers.append((b"x-custom", b"yes"))
                    message = {**message, "headers": headers}
                await send(message)

            await inner_app(scope, receive, custom_send)

        return middleware

    app.add_middleware(add_header_middleware)

    async with _make_client(app) as client:
        resp = await client.get("/mw")
        assert resp.status_code == 200
        assert resp.headers["x-custom"] == "yes"


# =====================================================================
# All HTTP methods
# =====================================================================


@pytest.mark.asyncio
async def test_all_http_methods() -> None:
    app = BlazeAPI()

    for method_name in ("get", "post", "put", "delete", "patch", "options", "head"):
        decorator = getattr(app, method_name)

        @decorator(f"/{method_name}")
        async def handler(request: Request, _method=method_name) -> JSONResponse:
            return JSONResponse({"method": _method})

    async with _make_client(app) as client:
        for method_name in ("get", "post", "put", "delete", "patch", "options"):
            resp = await getattr(client, method_name)(f"/{method_name}")
            assert resp.status_code == 200

        resp = await client.head("/head")
        assert resp.status_code == 200
