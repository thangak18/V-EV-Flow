# D/Tú Frontend and Map Implementation Plan

> **For agentic workers:** Read applicable AGENTS/SPEC and this plan. Implement within the assigned owner paths, run the focused checks and `make ci`, and record actual results in the PR. No external skill/plugin is required.

**Goal:** Deliver a responsive Driver experience and an Operator pressure/simulation experience that work against the frozen OpenAPI mock before real backend integration.

**Architecture:** One React/Vite/TypeScript application has Driver and Operator routes. All HTTP passes through a typed API service generated from OpenAPI; UI state lives in page-level hooks; map rendering is isolated behind a `MapAdapter` so tests and offline fallback do not require Goong.

**Tech Stack:** React, Vite, TypeScript, React Router, Vitest, Testing Library, Playwright, generated OpenAPI types, Goong Maps JS selected from verified official integration docs.

**Spec:** `app/frontend/SPEC.md` and `docs/UI_SPEC.md`

## Global Constraints

- Start `feat/web-map` from the green Phase 0 merge SHA.
- Edit only `app/frontend`, frontend tests/docs, and UI screenshots used as PR evidence.
- Do not edit backend code, contracts, OpenAPI, generated API types by hand, root tooling, or CI.
- Build against the committed mock API first; real integration must require no payload-shape changes.
- All HTTP uses `src/services/api`; components never call `fetch` directly.
- `/recommend` runs only after explicit user submit; render/refetch must not create virtual load.
- Probability, pressure proxy, and heuristic ranking score remain distinct.
- Map failure must preserve a usable textual plan.
- Every task uses red-green-refactor and a focused commit.

## File Map

```text
app/frontend/src/app/router.tsx                 Driver/Operator routes
app/frontend/src/services/api.ts                Only HTTP boundary
app/frontend/src/pages/DriverPage.tsx           Driver orchestration
app/frontend/src/pages/OperatorPage.tsx         Operator orchestration
app/frontend/src/features/driver/               Form and plan presentation
app/frontend/src/features/operator/             Pressure/simulation presentation
app/frontend/src/components/map/                Map adapter/view/fallback
app/frontend/src/components/common/             Badge/error/loading components
app/frontend/src/hooks/                         Request state hooks
app/frontend/e2e/                                Browser flows
```

---

### Task 1: Harden the Generated-Type API Service

**Files:**
- Modify: `app/frontend/src/services/api.ts`
- Create: `app/frontend/src/services/errors.ts`
- Create: `app/frontend/src/services/api.test.ts`

**Interfaces:**
- Produces: typed methods `listStations`, `predict`, `recommend`, `getPressure`, `simulate`, `reset`; `ApiError` with status/code/message/details.

- [ ] **Step 1: Write failing service tests**

```typescript
test("maps a business error without losing code", async () => {
  const fetcher = mockFetch(409, { code: "REQUEST_ID_CONFLICT", message: "conflict", details: {} });
  await expect(new ApiClient("/api", fetcher).recommend(validRequest)).rejects.toMatchObject({
    status: 409,
    code: "REQUEST_ID_CONFLICT",
  });
});
```

Add success tests per endpoint, standard FastAPI 422 mapping, network failure, abort signal, malformed JSON, and base URL normalization.

- [ ] **Step 2: Verify failure**

Run: `npm --prefix app/frontend test -- --run src/services/api.test.ts`

Expected: FAIL because full methods/error mapping do not exist.

- [ ] **Step 3: Implement one generic request primitive**

```typescript
private async request<T>(path: string, init: RequestInit): Promise<T> {
  const response = await this.fetcher(`${this.baseUrl}${path}`, init);
  const body: unknown = await response.json();
  if (!response.ok) throw ApiError.fromResponse(response.status, body);
  if (typeof body !== "object" || body === null) {
    throw new ApiError(502, "INVALID_API_RESPONSE", "API response must be an object", {});
  }
  return body as T;
}
```

Use generated `paths` operation request/response types for every public method. Each endpoint method checks its required discriminants (`data_type`, request ID, station/result collection, or reset flag) before returning. Do not duplicate DTO interfaces.

- [ ] **Step 4: Run service tests and typecheck**

