"""Redaction, identity hashing and policy guardrails."""
import hashlib
import re

REDACTED = "[REDACTED]"

_PATTERNS = [
    re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"),  # email
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=\-]{16,}"),
    re.compile(r"(?i)\b[\w-]*(?:key|token|secret|password|passwd|authorization)\b\s*[:=]\s*\S+"),
    re.compile(r"\b(?:sk|pk|rk)[-_][A-Za-z0-9_\-]{16,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}"),
    re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}"),  # JWT
    # long mixed letter+digit run (generic API key / hex / base64 blob); hyphens excluded so UUIDs survive
    re.compile(r"(?=[A-Za-z0-9_+/=]*\d)(?=[A-Za-z0-9_+/=]*[A-Za-z])[A-Za-z0-9_+/=]{32,}"),
]

# Fields that are known-safe digests; never run through redaction.
SAFE_KEYS = {"user_hash", "artifact_checksum_sha256", "response_checksum_sha256"}


def redact(text: str) -> str:
    for p in _PATTERNS:
        text = p.sub(REDACTED, text)
    return text


def redact_obj(value):
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, dict):
        return {k: (v if k in SAFE_KEYS else redact_obj(v)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact_obj(v) for v in value]
    return value


def hash_email(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()


DISALLOWED_PHRASES = (
    "steal credentials",
    "bypass access controls",
    "phish",
    "exfiltrate data",
)


def policy_violation(text: str):
    """Return the matched disallowed phrase (lowercased) or None."""
    low = " ".join(text.lower().split())
    for phrase in DISALLOWED_PHRASES:
        if phrase in low:
            return phrase
    return None
