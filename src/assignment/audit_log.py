"""
Assignment 11 — Audit Log starter (TODO).

Records every interaction for forensics. Never blocks by itself —
other layers catch attacks; this layer makes them reviewable.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path


def default_audit_log_path() -> str:
    """Always resolve to <repo>/outputs/… (safe when cwd is src/)."""
    repo_root = Path(__file__).resolve().parents[2]
    return str(repo_root / "outputs" / "audit_log.json")


class AuditLogPlugin:
    """Framework-agnostic audit logger (wire into ADK callbacks or your pipeline)."""

    def __init__(self):
        self.name = "audit_log"
        self.logs: list[dict] = []
        self._open: dict[str, dict] = {}

    def record_input(self, *, user_id: str, text: str, request_id: str | None = None) -> str:
        """Ghi nhận thông tin yêu cầu đầu vào và mốc thời gian bắt đầu xử lý.

        Args:
            user_id: Mã định danh người dùng.
            text: Nội dung câu hỏi người dùng nhập vào.
            request_id: Mã định danh phiên yêu cầu (tuỳ chọn).

        Returns:
            Key lưu trữ dùng để tra cứu khi hoàn thành yêu cầu.
        """
        key = request_id or f"{user_id}_{time.time()}"
        self._open[key] = {
            "start_time": time.time(),
            "user_id": user_id,
            "input_text": text,
            "timestamp": utc_now_iso(),
        }
        return key

    def record_output(
        self,
        *,
        user_id: str,
        text: str,
        blocked: bool = False,
        layer: str | None = None,
        request_id: str | None = None,
    ) -> dict:
        """Ghi nhận kết quả phản hồi, lớp bảo vệ can thiệp và độ trễ xử lý.

        Args:
            user_id: Mã định danh người dùng.
            text: Nội dung phản hồi (hoặc thông báo chặn).
            blocked: Trạng thái yêu cầu có bị chặn hay không.
            layer: Tên tầng bảo vệ đã can thiệp (ví dụ: 'input_guardrail', 'rate_limiter').
            request_id: Mã định danh phiên yêu cầu tương ứng.

        Returns:
            Bản ghi nhật ký đã được thêm vào danh sách logs.
        """
        key = request_id or user_id
        start_info = self._open.pop(key, None)

        latency_ms = 0.0
        input_text = ""
        if start_info:
            latency_ms = (time.time() - start_info["start_time"]) * 1000
            input_text = start_info.get("input_text", "")

        log_entry = {
            "request_id": request_id,
            "user_id": user_id,
            "timestamp": utc_now_iso(),
            "input": input_text,
            "output": text,
            "blocked": blocked,
            "layer": layer,
            "latency_ms": round(latency_ms, 2),
        }
        self.logs.append(log_entry)
        return log_entry

    def export_json(self, filepath: str | None = None) -> Path:
        """Xuất toàn bộ nhật ký kiểm toán ra file định dạng JSON.

        Args:
            filepath: Đường dẫn lưu file tuỳ chọn, mặc định lưu tại <repo>/outputs/audit_log.json.

        Returns:
            Đối tượng Path trỏ tới file JSON đã ghi.
        """
        out_path = Path(filepath or default_audit_log_path())
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(self.logs, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return out_path


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
