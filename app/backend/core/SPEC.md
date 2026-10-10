# Backend Core Specification

## Purpose

`core` contains only cross-cutting primitives that cannot belong to a domain module: validated application settings, version metadata, clock abstraction, startup configuration errors, and bootstrap-safe logging configuration.

## Boundaries

Core may depend on standard libraries and shared contracts but never on station data, simulation, prediction, recommendation, infrastructure, or API. Domain logic, repositories, provider clients, model loading, and FastAPI dependencies do not belong here.

Settings declare adapter choices and required configuration. Validation rejects invalid combinations and missing requirements at startup. Secrets use environment values and are never represented in logs or committed defaults.

## Required Tests and Done Criteria

Test defaults for mock mode, parsing and validation, missing real-adapter configuration, secret redaction, timezone defaults, and deterministic version reporting. Done means every runtime mode is selected through one validated settings object and no module reads environment variables directly.
