from __future__ import annotations
import json, os, pathlib, threading
from typing import Any, Dict

# Default config
_DEFAULT = {"print": True, "trace": True, "wait": True}

# Where to read logging options from:
# 1) ENV var TASK_AUTOMATION_LOGCFG points to a JSON file
# 2) app/logging.json
# 3) fallback to defaults above
def _load_cfg() -> Dict[str, Any]:
    cand: list[pathlib.Path] = []
    env = os.environ.get("TASK_AUTOMATION_LOGCFG")
    if env:
        cand.append(pathlib.Path(env))
    cand.append(pathlib.Path(__file__).resolve().parents[1] / "logging.json")
    for p in cand:
        try:
            if p.is_file():
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return {**_DEFAULT, **data}
        except Exception:
            pass
    return dict(_DEFAULT)

_CFG = _load_cfg()

def enabled(which: str) -> bool:
    # which in {"print", "trace", "wait"}
    try:
        return bool(_CFG.get(which, False))
    except Exception:
        return False

def thread_label() -> str:
    try:
        import threading
        return "main-thread" if threading.current_thread() is threading.main_thread() else f"worker:{threading.current_thread().name}"
    except Exception:
        return "unknown-thread"
