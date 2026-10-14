# C9 backend verification and PR evidence

## Revision and disposition

- Owner: Kiên, Backend & Recommendation. Verification date: October 14, 2026 (+07).
- Branch: `feat/recommend-api`.
- Audited HEAD/base: `cd5d67eae59a113ff9f0005bc1dd4fa6186dbd72`
  (`docs(api): finalize backend integration handoff`), initially clean.
- Scope: C9 runbook/SPEC completion and one essential HTTP integration test;
  no business algorithm, delivery signature, dependency or frozen-contract change.
- Current evidence applies to that base plus the **uncommitted C9 patch**, not
  a fabricated new commit or remote CI run. No commit/push/PR creation authorized.
- Verdict at this checkpoint: **PARTIAL — final clean-revision handoff pending**.
  Formal release requires fresh `make ci` after the final patch is committed on
  a clean revision and independent human review. Local checks are recorded below;
  this document is not human approval.
- Local documentation/test acceptance is verified; no failing required local
  check or unresolved blocking source defect remains. PARTIAL reflects the
  uncommitted final revision, not missing pyarrow, failing CI or an invented
  requirement to activate the deferred model/simulator.

## Previous review findings and resolutions

| Finding | Confirmed cause | Patch / evidence |
| --- | --- | --- |
| C9-01 P1: missing formal evidence | Initial C9 omitted actual environment/revision/command/results | This single evidence record distinguishes current runs, historical claims, clean-revision gate and external integrations |
| C9-02 P1: file demo not reproducible | Paths mentioned without generate→history commands, DATA_DIR parent logic or schema/scenario checks | Runbook section 6 documents executable generation, exact lags, schema/hash checks and mixed provenance; real pyarrow/file/live-HTTP checks below |
| C9-03 P2: HTTP sequence incomplete | No copyable simulate/whatif/retry/conflict/reset/reuse/error workflow | Runbook sections 4–5/8; real localhost HTTP in mock and file modes; new automated load inspection |
| C9-04 P2: SPEC handoff too brief | Implementation wiring, ranking measurements, temporal policies, adapter/errors/source distinctions missing | Added implementation/consumer, adapter/operator and API contract handoff sections, retaining earlier design rationale |

No C1–C8 remediation was necessary during this patch. Existing APIs and
business implementations were exercised, not rewritten.

## Actual environment and dependency readiness

| Component | Observed |
| --- | --- |
| Host | Linux 7.1.8-200.fc44.x86_64, Fedora, x86_64 |
| Shell | bash; commands from repository root |
| System Python | 3.14.6 (not the test interpreter) |
| `uv run python` | CPython 3.11.17, `.venv/bin/python` |
| uv | 0.13.0 |
| Node / npm | v22.23.1 / 10.9.8 |
| pyarrow | 26.0.0, actual installed module; no import stub |
| Setup | `make setup`, exit 0: frozen uv sync, npm ci, Playwright Chromium install |
| API | Uvicorn factory at 127.0.0.1:8000, one process, sequential mock/file instances |

Setup/security need network. Mock/fake runtime needs no external service. Setup
emitted the existing eslint deprecation and Playwright unsupported-OS fallback
warnings, but completed. Python and npm lockfiles were not changed.

## Reproducible fixture and file evidence

Executed from root, exit 0 for each:

```bash
uv run python -m app.backend.modules.station_data.cli generate \
  --scenario all --seed 42 --history-days 1 \
  --history-end '2026-10-13T23:55:00+07:00' --vehicles 100 \
  --output /tmp/v-ev-c9-data/generated
uv run python -m app.backend.modules.simulation.cli history \
  --input /tmp/v-ev-c9-data/generated
uv run python -m app.backend.modules.station_data.cli generate \
  --scenario all --seed 42 --history-days 1 \
  --history-end '2026-10-13T23:55:00+07:00' --vehicles 100 \
  --output /tmp/v-ev-c9-repeat/generated
uv run python -m app.backend.modules.simulation.cli history \
  --input /tmp/v-ev-c9-repeat/generated
```

Actual outputs: `stations.json`, per-scenario fixture_bundle/manifest, top-level
manifest and `station_status.parquet`. `DATA_DIR=/tmp/v-ev-c9-data`, **not** its
generated subdirectory. No copies, symlinks, mock substitution or tracked dataset.
Runbook uses mktemp roots to reproduce this without overwriting local fixtures.

