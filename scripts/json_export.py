"""JSON writer: saves enriched records with never-overwrite numbering."""

import json
from pathlib import Path


def next_available_path(path: Path) -> Path:
    """output.json -> output_1.json -> output_2.json -> ..."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        return path
    counter = 1
    while True:
        candidate = path.with_name(f"{path.stem}_{counter}{path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def write_json(records: list[dict], destination) -> Path:
    """Write enriched records (as plain dicts) to a pretty JSON file."""
    destination = Path(destination)
    if destination.suffix != ".json":
        destination = destination.with_suffix(".json")
    destination = next_available_path(destination)
    destination.write_text(json.dumps(records, indent=2), encoding="utf-8")
    return destination
