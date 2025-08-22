
from __future__ import annotations
from typing import Dict, Any, List, Tuple, Optional
import os
from .base import BaseNode
from ..core.registry import registry
from .utils import parse_bool_strict
from .scope_types import ScopeRef

try:
    from ..devices.tektronix_mso5 import TekMSO5, HAVE_VISA
except Exception:
    TekMSO5 = None  # type: ignore
    HAVE_VISA = False  # type: ignore

def _need(val) -> bool:
    return val not in (None, "", False)

def _get_input_or_default(node: BaseNode, kwargs: Dict[str, Any], key: str):
    v = kwargs.get(key, None)
    if v is None:
        v = node._params.get(f"in_default:{key}", node._params.get(key))
    return v

def _ensure_scope_ref(ref: Any) -> Optional[ScopeRef]:
    return ref if isinstance(ref, ScopeRef) else None

@registry.register
class connect_visa_vxi11(BaseNode):
    @classmethod
    def title(cls): return "Connect VISA (VXI-11)"
    @classmethod
    def type_name(cls): return "connect_visa_vxi11"
    @classmethod
    def inputs(cls): return {"host_or_ip": str, "timeout_ms": int, "backend": str}
    @classmethod
    def outputs(cls): return {"scope_ref": object, "idn": str, "connected": bool, "error": str}
    @classmethod
    def exec_inputs(cls): return ["in"]
    @classmethod
    def exec_outputs(cls): return ["then"]

    def on_exec(self, **kwargs) -> Tuple[List[str], Dict[str, Any]]:
        host = _get_input_or_default(self, kwargs, "host_or_ip")
        timeout_ms = _get_input_or_default(self, kwargs, "timeout_ms") or 10000
        backend = _get_input_or_default(self, kwargs, "backend") or ""

        if not _need(host):
            return ([], {})
        if not HAVE_VISA:
            return ([], {"scope_ref": None, "idn": "", "connected": False, "error": "PyVISA non disponible. Installez 'pyvisa' et éventuellement 'pyvisa-py'."})
        try:
            scope = TekMSO5(str(host), int(timeout_ms), str(backend))
            idn = scope.idn() or ""
            ref = ScopeRef(resource_name=f"TCPIP::{host}::INSTR", idn=idn, resource=scope.resource)
            return (["then"], {"scope_ref": ref, "idn": idn, "connected": bool(idn), "error": ""})
        except Exception as e:
            return ([], {"scope_ref": None, "idn": "", "connected": False, "error": str(e)})

@registry.register
class disconnect(BaseNode):
    @classmethod
    def title(cls): return "Disconnect Scope"
    @classmethod
    def type_name(cls): return "disconnect"
    @classmethod
    def inputs(cls): return {"scope_ref": object}
    @classmethod
    def outputs(cls): return {"disconnected": bool}
    @classmethod
    def exec_inputs(cls): return ["in"]
    @classmethod
    def exec_outputs(cls): return ["then"]

    def on_exec(self, **kwargs) -> Tuple[List[str], Dict[str, Any]]:
        ref = _ensure_scope_ref(_get_input_or_default(self, kwargs, "scope_ref"))
        if not ref:
            return ([], {})
        try:
            res = getattr(ref, "resource", None)
            if res:
                try: res.close()
                except Exception: pass
            ok = True
        except Exception:
            ok = False
        return (["then"], {"disconnected": ok})

@registry.register
class load_setup_from_pc(BaseNode):
    @classmethod
    def title(cls): return "Load Setup from PC"
    @classmethod
    def type_name(cls): return "load_setup_from_pc"
    @classmethod
    def inputs(cls): return {"in_path_pc": str, "scope_dest_path": str, "scope_ref": object}
    @classmethod
    def outputs(cls): return {"ok": bool}
    @classmethod
    def exec_inputs(cls): return ["in"]
    @classmethod
    def exec_outputs(cls): return ["then"]

    def on_exec(self, **kwargs):
        ref = _ensure_scope_ref(_get_input_or_default(self, kwargs, "scope_ref"))
        path_pc = _get_input_or_default(self, kwargs, "in_path_pc")
        scope_path = _get_input_or_default(self, kwargs, "scope_dest_path") or "C:/Temp/load.set"
        if not (ref and _need(path_pc)):
            return ([], {})
        with open(str(path_pc), "rb") as f:
            data = f.read()
        res = getattr(ref, "resource", None)
        res.write_binary_values(f'FILESystem:WRITEFile "{scope_path}",', data, datatype="s")
        res.write(f'RECAll:SETUp "{scope_path}"')
        try: res.query("*OPC?")
        except Exception: pass
        return (["then"], {"ok": True})

