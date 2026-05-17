from __future__ import annotations

import json
import os
import sys
import tempfile
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
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"WARNING: state file unreadable ({exc}); starting fresh", file=sys.stderr)
        return State()
    return State(
        seen_ids=set(data.get("seen_ids", [])),
        consecutive_failures=data.get("consecutive_failures", 0),
        initialized=data.get("initialized", False),
    )


def save_state(path: Path, state: State) -> None:
    path = Path(path)
    payload = {
        "seen_ids": sorted(state.seen_ids),
        "consecutive_failures": state.consecutive_failures,
        "initialized": state.initialized,
    }
    text = json.dumps(payload, indent=2)
    directory = path.parent if str(path.parent) not in ("", ".") else Path(".")
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".state-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
