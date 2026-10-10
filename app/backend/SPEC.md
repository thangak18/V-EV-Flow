# Backend Modular Monolith Specification

## Purpose

The backend hosts station data, simulation, prediction, recommendation, infrastructure adapters, and FastAPI in one Python 3.11 application. Module boundaries provide independent development without internal network services.

## Dependency Direction

`contracts` depends on no application module. Domain modules may import contracts and narrowly scoped `core` utilities. Infrastructure implements contract ports. API imports public module interfaces and infrastructure only to assemble dependencies. Domain modules must not import API or another module's private files.

Architecture tests enforce these rules. Cross-module behavior is exposed through documented package exports; imports from names marked `internal` are forbidden.

## Runtime Rules

- Startup validates settings and unavailable adapters fail fast.
- Business services receive dependencies through constructors or FastAPI providers.
- Domain failures are typed; API maps them to the documented HTTP errors.
- Simulation state is separate from Driver allocation state.
- One worker is the supported demo configuration unless state storage changes.

## Verification

Backend quality requires formatting, lint, type checks for public interfaces, architecture checks, unit tests, contract tests, integration tests, and the API smoke test.