| Check | Observed result |
| --- | --- |
| Stations / version / seed | 14 / station-data-0.1.0 / 42 |
| Status rows | 12,096 total; 4,032 each normal, holiday_30_4, tet |
| Schema | Six canonical columns; large_string IDs/scenarios, int64 counts, timestamp[us, tz=+07:00] |
| Integrity | No duplicate scenario/station/time keys; selected row counts sum to station capacity |
| File repositories | FileStationRepository loads all 14 stations; three ParquetStatusRepository scopes load exact `(0,15,30,60)` snapshots at 2026-10-13 16:00+07 for every station |
| Scenario isolation | All returned status scenarios equal repository scope; no namespace mixing |
| Re-generation | Same per-scenario fixture hashes and actual Parquet SHA-256 across both roots; verified against both manifests |
| Status file SHA-256 | `cd82764493bbd89882035db95ab448f3d284caab2f343ab759874f44ad5a9b9f` |
| normal fixture hash | `073145ce856080b93c64b527b516f5a1802619aecd30c9bdf3978632263b91e0` |
| holiday_30_4 fixture hash | `ff64f3cc21ee171b9682df0622c252823d1e931ad630a3ad580932f2519bb146` |
| tet fixture hash | `c62510ea35521e3b155a5416683ae149e518952c20e35bd9602ef3477480d4ed` |

These are synthetic profiles on a shared fixed day, not real holiday occupancy.
Creation timestamps differ and are not part of the deterministic fixture content.
The tested one-day smoke is not model-training/evaluation evidence; the default
14-day generation option is documented, not claimed as executed here. Hashes
detect corruption but do not authenticate origin or prove forecast accuracy.

Also executed `uv run python -m app.backend.modules.simulation.cli compare
--input /tmp/v-ev-c9-data/generated --scenario all --vehicles 100
--output /tmp/v-ev-c9-data/comparison`, exit 0. It emitted six actual baseline
results (nearest/currently_available for three scenarios) with the fixture
hashes above. No AI strategy was supplied; this does **not** change `/simulate`
or establish an AI win. Results remain local, not committed.

## Observed HTTP evidence

Started the real Uvicorn `app.backend.api.main:create_app --factory` on 8000,
first mock/fake/fake and then file/fake/fake. Settings fixed fake horizon 60,
SOC threshold default 10, expected load 1, assumed charge duration 60 and TTL
1800. Used curl health plus actual localhost HTTP requests with the exact
runbook DTO values; successful bodies were validated with shared response DTOs.
Both servers shut down after verification. No pyarrow stub or credentialed Goong
was used.

| Call | Mock / file observed status and semantics |
| --- | --- |
| health | 200 / 200, `status=ok` |
| ready | 200 / 200, ready=true and correct mock/file, fake, fake selections; composition-only |
| stations | 200 / 200, 14 stations; envelope mock / simulated |
| predict S001 16:00→16:30 | 200 / 200, p=0.75, fake-v1, rule, mock |
| recommend after reset | 200 / 200, real heuristic_ranking pipeline; primary S001 16:05, backup S003 16:20; source mock / mixed |
| pressure normal at 16:00 | 200 / 200, every station p=0.75, pressure=0.25 at +30 minutes; mock |
| simulate tet/42/100/ai_allocation | 200 / 200, fake-sim-v1; success .9, detour 2.5, wait 4, failed 10/100; mock fixture descriptor hash, not real runner output |
| identical recommendation retry | 200 / 200, original response exactly equal |
| same ID with scenario changed to tet | 409 / 409, REQUEST_CONFLICT |
| reset | 200 / 200, reset=true |
| changed payload using same ID after reset | 200 / 200, accepted as new intent |
| SOC 0 recommendation | 200 / 200, primary=null; valid no-plan |
| whatif illustrative P1 body | 503 / 503, FEATURE_NOT_READY; current route ignores body |
| unknown prediction station | 404 / 404, STATION_NOT_FOUND |
| prediction horizon 65 with configured max 60 | 422 / 422 |
| prediction observation expressed as UTC Z | 422 / 422, although instant equals +07 example |
| recommendation SOC 101 | 422 / 422 |

