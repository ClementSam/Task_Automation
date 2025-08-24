class CockpitRegistry:
    def __init__(self):
        self._map = {}

    def register(self, type_name, cls=None):
        def deco(c):
            self._map[type_name] = c
            c.type_name = type_name
            return c
        return deco if cls is None else deco(cls)

    def create(self, type_name, **kwargs):
        return self._map[type_name](**kwargs)

    def get(self, type_name):
        return self._map.get(type_name)

    def types(self):
        return list(self._map.keys())

cockpit_registry = CockpitRegistry()
