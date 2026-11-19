"""Chuẩn hóa chữ hiển thị giống nhau trước khi áp dụng quy tắc bảo vệ."""
from __future__ import annotations
import unicodedata


def normalize_text(text: str) -> str:
    """Đưa chữ fullwidth về chuẩn và loại ký tự định dạng vô hình."""
    return "".join(c for c in unicodedata.normalize("NFKC", text)
                   if unicodedata.category(c) != "Cf")


def fold_text(text: str) -> str:
    """Dạng không dấu dùng so khớp chủ đề tiếng Việt, giữ nguyên từ."""
    text = unicodedata.normalize("NFKD", normalize_text(text).casefold())
    return "".join(c for c in text if not unicodedata.combining(c)).replace("đ", "d")
