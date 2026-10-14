# C1–C9 backend stabilization and sign-off evidence

## 1. Revision, scope and verdict

- Owner: Kiên, Backend & Recommendation. Evidence captured October 14, 2026,
  22:09:43 +07:00; commands run locally on Fedora, not remote CI.
- Branch: `feat/recommend-api`.
- Audited HEAD/base: `8352af15416a21444de17cf76170f9c6c3535f34`.
  Initial worktree was clean. This stabilization candidate is **uncommitted**;
  the SHA identifies the base, not a fabricated final commit.
- Candidate contains exactly six tracked-file changes: prediction route,
  HTTP tests, API SPEC, recommendation SPEC, demo runbook and this evidence.
  No other runtime source, frozen contract, generated artifact or dependency
  changes. Runtime/test identity is recorded below; `git diff --binary HEAD`
  captures the complete candidate, including documentation.
- **PARTIAL — Implemented, release verification incomplete.** All executed
  local functional/static/contract/CI gates pass and no blocking backend
  correctness defect remains. The repository's formal handoff rule additionally
  requires fresh CI on the final **clean committed revision** and independent
  human review. Neither a new commit nor human approval is authorized/fabricated
  by this report. Optional live Goong and deferred integration are not blockers.

Verified source/test SHA-256:

| File | SHA-256 |
| --- | --- |
| `app/backend/api/routes/prediction.py` | `3c540cf9057288727f154db843e0dbf1a655ea02c5a271922cf41384383dfbc7` |
| `app/backend/tests/api/test_real_routes.py` | `3796a9d96fac6e94e82066244911a02b8d90c38f70c98efb0558eb9e89548762` |

The earlier cd5d67e/C9 checkpoint is superseded for this candidate. Historical
793-test results are not represented as current acceptance evidence.

## 2. Confirmed defect and minimal correction

Before patching, actual TestClient HTTP with S001, CCS2-only metadata and
`connector_type="UNSUPPORTED-CONNECTOR"` returned **200**, probability 0.75,
fake-v1/mock. Station existence/time validation did not check compatibility.

RED: `uv run pytest app/backend/tests/api/test_real_routes.py -q` exited 1:
**2 failed, 20 passed**. Both failures were unsupported-connector 200 instead
of 422, one each for mock/file data. This was not an import workaround.

The route now retains the resolved Station, validates existing time/horizon
rules, and checks exact membership in `station.connector_types` before Predictor
invocation. Unsupported known-station connector →422; unknown station →404;
supported input preserves Predictor output. No broad ValueError conversion,
connector substitution, current-occupancy filter or DTO mutation was introduced.

GREEN: the final API suite has **45 passing tests**, including 26 added cases
for mock/file repositories, single/multiple capabilities, both supported types,
unsupported types, unknown station, five time/horizon failures, exact result
preservation, occupied file snapshots, 503 dependency mapping and unexpected
internal ValueError remaining 500. A recording Predictor proves rejected input
does not invoke it; accepted output preserves probability 0.37129, version,
provenance, station, ETA and reasons exactly. Public-store checks confirm
prediction preserves allocation, including existing nonempty Driver demand.

## 3. Actual environment

| Component | Observed |
| --- | --- |
| OS | Linux 7.1.8-200.fc44.x86_64, Fedora, x86_64 |
| Runtime Python | CPython 3.11.17 via `uv run`; system Python is not the test interpreter |
| uv | 0.13.0 |
| Node / npm | v22.23.1 / 10.9.8 |
| pyarrow | 26.0.0, actual installed package, no stub |
| Setup | `make setup`, exit 0; frozen uv/npm locks unchanged |
| Execution | Offline ASGI/TestClient and HTTPX MockTransport; no credentialed Goong traffic |

Setup/security use network for packages/advisories. Runtime probes require no
external services. Dependencies/caches were restored after the previous cleanup;
they are ignored, not part of this patch.

## 4. C1–C9 acceptance and request-flow audit

