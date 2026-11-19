"""Quyết định dữ liệu được gửi đi; không thực hiện HTTP tới domain giả của lab."""
from __future__ import annotations
import re
from urllib.parse import urlparse
from guardrails.output_guardrails import content_filter

ALLOWED_EGRESS_HOSTS = frozenset({"api.vinbank.example", "cases.vinbank.example", "vinbank.example"})


def is_egress_allowed(destination: str, payload: str) -> bool:
    """Chỉ chấp nhận HTTPS, đúng host/port, không userinfo và không PII/secret."""
    if not isinstance(destination, str) or not isinstance(payload, str):
        return False
    if re.search(r"[\s\\\x00-\x1f]", destination):
        return False
    try:
        url = urlparse(destination)
        valid = (url.scheme == "https" and url.hostname in ALLOWED_EGRESS_HOSTS
                 and url.port in {None, 443} and url.username is None and url.password is None)
    except ValueError:
        return False
    if not valid or not content_filter(payload)["safe"]:
        return False
    return not re.search(r"\b(?:admin_password|api_key|db_host)\b", payload, re.IGNORECASE)
