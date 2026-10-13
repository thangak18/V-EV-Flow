# C2 Goong Routing Provider and Cache Design

**Date:** 2026-10-13  
**Status:** Approved design; implementation has not started  
**Owner:** Kiên (`feat/recommend-api`)

## Goal

Add a Goong Directions V2 adapter and bounded disk cache that implement the
frozen `RouteProvider` port. The work must be usable by later recommendation
code without changing contracts, API routes, composition, or fake mode.

## Frozen Interfaces and Scope

`RouteProvider.get_routes(request: RouteRequest) -> tuple[RouteResult, ...]`
remains unchanged. `RouteRequest` supplies origin, destination, timezone-aware
`depart_time`, and optional `Vehicle`; `RouteResult` supplies kilometres,
minutes, optional `tuple[Coordinate, ...]` geometry, and a source label.

Only these paths may change in C2:

```text
app/backend/infrastructure/routing/__init__.py
app/backend/infrastructure/routing/cache.py
app/backend/infrastructure/routing/goong.py
app/backend/tests/infrastructure/test_route_cache.py
app/backend/tests/infrastructure/test_goong_routing.py
```

Do not modify contracts, generated OpenAPI/types, settings, API composition or
routes, recommendation logic, fake adapters, other owners' modules, dependency
files, or root tooling. Task 7 performs `ROUTE_BACKEND=goong` wiring.

## Goong Provider

`GoongRouteProvider` receives `api_key`, an injected `httpx.AsyncClient`, a
`RouteCache`, and optional endpoint/clock values. The caller owns the client
lifecycle; Task 7 will create and close it in FastAPI lifespan. No provider may
create an unclosed implicit client.

It calls Goong Directions V2 with `GET /v2/direction`, `origin` and
`destination` as `lat,lng`, fixed `vehicle=car`, and the server-only API key.
The adapter emits every valid route alternative in upstream order. For each
alternative it sums numeric `legs[*].distance.value` (metres) and
`legs[*].duration.value` (seconds), then converts them to kilometres and
minutes. It never parses localized display fields or invents missing values.

Goong's encoded `overview_polyline.points` is decoded into the frozen
`tuple[Coordinate, ...]` geometry. A missing overview polyline yields
`geometry=None`; a present but malformed polyline invalidates the upstream
response. The adapter labels results `source="goong-directions-v2"`.

Timeouts, transport/HTTP failures, malformed JSON, no routes, malformed legs,
invalid numeric values, and invalid geometry raise `RouteUnavailableError`
without API key or raw response data in its public message. There is no retry
or fake/Haversine fallback in C2. Request validation remains Pydantic's frozen
DTO validation; defensive non-finite coordinate checks raise `ValueError` for
caller-invalid input.

## Cache

`RouteCache` is a disk-backed, injected-directory cache. Its persistent entry
contains schema version, cache-key payload digest, collected/expiry timestamps,
and Pydantic-serialized `tuple[RouteResult, ...]`; it stores neither API keys
nor raw Goong payloads. Writes use a temporary file plus `os.replace`.

Its SHA-256 key is canonical JSON of cache schema, provider version,
origin/destination coordinates, fixed `vehicle="car"`, and `depart_time` in
ISO format. Direction is therefore asymmetric. `depart_time` is not sent to
the current V2 request, but remains in the key because the port exposes it and
the architecture requires time-aware cache identity. SOC, connector and API
credentials do not affect Goong's current request and are excluded.

Expired, malformed, or validation-failing files are deleted and treated as a
miss. A successful provider response is returned even if its cache write fails;
failed responses are never cached. A per-key async lock in the provider covers
cache recheck, upstream call, and put, so concurrent identical requests make
one Goong call without blocking unrelated keys. Runtime wiring later supplies
the documented ignored cache directory under `app/backend/infrastructure/cache/`.

## Tests and Acceptance Criteria

Tests use `httpx.MockTransport`, temporary cache directories, and injected
clocks only; CI never needs a key or network. Cover V2 parameter formatting,
metre/second conversion, multi-leg/alternative ordering, geometry decode,
timeouts and each malformed response class. Cover cache key direction/time
sensitivity, hit/miss, expiry, corruption removal, atomic round trip,
credential exclusion, failed-call non-caching, write-failure return policy, and
same-key concurrency. Assert both Goong and existing fake adapters satisfy
`RouteProvider` and return contract-valid `RouteResult` values.

Run focused routing tests, existing infrastructure tests, backend lint/type and
architecture checks, then fresh `make ci`. Review the final diff to ensure it
is restricted to the C2 paths above.

## Non-goals

This task does not choose stations, calculate SOC, rank routes, reserve load,
handle API responses, configure settings, or select adapters at startup. Those
belong to C3–C8. Any provider capability requiring a new request/result field
or a contract/OpenAPI change stops for a separate reviewed contract PR.
