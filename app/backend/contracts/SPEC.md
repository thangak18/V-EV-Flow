# Shared Contracts and OpenAPI Specification

## Purpose and Ownership

This module freezes the shapes that allow four branches to integrate. Phase 0 owns its initial creation; later changes require a dedicated contract PR reviewed by affected producers and consumers.

## Required Contracts

Define strict DTOs and enums for stations, status snapshots/windows, scenarios, vehicle trips, prediction input/results, route results, ranked plans, recommendation requests/responses, pressure output, simulation requests/results, versions, and domain errors. Preserve field names and units from `docs/DATA_CONTRACT.md` and `docs/API_CONTRACT.md` unless a reviewed contract PR changes them.

Define ports for station/status repositories, route provider, predictor, allocation strategy, and simulation runner. Ports express behavior and typed inputs/outputs, not implementation details.

## OpenAPI Policy

`openapi.yaml` is the committed public HTTP artifact generated deterministically from FastAPI/Pydantic. It is not hand-edited. It includes stable operation IDs, examples, nullable behavior, enums, business errors, and source/version metadata. Frontend types are generated from this artifact.

Contract verification regenerates OpenAPI, lints it, validates examples, detects breaking changes against `main`, regenerates frontend types, and fails on any diff. Pydantic models reject unknown fields and validate timezone, ranges, coordinate bounds, port totals, and enum values.

## Forbidden Changes

Feature branches may not rename fields, weaken validation, introduce a parallel schema, or place module-specific algorithms here. A contract change is complete only when examples, tests, OpenAPI, generated frontend types, docs, and affected adapters agree.
