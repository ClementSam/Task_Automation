
from dataclasses import dataclass
from typing import Optional
try:
    import pyvisa
    HAVE_VISA = True
except Exception:  # pragma: no cover - optional dependency
    pyvisa = None
    HAVE_VISA = False


@dataclass
class TekMSO5:
    """Very thin helper for Tektronix 5-Series MSO over VISA (VXI-11)."""
    host: str
    timeout_ms: int = 10000
    backend: str = ""  # e.g. "@py" to force pyvisa-py

    def __post_init__(self):
        if not HAVE_VISA:
            raise RuntimeError("PyVISA is not available. Please install 'pyvisa' (and 'pyvisa-py' for VXI-11).")
        # FIX: if backend is empty, call ResourceManager() with no arg (avoids None bug on some versions)
        self._rm = pyvisa.ResourceManager(self.backend) if self.backend else pyvisa.ResourceManager()
        self._res = self._rm.open_resource(f"TCPIP::{self.host}::INSTR", timeout=self.timeout_ms)
        try:
            # generous chunks for large transfers (images / sessions / waveforms)
            self._res.chunk_size = max(getattr(self._res, "chunk_size", 1024*1024), 50 * 1024 * 1024)
        except Exception:
            pass

    @property
    def resource(self):
        return self._res

    def idn(self) -> str:
        try:
            return self._res.query("*IDN?").strip()
        except Exception:
            return ""

    def opc(self) -> None:
        try:
            self._res.query("*OPC?")
        except Exception:
            pass

    # ---- FileSystem helpers -------------------------------------------------
    def read_file(self, scope_path: str) -> bytes:
        # Request file content, then read raw IEEE block
        self._res.write(f'FILESystem:READFile "{scope_path}"')
        return self._res.read_raw()

    def write_file(self, scope_path: str, data: bytes) -> None:
        # Binary block write (IEEE 488.2)
        self._res.write_binary_values(f'FILESystem:WRITEFile "{scope_path}",', data, datatype="s")

    def list_dir(self, scope_dir: str) -> str:
        try:
            return self._res.query(f'FILESystem:LDIR? "{scope_dir}"')
        except Exception:
            return self._res.query(f'FILESystem:DIR? "{scope_dir}"')

    # ---- Save helpers -------------------------------------------------------
    def save_setup(self, scope_path: str) -> None:
        self._res.write(f'SAVe:SETUp "{scope_path}"')
        self.opc()

    def recall_setup(self, scope_path: str) -> None:
        self._res.write(f'RECAll:SETUp "{scope_path}"')
        self.opc()

    def save_image(self, scope_path: str) -> None:
        self._res.write(f'SAVe:IMAGe "{scope_path}"')
        self.opc()

    def save_waveform(self, sources: str, scope_path: str) -> None:
        self._res.write(f'SAVe:WAVEform {sources},"{scope_path}"')
        self.opc()

    def save_session(self, scope_path: str) -> None:
        self._res.write(f'SAVe:SESSion "{scope_path}"')
        self.opc()

    def close(self) -> None:
        try:
            self._res.close()
        except Exception:
            pass
