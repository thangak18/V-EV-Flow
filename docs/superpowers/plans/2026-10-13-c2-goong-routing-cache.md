# C2 Goong Routing Provider and Cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a cached Goong Directions V2 implementation of the frozen `RouteProvider` port without changing contracts or API composition.

**Architecture:** `RouteCache` persists only validated `RouteResult` tuples in an injected directory using atomic JSON writes. `GoongRouteProvider` translates Goong V2 payloads, decodes encoded polylines into the existing coordinate DTO, and uses a per-key async lock around cache lookup and the one external call. A later FastAPI lifespan owns the injected HTTP client.

**Tech Stack:** Python 3.11, httpx 0.28, Pydantic v2, asyncio, hashlib/json/tempfile, pytest, pytest-asyncio, httpx.MockTransport.

**Spec:** `docs/superpowers/specs/2026-10-13-c2-goong-routing-cache-design.md`

## Global Constraints

- Begin only after C1 PR #72 is accepted/merged; refresh `feat/recommend-api` by merging accepted `main`, never resetting or force-pushing it.
- Preserve `RouteProvider.get_routes(request: RouteRequest) -> tuple[RouteResult, ...]`, all contracts, OpenAPI, generated types, and existing FakeRouteProvider exactly.
- Modify only `app/backend/infrastructure/routing/` and the two C2 test files. Do not change settings, API composition/routes, recommendation, dependency files, CI, or another owner’s module.
- Use Goong Directions V2 with `lat,lng`, fixed `vehicle=car`, numeric distance/duration fields, `source="goong-directions-v2"`, no retry, and no fake/Haversine fallback.
- Inject an `httpx.AsyncClient`; do not create or close a client inside the provider.
- Cache entries contain no API key or raw upstream payload. A cache failure never turns a successful provider response into a failure.
- Tests use temporary directories, injected clocks and `httpx.MockTransport`; they never use a live key or network.

---

### Task 1: Implement a Versioned Disk Route Cache

**Files:**
- Create: `app/backend/infrastructure/routing/__init__.py`
- Create: `app/backend/infrastructure/routing/cache.py`
- Create: `app/backend/tests/infrastructure/test_route_cache.py`

**Interfaces:**
- Consumes: frozen `RouteRequest` and `RouteResult` DTOs.
- Produces:

```python
class RouteCache:
    def __init__(self, directory: Path, ttl: timedelta) -> None: ...
    @property
    def ttl(self) -> timedelta: ...
    def key_for(self, request: RouteRequest) -> str: ...
    def get(self, key: str, now: datetime) -> tuple[RouteResult, ...] | None: ...
    def put(
        self, key: str, routes: tuple[RouteResult, ...],
        collected_at: datetime, expires_at: datetime,
    ) -> None: ...
```

Keys are SHA-256 canonical JSON with `schema_version: 1`, provider version
`goong-directions-v2`, origin, destination, `depart_time` ISO text and fixed
`vehicle: car`. The cache stores a tuple, because the port returns alternatives.

- [ ] **Step 1: Write failing cache-key tests**

Define this test helper at the top of `test_route_cache.py`:

```python
UTC_PLUS_7 = timezone(timedelta(hours=7))

def route_request(
    *, origin: tuple[float, float], destination: tuple[float, float], hour: int,
    vehicle: Vehicle | None = None,
) -> RouteRequest:
    return RouteRequest(
        origin=Coordinate(lat=origin[0], lng=origin[1]),
        destination=Coordinate(lat=destination[0], lng=destination[1]),
        depart_time=datetime(2026, 10, 13, hour, tzinfo=UTC_PLUS_7),
        vehicle=vehicle,
    )
```

```python
def test_key_is_stable_and_direction_time_sensitive(cache: RouteCache) -> None:
    forward = route_request(origin=(10.7, 106.6), destination=(10.8, 106.8), hour=8)
    repeated = route_request(origin=(10.7, 106.6), destination=(10.8, 106.8), hour=8)
    reverse = route_request(origin=(10.8, 106.8), destination=(10.7, 106.6), hour=8)
    later = route_request(origin=(10.7, 106.6), destination=(10.8, 106.8), hour=9)

    assert cache.key_for(forward) == cache.key_for(repeated)
    assert cache.key_for(forward) != cache.key_for(reverse)
    assert cache.key_for(forward) != cache.key_for(later)
```

Assert a 64-character lowercase hex key. Add a request with a different optional
EV `Vehicle` and assert the key is unchanged: its SOC/connector are not Goong
parameters.

- [ ] **Step 2: Write failing round-trip, expiry and corruption tests**

