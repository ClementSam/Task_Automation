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

    def by_category(self):
        """Return mapping {category: [cls,...]} sorted by category and title."""
        from collections import defaultdict
        buckets = defaultdict(list)
        for cls in self._types.values():
            # allow nodes to opt-out from the palette (e.g. variable get/set)
            if getattr(cls, 'HIDDEN', False):
                continue
            cat = getattr(cls, 'CATEGORY', None)
            if not cat and hasattr(cls, 'category'):
                try:
                    cat = cls.category()
                except Exception:
                    cat = None
            if not cat:
                mod = getattr(cls, '__module__', '')
                key = mod.split('.')[-1].lower()
                mapping = {'control': 'Contrôle', 'math': 'Math', 'convert': 'Conversion'}
                cat = mapping.get(key, key.capitalize() or 'Divers')
            buckets[cat].append(cls)
        out = {}
        for cat in sorted(buckets.keys(), key=lambda s: s.lower()):
            items = sorted(buckets[cat], key=lambda c: getattr(c, 'title', lambda: c.__name__)())
            out[cat] = items
        return out

registry = NodeRegistry()