Run: `npm --prefix app/frontend test -- --run src/services/api.test.ts && npm --prefix app/frontend run build`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/frontend/src/services
git commit -m "feat(web): harden typed API service"
```

### Task 2: Add Application Routing and Shared Status Components

**Files:**
- Create: `app/frontend/src/app/router.tsx`
- Create: `app/frontend/src/app/AppShell.tsx`
- Create: `app/frontend/src/components/common/DataTypeBadge.tsx`
- Create: `app/frontend/src/components/common/AsyncState.tsx`
- Create: `app/frontend/src/components/common/common.test.tsx`
- Modify: `app/frontend/src/App.tsx`
- Prerequisite tooling PR (outside this feature branch): `app/frontend/package.json` and `app/frontend/package-lock.json` if routing dependency is missing.

**Interfaces:**
- Produces: `/driver`, `/operator`, default redirect, accessible nav, `DataTypeBadge`, and loading/error/empty primitives.

- [ ] **Step 1: Write failing route and status tests**

Test default redirect, active nav, `mock/simulated/real/mixed` badge copy, loading status role, retry action, and empty-state message.

- [ ] **Step 2: Verify failure**

Run: `npm --prefix app/frontend test -- --run src/components/common/common.test.tsx`

Expected: FAIL because router/components do not exist.

- [ ] **Step 3: Implement semantic shell and components**

First verify the routing dependency is present in the frozen manifest. If missing, create a separate tooling prerequisite and wait for its reviewed merge; then merge `main` and run `make setup`. Do not install/change manifests or locks on `feat/web-map`. Use links/buttons with visible focus, `aria-live="polite"` for async status, color plus text/icon rather than color alone, and no automatic endpoint calls in the shared shell.

- [ ] **Step 4: Run tests**

Run: `npm --prefix app/frontend test -- --run src/components/common/common.test.tsx`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/frontend/src/app app/frontend/src/components/common app/frontend/src/App.tsx
git commit -m "feat(web): add routes and shared status UI"
```

### Task 3: Build the Driver Request Form and Explicit Submit Flow

**Files:**
- Create: `app/frontend/src/features/driver/DriverForm.tsx`
- Create: `app/frontend/src/features/driver/DriverForm.test.tsx`
- Create: `app/frontend/src/hooks/useRecommendation.ts`
- Create: `app/frontend/src/pages/DriverPage.tsx`
- Create: `app/frontend/src/pages/DriverPage.test.tsx`

**Interfaces:**
- Produces: validated form values matching `RecommendRequest` and `useRecommendation.submit(request)`.

- [ ] **Step 1: Write failing form tests**

Test corridor presets, default SOC 20, battery 60 kWh, consumption 0.18 kWh/km, CCS2, invalid ranges, submit disabled while pending, and exactly one request per explicit click.

- [ ] **Step 2: Verify failure**

Run: `npm --prefix app/frontend test -- --run DriverForm DriverPage`

Expected: FAIL because Driver form/page do not exist.

- [ ] **Step 3: Implement controlled validation and request IDs**

Generate one `crypto.randomUUID()` per submit and retain it for retry of the same payload. A changed payload generates a new ID. Use timezone-aware ISO strings from the selected demo time.

- [ ] **Step 4: Implement request state hook**

The hook exposes `idle | loading | success | empty | error`, aborts superseded requests, retries only on user action, and never calls recommend during mount/render.

- [ ] **Step 5: Run tests**

Run: `npm --prefix app/frontend test -- --run DriverForm DriverPage`

Expected: PASS, including request-call count assertions.

- [ ] **Step 6: Commit**

```bash
git add app/frontend/src/features/driver app/frontend/src/hooks/useRecommendation.ts app/frontend/src/pages/DriverPage.tsx app/frontend/src/pages/DriverPage.test.tsx
git commit -m "feat(web): add explicit driver recommendation flow"
```

### Task 4: Render Primary, Backup, Probability, and Limitations

**Files:**
- Create: `app/frontend/src/features/driver/StationPlanCard.tsx`
- Create: `app/frontend/src/features/driver/PlanSummary.tsx`
- Create: `app/frontend/src/features/driver/PlanSummary.test.tsx`
- Modify: `app/frontend/src/pages/DriverPage.tsx`

**Interfaces:**
- Consumes: generated `RecommendResponse`.
- Produces: primary/backup cards and transparent plan probability/assumption copy.

- [ ] **Step 1: Write failing plan-display tests**

