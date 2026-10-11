# Integration, Demo, and Release Implementation Plan

> **For agentic workers:** Use the repository-owned [harness workflow](../../harness/workflow.md), applicable AGENTS/SPEC and assigned issue AC. Track task checkboxes as implementation notes; no external skill/plugin is required. Evidence and handoff follow the common workflow.

**Goal:** Integrate the four green owner branches into one reproducible demo, package it, enforce protected-main gates, and produce evidence for the 15/10 submission.

**Architecture:** Integration changes only composition and adapters unless a separately reviewed contract PR is unavoidable. Merge order follows producers before consumers: A/B public outputs, C composition/API, then D UI. The final demo uses one backend worker, built frontend, explicit mock/simulated labels, cached fixed-route fallback, and one immutable release commit.

**Tech Stack:** Git/GitHub, existing Python/Node toolchains, FastAPI, React build, Docker/Compose for local demo packaging, GitHub Actions release artifacts.

**Spec:** `docs/superpowers/specs/2026-10-11-parallel-development-design.md`, `docs/DEMO.md`, and `deploy/SPEC.md`

## Global Constraints

- Begin only after Phase 0 is merged and all four feature PRs are individually green against current `main`.
- Do not solve integration failures by weakening contracts, deleting tests, lowering coverage, or hard-coding successful metrics.
- Contract changes use a separate PR and require all affected branches to rebase.
- Run the three strategies with identical fixture hash, scenario, seed, and vehicle count.
- One backend worker is the supported demo mode while virtual allocation is in memory.
- Real keys remain outside Git; offline/mock demo remains available.
- Every task ends in a reviewable commit or documented repository setting change.

## File Map

```text
app/backend/api/dependencies.py               Final composition selections
app/backend/tests/integration/                Cross-module contract flows
app/frontend/e2e/                             Real-backend browser flows
deploy/backend.Dockerfile                     Backend package
deploy/frontend.Dockerfile                    Frontend static package
deploy/compose.demo.yml                       One-command demo orchestration
deploy/nginx.conf                             Frontend/API routing
deploy/README.md                              Verified runbook
docs/runbooks/integration.md                  Merge and rollback record
docs/runbooks/demo-checklist.md               Rehearsal evidence
docs/results/demo-summary.json                Small reviewed metric summary
```

---

### Task 1: Establish the Integration Base and Record Branch SHAs

**Files:**
- Create: `docs/runbooks/integration.md`

**Interfaces:**
- Consumes: green Phase 0 and owner branch SHAs.
- Produces: immutable integration manifest listing base, A, B, C, and D commits.

- [ ] **Step 1: Verify Phase 0 and protected-main state**

Run:

```bash
git fetch origin
git switch main
git pull --ff-only
make ci
git status --short
```

Expected: all checks pass and worktree is clean.

- [ ] **Step 2: Record candidate commits and CI links**

In `docs/runbooks/integration.md`, record the exact `git rev-parse` SHA for `main`, `origin/feat/data-simulator`, `origin/feat/ml-predict`, `origin/feat/recommend-api`, and `origin/feat/web-map`, plus each green CI run URL and contract version.

- [ ] **Step 3: Confirm no feature branch modifies protected shared files**

Run for each branch:

```bash
git diff --name-only main...origin/feat/data-simulator
git diff --name-only main...origin/feat/ml-predict
git diff --name-only main...origin/feat/recommend-api
git diff --name-only main...origin/feat/web-map
```

Expected: changes stay within owner paths documented by specs; unexpected contract/root/CI changes stop integration and return to the owner PR.

- [ ] **Step 4: Commit the integration manifest**

```bash
git add docs/runbooks/integration.md
git commit -m "docs: record integration candidates"
```

### Task 2: Integrate A and B Producer Modules

**Files:**
- Modify: `docs/runbooks/integration.md`
- Create: `app/backend/tests/integration/test_data_prediction_handoff.py`

**Interfaces:**
- Consumes: A status/fixture formats and B dataset/Predictor public exports.
- Produces: proof that B trains/infers from A output without private imports.

- [ ] **Step 1: Merge or update from reviewed A and B PRs through GitHub**

