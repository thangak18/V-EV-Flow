# Backend Test Suite Specification

## Test Layers

Module unit tests verify public behavior using fakes. Contract tests verify Pydantic models, examples, OpenAPI, generated types, and domain errors. Adapter conformance tests run the same behavior against every implementation of a port. Integration tests assemble the real composition root with fake/mock external dependencies. Smoke tests exercise HTTP without network credentials.

## Determinism and Isolation

Tests control time, seed, fixtures, and settings. They do not depend on execution order, developer files, external APIs, large ignored artifacts, or Driver allocation state left by another test. Each test resets mutable state explicitly.

## Completion Standard

The suite reports actionable failures, runs through canonical Make targets, and contributes to the required coverage gate. Aggregate coverage never replaces direct tests for contract validation, adapter selection, SOC/backup behavior, idempotency, temporal leakage, simulator state, and documented error paths.