Test ETA-specific probability formatting, arrival SOC, distance/detour, primary versus backup labels, absent backup, no-plan reasons, data/model versions, mock label, and independence assumption.

- [ ] **Step 2: Verify failure**

Run: `npm --prefix app/frontend test -- --run PlanSummary`

Expected: FAIL because plan components do not exist.

- [ ] **Step 3: Implement presentation without probability distortion**

Round probability for display only; preserve numeric value for semantics. Never render allocation score as probability. Show `plan_p_assumption` next to the combined plan estimate and use plain Vietnamese explanations from response reasons.

- [ ] **Step 4: Run tests**

Run: `npm --prefix app/frontend test -- --run PlanSummary`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/frontend/src/features/driver app/frontend/src/pages/DriverPage.tsx
git commit -m "feat(web): present transparent charging plans"
```

### Task 5: Add a Provider-Isolated Map and Offline Fallback

**Files:**
- Create: `app/frontend/src/components/map/types.ts`
- Create: `app/frontend/src/components/map/MapAdapter.ts`
- Create: `app/frontend/src/components/map/FakeMapAdapter.ts`
- Create: `app/frontend/src/components/map/GoongMapAdapter.ts`
- Create: `app/frontend/src/components/map/MapView.tsx`
- Create: `app/frontend/src/components/map/MapView.test.tsx`
- Modify: `app/frontend/src/pages/DriverPage.tsx`

**Interfaces:**
- Produces: `MapAdapter.mount(container, model)`, `MapAdapter.update(model)`, `MapAdapter.destroy()`, and textual fallback.

- [ ] **Step 1: Confirm the supported Goong browser SDK from official docs and record the package/script choice**

Record the exact SDK name, version, key usage, attribution, and coordinate order in `app/frontend/SPEC.md`. If a dependency must be installed, open a separate tooling prerequisite PR and integrate it before continuing this feature task. Do not use an inferred package name or edit manifests/lockfiles on this lane.

- [ ] **Step 2: Write failing adapter lifecycle tests**

Test mount/update/destroy calls, `[lng, lat]` conversion only inside adapter, primary/backup marker distinction, and fallback when adapter rejects.

- [ ] **Step 3: Verify failure**

Run: `npm --prefix app/frontend test -- --run MapView`

Expected: FAIL because map boundary does not exist.

- [ ] **Step 4: Implement fake adapter and MapView first**

MapView depends only on `MapAdapter`. Always render a station/plan text list outside the map. Catch provider load failure and keep the list visible with a network warning.

- [ ] **Step 5: Implement Goong adapter behind the same interface**

Read `VITE_GOONG_MAP_KEY`; fail visibly when absent in real-map mode. Restrict provider-specific types and `[lng, lat]` conversion to `GoongMapAdapter.ts`.

- [ ] **Step 6: Run tests and build**

Run: `npm --prefix app/frontend test -- --run MapView && npm --prefix app/frontend run build`

Expected: PASS; test suite uses fake adapter and no network/key.

- [ ] **Step 7: Commit**

```bash
git add app/frontend/src/components/map app/frontend/src/pages/DriverPage.tsx app/frontend/SPEC.md
git commit -m "feat(web): add isolated charging map"
```

### Task 6: Build Pressure Scenario and Time Controls

**Files:**
- Create: `app/frontend/src/features/operator/ScenarioSelector.tsx`
- Create: `app/frontend/src/features/operator/PressureLegend.tsx`
- Create: `app/frontend/src/hooks/usePressure.ts`
- Create: `app/frontend/src/pages/OperatorPage.tsx`
- Create: `app/frontend/src/pages/OperatorPage.test.tsx`

**Interfaces:**
- Produces: explicit scenario/time query and pressure station model for MapView.

- [ ] **Step 1: Write failing Operator pressure tests**

Test normal/30-4/Tết values, timezone-aware time, loading/error/empty, pressure legend, source/version labels, and pressure score displayed as risk proxy rather than probability guarantee.

- [ ] **Step 2: Verify failure**

Run: `npm --prefix app/frontend test -- --run OperatorPage`

Expected: FAIL because Operator page does not exist.

- [ ] **Step 3: Implement explicit controls and fetch hook**

Fetch on user-confirmed scenario/time change, abort old requests, and keep last successful result visible with stale/error indication during retry.

- [ ] **Step 4: Reuse MapView with pressure model**

Pass station colors plus numeric/text legend; do not reuse Driver allocation state or call recommend.

- [ ] **Step 5: Run tests**

Run: `npm --prefix app/frontend test -- --run OperatorPage`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/frontend/src/features/operator app/frontend/src/hooks/usePressure.ts app/frontend/src/pages/OperatorPage.tsx app/frontend/src/pages/OperatorPage.test.tsx
git commit -m "feat(web): add operator pressure view"
```