Additional actual TestClient probe with file mode and an observation outside
the generated window (October 14 16:00+07) returned 503
`DATA_SOURCE_UNAVAILABLE`. Startup probes explicitly rejected DATA_BACKEND=real,
model mode even with an existing MODEL_DIR, missing file metadata, and Goong
without a key. These are startup failures, not invented served 503 responses.

Verified mock/file primary: distance 0.358 km, SOC 19.8926, probability .75;
backup cumulative distance 10.27 km, SOC 16.919, probability .75.
Two-plan probability .9375 uses independent_stations assumption, not a guarantee.
Different loads/sources/settings need not reproduce those station choices.

The added `test_http_retry_conflict_and_reset_preserve_exactly_one_primary_allocation`
in `app/backend/tests/api/test_real_routes.py` sends HTTP requests through ASGI
and inspects the public app-scoped store at the returned ETA: first `{S001:1}`,
identical retry unchanged, conflicting scenario no extra contribution, reset
empty, then one Tết reservation after ID reuse. No internal debug endpoint.
Existing C6 tests cover concurrency/decision/reset/cancellation/TTL separately.

## Verification matrix

Results distinguish completed commands from outstanding final-revision checks.
Local logs are under `/tmp/v-ev-c9-*`, not tracked or required to reproduce.

| Command/check | Exit / counts | Classification |
| --- | --- | --- |
| `make setup` | 0 | PASS |
| Initial clean-base `uv run pytest app/backend/tests/api -q` with real pyarrow | 0; 18 passed | PASS (baseline before new test) |
| `uv run pytest app/backend/tests/api/test_real_routes.py -q` | 0; 4 passed | PASS |
| Fixture generation/history twice + schema/lag/hash probe | 0; 14 stations, three scenarios, 12,096 rows | PASS |
| Mock/file localhost HTTP sequence | 0; 18 calls per mode with expected statuses | PASS |
| `uv run pytest app/backend/modules/recommendation app/backend/tests/infrastructure app/backend/tests/api -v` (also repeated `-q` after test settings adjustment) | 0; 516 passed | PASS |
| `uv run ruff check app/backend/modules/recommendation app/backend/infrastructure app/backend/api app/backend/tests/api/test_real_routes.py` | 0; all checks passed | PASS |
| `uv run pyright app/backend/modules/recommendation app/backend/infrastructure app/backend/api app/backend/tests/api/test_real_routes.py` | 0; no errors/warnings | PASS |
| `make backend-lint` | 0; format, Ruff, Pyright and 2 import contracts pass | PASS |
| `make backend-test-suite` | 0; 793 tests passed; aggregate coverage 95.07% | PASS |
| `make contract-check` | 0; generated schema/types unchanged, 7 existing OpenAPI warnings | PASS |
| `make lint` | 0; frontend 2 existing Fast Refresh warnings, no errors | PASS |
| Exact runbook blocks (mock startup/HTTP/retry/error and file generation/schema/baseline) | 0; copyable commands executed, retry JSON equal, conflict/reuse observed | PASS |
| `make ci` on patched working tree | 0; 793 backend / 87 frontend / 16 E2E passed; backend coverage 95.07% | PASS (working-tree evidence, not final clean-revision handoff) |
| `git diff --check` and generated contract/type drift | 0; only intended C9 files changed | PASS |
| Live Goong | No authorized credentialed traffic attempted | NOT RUN, optional external verification |
| Real-model / real-runner HTTP binding | Explicitly gated/deferred in this composition | BLOCKED by post-C9 integration scope, not a failing C9 test |
| Fresh CI on final clean committed patch | No commit authorized | NOT RUN; formal handoff pending |

An initial type-check of the new test rejected `_env_file` as an unsupported
constructor keyword in static analysis. The test now supplies explicit supported
Settings fields (mock/fake paths, threshold, horizon, duration/load/TTL);
fresh Pyright and canonical backend-lint pass. No runtime Settings or tooling
was changed to suppress the diagnostic.

### Full CI capture

Executed from root with shell `pipefail` to preserve the Make exit code:

```bash
set -o pipefail
make ci 2>&1 | tee /tmp/v-ev-c9-ci.log
```

