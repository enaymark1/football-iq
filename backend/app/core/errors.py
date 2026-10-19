"""Errores de dominio y su traducción a respuestas HTTP."""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    status_code = 400

    def __init__(self, message: str, *, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(DomainError):
    status_code = 404


class InvalidRequestError(DomainError):
    status_code = 422


class DataUnavailableError(DomainError):
    """No hay datos importados (o no alcanzan) para responder."""

    status_code = 409


class ModelNotTrainedError(DomainError):
    status_code = 503


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain_error(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": type(exc).__name__, "message": exc.message, "details": exc.details},
        )