```python
def test_returns_valid_routes_only_before_expiry(cache: RouteCache, now: datetime) -> None:
    routes = (RouteResult(distance_km=12.5, duration_minutes=20, source="goong-directions-v2"),)
    key = "a" * 64
    cache.put(key, routes, now, now + timedelta(minutes=5))

    assert cache.get(key, now + timedelta(minutes=4, seconds=59)) == routes
    assert cache.get(key, now + timedelta(minutes=5)) is None
```

Add tests that `put` creates a missing nested directory; corrupted JSON,
wrong schema/key, expired timestamps and a DTO-invalid route return `None` and
remove the entry; and stored JSON contains neither `api_key`,
`GOONG_REST_API_KEY`, nor an upstream/raw payload field.

- [ ] **Step 3: Run the cache test to verify RED**

Run: `uv run pytest app/backend/tests/infrastructure/test_route_cache.py -v`

Expected: FAIL because `app.backend.infrastructure.routing.cache` does not exist.

- [ ] **Step 4: Implement the cache**

```python
def key_for(self, request: RouteRequest) -> str:
    payload = {
        "schema_version": 1,
        "provider": "goong-directions-v2",
        "origin": request.origin.model_dump(mode="json"),
        "destination": request.destination.model_dump(mode="json"),
        "depart_time": request.depart_time.isoformat(),
        "vehicle": "car",
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
```

Persist `{schema_version, key, collected_at, expires_at, routes}`. Use
`RouteResult.model_validate` for every decoded item. Reject naive timestamps
and `expires_at <= collected_at`. Treat missing, malformed, stale, wrong-key
and invalid-route files as misses, then best-effort unlink them. Create parent
directories inside `put`; write UTF-8 JSON to a same-directory temporary file,
fsync it and replace `<key>.json` atomically. Export `RouteCache` from
`routing/__init__.py`.

- [ ] **Step 5: Run the cache test to verify GREEN**

Run: `uv run pytest app/backend/tests/infrastructure/test_route_cache.py -v`

Expected: PASS.

- [ ] **Step 6: Commit the cache**

```bash
git add app/backend/infrastructure/routing/__init__.py \
  app/backend/infrastructure/routing/cache.py \
  app/backend/tests/infrastructure/test_route_cache.py
git commit -m "feat(infra): add versioned route cache"
```

### Task 2: Implement Goong V2 Translation and Geometry Decoding

**Files:**
- Modify: `app/backend/infrastructure/routing/__init__.py`
- Create: `app/backend/infrastructure/routing/goong.py`
- Create: `app/backend/tests/infrastructure/test_goong_routing.py`

**Interfaces:**
- Consumes: `RouteProvider`, `RouteRequest`, `RouteResult`, `RouteUnavailableError`, `RouteCache`, and injected `httpx.AsyncClient`.
- Produces:

```python
GOONG_DIRECTIONS_V2_ENDPOINT = "https://rsapi.goong.io/v2/direction"

class GoongRouteProvider:
    def __init__(
        self, api_key: str, client: httpx.AsyncClient, cache: RouteCache, *,
        endpoint: str = GOONG_DIRECTIONS_V2_ENDPOINT,
        clock: Callable[[], datetime],
        timeout: httpx.Timeout = httpx.Timeout(10.0, connect=2.0, read=5.0, write=5.0),
    ) -> None: ...

    async def get_routes(self, request: RouteRequest) -> tuple[RouteResult, ...]: ...
```

`routing/__init__.py` exports `GoongRouteProvider` and the endpoint constant.

- [ ] **Step 1: Write failing successful-response tests**

Define deterministic fixtures at the top of `test_goong_routing.py`:

```python
POLYLINE = "_p~iF~ps|U_ulLnnqC_mqNvxq`@"
POLYLINE_POINTS = (
    Coordinate(lat=38.5, lng=-120.2),
    Coordinate(lat=40.7, lng=-120.95),
    Coordinate(lat=43.252, lng=-126.453),
)

def valid_route(distance_m: float = 1250, duration_s: float = 90) -> dict[str, object]:
    return {
        "legs": [{"distance": {"value": distance_m}, "duration": {"value": duration_s}}],
        "overview_polyline": {"points": POLYLINE},
    }
```

```python
@pytest.mark.asyncio
async def test_formats_v2_request_and_normalizes_route(tmp_path: Path) -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"routes": [valid_route(distance_m=1250, duration_s=90)]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        routes = await make_provider(tmp_path, client).get_routes(valid_request())

    assert captured[0].url.params["origin"] == "10.7,106.6"
    assert captured[0].url.params["destination"] == "10.8,106.8"
    assert captured[0].url.params["vehicle"] == "car"
    assert routes[0].distance_km == pytest.approx(1.25)
    assert routes[0].duration_minutes == pytest.approx(1.5)
    assert routes[0].source == "goong-directions-v2"
    assert routes[0].geometry == POLYLINE_POINTS