@registry.register
class save_setup_to_pc(BaseNode):
    @classmethod
    def title(cls): return "Save Setup to PC"
    @classmethod
    def type_name(cls): return "save_setup_to_pc"
    @classmethod
    def inputs(cls): return {"pc_path": str, "scope_tmp_path": str, "scope_ref": object}
    @classmethod
    def outputs(cls): return {"ok": bool}
    @classmethod
    def exec_inputs(cls): return ["in"]
    @classmethod
    def exec_outputs(cls): return ["then"]

    def on_exec(self, **kwargs):
        ref = _ensure_scope_ref(_get_input_or_default(self, kwargs, "scope_ref"))
        pc_path = _get_input_or_default(self, kwargs, "pc_path")
        scope_tmp = _get_input_or_default(self, kwargs, "scope_tmp_path") or "C:/Temp/save.set"
        if not (ref and _need(pc_path)):
            return ([], {})
        res = getattr(ref, "resource", None)
        res.write(f'SAVe:SETUp "{scope_tmp}"')
        try: res.query("*OPC?")
        except Exception: pass
        res.write(f'FILESystem:READFile "{scope_tmp}"')
        data = res.read_raw()
        os.makedirs(os.path.dirname(str(pc_path) or "."), exist_ok=True)
        with open(str(pc_path), "wb") as f:
            f.write(data)
        return (["then"], {"ok": True})

@registry.register
class transfer_file_from_scope_to_pc(BaseNode):
    @classmethod
    def title(cls): return "Transfer File (Scope → PC)"
    @classmethod
    def type_name(cls): return "transfer_file_from_scope_to_pc"
    @classmethod
    def inputs(cls): return {"scope_path": str, "pc_path": str, "scope_ref": object}
    @classmethod
    def outputs(cls): return {"ok": bool}
    @classmethod
    def exec_inputs(cls): return ["in"]
    @classmethod
    def exec_outputs(cls): return ["then"]

    def on_exec(self, **kwargs):
        ref = _ensure_scope_ref(_get_input_or_default(self, kwargs, "scope_ref"))
        scope_path = _get_input_or_default(self, kwargs, "scope_path")
        pc_path = _get_input_or_default(self, kwargs, "pc_path")
        if not (ref and _need(scope_path) and _need(pc_path)):
            return ([], {})
        res = getattr(ref, "resource", None)
        res.write(f'FILESystem:READFile "{scope_path}"')
        data = res.read_raw()
        os.makedirs(os.path.dirname(str(pc_path) or "."), exist_ok=True)
        with open(str(pc_path), "wb") as f:
            f.write(data)
        return (["then"], {"ok": True})

@registry.register
class transfer_file_from_pc_to_scope(BaseNode):
    @classmethod
    def title(cls): return "Transfer File (PC → Scope)"
    @classmethod
    def type_name(cls): return "transfer_file_from_pc_to_scope"
    @classmethod
    def inputs(cls): return {"pc_path": str, "scope_path": str, "scope_ref": object}
    @classmethod
    def outputs(cls): return {"ok": bool}
    @classmethod
    def exec_inputs(cls): return ["in"]
    @classmethod
    def exec_outputs(cls): return ["then"]

    def on_exec(self, **kwargs):
        ref = _ensure_scope_ref(_get_input_or_default(self, kwargs, "scope_ref"))
        pc_path = _get_input_or_default(self, kwargs, "pc_path")
        scope_path = _get_input_or_default(self, kwargs, "scope_path")
        if not (ref and _need(scope_path) and _need(pc_path)):
            return ([], {})
        with open(str(pc_path), "rb") as f:
            data = f.read()
        res = getattr(ref, "resource", None)
        res.write_binary_values(f'FILESystem:WRITEFile "{scope_path}",', data, datatype="s")
        return (["then"], {"ok": True})

