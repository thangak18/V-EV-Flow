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

## Driver place dropdown

When Goong Places is enabled, opening either endpoint dropdown searches the
provider for the current query (including known preset names). An empty query
asks for at least two characters; it does not list fixture stations as map search
results. A source filter exposes the explicitly labelled demo directory separately.
Editing a resolved endpoint invalidates its coordinates, even when the new text
matches a demo label, until the user explicitly chooses a suggestion. Initial demo
endpoints remain preselected. Per-field invalid state only marks the affected
endpoint; duplicate coordinates invalidate both. Arrow/clear buttons, keyboard
selection, cancellation of stale responses and bounded tablet/mobile popovers
support the same selection flow.

## Product workspaces and contextual explanations

See [PRODUCT_UX.md](PRODUCT_UX.md) for the role-specific layouts, user flows and
design references. Driver and Operator are separate destinations with a workspace
menu instead of a shared tab strip. Production-facing copy omits demo branding
while preserving explicit simulated/mock/real provenance. Backup arrival, battery,
distance and forecast limitations are explained in context. Operator supports
Goong area selection and a coordinate-radius view filter; scenario simulations
and what-if retain their explicitly stated complete-network scope. Unknown areas
produce no-data states rather than fabricated stations or metrics. Detailed
calculation metadata, reproducibility controls and comparison tables are exposed
on demand. No shared API or generated type changes are part of this redesign.

## Station focus actions

The Driver's primary/backup location buttons emit a role-specific focus request
with a fresh sequence on every click. Goong centers the requested station at
zoom 14, highlights its marker and opens a station information card. Repeated
clicks re-center and reopen the card; changing/clearing a recommendation hides
stale focus details. Closing the card retains the current camera. Missing station
coordinates disable location actions rather than guessing a position. The
schematic adapter highlights and zooms the chosen diagram point, retaining its
non-navigation label. These actions do not call recommend or add allocations.

## Driver data clock

The vehicle-settings disclosure contains battery capacity and consumption only.
The Driver cannot edit observed_at: it comes from the runtime context and is
shown read-only as “Dữ liệu lúc …” in Vietnam time in the source note. A missing
or invalid supplied timestamp blocks submission and offers connection retry;
it never opens vehicle settings or asks the driver to repair an ISO timestamp.
Backend-clock updates immediately affect subsequent request timestamps. Live
mode retains click-time departure; replay mode retains the dataset timeline.

## Area forecast loading

Applying a valid area/radius or choosing the complete network also loads the
pressure forecast for the selected scenario/time. Repeated filtering reuses the
same complete-network response, including while it is loading; no simulation or
allocation is triggered. A scenario/time change hides incompatible forecasts.
KPI cards distinguish not-yet-loaded, loading, failed and no-data states rather
than displaying unexplained dashes or treating missing forecasts as zero risk.
Failed requests support explicit retry. The radius requires a resolved centre;
a nearby hint explains this prerequisite.

## Operator information hierarchy

The first block groups scenario/time and area/radius before the KPI cards and
map. A visible context line distinguishes the selected scenario from a loaded
forecast. Vehicle count and run settings live beside strategy comparison in the
second block; scenario selection is not duplicated there. Capacity what-if stays
in the third block. Monitoring filters retain local scope; simulation retains
its explicitly labelled complete-network scope.

## Operator data clock

The selected scenario uses the timestamp supplied by runtime, shown read-only
in Vietnamese local date/time. No fixed date is used before runtime responds.
Optional history selection lives in a collapsed advanced disclosure with a
native datetime-local picker, five-minute validation and explicit +07:00 request
conversion. A reset action restores the backend-supplied timestamp. History
selection does not trigger prediction until the user applies the scenario/filter.

## Road routes, map recovery and counterfactual geography

Goong overlays initialize when the style is ready, without requiring every
basemap tile/font to finish. Failed SDK tags are removed for retry; a manual
reload creates a fresh adapter while preserving the textual station list and
recommendation. ResizeObserver updates the map canvas; fitBounds includes route
geometry and stops, while explicit station focus retains its close zoom.

Driver requests read-only `/routes` geometry after an explicit recommendation.
The green route reaches the primary station, blue continues to the destination,
and dashed amber shows the fallback leg from primary to backup. Only actual
Goong geometry is drawn as a road; missing/mock geometry is reported explicitly.
Labels identify A/origin, 1/primary, 2/backup and B/destination. Editing a trip
cancels obsolete geometry requests; focusing markers never recommends again.

Added-port what-if includes a before/after map switch. Experiments highlight the
actual station and show its directory capacity plus the declared added ports.
Shift experiments describe the actual shifted population for the full network.
Success/wait metrics remain network-wide; the API does not supply per-station
outcome changes, so marker colors never claim those values. Changing experiment
inputs hides incompatible previous results, including late responses.

SDK references: https://document.goong.io/tutorial-Map.html and
https://document.goong.io/tutorial-Example.html (style, GeoJSON layers, camera).

Shift-departure what-if uses before/after schedule cards with actual returned
shifted count and unchanged population. Bars show the two vehicle groups only,
not a fabricated hourly histogram. Its unchanged station map is optional and
mounted only when coverage is expanded; it has no misleading before/after map
switch. Network outcome metrics remain in the comparison above.

Forecast loading locks only the selected scenario/time. Changing either while
an older request is pending allows applying the new valid selection; starting
that request aborts the old one. Late responses cannot overwrite the new KPIs.

## Explicit Driver departure

Driver exposes a Vietnam-time datetime-local departure picker. Replay defaults
to the source timestamp. Selecting a custom time within runtime history bounds
uses the actual historical snapshot at that time (floor to the previous five-
minute bucket). The selectable history is not restricted to three hours after
the default clock. Observations serialize without fractional seconds. Out-of-
history times are blocked rather than invented or interpolated.

Live mode preserves the latest observed_at and defaults to click-time departure;
custom live departures remain independent of that observation. In every mode,
model horizon still applies from the real selected observation to candidate ETA.
No extrapolation beyond the model capability is introduced.

Editing/resetting departure clears the previous plan without recommending again.
Scenario changes restore the data-clock default. The demand scenario label is
“Kịch bản nhu cầu sạc” in both workspaces; it does not claim holiday traffic
forecasts. No backend contracts change: RecommendationRequest.depart_time was
already supported and is now editable in the product UI.

## Driver vehicle inputs

Battery level uses a decimal numeric draft bounded to 0–100%, with Vietnamese
labels and contextual help. Comma/dot entry and empty-draft validation remain
compatible. Connector choices come from the loaded station directory. A single
supported type is read-only; multiple types use a select. An empty directory
blocks submission rather than accepting a made-up connector.
