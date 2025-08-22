from dataclasses import dataclass

@dataclass
class ScopeRef:
    resource_name: str
    idn: str = ''
    resource: object = None
