# Infrastructure Adapters Specification — C/Kiên

## Objective

Implement replaceable adapters for persistence and routing without leaking provider/file formats into domain modules.

## Adapter Set

Phase 0 provides mock repositories backed by small committed JSON fixtures, fake route/predictor/simulation adapters, and an in-memory virtual-load store. Kiên's P0 feature branch extends the data adapters to generated JSON/Parquet files and adds Goong routing with bounded cache. At integration, Thắng's public `Predictor` and Bảo's public `SimulationRunner` replace their fakes through the composition root; those implementations remain owned by their domain modules. A future Tasco/VETC adapter implements existing repository ports rather than changing consumers.

## Dependency Injection

The API composition root selects adapters from validated settings. Tests inject adapters directly. An unavailable selected backend fails startup; fallback must be explicit in the response source notes and logs.

## Conformance and Failure Behavior

All implementations of a port run the same reusable conformance suite. Route calls have timeout, normalized provider errors, deterministic fake responses, cache keys including route-relevant inputs, and recorded collection/expiry times. No adapter logs credentials or commits raw sensitive partner responses.

## Done Criteria

Mock and file adapters return equivalent DTO shapes, switching requires configuration only, provider failures map to typed domain failures, caches are reproducible for the fixed demo route, and integration tests do not require network access.
