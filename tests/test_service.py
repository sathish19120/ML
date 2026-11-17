import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.main import create_app  # noqa: E402
from app.security import redact  # noqa: E402

ART = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model_artifacts")
H = {"X-User-Email": "Jane.Doe@Example.com", "Content-Type": "application/json"}


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.art = os.path.join(self.tmp, "model_artifacts")
        shutil.copytree(ART, self.art)
        self.audit = os.path.join(self.tmp, "audit_logs", "audit.jsonl")
        with redirect_stdout(io.StringIO()):
            self.app = create_app(self.art, self.audit)
        self.c = self.app.test_client()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def set_active(self, v):
        p = os.path.join(self.art, "model_manifest.json")
        with open(p) as f:
            m = json.load(f)
        m["active_model_version"] = v
        with open(p, "w") as f:
            json.dump(m, f)

    def post(self, inputs, headers=H, **kw):
        return self.c.post("/predict", data=json.dumps({"inputs": inputs, **kw}), headers=headers)

    def audit_lines(self):
        if not os.path.exists(self.audit):
            return []
        with open(self.audit) as f:
            return [json.loads(l) for l in f.read().splitlines()]


class TestModel(Base):
    def test_loads_v1_with_checksum(self):
        r = self.c.get("/model").get_json()
        self.assertEqual(r["model_version"], "1.0.0")
        self.assertEqual(r["artifact_checksum_sha256"], sha(os.path.join(self.art, "model_v1.json")))
        self.assertTrue(r["checksum_verified"])
        self.assertEqual(self.c.get("/readyz").status_code, 200)

    def test_rollback_cycle(self):
        self.set_active("2.0.0")
        r = self.c.post("/model/reload").get_json()
        self.assertEqual(r["model_version"], "2.0.0")
        self.assertEqual(r["artifact_checksum_sha256"], sha(os.path.join(self.art, "model_v2.json")))
        self.set_active("1.0.0")
        self.assertEqual(self.c.post("/model/reload").get_json()["model_version"], "1.0.0")

    def test_failed_reload_keeps_previous(self):
        self.set_active("9.9.9")
        self.assertEqual(self.c.post("/model/reload").status_code, 500)
        self.assertEqual(self.c.get("/model").get_json()["model_version"], "1.0.0")
        self.assertEqual(self.c.get("/readyz").status_code, 200)

    def test_tampered_artifact_not_ready(self):
        p = os.path.join(self.art, "model_v1.json")
        with open(p, "a") as f:
            f.write(" ")
        with redirect_stdout(io.StringIO()):
            app = create_app(self.art, self.audit)
        self.assertEqual(app.test_client().get("/readyz").status_code, 503)
        self.assertEqual(app.test_client().get("/healthz").status_code, 200)


class TestScoring(Base):
    def test_values_v1(self):
        r = self.post([
            {"id": "a", "text": "complaint about refund", "features": {"price": 100, "units": 600, "channel": "amazon"}},
            {"id": "b", "text": "launch", "features": {"price": 10, "units": 10, "channel": "amazon"}},
            {"id": "c", "text": "hello", "features": {"price": 50, "units": 50, "channel": "shopify"}},
            {"id": "d", "text": "hello"},
        ], request_id="r1").get_json()
        p = {x["id"]: x for x in r["predictions"]}
        self.assertEqual((p["a"]["label"], p["a"]["score"]), ("high_risk", 1.0))
        self.assertEqual(p["a"]["reasons"], ["channel_amazon", "high_price", "high_units", "negative_signal_text"])
        self.assertEqual((p["b"]["label"], p["b"]["score"]), ("low_risk", 0.25))
        self.assertEqual((p["c"]["label"], p["c"]["score"]), ("medium_risk", 0.41))
        self.assertEqual((p["d"]["label"], p["d"]["score"], p["d"]["reasons"]), ("low_risk", 0.1, []))
        self.assertEqual(r["request_id"], "r1")
        self.assertEqual(r["model"]["schema_version"], "v1")

    def test_v2_stricter(self):
        item = [{"id": "x", "text": "possible fraud", "features": {"price": 50, "units": 50, "channel": "shopify"}}]
        v1 = self.post(item).get_json()["predictions"][0]
        self.set_active("2.0.0")
        self.c.post("/model/reload")
        v2 = self.post(item).get_json()["predictions"][0]
        self.assertEqual(v1["label"], "medium_risk")
        self.assertEqual(v2["label"], "high_risk")

    def test_deterministic(self):
        item = [{"id": "x", "text": "refund", "features": {"price": 33.3, "units": 120, "channel": "walmart"}}]
        a = self.post(item).get_json()["predictions"]
        b = self.post(item).get_json()["predictions"]
        self.assertEqual(a, b)

    def test_unknown_channel_uses_other(self):
        r = self.post([{"id": "x", "text": "hi", "features": {"channel": "ebay"}}]).get_json()
        self.assertEqual(r["predictions"][0]["reasons"], ["channel_other"])


