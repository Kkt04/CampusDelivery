"""FastAPI application factory, error handling and router registration."""
import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import auth, incidents, notifications, packages, pickups, reports, storage, users
from app.core.config import get_settings
from app.core.exceptions import AppError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("campus")


def _error(status: int, code: str, message: str, details=None, request_id: str | None = None) -> JSONResponse:  # noqa: ANN001
    body = {"error": {"code": code, "message": message, "details": details, "request_id": request_id}}
    return JSONResponse(status_code=status, content=body)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="Digitises the lifecycle of a campus package from Gate No. 2 intake to verified handover.",
    )
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=False,
                       allow_methods=["GET", "POST", "PATCH"], allow_headers=["Authorization", "Content-Type",
                                                                               "Idempotency-Key"])

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):  # noqa: ANN001, ANN202
        request.state.request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    def rid(request: Request) -> str | None:
        return getattr(request.state, "request_id", None)

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return _error(exc.status_code, exc.code, exc.message, exc.details, rid(request))

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        fields = [{"field": ".".join(str(p) for p in e["loc"] if p != "body"), "message": e["msg"]}
                  for e in exc.errors()]
        return _error(422, "VALIDATION_FAILED", "Some fields are missing or invalid.", fields, rid(request))

    @app.exception_handler(StarletteHTTPException)
    async def http_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _error(exc.status_code, "HTTP_ERROR", str(exc.detail), None, rid(request))

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error (request %s)", rid(request))
        return _error(500, "INTERNAL_ERROR", "Something went wrong on the server. The request ID helps "
                      "operations find the cause.", None, rid(request))

    for module in (auth, packages, pickups, storage, users, notifications, incidents, reports):
        app.include_router(module.router, prefix="/api/v1")

    @app.get("/api/v1/health", tags=["Health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