| Task | Entry/public interfaces and components verified | Validation/state/errors and evidence | Verdict |
| --- | --- | --- | --- |
| C1 | StationRepository/StatusRepository; mock, FileStationRepository, ParquetStatusRepository | Metadata/IDs/capabilities/capacity, exact lag/scenario windows, no future rows, missing/corrupt data; infrastructure tests and real 42-window file probe | PASS |
| C2 | RouteProvider; fake/Goong, RouteCache | Directions parsing, physical legs, timeout/provider/no-route, cache key/TTL/miss coalescing and no failed-response caching; 135 infrastructure tests include routing/cache, plus MockTransport HTTP/performance probes | PASS |
| C3 | C5 → public SOC/feasibility functions | Connector, working capacity, energy/arrival SOC and threshold exclusions; occupied ports not confused with broken capacity; recommendation tests, no formula change | PASS |
| C4 | C5 → rank_candidates/RankingConfig | Actual duration/capacity, configurable penalties, stable station-ID ties, scenario load and unchanged probabilities; recommendation tests, no scoring change | PASS |
| C5 | RecommendationService → station/status/route/predictor ports + VirtualLoadReader | Current status, physical/rounded ETA, horizon filtering, primary/fallback cumulative SOC without charging, no-plan vs outage and truthful provenance; service tests and 216 HTTP checks | PASS |
| C6 | AllocationCoordinator → one AllocationStore | Locked lookup→read committed demand→decide→reserve primary→immutable receipt; retry/conflict/reset/TTL/scenario/concurrency; allocation/state suites plus 16 duplicate HTTP requests | PASS |
| C7 | Settings → build_container → AppContainer | mock/fake/fake, file/fake/fake, file/fake/goong; unsupported real/model fail without fallback, shared store, isolated apps, owned/injected client lifecycle; selection tests and probes | PASS |
| C8 | HTTP routes → scenario Predictor/coordinator/SimulationRunner | 404/409/422/503, invalid DTO/time/horizon/connector, no-plan/primary-only/backup, pressure complement, fake simulation/reset isolation; 45 API tests and acceptance matrix below | PASS |
| C9 | Runbook/SPEC/verification evidence | Commands/provenance/modes/error examples audited; connector/horizon/TTL/performance wording refreshed; local CI passes, final clean-commit CI and human review pending | PARTIAL |

Representative exact tests: `test_parquet_status_repository_returns_only_exact_requested_scenario_window`,
`test_error_envelopes_never_become_no_route`,
`test_mixed_connector_aggregate_status_never_proves_capacity`,
`test_exact_ties_are_lexicographic_and_reordering_cannot_change_ranks`,
`test_virtual_load_per_candidate_eta_and_fallback_bucket`,
`test_backup_is_reached_from_primary_without_charging_there`,
`test_real_c5_concurrent_decisions_switch_stations_and_preserve_probability`,
`test_fifty_unique_coordinated_c5_requests_preserve_all_increments`,
`test_independent_store_reset_waits_for_active_decision`,
`test_goong_owned_client_closes_with_application_lifespan`, and the HTTP tests
in `app/backend/tests/api/test_real_routes.py`.

Independent read-only AI review found no blocking source defect and independently
ran virtual-load/allocation/service tests: **160 passed**, exit 0. It identified
the stale connector/horizon/evidence descriptions now corrected. This is technical
review, not non-author human approval. Full suites below, not source existence,
establish the local acceptance results.

## 5. HTTP acceptance matrix

The offline probe executed **54 checked HTTP calls per configuration**, across
all three scenarios: mock/fake/fake, file/fake/fake, file/fake/goong using
MockTransport, and an isolated one-station mock fixture for primary-only.
Total **216** checks, exit 0. Lifespan was entered/exited explicitly; no server
or client was left running. Results are API requests, not direct handler calls.

| Case | Observed HTTP/result |
| --- | --- |
| health / ready | 200 / 200, correct adapter names; ready is composition-only, not external readiness |
| stations | 200, 14 stations in normal fixtures, one in primary-only fixture; mock/simulated envelopes |
| valid prediction | 200; fake-v1/mock, p=0.75, requested station/ETA preserved |
| unsupported connector / unknown station | 422 / 404 STATION_NOT_FOUND; regression Predictor counters remain zero |
| invalid DTO, offset, bucket, ETA, >60-minute horizon | 422; request validation does not invoke Predictor |
| feasible recommendation | 200; real heuristic_ranking; primary+reachable backup and independent_stations assumption |
| one-station recommendation | 200 primary-only; no fabricated backup, plan_p equals primary probability |
| SOC 0 no-plan | 200, null primary/backup/plan_p; not a 503 outage |
| retry / changed-payload conflict | 200 identical response / 409 REQUEST_CONFLICT; primary demand remains 1 |
| reset / ID reuse | 200 clears load / 200 accepts intent again; post-reset same intent reproduces original plan |
| scenario isolation | Other scenario snapshots stay empty; status/predictor selection uses requested scenario |
| pressure | 200; p=0.75, pressure=0.25 at fixed +30-minute horizon; invalid time →422 |
| simulate | 200 fake-sim-v1; deterministic repeat before/after reset; Driver demand unchanged |
| whatif | 503 FEATURE_NOT_READY; P1 remains unimplemented |
| injected Predictor unavailable | 503 MODEL_NOT_READY for predict and recommendation; injection before composition for C5 |
| Goong transport outage | 503 ROUTE_UNAVAILABLE, no allocation, no key in error body |
| unexpected Predictor ValueError | 500, not hidden as a client 422 |

