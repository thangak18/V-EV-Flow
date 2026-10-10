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
