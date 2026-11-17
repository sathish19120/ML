"""Risk triad classifier service (Flask)."""
import hashlib
import json
import os
import re
import time
import uuid

from flask import Flask, Response, g, jsonify, request
from werkzeug.exceptions import HTTPException

from .audit import AuditLog
from .model import ModelLoadError, ModelRegistry, ValidationError, score_item, validate_payload
from .observability import Metrics, iso_now, log_event, setup_logging
from .security import hash_email, policy_violation, redact

EMAIL_HEADER_RE = re.compile(r"^[^@\s]+@[^@\s]+$")


def error_body(code, message, request_id=None, details=None, **extra):
    body = {"error": {"code": code, "message": message, "details": details or []}, "request_id": request_id}
    body.update(extra)
    return body


def create_app(artifacts_dir=None, audit_path=None):
    setup_logging()
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 1_000_000

    artifacts_dir = artifacts_dir or os.environ.get("MODEL_ARTIFACTS_DIR", "./model_artifacts")
    audit_path = audit_path or os.environ.get("AUDIT_LOG_PATH", "./audit_logs/audit.jsonl")

    metrics = Metrics()
    registry = ModelRegistry(artifacts_dir)
    audit = AuditLog(audit_path, metrics.audit_error)
    app.extensions["registry"] = registry
    app.extensions["metrics"] = metrics

    try:
        m = registry.load()
        log_event("model_loaded", version=m.model_version, artifact_checksum_sha256=m.checksum)
    except ModelLoadError as e:
        log_event("model_load_failed", level="error", error=str(e))

    # ---------- request lifecycle ----------
    @app.before_request
    def _start():
        g.t0 = time.perf_counter()
        g.request_id = None
        g.user_hash = None

    @app.after_request
    def _observe(resp):
        ms = (time.perf_counter() - g.t0) * 1000
        route = request.url_rule.rule if request.url_rule else "unmatched"
        metrics.observe_http(route, request.method, resp.status_code, ms)
        log_event("http_request", route=route, method=request.method, status=resp.status_code,
                  latency_ms=round(ms, 3), request_id=g.request_id, user_hash=g.user_hash)
        return resp

    @app.errorhandler(HTTPException)
    def _http_err(e):
        code = (e.name or "error").lower().replace(" ", "_")
        return jsonify(error_body(code, e.description or e.name)), e.code

    @app.errorhandler(Exception)
    def _unhandled(e):
        log_event("unhandled_exception", level="error", error=type(e).__name__)
        return jsonify(error_body("internal_error", "internal server error")), 500

    # ---------- probes / metadata ----------
    @app.get("/healthz")
    def healthz():
        return jsonify({"status": "ok"})

    @app.get("/readyz")
    def readyz():
        m = registry.current
        if m is None:
            return jsonify(error_body("not_ready", "no valid model artifact loaded")), 503
        return jsonify({"status": "ready", "model_version": m.model_version})

    def model_meta(m):
        return {
            "provider": m.provider,
            "model_name": m.model_name,
            "model_version": m.model_version,
            "created_at": m.created_at,
            "artifact_path": m.artifact_path,
            "artifact_checksum_sha256": m.checksum,
            "checksum_verified": m.checksum_verified,
            "rule_config": m.rule_config,
        }

    @app.get("/model")
    def get_model():
        m = registry.current
        if m is None:
            return jsonify(error_body("model_unavailable", "no model loaded")), 503
        return jsonify(model_meta(m))

    @app.post("/model/reload")
    def reload_model():
        try:
            m = registry.load()
        except ModelLoadError as e:
            log_event("model_reload_failed", level="error", error=str(e))
            return jsonify(error_body("model_reload_failed", str(e))), 500
        log_event("model_reloaded", version=m.model_version, artifact_checksum_sha256=m.checksum)
        return jsonify(model_meta(m))

    @app.get("/metrics")
    def get_metrics():
        return Response(metrics.render(registry.current), mimetype="text/plain; version=0.0.4")

    # ---------- predict ----------
    @app.post("/predict")
    def predict():
        start = g.t0
        model = registry.current
        ctx = {"request_id": None, "guardrails": []}

        def respond(http_status, body, status, num_inputs=0):
            latency = int((time.perf_counter() - start) * 1000)
            body["latency_ms"] = latency
            raw = json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8")
            audit.append({
                "timestamp": iso_now(),
                "request_id": redact(ctx["request_id"] or ""),
                "user_hash": g.user_hash,
                "route": "/predict",
                "model_version": model.model_version if model else None,
                "artifact_checksum_sha256": model.checksum if model else None,
                "num_inputs": num_inputs,
                "guardrails_triggered": ctx["guardrails"],
                "status": status,
                "latency_ms": latency,
                "response_checksum_sha256": hashlib.sha256(raw).hexdigest(),
            })
            metrics.observe_predict(status)
            return Response(raw, status=http_status, mimetype="application/json")

        def fail(http_status, code, message, details=None, status="error", num_inputs=0):
            body = error_body(code, message, ctx["request_id"], details, guardrails_triggered=ctx["guardrails"])
            return respond(http_status, body, status, num_inputs)

        try:
            payload = request.get_json(silent=True) if request.is_json else None
            if isinstance(payload, dict) and isinstance(payload.get("request_id"), str) and payload["request_id"].strip():
                ctx["request_id"] = payload["request_id"]
            else:
                ctx["request_id"] = str(uuid.uuid4())
            g.request_id = ctx["request_id"]

            email = (request.headers.get("X-User-Email") or "").strip()
            if not email:
                return fail(400, "missing_user_email", "X-User-Email header is required")
            if not EMAIL_HEADER_RE.match(email):
                return fail(400, "invalid_user_email", "X-User-Email is not a valid email")
            g.user_hash = hash_email(email)

            if not request.is_json:
                return fail(415, "unsupported_media_type", "Content-Type must be application/json")
            if payload is None:
                return fail(400, "invalid_json", "request body is not valid JSON")

            try:
                _, inputs = validate_payload(payload)
            except ValidationError as ve:
                n = len(payload.get("inputs", [])) if isinstance(payload.get("inputs"), list) else 0
                return fail(422, "validation_error", "request validation failed", ve.details, num_inputs=n)

            n = len(inputs)
            for i, it in enumerate(inputs):
                if policy_violation(it["text"]):
                    ctx["guardrails"] = ["policy_block"]
                    return fail(400, "policy_block", "request blocked by content policy",
                                [{"path": f"inputs[{i}].text", "message": "disallowed intent"}],
                                status="blocked", num_inputs=n)

            if model is None:
                return fail(503, "model_unavailable", "no model loaded", num_inputs=n)

            preds = []
            for it in inputs:
                score, label, reasons = score_item(model, it["text"], it.get("features") or {})
                preds.append({"id": it["id"], "label": label, "score": score, "reasons": reasons})

            body = {
                "request_id": ctx["request_id"],
                "model": {
                    "provider": model.provider,
                    "model_name": model.model_name,
                    "model_version": model.model_version,
                    "artifact_checksum_sha256": model.checksum,
                    "schema_version": "v1",
                },
                "predictions": preds,
                "guardrails_triggered": [],
            }
            return respond(200, body, "success", n)
        except Exception as e:  # noqa: BLE001 - any failure must still be audited
            log_event("predict_exception", level="error", error=type(e).__name__)
            return fail(500, "internal_error", "internal server error")

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
