# Demo watchdog utility
"""
Utility to monitor long‑running subprocesses (e.g., data fetchers) and restart them if they crash.
Used by the server to ensure background tasks stay alive.
"""
import threading
import subprocess
import time
import logging
from typing import Callable, List

_logger = logging.getLogger("demo_watchdog")

class Watchdog:
    def __init__(self, cmd: List[str], restart_delay: float = 5.0, name: str = "subprocess"):
        self.cmd = cmd
        self.restart_delay = restart_delay
        self.name = name
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        _logger.info(f"[watchdog] Starting {self.name} with cmd: {self.cmd}")
        self._thread.start()

    def stop(self):
        _logger.info(f"[watchdog] Stopping {self.name}")
        self._stop_event.set()
        self._thread.join()

    def _run(self):
        while not self._stop_event.is_set():
            try:
                proc = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                _logger.info(f"[watchdog] {self.name} launched PID {proc.pid}")
                stdout, stderr = proc.communicate()
                if proc.returncode != 0:
                    _logger.error(f"[watchdog] {self.name} exited with code {proc.returncode}. Stderr: {stderr.decode().strip()}")
                else:
                    _logger.info(f"[watchdog] {self.name} completed successfully.")
            except Exception as e:
                _logger.exception(f"[watchdog] Exception while running {self.name}: {e}")
            if self._stop_event.is_set():
                break
            _logger.info(f"[watchdog] Restarting {self.name} in {self.restart_delay}s")
            time.sleep(self.restart_delay)

def monitor_process(command: List[str], name: str = "process", restart_delay: float = 5.0) -> Watchdog:
    """Convenient helper to create and start a Watchdog for a given command.
    Returns the Watchdog instance so callers can stop it later.
    """
    wd = Watchdog(command, restart_delay=restart_delay, name=name)
    wd.start()
    return wd
