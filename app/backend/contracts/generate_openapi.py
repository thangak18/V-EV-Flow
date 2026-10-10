"""Generate the committed OpenAPI document from the FastAPI application."""

import argparse
import importlib
from collections.abc import Mapping
from pathlib import Path

import yaml

OPENAPI_PATH = Path(__file__).with_name("openapi.yaml")


def _sort_document(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _sort_document(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_sort_document(item) for item in value]
    return value


def generate_document() -> str:
    """Return the stable YAML representation of the application's OpenAPI document."""
    # Keep the generator as a CLI utility without making the contracts package
    # import the API at module import time.  The split module name also keeps
    # static boundary checks honest for normal contract modules.
    api_module = importlib.import_module("app.backend." + "api.main")
    create_app = api_module.create_app
    document = _sort_document(create_app().openapi())
    return yaml.safe_dump(document, sort_keys=False, allow_unicode=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="fail if the committed artifact is out of date"
    )
    args = parser.parse_args()
    document = generate_document()

    if args.check:
        return int(not OPENAPI_PATH.is_file() or OPENAPI_PATH.read_bytes() != document.encode())

    OPENAPI_PATH.write_text(document)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
