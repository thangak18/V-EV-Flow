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

`RecommendationService.recommend` is async and accepts scenario-specific status repositories and predictors, a shared route provider, ranking configuration, explicit source `data_type`, and a required `max_prediction_horizon_minutes` mapping. Current fake composition supplies the settings-backed `fake_prediction_horizon_minutes` capability. For deferred model integration, composition must supply each horizon from the same trained artifact's `split_metadata.max_horizon_minutes` used by its predictor; the frozen Predictor port does not expose that capability. Missing, invalid, or incomplete capability configuration fails explicitly. Unexpected inference errors, including capability/artifact mismatches, propagate rather than being converted to candidate exclusions.

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

Limitations: memory is process-local, not durable or multi-worker/distributed; virtual allocations do not guarantee arrival or a physical port. C7–C8 now wire one application-scoped store into both the coordinator and C5's `virtual_load_provider`, plus reset and existing `RequestConflictError`→409 mapping; separate stores would record reservations ranking cannot see. C6 itself remains independent of HTTP. Later simulator integration must use independent state and remains deferred after C9. Focused C6 checks: `uv run pytest app/backend/tests/infrastructure/test_virtual_load.py app/backend/modules/recommendation/tests/test_allocation.py app/backend/modules/recommendation/tests/test_service.py -v`; complete acceptance still requires fresh `make ci` on a clean revision.

## C7/C8 API Integration

The API calls `AllocationCoordinator.recommend`, not the legacy facade. C3 filters connector/SOC feasibility before C4 ranking; C5 sends ETA-bucketed prediction inputs, preserves model probability, selects a reachable primary then a primary-to-backup leg without charging at the failed primary, and computes `plan_p` under its independence assumption. C6 reads virtual load per candidate ETA, reserves only the selected primary, replays matching request IDs, rejects conflicts with `RequestConflictError`, and synchronizes reset with active decisions. Scenario mappings remain explicit. This is one-worker in-memory expected demand, not a physical booking. Charge-to, time shift, real model activation, and AI simulator integration remain deferred.

## C9 Implementation and Consumer Handoff

### Feasibility and measured ranking inputs

C3 evaluates each validated route alternative before prediction. A station must support the vehicle connector, have positive working capacity (`n_ports - ports_broken`) and arrival SOC at least the configured minimum (default demo 10%). Mixed-connector aggregate status is conservatively rejected because v0 has no per-connector capacity counts. Busy ports are not broken ports: present occupancy is not proof of availability at ETA. Energy consumed is `distance_km * consumption_kwh_per_km`; arrival SOC is `soc_pct - 100 * energy_kwh / battery_kwh`. Invalid/non-finite measurements fail validation rather than inventing feasibility. Rejections retain reason codes for incompatible connector, unsupported aggregate capacity, no working ports or insufficient SOC. These are heuristic demo assumptions, not road-safety guarantees.

C4 accepts `RankingInput(candidate, travel_minutes, working_ports)` and `RankingConfig`. Its defaults are probability weight 1.0, travel 0.2, SOC risk 0.2 and virtual load 0.3; travel reference 30 minutes, SOC risk band 20 percentage points. Score is weighted probability minus the three penalties. Travel normalizes `t/(t+reference)`, expected load `load/(load+working_ports)`, and SOC risk clamps `1-(arrival-minimum)/band` to [0,1]. Actual routed duration and validated working capacity are required; no guessed speed or total-port substitution. Missing load means zero. Sorting is descending score with station-ID tie-break. Score is not a probability; `p_available` is unchanged. Composition currently exposes the SOC threshold but uses the other RankingConfig defaults; weight changes require explicit composition configuration, not undocumented environment keys.

### Camera queue observations

`RankingInput` optionally carries `queue_waiting`, `queue_confidence` and `queue_age_minutes` (all or none). `blend_wait_minutes` mixes the camera-based wait with the virtual-load estimate by `camera_trust * confidence`, ignoring views older than `max_observation_age_minutes`; the time term becomes `norm(travel + wait)`. `RecommendationService` takes an optional `QueueObservationSource`, observes at the request's `observed_at`, adds an explanatory reason for primary and backup, and adds the observation's `data_type` to provenance. Without a source the behavior is unchanged except that the estimated wait from virtual load joins the time term.