Use squash merge after both branches are current with `main`. Pull `main` with `--ff-only`; record resulting merge SHAs.

- [ ] **Step 2: Write a failing handoff integration test**

```python
from pathlib import Path

from app.backend.contracts.enums import Scenario
from app.backend.modules.prediction.features import FeatureBuilder
from app.backend.modules.prediction.labels import build_labels
from app.backend.modules.prediction.dataset import validate_status_frame
from app.backend.modules.simulation.public import generate_status_history
from app.backend.modules.station_data.public import (
    generate_fixture_bundle,
    load_scenarios,
    load_stations,
)

STATIONS_FIXTURE = Path("app/backend/modules/station_data/fixtures/stations.json")
SCENARIOS_FIXTURE = Path("app/backend/modules/station_data/fixtures/scenarios.yaml")


def test_generated_status_history_builds_prediction_features() -> None:
    stations = load_stations(STATIONS_FIXTURE)
    config = load_scenarios(SCENARIOS_FIXTURE)[Scenario.NORMAL]
    bundle = generate_fixture_bundle(config, stations, vehicle_count=100)
    history = generate_status_history(bundle, stations)
    validated = validate_status_frame(history, stations)
    labels = build_labels(validated, horizons_minutes=[30])
    dataset = FeatureBuilder().build(validated, labels)
    assert not dataset.X.empty
    assert dataset.frame["observed_at"].max() < dataset.frame["eta"].max()
```

- [ ] **Step 3: Run and inspect the initial handoff result**

Run: `uv run pytest app/backend/tests/integration/test_data_prediction_handoff.py -v`

Expected: PASS if public handoff is complete; a schema/import failure is fixed in the owning module through a follow-up PR, not patched through private imports.

- [ ] **Step 4: Run A/B gates together**

Run: `uv run pytest app/backend/modules/station_data app/backend/modules/simulation app/backend/modules/prediction -v`

Expected: PASS.

- [ ] **Step 5: Commit only integration test/runbook changes**

```bash
git add app/backend/tests/integration/test_data_prediction_handoff.py docs/runbooks/integration.md
git commit -m "test: verify data to prediction handoff"
```

### Task 3: Integrate C with Real Predictor and Simulation Runner

**Files:**
- Modify: `app/backend/api/dependencies.py`
- Create: `app/backend/tests/integration/test_full_backend.py`
- Modify: `docs/runbooks/integration.md`

**Interfaces:**
- Consumes: B `load_predictor`, A `DefaultSimulationRunner`, C service/adapters.
- Produces: complete file/model/fake-route backend and contract-valid responses.

- [ ] **Step 1: Merge the reviewed C PR through GitHub and sync `main`**

Record its squash merge SHA. Run `make contract-check`; expected no OpenAPI/type diff.

- [ ] **Step 2: Write failing full-backend integration tests**

Create a temporary file data directory and tiny trained artifact. Build settings `file/model/fake`, call `/predict`, `/recommend`, `/simulate`, and `/reset`; validate each response with shared Pydantic contracts.

- [ ] **Step 3: Run the integration test**

Run: `uv run pytest app/backend/tests/integration/test_full_backend.py -v`

Expected: a failing composition import is corrected only in `dependencies.py`; domain behavior failures return to the owning module PR.

- [ ] **Step 4: Wire public exports in the composition root**

Use `load_predictor(settings.model_dir, status_repository, station_repository)` and `DefaultSimulationRunner(fixture_loader=load_fixture_bundle)`; keep Phase 0 fake selections available. Do not import private files.

- [ ] **Step 5: Run backend and contract gates**

Run: `uv run pytest app/backend -v && make contract-check && make lint`

Expected: PASS and generated artifacts unchanged.

- [ ] **Step 6: Commit integration-only wiring/tests**

```bash
git add app/backend/api/dependencies.py app/backend/tests/integration/test_full_backend.py docs/runbooks/integration.md
git commit -m "feat: integrate prediction simulation and API"
```

### Task 4: Integrate D Against the Real Local Backend

**Files:**
- Create: `app/frontend/e2e/integrated-driver.spec.ts`
- Create: `app/frontend/e2e/integrated-operator.spec.ts`
- Modify: `app/frontend/playwright.config.ts`
- Modify: `docs/runbooks/integration.md`

