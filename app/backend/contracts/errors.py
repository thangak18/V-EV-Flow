from .common import StrictModel


class DomainError(Exception):
    code = "domain_error"

    def __init__(self, message: str, details: object | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class StationNotFoundError(DomainError):
    code = "station_not_found"


class DataSourceUnavailableError(DomainError):
    code = "data_source_unavailable"


class ModelNotReadyError(DomainError):
    code = "model_not_ready"


class RouteUnavailableError(DomainError):
    code = "route_unavailable"


class RequestConflictError(DomainError):
    code = "request_conflict"


class ErrorResponse(StrictModel):
    code: str
    message: str
    details: object | None = None
