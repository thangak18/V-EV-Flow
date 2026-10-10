# Recommendation Module Specification — C/Kiên

## Objective

Select a feasible primary and backup station using routes, SOC, predicted availability, and virtual-load ranking while keeping prediction probability separate from heuristic allocation score.

## Injected Dependencies

Receive station/status repositories, `RouteProvider`, `Predictor`, clock/config, and virtual-load store through public ports. Do not instantiate file, Goong, or model implementations inside business services.

## Required Behavior

Filter incompatible or unreachable stations before ranking. Compute arrival SOC with documented units and configurable safety threshold. Backup follows origin → primary → backup and must remain reachable if primary cannot charge. Handle no primary/backup explicitly. Compute `plan_p` only with its independence assumption. Apply virtual load to primary charging buckets, not backup; retries with the same request ID/payload are idempotent and conflicting reuse is rejected.

## Boundaries and Non-goals

This module contains no FastAPI objects, filesystem access, external HTTP client, ML training, or simulator loop. Ranking weights and normalization are configurable and reported as heuristic. Charge-to advice is deferred.

## Required Tests and Done Criteria

Test SOC edges, connector filtering, backup route/SOC, no-plan responses, ranking penalties, zero capacity, idempotent retry, request conflicts, reset/TTL, and concurrent updates. Done means the public service works entirely with fakes and returns contract-valid, source-labelled results.
