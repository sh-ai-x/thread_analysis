"""Tests for thread_analysis.analyzer."""

from __future__ import annotations

import pytest

from thread_analysis.analyzer import ThreadStats, analyze


def test_empty_replies_returns_zero_stats() -> None:
    stats = analyze("root-1", [])
    assert stats == ThreadStats(
        root_id="root-1",
        reply_count=0,
        participant_count=0,
        longest_reply_chars=0,
    )


def test_counts_replies_and_unique_participants() -> None:
    replies = [
        {"author": "alice", "body": "hi"},
        {"author": "bob", "body": "hey"},
        {"author": "alice", "body": "follow-up"},
    ]
    stats = analyze("root-2", replies)
    assert stats.reply_count == 3
    assert stats.participant_count == 2
    assert stats.longest_reply_chars == len("follow-up")


def test_missing_keys_raises_value_error() -> None:
    with pytest.raises(ValueError, match="missing required keys"):
        analyze("root-3", [{"author": "alice"}])


def test_none_author_raises_value_error() -> None:
    """Regression: key-presence check alone lets None slip through and crash later."""
    with pytest.raises(ValueError, match="must be str"):
        analyze("root-4", [{"author": None, "body": "hi"}])


def test_none_body_raises_value_error() -> None:
    """Regression: None body previously slipped past key-presence and raised TypeError."""
    with pytest.raises(ValueError, match="must be str"):
        analyze("root-5", [{"author": "alice", "body": None}])
