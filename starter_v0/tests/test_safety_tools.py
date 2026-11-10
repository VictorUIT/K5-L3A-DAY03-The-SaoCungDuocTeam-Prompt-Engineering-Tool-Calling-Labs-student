"""Unit tests for the 3 safety action tools: post, email, share_doc.

All three are dry-run: they must never touch the network, must refuse to act
without explicit confirmation, and must validate their inputs first.
`block_network` (conftest.py) fails any test that makes a real HTTP call.
"""
from __future__ import annotations

from tools import TOOL_FUNCTIONS

post = TOOL_FUNCTIONS["post"]
email = TOOL_FUNCTIONS["email"]
share_doc = TOOL_FUNCTIONS["share_doc"]


# ---------------- post ----------------

def test_post_without_confirmation_asks_for_it_and_returns_preview() -> None:
    result = post(content="Hello X")
    assert result["status"] == "needs_confirmation"
    assert result["preview"] == "Hello X"


def test_post_confirmed_is_dry_run_and_publishes_nothing() -> None:
    result = post(content="Hello X", confirmed=True)
    assert result["status"] == "dry_run"
    assert result["preview"] == "Hello X"


def test_post_empty_content_is_invalid_even_when_confirmed() -> None:
    for content in ["", "   "]:
        assert post(content=content, confirmed=True)["status"] == "invalid_input"


def test_post_rejects_content_over_280_chars_but_accepts_exactly_280() -> None:
    assert post(content="a" * 281, confirmed=True)["status"] == "invalid_input"
    assert post(content="a" * 280, confirmed=True)["status"] == "dry_run"


# ---------------- email ----------------

def test_email_missing_recipient_is_reported_not_guessed() -> None:
    result = email(to="", content="Bản tin AI", confirmed=True)
    assert result["status"] == "missing_recipient"


def test_email_invalid_address_is_rejected() -> None:
    for address in ["team", "team@", "@example.com", "team @example.com"]:
        assert email(to=address, content="Bản tin AI", confirmed=True)["status"] == "invalid_recipient", address


def test_email_without_confirmation_asks_for_it_with_trimmed_recipient() -> None:
    result = email(to="  team@example.com ", content="Bản tin AI")
    assert result["status"] == "needs_confirmation"
    assert result["to"] == "team@example.com"
    assert result["preview"] == "Bản tin AI"


def test_email_confirmed_is_dry_run() -> None:
    result = email(to="team@example.com", content="Bản tin AI", confirmed=True)
    assert result["status"] == "dry_run"


def test_email_empty_content_is_checked_before_recipient() -> None:
    assert email(to="", content="", confirmed=True)["status"] == "invalid_input"


# ---------------- share_doc ----------------

def test_share_doc_missing_recipient_is_reported() -> None:
    result = share_doc(content="Báo cáo tuần", recipient="  ", confirmed=True)
    assert result["status"] == "missing_recipient"


def test_share_doc_without_confirmation_points_to_policy_check() -> None:
    result = share_doc(content="Báo cáo tuần", recipient="partner@example.com")
    assert result["status"] == "needs_confirmation"
    assert "policy" in result["message"].lower()


def test_share_doc_confirmed_is_dry_run_with_trimmed_recipient() -> None:
    result = share_doc(content="Báo cáo tuần", recipient=" partner@example.com ", confirmed=True)
    assert result["status"] == "dry_run"
    assert result["recipient"] == "partner@example.com"


def test_share_doc_empty_content_is_invalid() -> None:
    assert share_doc(content="", recipient="partner@example.com", confirmed=True)["status"] == "invalid_input"


# ---------------- shared contract ----------------

def test_safety_tools_report_their_registry_name() -> None:
    assert post(content="x")["tool"] == "post"
    assert email(to="a@b.co", content="x")["tool"] == "email"
    assert share_doc(content="x", recipient="a")["tool"] == "share_doc"
