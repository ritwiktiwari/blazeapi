"""Tests for strict-mode handler signature validation."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from blazeapi.response import JSONResponse, Response
from blazeapi.validation import validate_handler_signature

# -- Test models ----------------------------------------------------------


class UserModel(BaseModel):
    name: str
    age: int


class QueryModel(BaseModel):
    page: int
    size: int


# -- Rule 1: Return type annotation must exist ---------------------------


def test_missing_return_type_raises() -> None:
    def handler(request: object): ...

    with pytest.raises(TypeError, match="Missing return type annotation"):
        validate_handler_signature(handler, "/x", "GET")


# -- Rule 2: Return type must be structured -------------------------------


def test_dict_return_type_raises() -> None:
    def handler(request: object) -> dict:
        return {}

    with pytest.raises(TypeError, match="must be a Response subclass or BaseModel subclass"):
        validate_handler_signature(handler, "/x", "GET")


def test_list_return_type_raises() -> None:
    def handler(request: object) -> list:
        return []

    with pytest.raises(TypeError, match="must be a Response subclass or BaseModel subclass"):
        validate_handler_signature(handler, "/x", "GET")


def test_basemodel_return_type_ok() -> None:
    def handler(request: object) -> UserModel:
        return UserModel(name="a", age=1)

    validate_handler_signature(handler, "/x", "GET")


def test_json_response_return_type_ok() -> None:
    def handler(request: object) -> JSONResponse:
        return JSONResponse({})

    validate_handler_signature(handler, "/x", "GET")


def test_response_return_type_ok() -> None:
    def handler(request: object) -> Response:
        return Response()

    validate_handler_signature(handler, "/x", "GET")


# -- Rule 3: All params must be typed ------------------------------------


def test_untyped_path_param_raises() -> None:
    def handler(request: object, user_id) -> None: ...

    with pytest.raises(TypeError, match="no type annotation"):
        validate_handler_signature(handler, "/users/{user_id}", "GET")


# -- Rule 4: Body/non-path params must be models -------------------------


def test_dict_body_param_raises() -> None:
    def handler(request: object, data: dict) -> None: ...

    with pytest.raises(TypeError, match="must be a BaseModel subclass"):
        validate_handler_signature(handler, "/x", "POST")


# -- Rule 5: Query-style params use model --------------------------------


def test_primitive_non_path_param_raises() -> None:
    def handler(request: object, page: int) -> None: ...

    with pytest.raises(TypeError, match="must be a BaseModel subclass"):
        validate_handler_signature(handler, "/x", "GET")


def test_query_model_param_ok() -> None:
    def handler(request: object, query: QueryModel) -> None: ...

    validate_handler_signature(handler, "/x", "GET")


# -- Path params: typed primitives are OK ---------------------------------


def test_typed_path_param_ok() -> None:
    def handler(request: object, user_id: int) -> None: ...

    validate_handler_signature(handler, "/users/{user_id}", "GET")


def test_typed_path_param_with_type_suffix_ok() -> None:
    def handler(request: object, user_id: int) -> None: ...

    validate_handler_signature(handler, "/users/{user_id:int}", "GET")


# -- Combined valid handler -----------------------------------------------


def test_combined_valid_handler() -> None:
    def handler(request: object, user_id: int, data: UserModel) -> None: ...

    validate_handler_signature(handler, "/users/{user_id:int}", "POST")