### Task 7: Compare the Three Simulation Strategies

**Files:**
- Create: `app/frontend/src/features/operator/SimulationControls.tsx`
- Create: `app/frontend/src/features/operator/StrategyComparison.tsx`
- Create: `app/frontend/src/features/operator/StrategyComparison.test.tsx`
- Create: `app/frontend/src/hooks/useSimulationComparison.ts`
- Modify: `app/frontend/src/pages/OperatorPage.tsx`

**Interfaces:**
- Produces: same-scenario/seed/vehicle-count requests for `nearest`, `currently_available`, and `ai_allocation`; table/bar presentation of all metrics.

- [ ] **Step 1: Write failing comparison tests**

Test exactly three requests with same seed/config/count, no hard-coded winner, success rate/detour/wait/failed count, partial failure display, and disabled duplicate run while pending.

- [ ] **Step 2: Verify failure**

Run: `npm --prefix app/frontend test -- --run StrategyComparison`

Expected: FAIL because simulation comparison does not exist.

- [ ] **Step 3: Implement parallel requests with stable association**

Use `Promise.allSettled`, attach strategy to each result, preserve successful rows when one fails, and show seed/scenario/vehicle/model/data versions.

- [ ] **Step 4: Render accessible table and optional CSS bars**

Always show numeric values; bars are supplementary. Do not claim AI wins and do not conceal failed vehicles.

- [ ] **Step 5: Run tests**

Run: `npm --prefix app/frontend test -- --run StrategyComparison`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/frontend/src/features/operator app/frontend/src/hooks/useSimulationComparison.ts app/frontend/src/pages/OperatorPage.tsx
git commit -m "feat(web): compare charging strategies"
```

### Task 8: Polish Responsive, Error, and End-to-End Behavior

**Files:**
- Modify: `app/frontend/src/index.css`
- Modify: `app/frontend/src/pages/DriverPage.tsx`
- Modify: `app/frontend/src/pages/OperatorPage.tsx`
- Create: `app/frontend/e2e/driver.spec.ts`
- Create: `app/frontend/e2e/operator.spec.ts`
- Create: `app/frontend/e2e/map-failure.spec.ts`
- Modify: `app/frontend/SPEC.md`

**Interfaces:**
- Produces: verified 390px/full-mobile Driver and desktop Operator flows using mock API.

- [ ] **Step 1: Write failing E2E flows**

Driver: enter preset/SOC, submit once, see primary/backup and mock label. Operator: change scenario, see pressure, run three strategies. Map failure: block provider resources and retain textual plan.

- [ ] **Step 2: Verify E2E failure**

Run: `npm --prefix app/frontend run test:e2e`

Expected: at least one new flow fails before polish/fixtures are complete.

- [ ] **Step 3: Implement responsive CSS and accessibility fixes**

Driver desktop uses a readable ~390px panel and full viewport on narrow screens; Operator uses desktop grid. Preserve 44px touch targets, visible focus, labels, contrast, projector-readable text, and reduced-motion preference.

- [ ] **Step 4: Run the owner gate**

```bash
npm --prefix app/frontend run lint
npm --prefix app/frontend run format:check
npm --prefix app/frontend run test:coverage
npm --prefix app/frontend run build
npm --prefix app/frontend run test:e2e
make contract-check
```

Expected: PASS with no generated type diff.

- [ ] **Step 5: Capture PR evidence**

Capture Driver desktop/mobile, Operator pressure, strategy comparison, and map-failure fallback screenshots. Record browser/version and mock API commit SHA.

- [ ] **Step 6: Commit and open PR**

```bash
git add app/frontend
git commit -m "feat(web): complete responsive demo flows"
```

PR evidence includes command output, screenshots, API contract SHA, one-request-on-submit proof, source labels, map fallback, and known P1 exclusions.
