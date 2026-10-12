"""Provenance manifest and persistence for generated fixture bundles."""

import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.backend.contracts.enums import DataType
from app.backend.contracts.simulation import DataManifest, FixtureBundle

DATA_VERSION = "station-data-0.1.0"
BUNDLE_FILE = "fixture_bundle.json"
MANIFEST_FILE = "manifest.json"
_TZ = timezone(timedelta(hours=7))


def fixture_hash(bundle: FixtureBundle) -> str:
    """SHA-256 of the canonical bundle JSON; equal bundles hash equally."""
    return hashlib.sha256(bundle.model_dump_json().encode("utf-8")).hexdigest()


def build_manifest(bundle: FixtureBundle, generated_at: datetime | None = None) -> DataManifest:
    return DataManifest(
        fixture_hash=fixture_hash(bundle),
        data_version=DATA_VERSION,
        scenario=bundle.scenario,
        seed=bundle.seed,
        counts={
            "vehicles": len(bundle.vehicles),
            "background_arrivals": len(bundle.background_arrivals),
            "service_durations": len(bundle.service_durations),
            "port_events": len(bundle.port_events),
        },
        generated_at=generated_at or datetime.now(_TZ),
        data_type=DataType.SIMULATED,
    )


def write_fixture_bundle(bundle: FixtureBundle, output_dir: Path) -> DataManifest:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(bundle)
    (output_dir / BUNDLE_FILE).write_text(bundle.model_dump_json(), encoding="utf-8")
    (output_dir / MANIFEST_FILE).write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return manifest


def load_fixture_bundle(path: Path) -> FixtureBundle:
    """Read a bundle file; verify it against a sibling manifest when one exists."""
    path = Path(path)
    bundle = FixtureBundle.model_validate_json(path.read_text(encoding="utf-8"))
    manifest_path = path.with_name(MANIFEST_FILE)
    if manifest_path.exists():
        manifest = DataManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
        if manifest.fixture_hash != fixture_hash(bundle):
            raise ValueError(f"fixture hash mismatch for {path}")
    return bundle
