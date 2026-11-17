"""Prometheus-style metrics and redacted JSON logging."""
import json
import logging
import math
import sys
import threading
from collections import Counter, deque
from datetime import datetime, timezone

from .security import SAFE_KEYS, redact_obj


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class Metrics:
    def __init__(self):
        self._lock = threading.Lock()
        self.http = Counter()
        self.predict_requests = 0
        self.predict_errors = 0
        self.predict_blocked = 0
        self.audit_write_errors = 0
        self._lat = deque(maxlen=1000)

    def observe_http(self, route, method, status, latency_ms):
        with self._lock:
            self.http[(route, method, str(status))] += 1
            self._lat.append(latency_ms)

    def observe_predict(self, status):
        with self._lock:
            self.predict_requests += 1
            if status == "error":
                self.predict_errors += 1
            elif status == "blocked":
                self.predict_blocked += 1

    def audit_error(self):
        with self._lock:
            self.audit_write_errors += 1

    def p95(self) -> float:
        with self._lock:
            data = sorted(self._lat)
        if not data:
            return 0.0
        return round(data[max(0, math.ceil(0.95 * len(data)) - 1)], 3)

    def render(self, model=None) -> str:
        with self._lock:
            http = sorted(self.http.items())
            pr, pe, pb, ae = self.predict_requests, self.predict_errors, self.predict_blocked, self.audit_write_errors
        out = ["# TYPE http_requests_total counter"]
        for (route, method, status), n in http:
            out.append(f'http_requests_total{{route="{route}",method="{method}",status="{status}"}} {n}')
        out += [
            "# TYPE predict_requests_total counter", f"predict_requests_total {pr}",
            "# TYPE predict_errors_total counter", f"predict_errors_total {pe}",
            "# TYPE predict_blocked_total counter", f"predict_blocked_total {pb}",
            "# TYPE audit_write_errors_total counter", f"audit_write_errors_total {ae}",
            "# TYPE http_request_latency_ms_p95 gauge", f"http_request_latency_ms_p95 {self.p95()}",
        ]
        if model is not None:
            out += ["# TYPE model_info gauge",
                    f'model_info{{version="{model.model_version}",checksum="{model.checksum}"}} 1']
        return "\n".join(out) + "\n"


_logger = logging.getLogger("risk_service")


def setup_logging():
    if not _logger.handlers:
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(logging.Formatter("%(message)s"))
        _logger.addHandler(h)
        _logger.setLevel(logging.INFO)
        _logger.propagate = False


def log_event(event: str, level: str = "info", **fields):
    rec = {"ts": iso_now(), "level": level, "event": event}
    for k, v in fields.items():
        rec[k] = v if k in SAFE_KEYS else redact_obj(v)
    _logger.log(getattr(logging, level.upper()), json.dumps(rec, separators=(",", ":"), default=str))
