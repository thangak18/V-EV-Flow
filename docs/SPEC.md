# Documentation Specification

## Authority

The source proposals explain product intent. The approved design, module specs, data/API contracts, and implementation plans explain what agents must build. When they differ, `docs/SCOPE.md` controls P0/P1 scope, shared contracts control runtime shapes, and the newest approved design controls architecture.

## Rules

Documentation must distinguish implemented behavior from planned behavior, mock/simulated data from real data, and examples from measured results. Commands are documented as runnable only after verification. Contract changes update data/API docs, examples, OpenAPI, generated frontend types, and affected module specs together.

Each module `SPEC.md` states objective, ownership, inputs/outputs, boundaries, invariants, tests, non-goals, and Definition of Done. Implementation plans use exact paths, commands, expected outcomes, dependency fakes, and PR checkpoints so coding agents do not need to invent cross-project decisions.
