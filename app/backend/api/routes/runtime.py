"""Runtime clock/capability discovery and opt-in canonical partner ingestion."""

import secrets
from datetime import UTC, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException

from app.backend.api.dependencies import AppContainer, get_container
from app.backend.api.errors import FeatureNotReadyError
from app.backend.contracts.enums import DataType, Scenario
from app.backend.contracts.runtime import IngestResult, RuntimeContext, SnapshotBatch
from app.backend.infrastructure.repositories.files import ParquetStatusRepository

router = APIRouter()


@router.get("/runtime", response_model=RuntimeContext, operation_id="runtimeContext")
def runtime_context(
    scenario: Scenario = Scenario.NORMAL, container: AppContainer = Depends(get_container)
) -> RuntimeContext:
    settings = container.settings
    start = end = observed = None
    kind = (
        "mock"
        if settings.data_backend == "mock"
        else "live"
        if settings.data_backend == "real"
        else "replay"
    )
    message = "Dữ liệu minh họa."
    available = True
    if container.partner_history is not None:
        start, end = container.partner_history.bounds(scenario)
        observed = end
        available = (
            end is not None
            and 0 <= (datetime.now(UTC) - end).total_seconds() <= settings.live_max_age_seconds
        )
        message = (
            "Snapshot từ đối tác; model có thể vẫn được train bằng simulated data."
            if available
            else "Chưa có snapshot đối tác đủ mới và đầy đủ cho các trạm."
        )
        if settings.predictor_backend != "model":
            available = False
            message = "Cổng nhận dữ liệu đã bật, cần cấu hình model trước khi dự báo live."
    elif settings.data_backend == "file":
        repository = container.status_repositories_by_scenario[scenario]
        if isinstance(repository, ParquetStatusRepository):
            start, end = repository.bounds()
        if start is not None and end is not None:
            preferred = end.replace(hour=16, minute=0, second=0, microsecond=0)
            observed = preferred if start <= preferred <= end else end
            if settings.replay_observed_at:
                observed = settings.replay_observed_at
            available = start <= observed <= end
        else:
            available = False
        message = "Replay lịch sử simulated, không phải trạng thái cổng ở thời điểm hiện tại."
    else:
        observed = datetime(2026, 10, 13, 16, tzinfo=timezone(timedelta(hours=7)))
    return RuntimeContext(
        clock_mode=kind,  # type: ignore[arg-type]
        scenario=scenario,
        data_type=DataType(settings.data_backend)
        if settings.data_backend == "real"
        else DataType.SIMULATED
        if kind == "replay"
        else DataType.MOCK,
        observed_at=observed,
        history_start=start,
        history_end=end,
        max_horizon_minutes=container.prediction_horizons[scenario],
        places_available=container.places is not None,
        available=available,
        message=message,
        allocation_backend=settings.allocation_backend,
    )


@router.post("/partner/snapshots", response_model=IngestResult, operation_id="ingestSnapshots")
def ingest_snapshots(
    batch: SnapshotBatch,
    authorization: str | None = Header(default=None),
    container: AppContainer = Depends(get_container),
) -> IngestResult:
    token = container.settings.partner_ingest_token
    if container.partner_history is None or not token:
        raise FeatureNotReadyError("partner ingestion is not configured")
    if not authorization or not secrets.compare_digest(
        authorization.encode(), ("Bearer " + token).encode()
    ):
        raise HTTPException(401, "partner ingestion requires authentication")
    try:
        accepted = container.partner_history.ingest(batch)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    return IngestResult(accepted=accepted, source=container.partner_history.source)
