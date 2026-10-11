#!/usr/bin/env bash

# Write the OpenAPI artifact from a base revision for oasdiff.  The first
# artifact introduction has no historical document to compare, so it is
# explicitly allowed while all generation, lint, and drift checks still run.
set -euo pipefail

base_ref="${1:-origin/main}"
baseline_path="${2:-.openapi-main.yaml}"
artifact_path="app/backend/contracts/openapi.yaml"

if ! git cat-file -e "${base_ref}^{commit}" 2>/dev/null; then
  echo "OpenAPI baseline base ref '${base_ref}' does not resolve to a commit." >&2
  exit 2
fi

if git cat-file -e "${base_ref}:${artifact_path}" 2>/dev/null; then
  git show "${base_ref}:${artifact_path}" >"${baseline_path}"
  echo "present=true" >>"${GITHUB_OUTPUT:-/dev/stdout}"
  echo "OpenAPI baseline found at ${base_ref}; oasdiff breaking check will run."
else
  rm -f "${baseline_path}"
  echo "present=false" >>"${GITHUB_OUTPUT:-/dev/stdout}"
  echo "No OpenAPI artifact exists at ${base_ref}; accepting the first committed OpenAPI artifact."
  echo "Generation, lint, and generated-type drift checks still ran; oasdiff resumes on later changes."
fi
