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

## C6 Virtual Allocation

`AllocationCoordinator.recommend` wraps read-only C5 with a serialized lookup → decide → reserve cycle. Instantiate it with one application-scoped `VirtualLoadStore`, an explicit `charge_duration_minutes` assumption and a `service_factory(reader)` that constructs C5 with `virtual_load_provider=reader`. Default expected compliance/load is 1.0; no guessed charging duration is supplied. Direct `RecommendationService.recommend` remains read-only, and without a reader preserves zero-load behavior. C5 queries each primary candidate's prediction ETA and scenario, and each backup's routed fallback ETA. Load changes ranking scores only, never model probabilities.

The store API is `lookup(request_id, payload_hash)`, `reserve(request_id, payload_hash, result, reservation)`, `snapshot(at, scenario)` and `reset()`, all async. Passing the result extends the owner-plan sketch to support exact response replay, including no-plan. Request IDs conflict globally across scenarios; SHA-256 covers the entire revalidated JSON request using sorted keys and compact serialization. Receipts store immutable JSON and expose newly validated response copies on access. Only primary creates a reservation; backup creates no expected demand.

Buckets are `(scenario, station_id, five_minute_start)` on the +07:00 grid. Reservation ETA must be aligned; queries floor into the containing bucket. A positive finite charge duration is capped at 24 hours (288 five-minute buckets) and covers the half-open interval `[eta, eta + duration)`, including a partial final bucket. Counters represent expected allocated demand, not occupancy, ports_free, ML prediction or a confirmed port booking.

Receipt TTL defaults to 30 processing-time minutes, is configurable, and uses an injected aware clock rather than observation time. Expiry is inclusive at `expires_at`; reads/writes prune expired receipts and their own load contributions. The ID is reusable after expiry. TTL retention and charging duration are separate assumptions: demand is removed on expiry even if the modeled charging interval has not ended. Per-receipt decimal contributions avoid subtraction drift and negative residuals. Zero expected load retains a receipt without load.

All coordinators sharing a store share its decision lock. Lock acquisition order is decision → state; C5 external awaits hold only the decision lock, while store mutations contain no external awaits. This serializes expensive work intentionally for the bounded single-worker MVP. Independent store reset acquires the same decision lock, waits for an active decision to finish, then atomically clears receipts and buckets; coordinator reset delegates without reacquiring that lock. Cancellation before commit leaves no reservation; a committed decision remains replayable. Direct store reserve is counter-atomic but cannot replace the coordinator's decision serialization.

`RecommendationAllocationStrategy.select(context)` implements the frozen synchronous `AllocationStrategy` port. Supply immutable `CandidateMetadata(travel_minutes, working_ports)` and expected-load mappings keyed by `(scenario, station_id, eta)`, measured and validated upstream. Missing eligible-candidate metadata raises; below-threshold SOC is filtered. No speed, capacity, routing, prediction or Driver state is inferred/accessed. With a selected primary and no independent fallback evidence it returns primary-only, `backup=None` and `plan_p=primary.p_available`; with no eligible candidate it returns no plan and an explicit no-eligible-station reason. It copies injected mappings and does not mutate input candidates.

Limitations: memory is process-local, not durable or multi-worker/distributed; virtual allocations do not guarantee arrival or a physical port. C7–C8 must wire one singleton store into both the coordinator and C5's `virtual_load_provider`, plus reset and existing `RequestConflictError`→409 mapping in the API composition root; separate stores would record reservations that ranking cannot see. C9 must use independent simulation state; this task does not change API or simulation wiring. Focused C6 checks: `uv run pytest app/backend/tests/infrastructure/test_virtual_load.py app/backend/modules/recommendation/tests/test_allocation.py app/backend/modules/recommendation/tests/test_service.py -v`; complete acceptance still requires fresh `make ci` on a clean revision.