Observed **exit 0** against HEAD `cd5d67eae59a113ff9f0005bc1dd4fa6186dbd72`
plus this C9 working-tree patch. All canonical stages completed: backend/frontend
lint, backend tests (793, coverage 95.07%), frontend coverage tests (87 in 18
files), frontend build, OpenAPI/type contract-check, Chromium E2E (16), secret
scan, pip-audit (no known vulnerabilities), npm audit (zero vulnerabilities).
Architecture tests were included in backend tests and import-linter kept both
declared contracts. No failed stage remains. The final evidence-result text is
an execution record, not a new runtime change or pretend committed SHA.

Warnings are pre-existing/non-failing: two frontend Fast Refresh exports,
seven OpenAPI lint warnings, Starlette/httpx deprecation, Playwright platform
fallback and NO_COLOR/FORCE_COLOR messages. No dependency or generated contract
was updated to remove them. Logs are local artifacts; no remote CI URL is claimed.

### Independent technical review

A separate read-only reviewer checked source/doc consistency, scope and new
test, independently ran the four real-route API tests, and inspected both
generated datasets/scenario lags/hashes. No critical/important blocking issue
was found. One low-priority HTTPX timeout wording issue was corrected: phase
timeouts are not an overall request deadline. The HTTP test focuses on load
at primary ETA; existing C6 tests cover the full charging interval and backup
reservation invariants, so no additional production logic was introduced.

The reviewer did not claim to rerun full CI or authorize commit/merge. Main's
exact runbook-block execution and full gate captures are separate evidence.

## Contract stability and scope

No route signature, frozen model/port, generated OpenAPI/TypeScript or root
dependency/tooling change is intended. Contract generation must remain byte-for-
byte stable; final `make contract-check` and Git drift results are recorded above.

Observed unchanged artifact SHA-256:

- OpenAPI: `b71de0b704792cbc1b2ac0128ef4fa7e85e73ad7beecbc15ae90e854f789801e`.
- Generated TypeScript: `db2f1cbdaaa7fdb87c5a25932beeebfd9c7ec96fb60912f5f98d19a57aa2bf9a`.

Files in this patch:

- `docs/runbooks/backend-demo.md`: executable environment/modes/data/HTTP/error/retry/reset/handoff guide.
- `docs/runbooks/backend-verification-evidence.md`: single revision/environment/result/PR evidence record.
- `app/backend/modules/recommendation/SPEC.md`: C3/C4 measurements, C5/C6 flow and public consumer boundary.
- `app/backend/infrastructure/SPEC.md`: adapter matrix, file/Goong/state lifecycle, actual provenance.
- `app/backend/api/SPEC.md`: composition/endpoint/time/error/idempotency/pressure/deferred binding details.
- `app/backend/tests/api/test_real_routes.py`: essential missing HTTP load/retry/conflict/reset proof, no runtime changes.

No secrets, histories, binaries, caches, results or raw test logs are tracked.

## Post-C9 team handoff and PR summary

**Owner/scope:** Kiên; complete C9-01..04 reproducibility/documentation/evidence,
not a new feature or implicit real-model/simulator integration.

**Team dependencies:** Bảo provides validated immutable bundles/config and the
public DefaultSimulationRunner; composition must select each requested strategy
and keep run state separate from Driver. Thắng provides the public Predictor,
trusted artifacts/version, scenario capability horizons, exact status lags and
explicit simulated/mixed provenance. Joint availability callback is
`availability(station_id, observed_at, eta)`. Kiên's pure AllocationStrategy
requires verified actual travel/capacity/load metadata keyed scenario/station/ETA;
no fabricated capacities or fallback reachability. Tú consumes unchanged generated
types, preserves retry intent IDs, handles 409/422/503/null plans and labels
mock/mixed data, independent plan probability, fake simulator and pressure proxy.

**Limitations:** one process/worker; in-memory receipts/load lost on restart;
no distributed consistency, physical booking or compliance guarantee. Duration
60 minutes/load 1 are explicit assumptions. Scenario fake predictions are not
scenario-sensitive trained output. Goong live traffic/model deployment/AI runner
HTTP binding/what-if remain unverified or deferred as explicitly distinguished.

**Rollback:** revert this documentation/test-only patch; no state migration,
contract regeneration or runtime rollback required. No production algorithm
changed. Never reset/discard unrelated work.

**Review:** independent technical review found no blocking issue; human approval/merge and remote
CI links are NOT RUN/not supplied. Keep the owner branch as-is; no unauthorized
commit, push, PR creation or merge. Final clean-revision CI is the remaining
formal release gate even when all local checks pass.