### End-to-end service behavior

`RecommendationService` receives station repository, scenario-indexed status repositories/predictors, RouteProvider, ranking config, explicit non-model data label, matching scenario horizon limits and an optional read-only `VirtualLoadReader`. C5 reads current status with `lags=(0,)`; later real Predictor binding must manage its own current/lag requirements. It validates route alternatives, uses feasible actual origin→station travel, and evaluates onward routing to destination for detour. Direct origin→destination road distance is the reference; detour is nonnegative routed itinerary excess. An explicit empty route tuple excludes an edge; provider failures propagate.

Physical ETA comes from travel duration. Prediction ETA rounds up to the +07 five-minute grid, at least one bucket after observation. Horizon checks use prediction ETA minus observation, including delayed departures and cumulative fallback travel. Known unsupported candidates are filtered before inference; capability inconsistency or unexpected inference errors are not disguised as no-plan. C4 chooses primary after C3; backups are separately routed from that primary at **physical**, not rounded, primary arrival. They use origin→primary→backup cumulative distance/duration and SOC, with no charging at failed primary. Backup probability is obtained for its own fallback bucket. Load lookup also uses those exact primary/fallback prediction buckets and the request scenario.

Two selected plans use `1-(1-p_primary)*(1-p_backup)` with `plan_p_assumption="independent_stations"`; primary-only uses primary probability with no combined assumption; no-plan returns null plans/probability, explanatory reasons and `model_version="not_used"`. All are contract-valid results, and the coordinator records no-plan receipts too. Selected predictions must agree on model/contract/provenance. Result data type combines prediction and explicitly injected non-model provenance: mock+mock stays mock; file simulated+fake prediction becomes mixed. It does not certify source accuracy or infer live occupancy from Goong routing.

### Public allocation entry point and team boundary

C8 calls `await container.allocation_coordinator.recommend(request)` with `RecommendationRequest` and receives `RecommendationResult`; reset calls its async `reset()`. The app-scoped coordinator factory binds the same store to C5 snapshots and C6 reservations. Settings inject assumed duration (default 60 minutes, maximum 1440), expected load (default 1.0) and processing TTL (default 1800 seconds). Hash/receipt lookup precedes external work; a shared decision lock serializes the complete read→decide→commit transaction, while the store lock protects only atomic state operations. All primary charging buckets commit with the immutable response receipt. Retry avoids repeated routing/inference; payload conflict is global across scenarios. Expiry/reset reverses each receipt contribution; cancellation before commit leaves none. Direct C5 remains a separate read-only recommendation responsibility.

`RecommendationAllocationStrategy.select(AllocationContext)` remains synchronous and pure. Frozen v0 candidates lack travel duration/capacity, so upstream must inject verified `CandidateMetadata` and load by `(scenario, station_id, eta)`. It rejects missing eligible metadata and never accesses Driver storage, HTTP or models. Without verified fallback evidence it returns primary-only rather than claiming the second origin-feasible station is reachable through primary. API `/simulate` has not been bound to this strategy or the real runner/model; that joint A/B/C integration is post-C9. Charge-to, time-shift, what-if, physical reservations and distributed/persistent allocation remain outside implemented scope.

Reproduction and exact HTTP examples: `docs/runbooks/backend-demo.md`; current command/count/revision evidence: `docs/runbooks/backend-verification-evidence.md`. Independent human review and fresh CI on the final clean revision remain the release gate.


## P1 time-shift probes

Optional time_shift_minutes=(15,30) probes the same selected primary from the unchanged observed_at. Travel time is held fixed and ETA cannot exceed the injected artifact capability. Keep the earliest delay tied at the best probability and require >=5 percentage-point improvement. Estimates are advisory only; current primary/backup and one C6 reservation stay unchanged. Evaluated-without-improvement is explicit, not fabricated positive advice.