Additional state probe: 16 simultaneous identical HTTP recommendations returned
the same result with primary load **1**, while a separate application store stayed
**0**. Both successful/rejected prediction calls preserved existing load. C6
tests additionally cover distinct concurrent IDs, reset races, cancellation and
no lost increments. Simulation evidence is MOCK/FakeSimulationRunner, not an
experimentally validated AI comparison.

An initial probe tried replacing the container predictor map after construction
to simulate a C5 outage. C5 intentionally copies injected dependencies when
constructed; that instrumentation did not replace its Predictor. The corrected
probe injects through the predictor factory before composition and observes 503.
No production change was made for this probe-design error.

## 6. Real file-backed verification

Executed twice, with output roots `/tmp/v-ev-final-data` and
`/tmp/v-ev-final-repeat`, exit 0 for generation/history and comparison:

```bash
uv run python -m app.backend.modules.station_data.cli generate \
  --scenario all --seed 42 --history-days 1 \
  --history-end '2026-10-13T23:55:00+07:00' --vehicles 100 \
  --output /tmp/v-ev-final-data/generated
uv run python -m app.backend.modules.simulation.cli history \
  --input /tmp/v-ev-final-data/generated
```

CLI `--help` was checked against the runbook before execution. DATA_DIR is the
parent of `generated/`. Actual pyarrow read **12,096 rows, 4,032 per scenario**,
six canonical columns, integer counts and timestamp[us, tz=+07:00]. Metadata
loaded 14 stations. No duplicate scenario/station/time keys; counts conserve
capacity. All 42 station/scenario windows return exact `(0,15,30,60)` lags at
16:00 with no future/scenario leakage. Current free-port vectors differ between
scenario scopes, so scenario correctness is not inferred merely from labels.
File/fake/fake and file/fake/goong HTTP both succeed; stations are simulated,
fake predictions mock, successful recommendations mixed.

| Artifact | Observed SHA-256 |
| --- | --- |
| status Parquet | `cd82764493bbd89882035db95ab448f3d284caab2f343ab759874f44ad5a9b9f` |
| normal fixture | `073145ce856080b93c64b527b516f5a1802619aecd30c9bdf3978632263b91e0` |
| holiday_30_4 fixture | `ff64f3cc21ee171b9682df0622c252823d1e931ad630a3ad580932f2519bb146` |
| tet fixture | `c62510ea35521e3b155a5416683ae149e518952c20e35bd9602ef3477480d4ed` |

Both roots match fixture/Parquet hashes and manifests. Generated_at timestamps
may differ. These are fixed synthetic October 13 profiles, not actual holiday
occupancy, trained-model evaluation or real partner data. Nothing generated is
staged/committed. Missing/corrupt files, schemas, snapshots and scenario isolation
are additionally exercised by the infrastructure suite with real pyarrow.

## 7. Routing performance and decision lock

Method: actual GoongRouteProvider + RouteCache with HTTPX MockTransport, counting
wrapper at the public RouteProvider interface, existing 14-station mock fixtures,
normal scenario, 20% SOC, departure 16:00+07 and 60-minute horizon. Transport
returns distances/durations from the deterministic FakeRouteProvider, with a
**synthetic 2 ms sleep per fetch**. Timings use perf_counter. Fresh temporary
cache per cohort; new IDs for ranking work; store reset for repeat warm cohorts.
No production parser/cache/selection/lock code changed.

| Scenario | Stations | Route calls | HTTP fetches / served without fetch | Cache state | Total latency ms |
| --- | ---: | ---: | ---: | --- | ---: |
| Single request | 14 | 38 | 38 / 0 | Cold | 155.596 |
| Same input, new ID, store reset | 14 | 38 | 0 / 38 | Warm, same departure | 8.023 |
| Exact idempotent retry | 14 | 0 | 0 / 0 | Warm receipt | 0.193 |
| Four sequential distinct IDs | 14 | 151 | 54 / 97 | Initially cold | 240.099 |
| Four concurrent distinct IDs | 14 | 151 | 54 / 97 | Initially cold | 238.472 |
| Four concurrent distinct IDs, reset | 14 | 151 | 0 / 151 | Warm cohort | 26.760 |
| No route to S001 | 14 | 35 | 35 / 0 | Cold; no-route not cached | 133.023 |