**Interfaces:**
- Consumes: real local backend with file/model/fake-route mode and frontend generated types.
- Produces: browser proof for Driver and Operator P0.

- [ ] **Step 1: Merge the reviewed D PR through GitHub and sync `main`**

Run `make contract-check`; expected no generated type diff.

- [ ] **Step 2: Add real-backend Playwright projects**

Start backend in a deterministic demo replay mode, start Vite with `VITE_API_BASE_URL=http://127.0.0.1:8000/api`, and retain the existing mock project.

- [ ] **Step 3: Write Driver integration flow**

Reset allocation, submit the 20% preset once, assert request ID stability on retry, primary/backup feasibility, probability-at-ETA label, source/model versions, and text plan present even when map resources are blocked.

- [ ] **Step 4: Write Operator integration flow**

Switch normal → 30/4 → Tết, assert pressure response changes by scenario, run the same 100-vehicle seed for three strategies, and display all metrics without a hard-coded winner.

- [ ] **Step 5: Run browser and full gates**

Run: `npm --prefix app/frontend run test:e2e && make ci`

Expected: PASS in no-network fake-route mode.

- [ ] **Step 6: Commit integration tests/runbook only**

```bash
git add app/frontend/e2e app/frontend/playwright.config.ts docs/runbooks/integration.md
git commit -m "test: verify integrated demo flows"
```

### Task 5: Generate Honest Demo Results

**Files:**
- Create: `docs/results/demo-summary.json`
- Create: `docs/results/README.md`
- Create: `app/backend/tests/integration/test_demo_result_manifest.py`

**Interfaces:**
- Produces: small reviewable summary for three scenarios and strategies with fixture/model/config hashes.

- [ ] **Step 1: Write failing result-manifest validation test**

Assert each scenario has all three strategies, same fixture hash/seed/count per comparison, bounded success rate, non-negative metrics, `0 <= failed_count <= vehicle_count`, versions, timestamp, and `data_type="simulated"`. Independently assert the runner emitted exactly one terminal outcome record per requested vehicle.

- [ ] **Step 2: Generate results through the real runner**

Run the documented A CLI with seed 42, vehicle count 100, each scenario, and all strategies. Write large/raw outputs to ignored result paths; extract only the contract-valid summary into `docs/results/demo-summary.json`.

- [ ] **Step 3: Run validation**

Run: `uv run pytest app/backend/tests/integration/test_demo_result_manifest.py -v`

Expected: PASS. If AI does not win, retain the result and explain it; never edit the metrics manually.

- [ ] **Step 4: Document metric definitions and limitations**

README states immediate-arrival success definition, wait cap/population, detour definition, simulated-data limitation, fixture/model/config versions, and exact regeneration command.

- [ ] **Step 5: Commit**

```bash
git add docs/results app/backend/tests/integration/test_demo_result_manifest.py
git commit -m "docs: publish reproducible demo metrics"
```

### Task 6: Package the One-Worker Demo

**Files:**
- Create: `deploy/backend.Dockerfile`
- Create: `deploy/frontend.Dockerfile`
- Create: `deploy/nginx.conf`
- Create: `deploy/compose.demo.yml`
- Create: `deploy/.env.demo.example`
- Create: `deploy/README.md`
- Create: `app/backend/tests/integration/test_health.py`

**Interfaces:**
- Produces: `docker compose -f deploy/compose.demo.yml up --build` with frontend, one backend worker, health/readiness, and mounted artifacts/cache.

- [ ] **Step 1: Write failing health/readiness tests**

Assert `/health` returns process status and `/ready` reports selected repository/predictor/route readiness without leaking secrets.

- [ ] **Step 2: Add minimal multi-stage images**

Backend installs from `uv.lock`, runs as non-root, exposes one Uvicorn worker, and has a health check. Frontend builds from `package-lock.json`, serves static assets through Nginx, and proxies `/api` to backend.

- [ ] **Step 3: Add Compose modes**

Default uses `mock/fake/fake` with no secrets. Document file/model/fake-route demo overrides and optional Goong key injection from an uncommitted `.env`.

