# Risk Triad Classifier Service

Flask service serving the deterministic rule-based models in `model_artifacts/`.

## Run
    pip install -r requirements.txt
    python -m app.main                      # dev, port 8000
    gunicorn -w 4 -b 0.0.0.0:8000 'app.main:create_app()'   # prod

    # note: audit log is a per-process append; with multiple workers each write is one O_APPEND
    # line, so records don't interleave.

Env: `MODEL_ARTIFACTS_DIR` (default `./model_artifacts`), `AUDIT_LOG_PATH` (default `./audit_logs/audit.jsonl`), `PORT`.

## Test
    python -m unittest discover -s tests -v

## Rollback
Set `active_model_version` in `model_manifest.json`, then `POST /model/reload`.
A failed reload (bad version, checksum mismatch, invalid artifact) keeps the previous model serving.

## Design decisions
- **Scoring**: price/units rules are first-match (`gte` tiers then `lt`); each text rule applies once if any keyword
  matches (case-insensitive substring); unknown channel falls back to `other`; missing features contribute nothing.
  Score is rounded to 6 dp before labeling so threshold comparisons are stable.
- **Integrity**: the model file's sha256 is checked against `CHECKSUMS.json` (mismatch = refuse to load, `/readyz` 503).
  The manifest checksum is not enforced because rollback edits the manifest.
- **Errors**: `{"error": {"code","message","details"}, "request_id"}`. 400 policy block / bad JSON / missing email,
  415 wrong content type, 422 validation, 503 no model, 500 internal.
- **Audit**: exactly one record per `POST /predict` (success, blocked, error). Audit failures never fail the request;
  they increment `audit_write_errors_total`.
- **Determinism**: predictions are identical for the same payload + model version. `latency_ms` and a generated
  `request_id` (when none is sent) naturally vary.
- **Redaction**: emails, bearer/API/cloud/GitHub/Slack tokens, JWTs, `key=value` secrets and long mixed alnum blobs
  are redacted in all logs and audit free-text fields. Request text is never logged.