Single-request phase counts: direct **1**, origin-to-station **14**, onward to
destination **10**, primary-to-backup **13**. Four-request cohort counts are
4/56/39/52; load-aware later decisions can change primary and keys. No-route
S001 counts are 1/14/7/13 and select S003/S004 rather than inventing a route.
“Served without fetch” is observed provider calls minus MockTransport fetches,
not raw cache.get lookup counts (the adapter double-checks misses under a lock).

Cold concurrent request latencies from submission: **150.776, 157.095, 230.081,
237.151 ms**; sequential: **152.857, 7.136, 73.192, 6.863 ms**. Maximum active
transport calls observed: **1**. The decision lock serializes full decisions,
including routing, so external latency affects all queued requests. Warm-cache
work may run without an external suspension; it still uses the same lock.

These are measured offline numbers, **not live Goong latency/quota or production
throughput evidence**. No MVP correctness blocker was measured. Live latency,
credit policy and different-departure cache reuse remain separate follow-ups.
Exact departure participates in cache keys. Future optimization must preserve
candidate eligibility, fallback physical routing, probabilities and atomic
read→decide→commit; do not remove the lock or replace road routes with straight
lines. No worst-case traffic estimate is presented as measured traffic.

## 8. TTL and demand-lifetime policy

Defaults: receipt TTL **1800 processing seconds**, charging duration **60
minutes**, horizon **60 minutes**, expected load **1**. Reservation immediately
contributes only primary buckets covering `[eta, eta + duration)`; a 60-minute
aligned interval has 12 buckets. Bucket values are expected demand, not occupancy
or a physical booking. Backup has no contribution.

Receipt creation starts TTL independently of replay observation/departure/ETA.
Retry does not refresh expiry. On the next lookup/reserve/snapshot at
`expires_at <= now`, pruning reverses every contribution of that receipt and
allows request-ID reuse. Reset instead clears **all** receipts/buckets while
synchronized with active decisions. Restart also loses process-local state.

Controlled-clock probe: commit at synthetic 22:10, ETA 22:50, TTL expiry 22:40,
assumed charging end 23:50 on October 14. Snapshot at future ETA changes
**1→0 at expiry**, before arrival; changed-payload ID reuse then restores 1 and
reset returns 0. This confirms the consistent policy rather than changing it.
It can underrepresent long-lived expected demand and is suitable only for the
short demo/explicit retention assumptions, not sustained production balancing.
Separating idempotency retention from session/ETA demand lifetime is a post-C9
business-policy improvement, not an unproven contract violation. Defaults and
C6 semantics remain unchanged. One process/worker is mandatory.

## 9. Executed verification gates

All table results are actual local executions on the base plus source/test patch.
After documentation refresh, a frozen-candidate rerun completed October 14,
2026, **22:22:03–22:24:03 +07:00**, exit 0: 819/87/16 tests and all stages pass.
Its before/after binary-diff comparison also passed. This result-record update
is documentation-only; run the aggregate once more without intervening edits
on the complete record. The final CLI report records that last frozen diff
identity/result, avoiding a self-referential digest inside the evidence file.
Local logs/probes under `/tmp/v-ev-final-*` are not committed.

| Gate | Command | Exit code | Observed result | Status |
| --- | --- | ---: | --- | --- |
| Setup | `make setup` | 0 | Frozen Python/npm setup and Chromium install | PASS |
| Recommendation | `uv run pytest app/backend/modules/recommendation/tests -v` | 0 | 362 passed | PASS |
| Infrastructure | `uv run pytest app/backend/tests/infrastructure -v` | 0 | 135 passed | PASS |
| API | `uv run pytest app/backend/tests/api -v` | 0 | 45 passed | PASS |
| Core/settings | `uv run pytest app/backend/tests/core -v` | 0 | 6 passed | PASS |
| Owner Ruff | `uv run ruff check app/backend/modules/recommendation app/backend/infrastructure app/backend/api` | 0 | All checks passed | PASS |
| Owner Pyright | `uv run pyright app/backend/modules/recommendation app/backend/infrastructure app/backend/api` | 0 | 0 errors/warnings | PASS |
| Backend lint | `make backend-lint` | 0 | Format/Ruff/Pyright and both import contracts pass | PASS |
| Backend coverage | `make backend-test-suite` | 0 | 819 passed, **95.15%**, gate ≥75% | PASS |
| Contract | `make contract-check` | 0 | OpenAPI check/types regeneration, no generated drift | PASS |
| Frontend | `make ci` frontend lint/test/build stages | 0 | 87 tests, coverage/build pass | PASS |
| Smoke | `make ci` → `make smoke` | 0 | 16 Chromium E2E tests pass | PASS |
| Security | `make ci` security stage | 0 | detect-secrets, pip-audit no known vulnerabilities, npm audit 0 | PASS |
| Full CI | `make ci > /tmp/v-ev-final-ci-initial.log 2>&1` | 0 | All canonical stages above | PASS, working-tree candidate |
| Frozen CI rerun | `make ci > /tmp/v-ev-final-ci.log 2>&1` | 0 | Again 819 backend / 87 frontend / 16 E2E; before/after diff comparison passes | PASS, frozen working-tree candidate |
| File/HTTP probes | `PYTHONPATH=. uv run python /tmp/v-ev-final-flow-probe.py` | 0 | Real Parquet and 216 checked HTTP calls | PASS |
| Routing probe | `PYTHONPATH=. uv run python /tmp/v-ev-final-route-probe.py` | 0 | Seven measured cases above | PASS |
| State/TTL probe | `PYTHONPATH=. uv run python /tmp/v-ev-final-state-probe.py` | 0 | Expiry/reuse/reset, 16 duplicates, app isolation, route-outage redaction | PASS |
| Final clean-commit CI | Not executed: stabilization patch is not committed | — | No new commit authorized | NOT RUN, formal release gate |
| Human approval/merge | Not supplied | — | Agent cannot manufacture independent approval | NOT RUN |
| Live Goong | No credentialed requests | — | Optional external operational check | NOT RUN |