@registry.register
class transfer_dir_from_scope_to_pc(BaseNode):
    @classmethod
    def title(cls): return "Transfer Directory (Scope → PC)"
    @classmethod
    def type_name(cls): return "transfer_dir_from_scope_to_pc"
    @classmethod
    def inputs(cls): return {"scope_dir": str, "pc_dir": str, "recursive": bool, "scope_ref": object}
    @classmethod
    def outputs(cls): return {"ok": bool}
    @classmethod
    def exec_inputs(cls): return ["in"]
    @classmethod
    def exec_outputs(cls): return ["then"]

    def on_exec(self, **kwargs):
        ref = _ensure_scope_ref(_get_input_or_default(self, kwargs, "scope_ref"))
        scope_dir = _get_input_or_default(self, kwargs, "scope_dir")
        pc_dir = _get_input_or_default(self, kwargs, "pc_dir")
        recursive = _get_input_or_default(self, kwargs, "recursive")
        recursive = parse_bool_strict(recursive)
        if recursive is None: recursive = False
        if not (ref and _need(scope_dir) and _need(pc_dir)):
            return ([], {})
        res = getattr(ref, "resource", None)
        os.makedirs(str(pc_dir), exist_ok=True)

        try:
            listing = res.query(f'FILESystem:LDIR? "{scope_dir}"')
        except Exception:
            listing = res.query(f'FILESystem:DIR? "{scope_dir}"')

        for line in listing.splitlines():
            parts = [p.strip() for p in line.split(",")]
            if not parts:
                continue
            name = parts[0].strip('"')
            kind = (parts[1] if len(parts) > 1 else "FILE").upper()
            if kind.startswith("DIR"):
                if recursive:
                    sub = type(self)()
                    sub._params = dict(self._params)
                    sub._scheduler = self._scheduler
                    sub._engine = getattr(self, "_engine", None)
                    sub.on_exec(scope_ref=ref, scope_dir=f"{scope_dir}/{name}", pc_dir=os.path.join(str(pc_dir), name), recursive=True)
                continue
            res.write(f'FILESystem:READFile "{scope_dir}/{name}"')
            data = res.read_raw()
            dst = os.path.join(str(pc_dir), name)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as f:
                f.write(data)
        return (["then"], {"ok": True})

@registry.register
class save_measure_to_scope(BaseNode):
    @classmethod
    def title(cls): return "Save Waveforms to Scope"
    @classmethod
    def type_name(cls): return "save_measure_to_scope"
    @classmethod
    def inputs(cls): return {"scope_ref": object, "sources": str, "scope_path": str}
    @classmethod
    def outputs(cls): return {"ok": bool}
    @classmethod
    def exec_inputs(cls): return ["in"]
    @classmethod
    def exec_outputs(cls): return ["then"]

    def on_exec(self, **kwargs):
        ref = _ensure_scope_ref(_get_input_or_default(self, kwargs, "scope_ref"))
        sources = _get_input_or_default(self, kwargs, "sources") or "ALL"
        scope_path = _get_input_or_default(self, kwargs, "scope_path") or "C:/Temp/waveforms.wfm"
        if not ref:
            return ([], {})
        res = getattr(ref, "resource", None)
        res.write(f'SAVe:WAVEform {sources},"{scope_path}"')
        try: res.query("*OPC?")
        except Exception: pass
        return (["then"], {"ok": True})

@registry.register
class save_image_to_scope(BaseNode):
    @classmethod
    def title(cls): return "Save Image to Scope"
    @classmethod
    def type_name(cls): return "save_image_to_scope"
    @classmethod
    def inputs(cls): return {"scope_ref": object, "scope_path": str}
    @classmethod
    def outputs(cls): return {"ok": bool}
    @classmethod
    def exec_inputs(cls): return ["in"]
    @classmethod
    def exec_outputs(cls): return ["then"]

    def on_exec(self, **kwargs):
        ref = _ensure_scope_ref(_get_input_or_default(self, kwargs, "scope_ref"))
        scope_path = _get_input_or_default(self, kwargs, "scope_path") or "C:/Temp/screenshot.png"
        if not ref:
            return ([], {})
        res = getattr(ref, "resource", None)
        res.write(f'SAVe:IMAGe "{scope_path}"')
        try: res.query("*OPC?")
        except Exception: pass
        return (["then"], {"ok": True})

