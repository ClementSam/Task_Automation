from typing import Dict, Any, List, Tuple

class BaseNode:
    def __init__(self, **params):
        self._params = params

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
