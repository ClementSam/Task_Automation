from ...core.cockpit_registry import cockpit_registry
from ...core.cockpit_model import CockpitItemModel
# ensure classes are registered
from .button import CockpitButtonItem  # noqa: F401
from .led import CockpitLedItem        # noqa: F401
from .text import CockpitTextItem      # noqa: F401

def create_cockpit_item(scheduler, model: CockpitItemModel):
    cls = cockpit_registry.get(model.type_name)
    if not cls:
        # fallback to a button
        cls = cockpit_registry.get("UIButton")
    return cls(scheduler, model)
