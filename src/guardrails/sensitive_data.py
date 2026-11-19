"""Các quy tắc che dữ liệu dùng chung cho output, audit và egress."""
from __future__ import annotations
import base64
import codecs
import re
from core.config import DEMO_SECRETS
from guardrails.normalization import normalize_text

PATTERNS = {
    "phone": r"(?<!\w)(?:\+84|0)[ .-]?(?:[35789](?:[ .-]?\d){8}|2(?:[ .-]?\d){9})(?!\w)",
    "email": r"[\w.+%-]+@[\w.-]+\.[a-zA-Z]{2,}",
    "national_id": r"(?<!\w)(?:\d{12}|\d{9})(?!\w)",
    "api_key": r"\bsk-[a-zA-Z0-9_-]+",
}
PASSWORD = re.compile(
    r"\b(?:password|mật\s*khẩu|mat\s*khau)"
    r"(?:\s*[:=]\s*|\s+(?:is|là|la)\s+|\s+)"
    r"[\"'`]?([^\s,;\"'`<>]+)", re.IGNORECASE,
)
BENIGN_PASSWORD_WORDS = {
    "reset", "policy", "policies", "requirements", "security", "protection",
    "manager", "management", "recovery", "should", "must", "can", "cannot",
    "never", "not", "for", "to", "and", "or", "is", "là", "la", "an", "mạnh",
}


def filter_sensitive(response: str) -> dict:
    """Che PII/secret; kết quả đã che có thể được kiểm tra lại an toàn."""
    text = normalize_text(response or "")
    issues: list[str] = []

    def redact_password(match: re.Match[str]) -> str:
        value = match.group(1).strip(".:")
        if value.casefold() in BENIGN_PASSWORD_WORDS or value == "[REDACTED]":
            return match.group(0)
        issues.append("password: 1 found")
        return "[REDACTED]"

    text = PASSWORD.sub(redact_password, text)
    for name, pattern in PATTERNS.items():
        text, count = re.subn(pattern, "[REDACTED]", text, flags=re.IGNORECASE)
        if count:
            issues.append(f"{name}: {count} found")
    for secret in sorted(DEMO_SECRETS, key=len, reverse=True):
        if not secret:
            continue
        variants = {secret, secret[::-1], codecs.encode(secret, "rot_13"),
                    secret.encode().hex(), base64.b64encode(secret.encode()).decode()}
        letters = re.sub(r"[^a-zA-Z0-9]", "", secret)
        patterns = [re.escape(v) for v in variants]
        if len(letters) >= 8:
            patterns.append(r"[\W_]*".join(map(re.escape, letters)))
        text, count = re.subn("|".join(patterns), "[REDACTED]", text, flags=re.IGNORECASE)
        if count:
            issues.append(f"protected_secret: {count} found")
    return {"safe": not issues, "issues": issues, "redacted": text}
