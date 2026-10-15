"""Start the single-worker simulated demo from a trusted unpacked ML release."""

import argparse
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

import uvicorn

from app.backend.api.main import create_app
from app.backend.core.settings import Settings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-dir", required=True, type=Path)
    parser.add_argument("--capacity-models-dir", type=Path)
    parser.add_argument("--allocation-db", type=Path)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--route-backend", choices=("fake", "goong"), default="fake")
    args = parser.parse_args()
    release = args.release_dir.resolve()
    for relative in (
        "model/manifest.json",
        "data/stations.json",
        "data/station_status.parquet",
        "data/manifest.json",
        "producer_scenarios.yaml",
    ):
        if not (release / relative).is_file():
            parser.error(f"release is missing {relative}")
    # DATA_DIR's canonical layout is generated/, whereas a release uses data/.
    # Copy small simulated fixtures to a process-owned directory; leave the release immutable.
    with TemporaryDirectory(prefix="v-ev-flow-demo-") as temporary:
        data_dir = Path(temporary)
        shutil.copytree(release / "data", data_dir / "generated")
        settings = Settings(
            data_backend="file",
            capacity_models_dir=args.capacity_models_dir,
            allocation_backend="sqlite" if args.allocation_db else "memory",
            allocation_db_path=args.allocation_db or Path(".cache/allocation.sqlite3"),
            predictor_backend="model",
            simulation_backend="stateful",
            prediction_explanations=True,
            time_shift_suggestions=True,
            route_backend=args.route_backend,
            places_backend="goong" if args.route_backend == "goong" else "disabled",
            data_dir=data_dir,
            model_dir=release / "model",
            simulation_scenarios_path=release / "producer_scenarios.yaml",
        )
        app = create_app(settings)
        print(
            "V-EV Flow: simulated data, calibrated model, stateful runner; one worker.", flush=True
        )
        uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
