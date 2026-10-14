# Recommendation Module Specification — C/Kiên

## Objective

Select a feasible primary and backup station using routes, SOC, predicted availability, and virtual-load ranking while keeping prediction probability separate from heuristic allocation score.

## Injected Dependencies

Receive station/status repositories, `RouteProvider`, `Predictor`, clock/config, and virtual-load store through public ports. Do not instantiate file, Goong, or model implementations inside business services.

## Required Behavior

Filter incompatible or unreachable stations before ranking. Compute arrival SOC with documented units and configurable safety threshold. Backup follows origin → primary → backup and must remain reachable if primary cannot charge. Handle no primary/backup explicitly. Compute `plan_p` only with its independence assumption. Apply virtual load to primary charging buckets, not backup; retries with the same request ID/payload are idempotent and conflicting reuse is rejected.

## Boundaries and Non-goals

This module contains no FastAPI objects, filesystem access, external HTTP client, ML training, or simulator loop. Ranking weights and normalization are configurable and reported as heuristic. Charge-to advice is deferred.

## Required Tests and Done Criteria

Test SOC edges, connector filtering, backup route/SOC, no-plan responses, ranking penalties, zero capacity, idempotent retry, request conflicts, reset/TTL, and concurrent updates. Done means the public service works entirely with fakes and returns contract-valid, source-labelled results.

## C5 Service Integration

`RecommendationService.recommend` is async and accepts scenario-specific status repositories and predictors, a shared route provider, ranking configuration, explicit source `data_type`, and a required `max_prediction_horizon_minutes` mapping. Composition must supply each horizon from the same trained artifact's `split_metadata.max_horizon_minutes` used by its predictor; the frozen Predictor port does not expose that capability. Missing, invalid, or incomplete capability configuration fails explicitly. Unexpected inference errors, including capability/artifact mismatches, propagate rather than being converted to candidate exclusions.

C3 feasibility precedes inference. Physical arrival is rounded up to a positive five-minute prediction bucket, and capability filtering checks the resulting horizon relative to `observed_at`, including delayed departure and cumulative fallback travel. Unsupported primary or backup candidates are excluded without inference, extrapolation, or probability clamping. Returned plan ETA is the prediction bucket, not an exact arrival guarantee. Observations require the aligned +07:00 grid; departure must be +07:00 and not precede observation.

Primary is selected by C4 ranking. Backup distance, travel duration, and SOC use origin → primary → backup without charging at primary; only physical arrival, not the rounded primary bucket, determines fallback departure. Detour is `max(0, routed itinerary distance - direct origin→destination road distance)`, including the onward leg to destination. Missing routes exclude the affected edge, while provider failures propagate. Responses preserve model probabilities, label combined probability with the independence assumption, and explain actual exclusions. No-plan reports `model_version="not_used"` and explicitly injected source provenance.

C5 does not reserve virtual load, implement idempotency, integrate the API/simulator, or provide time-shift/charge-to advice; those remain C6–C9 or deferred. Focused offline verification: `uv run pytest app/backend/modules/recommendation/tests app/backend/tests/infrastructure/test_goong_routing.py app/backend/tests/infrastructure/test_route_cache.py -v`; canonical handoff verification remains `make ci`.
