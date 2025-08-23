from typing import Dict, Any, List, Tuple
from .base import BaseNode
from ..core.registry import registry


@registry.register
class CustomEvent(BaseNode):
    """Event node triggered programmatically.

    It exposes a single exec output and generates tokens when
    the scheduler's ``trigger_custom_event`` is called with a matching name.
    """
    event_node = True
    is_event_source = True
    auto_start = False
    allow_title_edit = True
    is_custom_event = True

    @classmethod
    def title(cls) -> str:
        return "CustomEvent"

    @classmethod
    def exec_outputs(cls) -> List[str]:
        return ["exec_out"]

    def on_exec(self, **kwargs) -> Tuple[List[str], Dict[str, Any]]:
        return (["exec_out"], {})


@registry.register
class CallCustomEvent(BaseNode):
    """Node that triggers all ``CustomEvent`` nodes sharing its name."""
    allow_title_edit = True

    @classmethod
    def title(cls) -> str:
        return "CallCustomEvent"

    @classmethod
    def exec_inputs(cls) -> List[str]:
        return ["exec_in"]

    @classmethod
    def exec_outputs(cls) -> List[str]:
        return ["exec_out"]

    def on_exec(self, **kwargs) -> Tuple[List[str], Dict[str, Any]]:
        name = self._params.get("name")
        if name and getattr(self, "_scheduler", None):
            try:
                self._scheduler.trigger_custom_event(str(name))
            except Exception:
                pass
        return (["exec_out"], {})
