"""Structured audit log: ring buffer + stdout."""
import json
import sys
from collections import deque
from datetime import datetime, timezone

_ring: deque = deque(maxlen=1000)


def emit(entry: dict, verbose: bool) -> None:
    entry["ts"] = datetime.now(timezone.utc).isoformat()
    _ring.append(entry)
    if verbose:
        print(json.dumps(entry), file=sys.stdout, flush=True)


def get_all() -> list[dict]:
    return list(_ring)
