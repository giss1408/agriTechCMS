from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    """A business or access error rendered in the standard envelope.

    `code` is stable and machine-readable (the mobile app switches on it); `message` is French, for humans.
    """

    def __init__(self, status: int, code: str, message: str, **details):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details


def not_found(entity: str) -> ApiError:
    return ApiError(404, "not_found", f"{entity} introuvable")


def _body(errors: list[dict]) -> dict:
    return {"success": False, "data": None, "meta": None, "errors": errors}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError):
        return JSONResponse(
            status_code=exc.status,
            content=_body([{"code": exc.code, "message": exc.message, **exc.details}]),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        errors = [
            {
                "code": "validation_error",
                "field": ".".join(str(p) for p in err["loc"] if p != "body"),
                "message": err["msg"],
            }
            for err in exc.errors()
        ]
        return JSONResponse(status_code=400, content=_body(errors))

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        code = {401: "unauthorized", 403: "forbidden", 404: "not_found", 405: "method_not_allowed"}
        return JSONResponse(
            status_code=exc.status_code,
            content=_body([{"code": code.get(exc.status_code, "http_error"), "message": str(exc.detail)}]),
            headers=getattr(exc, "headers", None),
        )
