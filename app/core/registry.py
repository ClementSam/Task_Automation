from typing import Dict, Type

class NodeRegistry:
    def __init__(self):
        self._types: Dict[str, Type] = {}

    def register(self, cls):
        self._types[cls.type_name()] = cls
        return cls

    def create(self, type_name: str, **params):
        cls = self._types[type_name]
        return cls(**params)

    def types(self) -> Dict[str, Type]:
        return dict(self._types)

registry = NodeRegistry()
