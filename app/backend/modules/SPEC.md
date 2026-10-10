# Backend Domain Modules Specification

## Purpose

Each child directory is an independently understandable module with a documented public package surface and private implementation. Module owners may choose internal structure and algorithms while preserving shared contracts and dependency direction.

## Rules

- Import shared DTOs and ports from `backend/contracts`.
- Export supported entry points explicitly; consumers do not import private/internal files.
- Do not instantiate infrastructure adapters or read environment variables.
- Do not import API delivery code.
- Do not change another module or shared contract in a feature PR.
- Keep tests close enough that module behavior can be verified with fakes.

Architecture checks must reject cycles and forbidden imports. A new cross-module need is expressed as a consumer-facing port and handled through a contract PR before implementation branches consume it.
