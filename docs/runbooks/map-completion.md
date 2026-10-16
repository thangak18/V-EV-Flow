# Map integration evidence

Source: simulated V2 release (`simulator-v2-180m`), capacity variant S001+2.
Road geometry: server-side Goong Directions V2, not simulator coordinates joined
as a substitute road. Secrets and binaries remain outside Git.

## Reproduce

Use the normal V2 launcher with Goong routing and the capacity models directory.
The current local instance is backend :8010, frontend :5176.

1. Driver: submit a feasible trip, inspect green primary/blue onward/dashed amber
   fallback lines. Focus either station; verify the information card and zoom.
   Editing the trip hides old geometry and cancels pending route requests.
2. Operator: select Tết, apply, run S001 +2 ports with AI/100 vehicles/seed 42.
   Toggle the geographic view before/after; S001 displays 4 then 6 ports.
3. Select shift departures, rerun and check actual shifted count (20/100).
4. Block the SDK once, retry loading the map; station list survives the failure.
   Block glyph requests and verify station overlays still initialize.
5. Check desktop/tablet/mobile: fixed WebGL viewport does not grow with resize.

## Observed locally

- Driver provider responses: three actual geometries (218, 1078, 219 points);
  the three corresponding line layers and four labelled stops rendered.
- S001+2, Tết, AI, seed 42, 100 vehicles: immediate service 63% -> 73%;
  mean wait 7.9 -> 5.1 minutes; explicit capacity_retrained mode.
- Shift experiment: 20 vehicles moved to 21:00–21:55.
- Injected first SDK failure: retry fetched SDK again, 14 markers recovered;
  blocked glyphs did not prevent overlays. Canvas height remained 418 px.
- Focused backend routes/OpenAPI tests: 14 passed. Focused frontend route/map/API/
  what-if tests passed. Full canonical verification is `make ci`; execution logs
  are local `/tmp/vev-map-completion-ci.log`, not tracked data.

## Interpretation and rollback

The port-count comparison is station-level configuration evidence; outcome
metrics are network-wide. There are no per-station simulated success/wait values
in WhatIfResult, so map colors never imply such outcome improvements. Shift
experiments retain identical station locations and describe network-level demand
changes. Real road geometry does not make charger availability real.

The old map initialization required every initial resource before a 15-second
load deadline. Initialization now accepts style readiness; explicit retry handles
transient failures. A fixed container size also prevents canvas/ResizeObserver
feedback when SDK canvas is in normal flow. Network, provider quota and valid
credentials remain prerequisites; text lists and prediction results survive map
failure.

Rollback: revert the map feature commit first, then the additive read-only route
API commit if no client consumes it. Existing prediction/allocation contracts and
stored models are unchanged; `/routes` never allocates.
