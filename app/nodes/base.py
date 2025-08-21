from typing import Dict, Any, List, Tuple
from collections import deque
from PyQt5 import QtCore


class BaseNode:
    reentrant: bool = False

    def __init__(self, **params):
        self._params = params
        # scheduler will attach itself to nodes at run time
        self._scheduler = None  # type: ignore
        self._nid: str | None = None
        self.busy: bool = False
        self._local_q: deque[int] = deque()

    @classmethod
    def type_name(cls) -> str:
        return cls.__name__

    @classmethod
    def title(cls) -> str:
        return cls.__name__

    # ----- DATA -----
    @classmethod
    def inputs(cls) -> Dict[str, type]:
        return {}

    @classmethod
    def outputs(cls) -> Dict[str, type]:
        return {}

    # ----- EXEC -----
    @classmethod
    def exec_inputs(cls) -> List[str]:
        return []

    @classmethod
    def exec_outputs(cls) -> List[str]:
        return []

    def params(self) -> Dict[str, Any]:
        # copie simple
        return dict(self._params)

    def process(self, **kwargs) -> Dict[str, Any]:
        return {}

    def on_exec(self, **kwargs) -> Tuple[list, dict]:
        outs = list(self.exec_outputs())[:1]
        return outs, {}

    # ----- scheduler integration -----
    def attach(self, scheduler, nid: str) -> None:
        """Called by the scheduler to give context about the graph."""
        self._scheduler = scheduler
        self._nid = nid

    # local FIFO for single-seat behaviour
    def enqueue_local(self, token_id: int) -> None:
        self._local_q.append(token_id)

    def dequeue_local(self) -> int | None:
        return self._local_q.popleft() if self._local_q else None

    # default start implementation for synchronous nodes
    def start(self, token_id: int, **kwargs) -> None:
        outs, data = self.on_exec(token_id=token_id, **kwargs)
        # bounce back to scheduler asynchronously to avoid re-entrancy
        QtCore.QTimer.singleShot(
            0,
            lambda: self._scheduler.on_node_finished(
                self._nid, token_id, outs, data
            ),
        )

    # optional cancel hook for slow nodes
    def cancel(self) -> None:  # pragma: no cover - default noop
        pass

    # optional pause/resume hooks for long-running nodes
    def pause(self) -> None:  # pragma: no cover - default noop
        pass

    def resume(self) -> None:  # pragma: no cover - default noop
        pass
