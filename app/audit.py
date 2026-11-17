"""Append-only JSONL audit log."""
import json
import os
import threading


class AuditLog:
    def __init__(self, path: str, on_error):
        self.path = path
        self.on_error = on_error
        self._lock = threading.Lock()

    def append(self, record: dict) -> bool:
        line = (json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n").encode("utf-8")
        try:
            with self._lock:
                os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
                fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o640)
                try:
                    os.write(fd, line)  # single O_APPEND write == one atomic record
                finally:
                    os.close(fd)
            return True
        except OSError:
            self.on_error()
            return False
