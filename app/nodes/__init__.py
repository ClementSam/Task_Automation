
from . import base, control, convert, math, text, custom_events, arrays
# optional: serial node
try:
    from . import serial  # noqa: F401
except Exception:
    pass
from . import variables_runtime, constants  # noqa: F401

# optional: scope nodes (PyVISA)
try:
    from . import scope  # noqa: F401
except Exception:
    pass