@registry.register
class save_full_history_to_scope(BaseNode):
    @classmethod
    def title(cls): return "Save Session to Scope"
    @classmethod
    def type_name(cls): return "save_full_history_to_scope"
    @classmethod
    def inputs(cls): return {"scope_ref": object, "scope_path": str}
    @classmethod
    def outputs(cls): return {"ok": bool}
    @classmethod
    def exec_inputs(cls): return ["in"]
    @classmethod
    def exec_outputs(cls): return ["then"]

    def on_exec(self, **kwargs):
        ref = _ensure_scope_ref(_get_input_or_default(self, kwargs, "scope_ref"))
        scope_path = _get_input_or_default(self, kwargs, "scope_path") or "C:/Temp/session.tss"
        if not ref:
            return ([], {})
        res = getattr(ref, "resource", None)
        res.write(f'SAVe:SESSion "{scope_path}"')
        try: res.query("*OPC?")
        except Exception: pass
        return (["then"], {"ok": True})

def _save_then_pull(res, save_cmd: str, scope_path: str, pc_path: str) -> None:
    res.write(save_cmd.format(path=scope_path))
    try: res.query("*OPC?")
    except Exception: pass
    res.write(f'FILESystem:READFile "{scope_path}"')
    data = res.read_raw()
    os.makedirs(os.path.dirname(str(pc_path) or "."), exist_ok=True)
    with open(str(pc_path), "wb") as f:
        f.write(data)

@registry.register
class save_measure_to_pc(BaseNode):
    @classmethod
    def title(cls): return "Save Waveforms to PC"
    @classmethod
    def type_name(cls): return "save_measure_to_pc"
    @classmethod
    def inputs(cls): return {"scope_ref": object, "sources": str, "pc_path": str, "scope_tmp_path": str}
    @classmethod
    def outputs(cls): return {"ok": bool}
    @classmethod
    def exec_inputs(cls): return ["in"]
    @classmethod
    def exec_outputs(cls): return ["then"]

    def on_exec(self, **kwargs):
        ref = _ensure_scope_ref(_get_input_or_default(self, kwargs, "scope_ref"))
        sources = _get_input_or_default(self, kwargs, "sources") or "ALL"
        pc_path = _get_input_or_default(self, kwargs, "pc_path")
        scope_tmp = _get_input_or_default(self, kwargs, "scope_tmp_path") or "C:/Temp/waveforms.wfm"
        if not (ref and _need(pc_path)):
            return ([], {})
        res = getattr(ref, "resource", None)
        _save_then_pull(res, f'SAVe:WAVEform {sources},"' + '{path}"', scope_tmp, pc_path)
        return (["then"], {"ok": True})

@registry.register
class save_image_to_pc(BaseNode):
    @classmethod
    def title(cls): return "Save Image to PC"
    @classmethod
    def type_name(cls): return "save_image_to_pc"
    @classmethod
    def inputs(cls): return {"scope_ref": object, "pc_path": str, "scope_tmp_path": str}
    @classmethod
    def outputs(cls): return {"ok": bool}
    @classmethod
    def exec_inputs(cls): return ["in"]
    @classmethod
    def exec_outputs(cls): return ["then"]

    def on_exec(self, **kwargs):
        ref = _ensure_scope_ref(_get_input_or_default(self, kwargs, "scope_ref"))
        pc_path = _get_input_or_default(self, kwargs, "pc_path")
        scope_tmp = _get_input_or_default(self, kwargs, "scope_tmp_path") or "C:/Temp/screenshot.png"
        if not (ref and _need(pc_path)):
            return ([], {})
        res = getattr(ref, "resource", None)
        _save_then_pull(res, 'SAVe:IMAGe "' + '{path}"', scope_tmp, pc_path)
        return (["then"], {"ok": True})

@registry.register
class save_full_history_to_pc(BaseNode):
    @classmethod
    def title(cls): return "Save Session to PC"
    @classmethod
    def type_name(cls): return "save_full_history_to_pc"
    @classmethod
    def inputs(cls): return {"scope_ref": object, "pc_path": str, "scope_tmp_path": str}
    @classmethod
    def outputs(cls): return {"ok": bool}
    @classmethod
    def exec_inputs(cls): return ["in"]
    @classmethod
    def exec_outputs(cls): return ["then"]

    def on_exec(self, **kwargs):
        ref = _ensure_scope_ref(_get_input_or_default(self, kwargs, "scope_ref"))
        pc_path = _get_input_or_default(self, kwargs, "pc_path")
        scope_tmp = _get_input_or_default(self, kwargs, "scope_tmp_path") or "C:/Temp/session.tss"
        if not (ref and _need(pc_path)):
            return ([], {})
        res = getattr(ref, "resource", None)
        _save_then_pull(res, 'SAVe:SESSion "' + '{path}"', scope_tmp, pc_path)
        return (["then"], {"ok": True})
