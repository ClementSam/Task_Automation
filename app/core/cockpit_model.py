from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class CockpitItemModel:
    id: str
    type_name: str
    display_name: str = ""
    event_key: str = ""
    props: Dict[str, Any] = field(default_factory=dict)
    x: float = 0.0
    y: float = 0.0

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type_name,
            "display_name": self.display_name,
            "event_key": self.event_key,
            "props": self.props,
            "x": self.x,
            "y": self.y,
        }

    @staticmethod
    def from_dict(d):
        return CockpitItemModel(
            id=d.get("id") or d.get("nid") or "",
            type_name=d.get("type") or d.get("type_name") or "UIButton",
            display_name=(d.get("display_name") or ""),
            event_key=(d.get("event_key") or ""),
            props=d.get("props", {}),
            x=float(d.get("x", 0)),
            y=float(d.get("y", 0)),
        )