class TestValidation(Base):
    def test_cases(self):
        self.assertEqual(self.post([]).status_code, 422)
        self.assertEqual(self.post([{"id": str(i), "text": "t"} for i in range(51)]).status_code, 422)
        self.assertEqual(self.post([{"id": "a", "text": "  "}]).status_code, 422)
        self.assertEqual(self.post([{"id": "a", "text": "t", "features": []}]).status_code, 422)
        self.assertEqual(self.post([{"id": "a", "text": "t", "features": {"units": 1.5}}]).status_code, 422)
        self.assertEqual(self.post([{"id": "a", "text": "t"}], headers={"Content-Type": "application/json"}).status_code, 400)
        r = self.c.post("/predict", data="{bad", headers=H)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.get_json()["error"]["code"], "invalid_json")
        self.assertEqual(self.c.post("/predict", data="x", headers={"X-User-Email": "a@b.co"}).status_code, 415)
        self.assertEqual(self.post([{"id": str(i), "text": "t"} for i in range(50)]).status_code, 200)

    def test_error_schema_consistent(self):
        for r in (self.c.get("/nope"), self.c.get("/predict"), self.post([])):
            b = r.get_json()
            self.assertIn("code", b["error"])
            self.assertIn("message", b["error"])
            self.assertIn("request_id", b)