- [ ] **Step 4: Build and smoke test containers**

```bash
docker compose -f deploy/compose.demo.yml build
docker compose -f deploy/compose.demo.yml up -d
curl --fail http://localhost:8000/health
curl --fail http://localhost:5173/api/stations
docker compose -f deploy/compose.demo.yml down
```

Expected: both curls succeed; no secret exists in image history/config.

- [ ] **Step 5: Run packaging tests and commit**

```bash
uv run pytest app/backend/tests/integration/test_health.py -v
git add deploy app/backend/tests/integration/test_health.py
git commit -m "build: package reproducible demo"
```

### Task 7: Enforce GitHub Protection and Release Artifact

**Files:**
- Modify: `.github/workflows/release.yml`
- Modify: `docs/runbooks/branch-protection.md`
- Modify: `docs/runbooks/integration.md`

**Interfaces:**
- Produces: protected `main` and immutable `demo-v*` release artifact/image tied to a green commit.

- [ ] **Step 1: Confirm required checks in repository settings**

Require `python-quality`, `python-tests`, `contract-check`, `frontend-quality`, `integration-smoke`, and `security`; one non-author approval; stale dismissal; resolved conversations; up-to-date branches; linear history; no force push/deletion; no routine admin bypass.

- [ ] **Step 2: Finalize verified code owners**

List repository collaborators through GitHub settings or `gh api repos/thangak18/V-EV-Flow/collaborators`, map Bảo/Thắng/Kiên/Tú to confirmed handles, add at least two maintainers for shared contracts/workflows/tooling in `.github/CODEOWNERS`, then enable required code-owner review. Record the mapping in the private team handoff, not in public source if a member requests privacy.

- [ ] **Step 3: Extend release workflow to build demo images/artifacts**

After `make ci`, build both images, label them with full commit SHA, generate checksums, upload Compose/runbook/frontend build/demo summary, and publish only on manual approval or `demo-v*` tag.

- [ ] **Step 4: Exercise release without production deployment**

Run workflow dispatch from a green commit. Download artifacts, verify checksums, start the Compose bundle locally, and record workflow/artifact URLs in integration runbook.

- [ ] **Step 5: Commit workflow/runbook changes**

```bash
git add .github/CODEOWNERS .github/workflows/release.yml docs/runbooks/branch-protection.md docs/runbooks/integration.md
git commit -m "ci: package verified demo releases"
```

### Task 8: Rehearse, Freeze, and Tag the Demo

**Files:**
- Create: `docs/runbooks/demo-checklist.md`
- Modify: `docs/DEMO.md`

**Interfaces:**
- Produces: timed 3–5 minute rehearsal, offline fallback, video evidence, and release tag.

- [ ] **Step 1: Run the clean-clone gate**

```bash
make setup
make ci
docker compose -f deploy/compose.demo.yml up --build -d
git status --short
```

Expected: gates pass, services healthy, and worktree clean.

- [ ] **Step 2: Execute the exact demo flow twice after reset**

Run Driver 20% plan, Operator scenario switch, and three-strategy comparison. Confirm repeated runs use recorded seed/fixture/model and give identical results after reset.

- [ ] **Step 3: Test failure modes**

Disable network/map, remove Goong key, select unavailable model path, and stop backend once. Confirm explicit UI/API errors, textual map fallback, and usable mock/offline recovery.

- [ ] **Step 4: Record checklist evidence**

Record time per step, browser/laptop, release SHA, fixture/model/data versions, screenshots, video path/checksum, backup commands, and every observed limitation.

- [ ] **Step 5: Commit final runbook updates**

```bash
git add docs/DEMO.md docs/runbooks/demo-checklist.md
git commit -m "docs: finalize demo rehearsal checklist"
```

- [ ] **Step 6: Freeze features and create release tag**

After all required checks pass and the submission commit is approved:

```bash
git tag -a demo-v1.0.0 -m "V-EV Flow hackathon demo"
git push origin demo-v1.0.0
```

Expected: release workflow packages the exact tagged green commit. After the freeze, accept only reviewed bug fixes; no P1 feature enters the demo release.