Existing non-failing warnings: Starlette/httpx deprecation, frontend Fast Refresh
exports, seven OpenAPI lint warnings, Playwright platform fallback and color-env
warnings. No lockfile/tooling changes were used to suppress them.

## 10. Contract, security and final-diff review

| Changed file | Justification |
| --- | --- |
| `app/backend/api/routes/prediction.py` | Retain resolved Station and reject unsupported connector before Predictor |
| `app/backend/tests/api/test_real_routes.py` | HTTP regressions for compatibility, valid-result preservation, occupancy/state/time/error behavior |
| `app/backend/api/SPEC.md` | Document connector validation and its 422 classification accurately |
| `app/backend/modules/recommendation/SPEC.md` | Distinguish current settings-backed fake horizons from deferred artifact-derived capabilities |
| `docs/runbooks/backend-demo.md` | Correct prediction/error examples; clarify TTL and observed routing/lock limitations |
| `docs/runbooks/backend-verification-evidence.md` | Replace stale checkpoint with this actual candidate audit, results and sign-off |

Routes, operation IDs, request/response schemas and generated types remain frozen;
`make contract-check` exits 0. Observed unchanged SHA-256:

- OpenAPI: `b71de0b704792cbc1b2ac0128ef4fa7e85e73ad7beecbc15ae90e854f789801e`.
- TypeScript: `db2f1cbdaaa7fdb87c5a25932beeebfd9c7ec96fb60912f5f98d19a57aa2bf9a`.

`git diff --check` passes; `.env` is not tracked. No credential, private model,
generated dataset, cache or local log is included. Goong outage messages do not
expose the supplied test key. Owned AsyncClients close at lifespan; caller-owned
clients remain open until their caller closes them. Source scope is only the
HTTP connector fix; C3–C6 algorithms, parser/cache, predictor/simulator internals,
frontend and data generation are untouched.

## 11. Handoff, deferred work and submission summary

**No unresolved blocking correctness issue found.** Remaining formal release
work: authorize/create the stabilization commit, rerun fresh `make ci` on that
clean SHA, record actual result and obtain independent human review/merge decision.
This report intentionally does not create/commit/push a branch or update a PR.

Post-C9 integration remains separate: Kiên's AllocationStrategy, Thắng's trusted
Predictor with exact scenario/status lags `(0,15,30,60)` and matching artifact
horizons, and Bảo's DefaultSimulationRunner with immutable bundles, per-strategy
fresh state, `strategy_for(..., ai_strategy=...)` and explicit
`availability(station_id, observed_at, eta)`. No model backend was activated,
runner rewritten, AI improvement fabricated or `/whatif` implemented. Driver
and simulation allocation must remain separate. Live routing evaluation and
TTL/demand-lifetime policy improvements are follow-ups, not unfinished C1–C9
implementation defects.

Suggested authorized commit/PR subject:
`fix(api): finalize C1-C9 backend validation and handoff`.
Summary: reject incompatible prediction connectors before inference; preserve
valid output/state/error contracts; add mock/file HTTP regressions; refresh
full-flow/Parquet/routing/TTL and CI evidence. Rollback the bounded route/test/docs
patch or revert its eventual commit; no migration or contract regeneration needed.
