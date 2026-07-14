"""Thread analysis primitives.

Kept dependency-free so the module can be imported anywhere in the
test harness without provisioning extra packages.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ThreadStats:
    """Summary metrics for a single thread (one post + its replies)."""

    root_id: str
    reply_count: int
    participant_count: int
    longest_reply_chars: int


def analyze(root_id: str, replies: list[dict]) -> ThreadStats:
    """Compute :class:`ThreadStats` from a root id and a list of reply dicts.

    Each reply dict must carry ``author`` (str) and ``body`` (str). Missing
    keys raise :class:`ValueError` so the caller learns about malformed
    input instead of silently producing wrong numbers.
    """
    if not replies:
        return ThreadStats(
            root_id=root_id,
            reply_count=0,
            participant_count=0,
            longest_reply_chars=0,
        )

    for r in replies:
        if "author" not in r or "body" not in r:
            raise ValueError(f"reply missing required keys: {sorted(r)}")

    participants = {r["author"] for r in replies}
    longest = max(len(r["body"]) for r in replies)
    return ThreadStats(
        root_id=root_id,
        reply_count=len(replies),
        participant_count=len(participants),
        longest_reply_chars=longest,
    )
