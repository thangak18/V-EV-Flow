# FastAPI and Composition Specification — C/Kiên

## Current runtime integration

Runtime integration now supports `DATA_BACKEND=file`, `PREDICTOR_BACKEND=model` and `SIMULATION_BACKEND=stateful`. The historical C7–C9 fake-only limitations below are superseded for this explicit selection; defaults remain mock/fake. `runtime.py` binds the public model loader, scenario-specific histories/horizons, real simulator and pure AI allocation. See `docs/runbooks/runtime-integration.md` for launch, provenance, checks and limitations.

## Objective

Expose the agreed `/api` endpoints, assemble the modular monolith, and map typed domain results/errors to the committed OpenAPI contract.

## Responsibilities

Implement `/stations`, `/predict`, `/recommend`, `/pressure`, `/simulate`, optional P1 `/whatif`, and demo `/reset` as documented. Route handlers validate/translate HTTP only; recommendation, prediction, simulation, and persistence behavior remains in modules/adapters. The composition root creates settings and concrete dependencies once at startup.

## OpenAPI and Errors

Use stable operation IDs and declared response models/examples. Generate `contracts/openapi.yaml` deterministically. Preserve standard FastAPI 422 validation responses; map domain errors to documented `{code, message, details}` responses. No-plan is a successful empty plan with reasons; missing station is 404, request conflict 409, and unavailable required dependency 503.

## Runtime Rules

Support one demo worker while allocation is in memory. Lock allocation/reset updates. `/simulate` state is isolated from Driver state. Configure CORS from settings. Health/readiness must distinguish process availability from dependency readiness.

## Required Tests and Done Criteria

Test every success/error response, DI selections, CORS, idempotency, reset, source labels, OpenAPI generation, and mock vertical slice. Done means frontend can use only generated types/examples and every documented endpoint passes contract validation.

## C7/C8 Runtime Integration

Settings select mock/file data, fake/model prediction, and fake/Goong routing. Unavailable real/model selections fail explicitly. `AppContainer` owns scenario-scoped predictors/status repositories, one `VirtualLoadStore`, and one `AllocationCoordinator`. Routes delegate `/stations`, `/predict`, `/recommend`, `/pressure`, `/simulate`, and `/reset` to those dependencies; `/whatif` remains P1 unavailable. API prediction observations and ETAs require +07:00 five-minute buckets and supported positive horizons. Pressure is the fixed 30-minute `1 - p_available` risk proxy, not occupancy. Goong clients owned by the app close through lifespan.

## C9 Runtime Contract and Handoff

### Composition and public endpoint mapping

`create_app(settings=None, *, route_client=None)` validates Settings and constructs AppContainer before serving. Environment/default selection comes from Settings/get_settings; tests may pass explicit settings and HTTP transport clients. Mock/file repositories, scenario maps, ranking config, one shared VirtualLoadStore and one AllocationCoordinator are bound once per app. Fake prediction is the only currently selectable Predictor; real/model selection fails startup rather than serving fake results under a real label. Fake/Goong routing is supported with explicit prerequisites. Lifespan closes only the app-owned Goong client. Full adapter matrix and path validation are in infrastructure SPEC.

| Public endpoint | Dependency and actual behavior |
| --- | --- |
| `GET /api/health` | HTTP-process liveness, `{status: ok}` |
| `GET /api/ready` | AppContainer.ready and selected adapter names; composition-only, not live network/model/status probe |
| `GET /api/stations` | StationRepository; StationListResponse with mock or simulated envelope, source notes and per-station assumptions |
| `POST /api/predict` | Station existence + time/horizon + station connector compatibility validation, then `predictors_by_scenario[scenario]`; validated PredictionResult |
| `POST /api/recommend` | Request validation, then `await allocation_coordinator.recommend(request)`; C5 decisions with C6 receipt/load commit |
| `GET /api/pressure?scenario=...&time=...` | Scenario Predictor at time+30 minutes for each station, fixed `1-p_available` proxy |
| `POST /api/simulate` | `simulation.run(request, allocation)`; configured FakeSimulationRunner, not real strategy comparison |
| `POST /api/reset` | ResetRequest (`{}` valid); await coordinator reset and clear legacy request cache, return ResetResponse |
| `POST /api/whatif` | Always 503 FEATURE_NOT_READY; no request-body schema declared in current OpenAPI |

`/openapi.json` and `/docs` expose the generated runtime schema. Stable operation IDs, endpoint signatures and committed examples are unchanged by C9. Runtime domain mapping can include errors not explicitly enumerated in each frozen endpoint's responses; this documentation does not add declarations or hand-edit artifacts. Signature/model changes require a separate reviewed contract PR.

### Time, validation and response semantics