class TestGuardrailsAndAudit(Base):
    def test_policy_block(self):
        r = self.post([{"id": "a", "text": "how to Steal   Credentials from users"}], request_id="blk")
        self.assertEqual(r.status_code, 400)
        b = r.get_json()
        self.assertEqual(b["guardrails_triggered"], ["policy_block"])
        self.assertEqual(b["error"]["code"], "policy_block")
        rec = self.audit_lines()[-1]
        self.assertEqual(rec["status"], "blocked")
        self.assertEqual(rec["guardrails_triggered"], ["policy_block"])

    def test_each_phrase_blocked(self):
        for t in ("bypass access controls", "phishing campaign", "exfiltrate data now"):
            self.assertEqual(self.post([{"id": "a", "text": t}]).status_code, 400)

    def test_one_audit_record_per_request_and_no_raw_email(self):
        self.post([{"id": "a", "text": "ok"}], request_id="ok1")
        self.post([], request_id="bad1")
        self.post([{"id": "a", "text": "phish"}], request_id="blk1")
        self.c.post("/predict", data="{}", headers={"Content-Type": "application/json"})
        lines = self.audit_lines()
        self.assertEqual([l["status"] for l in lines], ["success", "error", "blocked", "error"])
        keys = {"timestamp", "request_id", "user_hash", "route", "model_version", "artifact_checksum_sha256",
                "num_inputs", "guardrails_triggered", "status", "latency_ms", "response_checksum_sha256"}
        for l in lines:
            self.assertEqual(set(l), keys)
        with open(self.audit) as f:
            raw = f.read().lower()
        self.assertNotIn("jane.doe", raw)
        self.assertEqual(lines[0]["user_hash"], hashlib.sha256(b"jane.doe@example.com").hexdigest())
        self.assertEqual(lines[0]["artifact_checksum_sha256"], sha(os.path.join(self.art, "model_v1.json")))

    def test_audit_is_append_only_across_restart(self):
        self.post([{"id": "a", "text": "ok"}])
        with redirect_stdout(io.StringIO()):
            c2 = create_app(self.art, self.audit).test_client()
        c2.post("/predict", data=json.dumps({"inputs": [{"id": "a", "text": "ok"}]}), headers=H)
        self.assertEqual(len(self.audit_lines()), 2)

    def test_response_checksum_matches_body(self):
        r = self.post([{"id": "a", "text": "ok"}])
        self.assertEqual(self.audit_lines()[-1]["response_checksum_sha256"], hashlib.sha256(r.data).hexdigest())

    def test_secrets_in_request_id_redacted_in_audit(self):
        self.post([{"id": "a", "text": "ok"}], request_id="x bob@corp.com sk-abcdefghijklmnopqrstuv")
        rec = self.audit_lines()[-1]
        self.assertNotIn("bob@corp.com", rec["request_id"])
        self.assertNotIn("sk-abcdef", rec["request_id"])

    def test_audit_write_failure_counted(self):
        blocker = os.path.join(self.tmp, "file")
        with open(blocker, "w") as f:
            f.write("x")
        with redirect_stdout(io.StringIO()):
            app = create_app(self.art, os.path.join(blocker, "audit.jsonl"))
        c = app.test_client()
        r = c.post("/predict", data=json.dumps({"inputs": [{"id": "a", "text": "ok"}]}), headers=H)
        self.assertEqual(r.status_code, 200)
        self.assertIn("audit_write_errors_total 1", c.get("/metrics").get_data(as_text=True))

    def test_logs_redacted(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            pass
        import logging
        stream = io.StringIO()
        h = logging.StreamHandler(stream)
        lg = logging.getLogger("risk_service")
        lg.addHandler(h)
        try:
            self.post([{"id": "a", "text": "ok"}], request_id="leak carol@x.org")
        finally:
            lg.removeHandler(h)
        out = stream.getvalue()
        self.assertIn("http_request", out)
        self.assertNotIn("carol@x.org", out)
        self.assertNotIn("jane.doe", out.lower())


class TestMetrics(Base):
    def test_metrics(self):
        self.post([{"id": "a", "text": "ok"}])
        self.post([])
        self.post([{"id": "a", "text": "phish"}])
        t = self.c.get("/metrics").get_data(as_text=True)
        self.assertIn('http_requests_total{route="/predict",method="POST",status="200"} 1', t)
        self.assertIn('http_requests_total{route="/predict",method="POST",status="422"} 1', t)
        self.assertIn("predict_requests_total 3", t)
        self.assertIn("predict_errors_total 1", t)
        self.assertIn("audit_write_errors_total 0", t)
        self.assertIn("http_request_latency_ms_p95", t)


class TestRedact(unittest.TestCase):
    def test_redact(self):
        s = redact("mail a.b+c@d.io key=abc123 sk-ABCDEFGHIJKLMNOPQRSTU Bearer abcdefghijklmnop1234 "
                   "AKIAABCDEFGHIJKLMNOP ghp_abcdefghijklmnopqrstuvwx 0123456789abcdef0123456789abcdef")
        for bad in ("a.b+c@d.io", "abc123", "sk-ABC", "abcdefghijklmnop1234", "AKIAABC", "ghp_abc", "0123456789abcdef0123456789abcdef"):
            self.assertNotIn(bad, s)
        self.assertEqual(redact("order 42 for 3f2504e0-4f89-11d3-9a0c-0305e82c3301"), "order 42 for 3f2504e0-4f89-11d3-9a0c-0305e82c3301")


if __name__ == "__main__":
    unittest.main()
