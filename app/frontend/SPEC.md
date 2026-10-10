# Frontend Specification — D/Tú

## Objective

Deliver one React + Vite application with Driver and Operator routes. It must work first against the OpenAPI mock and later against the real backend without changing component payload shapes.

## Contract Boundary

All HTTP calls pass through `src/services/api`; components do not call `fetch` directly. Types are generated from `app/backend/contracts/openapi.yaml` into `src/types/api.generated.ts` and are not hand-edited. Runtime parsing/error handling must not silently accept an incompatible payload.

## P0 Output

Driver is mobile-first and provides preset origin/destination, SOC/connector input, explicit submit, route/station map, primary/backup cards, ETA probability, arrival SOC, reasons, and loading/error/empty/retry states. Operator is desktop-first and provides scenario/time selection, pressure legend/map, and three-strategy metrics with seed/version/source labels. Mock and simulated data are visibly labelled.

## Behavioral Invariants

Do not call `/recommend` during render or passive refetch because it records virtual load. Do not display ranking score as probability. Preserve plan independence assumption and simulation limitations. The UI remains usable as a textual list when map tiles fail.

## Freedom, Tests, and Done Criteria

Tú chooses component composition and visual styling within `docs/UI_SPEC.md`. Test the API service, core states, responsive Driver layout, Operator metrics, map failure fallback, and the mock vertical slice. Done means production build succeeds, generated types are current, screenshots cover Driver/Operator, and no UI fixture contradicts OpenAPI examples.
