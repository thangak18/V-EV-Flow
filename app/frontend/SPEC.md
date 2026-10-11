# Frontend Specification — D/Tú

## Objective

Deliver one React + Vite application with Driver and Operator routes. It must work first against the OpenAPI mock and later against the real backend without changing component payload shapes.

## Contract Boundary

All HTTP calls pass through `src/services/api`; components do not call `fetch` directly. Types are generated from `app/backend/contracts/openapi.yaml` into `src/types/api.generated.ts` and are not hand-edited. Runtime parsing/error handling must not silently accept an incompatible payload.

## P0 Output

Driver is mobile-first and provides preset origin/destination, SOC/connector input, explicit submit, route/station map, primary/backup cards, ETA probability, arrival SOC, reasons, and loading/error/empty/retry states. Operator is desktop-first and provides scenario/time selection, pressure legend/map, and three-strategy metrics with seed/version/source labels. Mock and simulated data are visibly labelled.

## Behavioral Invariants

Do not call `/recommend` during render or passive refetch because it records virtual load. Do not display ranking score as probability. Preserve plan independence assumption and simulation limitations. The UI remains usable as a textual list when map tiles fail.

## Map SDK choice (verified)

| Field | Value |
| --- | --- |
| SDK | `@goongmaps/goong-js` |
| Version | `1.0.9` (official docs current) |
| Delivery | jsDelivr CDN script + CSS from https://docs.goong.io/javascript/ (not npm-bundled; avoids audit-critical transitive deps) |
| Style | `https://tiles.goong.io/assets/goong_map_web.json` |
| Key | `VITE_GOONG_MAP_KEY` (public maptiles key; never commit secrets) |
| Coordinates | Contract uses `{lat,lng}`; conversion to `[lng, lat]` happens only inside `GoongMapAdapter` |
| Attribution | Map tiles © Goong |
| Offline / tests | `FakeMapAdapter` + always-visible textual station list |

## Freedom, Tests, and Done Criteria

Tú chooses component composition and visual styling within `docs/UI_SPEC.md`. Test the API service, core states, responsive Driver layout, Operator metrics, map failure fallback, and the mock vertical slice. Done means production build succeeds, generated types are current, screenshots cover Driver/Operator, and no UI fixture contradicts OpenAPI examples.
