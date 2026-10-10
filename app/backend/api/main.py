from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.backend.api.dependencies import build_container
from app.backend.api.errors import domain_error_handler
from app.backend.contracts.errors import DomainError
from app.backend.core.settings import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    selected = settings if settings is not None else get_settings()
    container = build_container(selected)
    app = FastAPI(title="V-EV Flow API", version="0.1.0")
    app.state.container = container
    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
    )

    from app.backend.api.routes.prediction import router as prediction_router
    from app.backend.api.routes.recommendation import router as recommendation_router
    from app.backend.api.routes.stations import router as stations_router

    app.include_router(stations_router, prefix="/api")
    app.include_router(prediction_router, prefix="/api")
    app.include_router(recommendation_router, prefix="/api")

    @app.get("/api/health", operation_id="health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/ready", operation_id="ready")
    def ready() -> dict[str, object]:
        return {
            "ready": container.ready,
            "data_backend": selected.data_backend,
            "predictor_backend": selected.predictor_backend,
            "route_backend": selected.route_backend,
        }

    return app


__all__ = ["create_app"]