```

Use a fixture whose `overview_polyline.points` encodes the two expected
`Coordinate` instances. Add multi-leg summation and multiple-alternative tests;
alternatives must stay in provider response order.

- [ ] **Step 2: Write failing invalid-response and conformance tests**

```python
@pytest.mark.parametrize("payload", [
    {},
    {"routes": []},
    {"routes": [{"legs": []}]},
    {"routes": [{"legs": [{"distance": {"value": -1}, "duration": {"value": 1}}]}]},
])
async def test_rejects_unusable_upstream_payload(payload: dict[str, object]) -> None:
    with pytest.raises(RouteUnavailableError):
        await make_provider_with_json(payload).get_routes(valid_request())
```

Cover missing/non-numeric/non-finite distance or duration, malformed present
polyline, invalid JSON, timeout, connect error, 401/403/429/5xx. Assert public
exception strings do not contain the supplied secret. Assert blank API key is
rejected during construction, `isinstance(provider, RouteProvider)` is true,
and existing `FakeRouteProvider` remains protocol-conformant.

- [ ] **Step 3: Run the provider test to verify RED**

Run: `uv run pytest app/backend/tests/infrastructure/test_goong_routing.py -v`

Expected: FAIL because `GoongRouteProvider` does not exist.

- [ ] **Step 4: Implement V2 calls and parsing**

Implement `_coordinate_text` as `f"{coordinate.lat},{coordinate.lng}"` after
`math.isfinite` checks. Call `client.get(endpoint, params={"origin": ...,
"destination": ..., "vehicle": "car", "api_key": api_key}, timeout=timeout)`.
Catch HTTP/transport errors and malformed JSON at this boundary, raising
`RouteUnavailableError("Goong route service unavailable")` without URL query
parameters or provider body in the public message.

Implement `_parse_routes(payload)`: require a non-empty route list and a
non-empty legs list per alternative; sum finite non-negative numeric
`distance.value` and `duration.value`; convert m→km and s→minutes; decode an
optional overview polyline; then construct `RouteResult`. Any invalid
alternative invalidates the full response—never silently skip it. Implement the
standard encoded-polyline algorithm privately as `_decode_polyline`, returning
`tuple[Coordinate, ...]` and rejecting unterminated chunks or DTO-invalid
coordinates. Do not add a polyline dependency.

- [ ] **Step 5: Run the provider test to verify GREEN**

Run: `uv run pytest app/backend/tests/infrastructure/test_goong_routing.py -v`

Expected: PASS without a network call.

- [ ] **Step 6: Commit the provider**

```bash
git add app/backend/infrastructure/routing/__init__.py \
  app/backend/infrastructure/routing/goong.py \
  app/backend/tests/infrastructure/test_goong_routing.py
git commit -m "feat(infra): add Goong V2 route provider"
```

### Task 3: Integrate Cache, Single-Flight, and Cache-Failure Policy

**Files:**
- Modify: `app/backend/infrastructure/routing/goong.py`
- Modify: `app/backend/tests/infrastructure/test_goong_routing.py`
- Modify: `app/backend/tests/infrastructure/test_route_cache.py`

**Interfaces:**
- Consumes: completed `RouteCache.key_for/get/put` and parsed provider routes.
- Produces: cache-first `get_routes` with one upstream call for simultaneous identical keys.

- [ ] **Step 1: Write failing cache hit/miss tests**

```python
@pytest.mark.asyncio
async def test_cached_route_avoids_second_upstream_call(tmp_path: Path) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"routes": [valid_route()]})

    async with client_for(handler) as client:
        provider = make_provider(tmp_path, client)
        first = await provider.get_routes(valid_request())
        second = await provider.get_routes(valid_request())

    assert first == second
    assert calls == 1
