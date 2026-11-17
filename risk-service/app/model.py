"""Model registry (manifest -> active artifact) and deterministic scoring."""
import hashlib
import json
import math
import os
import threading
from dataclasses import dataclass
from pathlib import Path


class ModelLoadError(Exception):
    pass


@dataclass(frozen=True)
class LoadedModel:
    provider: str
    model_name: str
    model_version: str
    created_at: str
    artifact_path: str
    checksum: str
    checksum_verified: bool
    rule_config: dict


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_json(path: Path) -> tuple:
    try:
        raw = path.read_bytes()
        return json.loads(raw), raw
    except (OSError, ValueError) as e:
        raise ModelLoadError(f"cannot read {path.name}: {e}") from e


def _validate_rule_config(rc: dict) -> None:
    try:
        for k in ("base_score", "channel_weights", "price_rules", "units_rules", "text_rules", "thresholds"):
            if k not in rc:
                raise ModelLoadError(f"rule_config missing '{k}'")
        float(rc["base_score"])
        t = rc["thresholds"]
        if not (0 <= float(t["low_risk_max"]) <= float(t["medium_risk_max"]) <= 1):
            raise ModelLoadError("invalid thresholds")
    except (KeyError, TypeError, ValueError) as e:
        raise ModelLoadError(f"invalid rule_config: {e}") from e


class ModelRegistry:
    def __init__(self, artifacts_dir: str):
        self.dir = Path(artifacts_dir)
        self._model = None
        self._lock = threading.Lock()

    @property
    def current(self):
        return self._model

    def _load(self) -> LoadedModel:
        manifest, _ = _read_json(self.dir / "model_manifest.json")
        version = manifest.get("active_model_version")
        rel = (manifest.get("paths") or {}).get(version)
        if not version or not rel:
            raise ModelLoadError(f"active version {version!r} not mapped in manifest")
        path = (self.dir / rel).resolve()
        if not path.is_relative_to(self.dir.resolve()):
            raise ModelLoadError("artifact path escapes artifacts directory")
        artifact, raw = _read_json(path)
        checksum = _sha256(raw)

        # Only model files are verified strictly. The manifest is edited on rollback,
        # so its checksum is expected to drift and is not enforced.
        verified = False
        sums_path = self.dir / "CHECKSUMS.json"
        if sums_path.exists():
            sums, _ = _read_json(sums_path)
            expected = sums.get(path.name)
            if expected:
                if expected != checksum:
                    raise ModelLoadError(f"checksum mismatch for {path.name}")
                verified = True

        if artifact.get("model_version") != version:
            raise ModelLoadError("artifact model_version does not match manifest")
        _validate_rule_config(artifact.get("rule_config") or {})
        return LoadedModel(
            provider="mock",
            model_name=artifact.get("model_name", "risk_triad_classifier"),
            model_version=version,
            created_at=artifact.get("created_at", ""),
            artifact_path=os.path.join(str(self.dir), rel),
            checksum=checksum,
            checksum_verified=verified,
            rule_config=artifact["rule_config"],
        )

    def load(self) -> LoadedModel:
        """Load and atomically swap. On failure the previous model stays active."""
        with self._lock:
            model = self._load()
            self._model = model
            return model


def _first_match(rules: list, value, gte_key: str, lt_key: str):
    for r in rules:
        if gte_key in r and value >= r[gte_key]:
            return r
        if lt_key in r and value < r[lt_key]:
            return r
    return None


def score_item(model: LoadedModel, text: str, features: dict) -> tuple:
    """Returns (score, label, reasons). Pure function of (model, input)."""
    rc = model.rule_config
    score = float(rc["base_score"])
    reasons = []

    channel = features.get("channel")
    if channel is not None:
        weights = rc["channel_weights"]
        key = channel.strip().lower()
        key = key if key in weights else "other"
        if key in weights:
            score += weights[key]
            reasons.append(f"channel_{key}")

    price = features.get("price")
    if price is not None:
        r = _first_match(rc["price_rules"], price, "if_price_gte", "if_price_lt")
        if r:
            score += r["add"]
            reasons.append(r["reason"])

    units = features.get("units")
    if units is not None:
        r = _first_match(rc["units_rules"], units, "if_units_gte", "if_units_lt")
        if r:
            score += r["add"]
            reasons.append(r["reason"])

    low = text.lower()
    for r in rc["text_rules"]:
        if any(k in low for k in r["keywords_any"]):
            score += r["add"]
            reasons.append(r["reason"])

    score = round(max(0.0, min(1.0, score)), 6)
    t = rc["thresholds"]
    if score <= t["low_risk_max"]:
        label = "low_risk"
    elif score <= t["medium_risk_max"]:
        label = "medium_risk"
    else:
        label = "high_risk"
    return score, label, reasons


class ValidationError(Exception):
    def __init__(self, details):
        self.details = details


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def validate_payload(payload):
    """Returns (request_id_or_None, inputs). Raises ValidationError."""
    errs = []
    if not isinstance(payload, dict):
        raise ValidationError([{"path": "$", "message": "body must be a JSON object"}])
    rid = payload.get("request_id")
    if rid is not None and not isinstance(rid, str):
        errs.append({"path": "request_id", "message": "must be a string"})
    inputs = payload.get("inputs")
    if not isinstance(inputs, list) or not (1 <= len(inputs) <= 50):
        raise ValidationError(errs + [{"path": "inputs", "message": "must be a list of 1-50 items"}])
    for i, it in enumerate(inputs):
        p = f"inputs[{i}]"
        if not isinstance(it, dict):
            errs.append({"path": p, "message": "must be an object"})
            continue
        if not isinstance(it.get("id"), str) or not it["id"].strip():
            errs.append({"path": f"{p}.id", "message": "must be a non-empty string"})
        t = it.get("text")
        if not isinstance(t, str) or not t.strip():
            errs.append({"path": f"{p}.text", "message": "must be a non-empty string"})
        elif len(t) > 10_000:
            errs.append({"path": f"{p}.text", "message": "must be at most 10000 characters"})
        if "features" in it:
            f = it["features"]
            if not isinstance(f, dict):
                errs.append({"path": f"{p}.features", "message": "must be an object"})
                continue
            if "price" in f and (not _is_num(f["price"]) or f["price"] < 0):
                errs.append({"path": f"{p}.features.price", "message": "must be a non-negative number"})
            if "units" in f and (not isinstance(f["units"], int) or isinstance(f["units"], bool) or f["units"] < 0):
                errs.append({"path": f"{p}.features.units", "message": "must be a non-negative integer"})
            if "channel" in f and not isinstance(f["channel"], str):
                errs.append({"path": f"{p}.features.channel", "message": "must be a string"})
    if errs:
        raise ValidationError(errs)
    return rid, inputs
