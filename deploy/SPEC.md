# Demo Deployment Specification

## Purpose

`deploy/` contains reproducible packaging and local/demo orchestration, not application logic. Phase 0 defines intended files and validation; actual deployment remains subordinate to a green local P0.

## Required Outcome

The demo package starts one backend worker and the built frontend with documented environment variables, health checks, startup order, persistent cache/artifact mounts where needed, and no baked-in secrets. Mock mode must run without external credentials. Real Goong/model/data modes fail clearly when required configuration is absent.

CI builds deployment artifacts to catch packaging errors. Release automation is manual or tag-driven; production infrastructure, high availability, database server, and automatic production rollout are outside hackathon scope.
