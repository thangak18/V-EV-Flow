from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.backend.contracts.errors import DomainError, ErrorResponse


class FeatureNotReadyError(DomainError):
    code = "feature_not_ready"


async def domain_error_handler(request: Request, exc: Exception) -> JSONResponse:
    del request
    assert isinstance(exc, DomainError)
    status = {
        "station_not_found": 404,
        "request_conflict": 409,
        "data_source_unavailable": 503,
        "model_not_ready": 503,
        "route_unavailable": 503,
        "feature_not_ready": 503,
    }.get(exc.code, 500)
    payload = ErrorResponse(code=exc.code.upper(), message=exc.message, details=exc.details)
    return JSONResponse(status_code=status, content=payload.model_dump())


async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    del request
    return JSONResponse(status_code=422, content={"detail": exc.errors()})
