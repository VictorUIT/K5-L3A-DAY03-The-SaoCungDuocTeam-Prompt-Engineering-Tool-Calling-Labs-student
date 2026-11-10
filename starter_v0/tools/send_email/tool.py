from __future__ import annotations

import re
from typing import Any


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def send_email(to: str = "", content: str = "", confirmed: bool = False) -> dict[str, Any]:
    """Dry-run: không gửi mail. Kiểm tra người nhận rồi mô phỏng bước gửi."""
    if not isinstance(content, str) or not content.strip():
        return {"tool": "email", "status": "invalid_input", "message": "content is empty"}
    if not isinstance(to, str) or not to.strip():
        return {"tool": "email", "status": "missing_recipient", "message": "to is required"}
    if not EMAIL_RE.match(to.strip()):
        return {"tool": "email", "status": "invalid_recipient", "message": f"not an email: {to}"}
    if not confirmed:
        return {
            "tool": "email",
            "status": "needs_confirmation",
            "to": to.strip(),
            "preview": content,
            "message": "Confirm recipient and content with the user before sending.",
        }
    return {
        "tool": "email",
        "status": "dry_run",
        "to": to.strip(),
        "preview": content,
        "message": "Lab mode: nothing was sent.",
    }