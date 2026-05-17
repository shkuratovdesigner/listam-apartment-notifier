from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class State:
    seen_ids: set[str] = field(default_factory=set)
    consecutive_failures: int = 0
    initialized: bool = False


def load_state(path: Path) -> State:
    path = Path(path)
    if not path.exists():
        return State()
    data = json.loads(path.read_text(encoding="utf-8"))
    return State(
        seen_ids=set(data.get("seen_ids", [])),
        consecutive_failures=data.get("consecutive_failures", 0),
        initialized=data.get("initialized", False),
    )


def save_state(path: Path, state: State) -> None:
    payload = {
        "seen_ids": sorted(state.seen_ids),
        "consecutive_failures": state.consecutive_failures,
        "initialized": state.initialized,
    }
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
