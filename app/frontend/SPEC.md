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
| Offline / tests | `FakeMapAdapter` draws a corridor schematic with markers when `VITE_GOONG_MAP_KEY` is empty; textual station list always visible |
| Env | Vite `envDir` is the repo root so `VITE_GOONG_MAP_KEY` in `/.env` is picked up after restart |

## Freedom, Tests, and Done Criteria

Tú chooses component composition and visual styling within `docs/UI_SPEC.md`. Test the API service, core states, responsive Driver layout, Operator metrics, map failure fallback, and the mock vertical slice. Done means production build succeeds, generated types are current, screenshots cover Driver/Operator, and no UI fixture contradicts OpenAPI examples.

## P0 demo completion

AppShell reads the existing dictionary-shaped `/ready` endpoint once to display the
configured Driver routing/prediction mode. This is configuration information, not a
live provider-health probe. All calls still pass through ApiClient; mounting or
resetting a page never calls `/recommend` automatically.

The explicit Đặt lại demo button calls the existing versioned `/reset` request,
then remounts the current page only after a confirmed success. Failed or
unconfirmed resets preserve the visible result and support retry. Reset clears
Driver virtual allocation/receipts; it does not rewrite histories, model files or
Goong caches. Operator output is independently reproducible from the same seed.

Known backend feasibility reasons are translated for the Driver; unknown reasons
are preserved. Technical identifiers remain in collapsed details. Short nonzero
road distances are no longer displayed as 0 km, and probabilities near zero/one
use <1%/>99% rather than implying exact certainty through integer rounding.

`e2e/demo-flow.spec.ts` exercises plan/reset/no-plan/recovery and pressure/compare.
RECORD_DEMO=1 enables browser-only backup videos against a caller-selected live
server; normal CI blocks map dependencies and records no videos. See
`docs/runbooks/demo-flow.md` for the presenter sequence and configuration.


## P1 UI

Driver exposes native TreeSHAP raw-margin contributions in an optional disclosure and a non-binding shift estimate (or explicit no-improvement status). Operator what-if supports +2 ports and 20% shifted departures with before/after metrics and always-visible frozen-capacity-model limitations. SimulationControls reports current parsed drafts so what-if never uses an old seed/count; invalid drafts disable execution. HTTP stays inside ApiClient and validates returned experiment identity.

## Editable trip endpoints

Driver has independent searchable native dropdowns (input/datalist) for origin and
destination, populated from the station directory plus the two demo city centres.
Each selection resolves to its actual coordinates for map and recommendation;
unknown/empty drafts and identical coordinates block submit. Editing either end
aborts stale requests and clears the previous plan. No automatic recommendations
or geocoding calls occur while typing. Coverage remains the simulated demo region;
this is not nationwide address autocomplete. Native dropdown presentation varies
by browser. Directory failures retain the two city options and show a warning.

## Runtime V2 behavior

Driver uses backend runtime clock/capabilities, blocks submit while loading or when
source data is unavailable, and clears stale plans when the observation changes.
Goong autocomplete/detail use ApiClient, debounce and AbortController; typed text
alone cannot supply coordinates. Local directory coordinates remain an explicit
offline choice. Remote selectors support keyboard selection and ignore late
resolved details after edits. Operator initializes time from the same source.
Capacity what-if displays an explicitly retrained model when the response carries
validated model/history evidence; otherwise the frozen-capacity caveat remains.