```

Advance the injected clock beyond TTL and assert two calls. Corrupt an entry
and assert one replacement call. Make the upstream response fail and assert no
entry is written.

- [ ] **Step 2: Write failing concurrency and write-failure tests**

```python
@pytest.mark.asyncio
async def test_identical_concurrent_requests_share_one_call(tmp_path: Path) -> None:
    calls = 0
    entered = asyncio.Event()
    release = asyncio.Event()

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        entered.set()
        await release.wait()
        return httpx.Response(200, json={"routes": [valid_route()]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = make_provider(tmp_path, client)
        first = asyncio.create_task(provider.get_routes(valid_request()))
        await entered.wait()
        second = asyncio.create_task(provider.get_routes(valid_request()))
        release.set()
        assert (await first) == (await second)
        assert calls == 1
```

Monkeypatch `cache.put` to raise `OSError`; assert the valid provider result is
returned and the following identical request fetches again. Do not use sleeps.

- [ ] **Step 3: Run integration tests to verify RED**

Run: `uv run pytest app/backend/tests/infrastructure/test_route_cache.py app/backend/tests/infrastructure/test_goong_routing.py -v`

Expected: FAIL because the provider does not yet use the cache/single-flight flow.

- [ ] **Step 4: Implement cache-first per-key locking**

```python
async def get_routes(self, request: RouteRequest) -> tuple[RouteResult, ...]:
    key = self._cache.key_for(request)
    cached = self._cache.get(key, self._clock())
    if cached is not None:
        return cached
    lock = self._lock_for(key)
    async with lock:
        cached = self._cache.get(key, self._clock())
        if cached is not None:
            return cached
        routes = await self._fetch_routes(request)
        now = self._clock()
        try:
            self._cache.put(key, routes, now, now + self._cache.ttl)
        except OSError:
            pass
        return routes
```

Keep locks in a provider-local `dict[str, asyncio.Lock]`; remove each unlocked
entry after its owner finishes. Do not hold a global lock during HTTP I/O, cache
exceptions, or swallow provider errors.

- [ ] **Step 5: Run focused C2 verification**

Run: `uv run pytest app/backend/tests/infrastructure/test_route_cache.py app/backend/tests/infrastructure/test_goong_routing.py app/backend/tests/infrastructure/test_mock_adapters.py app/backend/tests/infrastructure/test_file_repositories.py -v`

Expected: PASS without network/key access.

- [ ] **Step 6: Commit cache integration**

```bash
git add app/backend/infrastructure/routing/goong.py \
  app/backend/tests/infrastructure/test_goong_routing.py \
  app/backend/tests/infrastructure/test_route_cache.py
git commit -m "feat(infra): cache Goong route responses"
```

### Task 4: Verify Boundaries and Prepare the C2 Handoff

**Files:**
- Modify: `docs/superpowers/specs/2026-10-13-c2-goong-routing-cache-design.md` only for an approved factual correction.
- Modify: `docs/superpowers/plans/2026-10-13-c2-goong-routing-cache.md` only to record actual execution evidence.

**Interfaces:**
- Consumes: completed C2 routing implementation and frozen contracts.
- Produces: a reviewable C2 commit series with no contract/API drift.

- [ ] **Step 1: Check scope before broad verification**

Run:

```bash
C2_BASE="$(git merge-base HEAD origin/main)"
git diff --name-only "$C2_BASE"..HEAD
git diff "$C2_BASE"..HEAD -- app/backend/contracts app/backend/api app/backend/core pyproject.toml uv.lock
```

Expected: only C2 routing/test paths appear and the protected-path diff is
empty. Stop for a separate contract/tooling PR if an implementation requires a
DTO, setting, dependency, API route, or provider-selection change.

- [ ] **Step 2: Run backend quality and architecture checks**

Run:

```bash
uv run ruff format --check app
uv run ruff check app
uv run pyright app/backend
uv run lint-imports
uv run pytest app/backend --cov=app.backend --cov-report=term-missing --cov-fail-under=75
```

Expected: every command exits 0. Record real output and tested SHA; do not call
an unrun command successful.

- [ ] **Step 3: Run the canonical gate**

Run: `make ci`

Expected: exit 0 on a clean revision. If local environment blocks a check,
record `BLOCKED` with command output and cause; do not hand off C2 as complete
until fresh `make ci` succeeds.

- [ ] **Step 4: Review hygiene and contract boundary**

Run:

```bash
C2_BASE="$(git merge-base HEAD origin/main)"
git diff --check "$C2_BASE"..HEAD
git grep -n -i -E 'goong.*(key|secret)|api_key' -- app/backend/infrastructure/routing
git status --short
```

Expected: only injected-key handling appears in source, no real credential or
raw payload appears in cache fixtures, public errors have no secret, and the
working tree is clean.

- [ ] **Step 5: Commit documentation evidence only if it changed**

Run:

```bash
git add docs/superpowers/specs/2026-10-13-c2-goong-routing-cache-design.md \
  docs/superpowers/plans/2026-10-13-c2-goong-routing-cache.md
git commit -m "docs: record C2 routing verification"
```

Skip this commit if neither document changed; never create an empty commit.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-10-13-c2-goong-routing-cache.md`. Two execution options:

1. Subagent-Driven (recommended) - I dispatch a fresh subagent per task, review between tasks, fast iteration

2. Inline Execution - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
