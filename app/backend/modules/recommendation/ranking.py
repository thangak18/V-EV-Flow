"""Pure post-prediction heuristic scoring, separate from model probability.

Travel uses t/(t + reference); virtual load uses load/(load + working ports).
Ratios use scaled arithmetic to avoid overflowing their sums and saturate at
the largest float below 1 when floating precision would otherwise yield 1.
SOC risk is clamp(1 - (arrival - minimum)/band, 0, 1), algebraically equivalent
to the documented risk-upper formulation without losing very small bands.

C5 supplies actual route duration, C3-validated operational capacity and a
canonical candidate with a real prediction. C6 supplies the load snapshot for
the candidate ETA window; missing stations mean zero virtual allocation. This
module neither selects plans nor aggregates/reserves loads. AllocationContext
alone lacks the duration/capacity metadata, so simulation integration needs an
explicit upstream metadata source, not guessed speed/capacity or contract edits.
C5 must inject the same effective minimum arrival SOC into C3 filtering and
RankingConfig. Ranking rejects below-threshold candidates rather than silently
overriding either configuration, including when C3 uses a nondefault threshold.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from math import isfinite, nextafter

from app.backend.contracts.recommendation import FeasibleCandidate, RankedCandidate


@dataclass(frozen=True)
class RankingConfig:
    """Configurable heuristic defaults, not calibrated or real-world safety policy.

    Weights are used as supplied, without requiring or forcing a unit sum.
    Travel reference is minutes; minimum SOC and risk band are percentage points.
    """

    weight_probability: float = 1.0
    weight_travel: float = 0.2
    weight_soc_risk: float = 0.2
    weight_virtual_load: float = 0.3
    travel_reference_minutes: float = 30.0
    min_arrival_soc_pct: float = 10.0
    soc_risk_band_pct: float = 20.0
    mean_service_minutes: float = 30.0
    camera_trust: float = 0.8
    max_observation_age_minutes: float = 15.0

    def __post_init__(self) -> None:
        _validate_config(self)


@dataclass(frozen=True)
class RankingInput:
    """Required measured metadata; the nested shared candidate remains mutable."""

    candidate: FeasibleCandidate
    travel_minutes: float
    working_ports: int
    queue_waiting: int | None = None
    queue_confidence: float | None = None
    queue_age_minutes: float | None = None


@dataclass(frozen=True)
class RankingBreakdown:
    probability: float
    normalized_travel_time: float
    normalized_soc_risk: float
    normalized_virtual_load: float
    score: float
    wait_minutes: float = 0.0
    camera_weight: float = 0.0


def _nonnegative_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite nonnegative number")
    try:
        number = float(value)
    except OverflowError:
        raise ValueError(f"{name} must be a finite nonnegative number") from None
    if not isfinite(number) or number < 0:
        raise ValueError(f"{name} must be a finite nonnegative number")
    return number


def _positive_number(value: object, name: str) -> float:
    number = _nonnegative_number(value, name)
    if number == 0:
        raise ValueError(f"{name} must be positive")
    return number


def _percentage(value: object, name: str) -> float:
    number = _nonnegative_number(value, name)
    if number > 100:
        raise ValueError(f"{name} must be between 0 and 100")
    return number


def _capacity(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError("working_ports must be a positive integer")
    _positive_number(value, "working_ports")
    return value


def _validate_config(config: RankingConfig) -> None:
    if not isinstance(config, RankingConfig):
        raise ValueError("config must be a RankingConfig")
    weights = [
        _nonnegative_number(getattr(config, name), name)
        for name in (
            "weight_probability",
            "weight_travel",
            "weight_soc_risk",
            "weight_virtual_load",
        )
    ]
    if not any(weight > 0 for weight in weights):
        raise ValueError("at least one weight must be positive")
    _positive_number(config.travel_reference_minutes, "travel_reference_minutes")
    _percentage(config.min_arrival_soc_pct, "min_arrival_soc_pct")
    _positive_number(config.soc_risk_band_pct, "soc_risk_band_pct")
    _positive_number(config.mean_service_minutes, "mean_service_minutes")
    if _nonnegative_number(config.camera_trust, "camera_trust") > 1:
        raise ValueError("camera_trust must be between 0 and 1")
    _nonnegative_number(config.max_observation_age_minutes, "max_observation_age_minutes")


def _bounded_ratio(value: float, reference: float) -> float:
    if value <= reference:
        ratio = value / reference
        result = ratio / (1 + ratio)
    else:
        result = 1 / (1 + reference / value)
    return min(result, nextafter(1.0, 0.0))


def normalize_travel_time(travel_minutes: float, travel_reference_minutes: float) -> float:
    """Actual travel minutes mapped continuously to [0, 1)."""
    travel = _nonnegative_number(travel_minutes, "travel_minutes")
    reference = _positive_number(travel_reference_minutes, "travel_reference_minutes")
    return _bounded_ratio(travel, reference)


def normalize_soc_risk(
    arrival_soc_pct: float, min_arrival_soc_pct: float, soc_risk_band_pct: float
) -> float:
    """Risk in [0, 1]; below-threshold input violates the feasibility precondition."""
    arrival = _percentage(arrival_soc_pct, "arrival_soc_pct")
    minimum = _percentage(min_arrival_soc_pct, "min_arrival_soc_pct")
    band = _positive_number(soc_risk_band_pct, "soc_risk_band_pct")
    if arrival < minimum:
        raise ValueError("arrival_soc_pct must meet min_arrival_soc_pct before ranking")
    excess = arrival - minimum
    return 0.0 if excess >= band else 1 - excess / band


def normalize_virtual_load(virtual_load: float, working_ports: int) -> float:
    """Expected allocations relative to operational ports, not currently busy ports."""
    capacity = _capacity(working_ports)
    load = _nonnegative_number(virtual_load, "virtual_load")
    return _bounded_ratio(load, float(capacity))


def _validated_input(item: RankingInput, config: RankingConfig) -> RankingInput:
    if not isinstance(item, RankingInput):
        raise ValueError("each entry must be a RankingInput")
    candidate = item.candidate
    if not isinstance(candidate, FeasibleCandidate):
        raise ValueError("candidate must be a FeasibleCandidate")
    if isinstance(candidate, RankedCandidate):
        raise ValueError("RankingInput requires an unranked FeasibleCandidate")
    probability = _nonnegative_number(candidate.p_available, "p_available")
    if probability > 1:
        raise ValueError("p_available must be between 0 and 1")
    arrival = _percentage(candidate.arrival_soc_pct, "arrival_soc_pct")
    if arrival < config.min_arrival_soc_pct:
        raise ValueError("arrival_soc_pct must meet min_arrival_soc_pct before ranking")
    _nonnegative_number(candidate.distance_km, "distance_km")
    _nonnegative_number(candidate.detour_km, "detour_km")
    if not isinstance(candidate.station_id, str) or not candidate.station_id:
        raise ValueError("station_id must be a nonempty string")
    if (
        not isinstance(candidate.eta, datetime)
        or candidate.eta.tzinfo is None
        or candidate.eta.utcoffset() is None
    ):
        raise ValueError("eta must be timezone-aware")
    travel = _nonnegative_number(item.travel_minutes, "travel_minutes")
    capacity = _capacity(item.working_ports)
    snapshot = FeasibleCandidate.model_validate(candidate.model_dump())
    waiting, confidence, age = _validated_queue(item)
    return RankingInput(snapshot, travel, capacity, waiting, confidence, age)


def _validated_queue(item: RankingInput) -> tuple[int | None, float | None, float | None]:
    """A camera observation is all three fields or none of them."""
    waiting, confidence, age = item.queue_waiting, item.queue_confidence, item.queue_age_minutes
    if waiting is None and confidence is None and age is None:
        return None, None, None
    if waiting is None or confidence is None or age is None:
        raise ValueError("queue observation needs waiting, confidence and age together")
    if isinstance(waiting, bool) or not isinstance(waiting, int) or waiting < 0:
        raise ValueError("queue_waiting must be a nonnegative integer")
    if _nonnegative_number(confidence, "queue_confidence") > 1:
        raise ValueError("queue_confidence must be between 0 and 1")
    return waiting, float(confidence), _nonnegative_number(age, "queue_age_minutes")


def blend_wait_minutes(
    *, virtual_load: float, working_ports: int, item: RankingInput, config: RankingConfig
) -> tuple[float, float]:
    """Expected wait and the camera weight used, from a camera view and the load estimate.

    The estimate treats expected allocations as vehicles that will queue. A fresh
    camera view replaces part of it by ``camera_trust * confidence``; a missing,
    zero-confidence or stale view leaves the estimate untouched.
    """
    per_port = config.mean_service_minutes / working_ports
    estimate = virtual_load * per_port
    waiting, confidence, age = item.queue_waiting, item.queue_confidence, item.queue_age_minutes
    if waiting is None or confidence is None or age is None:
        return estimate, 0.0
    if age > config.max_observation_age_minutes:
        return estimate, 0.0
    weight = config.camera_trust * confidence
    return weight * waiting * per_port + (1 - weight) * estimate, weight


def _score_validated(
    item: RankingInput, config: RankingConfig, virtual_load: float
) -> RankingBreakdown:
    probability = item.candidate.p_available
    load = normalize_virtual_load(virtual_load, item.working_ports)
    wait, camera_weight = blend_wait_minutes(
        virtual_load=float(virtual_load), working_ports=item.working_ports, item=item, config=config
    )
    travel = normalize_travel_time(item.travel_minutes + wait, config.travel_reference_minutes)
    risk = normalize_soc_risk(
        item.candidate.arrival_soc_pct, config.min_arrival_soc_pct, config.soc_risk_band_pct
    )
    score = (
        config.weight_probability * probability
        - config.weight_travel * travel
        - config.weight_soc_risk * risk
        - config.weight_virtual_load * load
    )
    if not isfinite(score):
        raise ValueError("ranking score must be finite")
    return RankingBreakdown(probability, travel, risk, load, score, wait, camera_weight)


def score_candidate(
    item: RankingInput, config: RankingConfig, virtual_load: float = 0.0
) -> RankingBreakdown:
    """Validate and explain a candidate using the same scoring path as ranking."""
    _validate_config(config)
    return _score_validated(_validated_input(item, config), config, virtual_load)


def rank_candidates(
    candidates: Iterable[RankingInput],
    config: RankingConfig,
    virtual_loads: Mapping[str, float],
) -> tuple[RankedCandidate, ...]:
    """Return every candidate by descending score, exact ties by station ID.

    Validate the whole supplied load snapshot, even unused entries. Missing
    station entries mean zero load, not missing measured capacity. Candidate
    DTOs are revalidated into snapshots before scoring; outputs are newly
    validated shared DTOs and preserve the supplied probability exactly.
    """
    _validate_config(config)
    loads: dict[str, float] = {}
    for station_id, load in virtual_loads.items():
        if not isinstance(station_id, str) or not station_id:
            raise ValueError("virtual_load station_id must be a nonempty string")
        loads[station_id] = _nonnegative_number(load, "virtual_load")
    seen: set[str] = set()
    scored: list[tuple[FeasibleCandidate, RankingBreakdown]] = []
    for candidate in candidates:
        selected = _validated_input(candidate, config)
        station_id = selected.candidate.station_id
        if station_id in seen:
            raise ValueError(f"duplicate station_id: {station_id}")
        seen.add(station_id)
        breakdown = _score_validated(selected, config, loads.get(station_id, 0.0))
        scored.append((selected.candidate, breakdown))
    scored.sort(key=lambda entry: (-entry[1].score, entry[0].station_id))
    return tuple(
        RankedCandidate(**candidate.model_dump(), rank=rank, score=breakdown.score)
        for rank, (candidate, breakdown) in enumerate(scored, start=1)
    )
