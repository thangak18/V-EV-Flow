# FastAPI and Composition Specification — C/Kiên

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