Prediction observations and ETA must be aware +07:00 five-minute grid values (zero seconds/microseconds). Horizon must be positive, a five-minute multiple and no greater than `FAKE_PREDICTION_HORIZON_MINUTES` (default 60). Settings requires this fake capability to be at least 30, so pressure's fixed horizon is supported; merely checking the field does not deploy a model. Recommendation observation uses the same grid, departure uses +07 and cannot precede observation but need not be five-minute aligned. C5 physical travel ETA is rounded up for prediction; returned plan ETA is that conservative bucket. Candidate horizons include departure delay and fallback cumulative travel; unsupported candidates are excluded before inference rather than extrapolated.

Pydantic validates required fields, coordinate/SOC bounds, enums, aware times and extra fields. Additional semantic failures use HTTPException 422. `/predict` resolves Station metadata, preserves unknown-station 404, validates time/horizon and exact membership in its `connector_types` before invoking the scenario Predictor, then matches output station/ETA. Unsupported connectors return 422 without inference. Compatibility is not current occupancy: a supported but occupied connector may still have future availability. Neither the station/request DTO nor Predictor probability, model version or provenance is changed. FakePredictor still has no model-specific status/eligibility checks, and successful fake prediction does not establish reachability or connector-specific trained-model capability at mixed-connector stations. Recommendation C3 separately checks connector/capacity/SOC. No-plan is HTTP 200 with null primary/backup/plan_p, reasons and not_used model_version; it is distinct from dependency failure.

| Status | Domain/client failure | Response |
| --- | --- | --- |
| 404 | StationNotFoundError | `code="STATION_NOT_FOUND"` |
| 409 | RequestConflictError | `code="REQUEST_CONFLICT"` |
| 422 | Invalid request model/time/horizon or station connector incompatibility | FastAPI `detail` list or semantic-validator `detail` string |
| 503 | DataSourceUnavailableError | `code="DATA_SOURCE_UNAVAILABLE"` |
| 503 | ModelNotReadyError | `code="MODEL_NOT_READY"`; mapping exists, model backend selection presently fails startup |
| 503 | RouteUnavailableError | `code="ROUTE_UNAVAILABLE"` |
| 503 | FeatureNotReadyError | `code="FEATURE_NOT_READY"` for P1 what-if |

Domain envelopes are `{code, message, details}` with uppercase codes; unmapped DomainError defaults to 500. Dependency/configuration failure before app startup is not a served HTTP error. Empty road routes exclude a candidate; an outage is not converted into a successful no-plan or silent fake fallback.

### HTTP idempotency and reset

Use a stable request_id only when retrying the exact intent. C6 hashes the fully revalidated payload, including scenario; same ID/payload returns a defensive copy of the recorded response without another reservation, routing or prediction. Same ID/different payload returns 409 globally across scenarios. No-plan also replays. A new user intent uses a new ID, not a new ID for each render/network retry. TTL (default 1800 processing-time seconds) expires receipts and removes their own expected demand; the ID then becomes reusable. Request observation does not control receipt TTL.

Only selected primary expected demand is added for the assumed charging interval (default 60 minutes, compliance/load 1.0); backups are not physical bookings. Decision locking serializes lookup→C5→commit; reset takes the same shared decision lock so a pre-reset decision cannot repopulate state after the reset completes. `/reset` clears Driver receipts/load and legacy cache, not generated histories, model files, Goong routes or simulation fixtures. API integration tests inspect the public VirtualLoadStore at returned ETA to prove load 1→1→0 across first/retry/reset; matching response JSON alone is not enough.

### Pressure, source labels and deferred integrations

Pressure uses the scenario-specific Predictor with ETA exactly 30 minutes after the validated query time. `pressure_score=1-p_available` is an availability-risk proxy, neither occupancy nor virtual-load ranking. Fake predictor produces identical 0.75 in all scenarios, so switching mock scenarios does not demonstrate scenario-sensitive trained probabilities. URL-encode query time to preserve `+07:00`.

Supported mock/fake composition returns mock station/prediction/recommendation data; file station/status is simulated, fake prediction remains mock and successful recommendations combine them as mixed. No-plan uses explicit non-model provenance. Goong source does not turn fake probabilities into live availability. `/simulate` still returns FakeSimulationRunner's deterministic fake metrics/hash/model_version for any data mode/strategy; those values do not prove the real runner or AI works. The HTTP DTO has no simulation data_type field, so UI must identify fake-sim-v1 truthfully rather than implying measured results.

Post-C9 integration must supply Bảo's public DefaultSimulationRunner and request-specific strategy selection, verified immutable fixtures/config, Thắng's public Predictor with trusted artifacts/scenario horizons/history/provenance, and Kiên's pure AllocationStrategy with actual route/capacity/load metadata. Runner/Driver state remains separate; no new binding is claimed here. Tú's frontend consumes committed types, maps domain errors, preserves retry IDs, labels source/pressure/independence assumptions and handles null plans. One process/worker remains mandatory. Charge-to, time-shift, distributed storage and what-if remain deferred.

Executable setup, generation, all endpoints, error/retry/reset sequences and troubleshooting: `docs/runbooks/backend-demo.md`. Tested revision, gate results, HTTP observations, provenance and remaining release blockers: `docs/runbooks/backend-verification-evidence.md`.
