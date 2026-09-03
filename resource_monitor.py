"""Lightweight host and NVIDIA GPU statistics for the Reaper menu monitor."""

from __future__ import annotations

import threading
from typing import Any

try:
    import psutil
except ImportError:  # Keep the extension loadable until requirements are installed.
    psutil = None


class _NvidiaMonitor:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._nvml: Any = None
        self._handles: list[Any] = []
        self._names: list[str] = []
        self._attempted = False

    def _initialize(self) -> None:
        if self._attempted:
            return
        self._attempted = True
        try:
            import pynvml

            pynvml.nvmlInit()
            self._nvml = pynvml
            for index in range(pynvml.nvmlDeviceGetCount()):
                handle = pynvml.nvmlDeviceGetHandleByIndex(index)
                name = pynvml.nvmlDeviceGetName(handle)
                if isinstance(name, bytes):
                    name = name.decode("utf-8", errors="replace")
                self._handles.append(handle)
                self._names.append(str(name))
        except Exception:
            self._nvml = None
            self._handles.clear()
            self._names.clear()

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            self._initialize()
            if self._nvml is None:
                return []
            result = []
            for index, handle in enumerate(self._handles):
                try:
                    utilization = self._nvml.nvmlDeviceGetUtilizationRates(handle)
                    memory = self._nvml.nvmlDeviceGetMemoryInfo(handle)
                    temperature = self._nvml.nvmlDeviceGetTemperature(
                        handle, self._nvml.NVML_TEMPERATURE_GPU
                    )
                    power_watts = None
                    power_limit_watts = None
                    power_percent = None
                    try:
                        power_watts = float(
                            self._nvml.nvmlDeviceGetPowerUsage(handle)
                        ) / 1000.0
                        power_limit_watts = float(
                            self._nvml.nvmlDeviceGetEnforcedPowerLimit(handle)
                        ) / 1000.0
                        if power_limit_watts > 0:
                            power_percent = power_watts / power_limit_watts * 100.0
                    except Exception:
                        pass
                    result.append(
                        {
                            "index": index,
                            "name": self._names[index],
                            "utilization": float(utilization.gpu),
                            "temperature": float(temperature),
                            "vram_used": int(memory.used),
                            "vram_total": int(memory.total),
                            "vram_percent": (
                                float(memory.used) / float(memory.total) * 100.0
                                if memory.total
                                else 0.0
                            ),
                            "power_watts": power_watts,
                            "power_limit_watts": power_limit_watts,
                            "power_percent": power_percent,
                        }
                    )
                except Exception:
                    continue
            return result


_nvidia = _NvidiaMonitor()


def resource_snapshot() -> dict[str, Any]:
    """Return a JSON-safe, point-in-time resource snapshot."""
    if psutil is None:
        return {
            "available": False,
            "error": "psutil is not installed; run pip install -r requirements.txt",
            "gpus": _nvidia.snapshot(),
        }

    ram = psutil.virtual_memory()
    return {
        "available": True,
        "cpu_percent": float(psutil.cpu_percent(interval=None)),
        "ram_used": int(ram.used),
        "ram_total": int(ram.total),
        "ram_percent": float(ram.percent),
        "gpus": _nvidia.snapshot(),
    }
