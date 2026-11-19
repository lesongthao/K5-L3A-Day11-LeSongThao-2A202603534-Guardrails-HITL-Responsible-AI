"""Kiểm tra model mà không in API key; chỉ kết nối dịch vụ đã cấu hình cho lab."""
from __future__ import annotations
import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from core.config import BLUE_MODEL, blue_client_kwargs, get_blue_model


def safe_detail(error: Exception) -> str:
    detail = str(getattr(error, "body", None) or type(error).__name__)
    for name in ("OPENROUTER_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY"):
        value = os.environ.get(name, "")
        if value:
            detail = detail.replace(value, "[REDACTED]")
    return re.sub(r"sk-[A-Za-z0-9_-]{16,}|AIza[A-Za-z0-9_-]{20,}", "[REDACTED]", detail)[:1500]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list-free", action="store_true")
    parser.add_argument("--blue-model")
    args = parser.parse_args()
    try:
        if args.list_free:
            with urlopen("https://openrouter.ai/api/v1/models", timeout=25) as response:
                data = json.load(response)
            models = [row["id"] for row in data["data"] if row["id"].endswith(":free")]
            print(json.dumps({"free_models": models}, ensure_ascii=False, indent=2))
        else:
            from openai import OpenAI
            model = args.blue_model or get_blue_model()
            client = OpenAI(**blue_client_kwargs(), timeout=25, max_retries=0)
            response = client.chat.completions.create(
                model=model, messages=[{"role": "user", "content": "Reply with OK only."}])
            if not response.choices[0].message.content:
                raise ValueError("Model returned an empty answer")
            print(json.dumps({"ok": bool(response.choices[0].message.content), "requested_model": model,
                              "response_model": response.model, "lab_required_model": BLUE_MODEL}))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "type": type(exc).__name__,
                          "http_status": getattr(exc, "status_code", None), "detail": safe_detail(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
