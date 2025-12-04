from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from nectar.account import Account
from nectar.comment import Comment
from nectar.exceptions import ContentDoesNotExistsException

logger = logging.getLogger(__name__)


def _safe_get(d: dict, *keys, default=None):
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def _normalize_ts(value: Any) -> str:
    """Normalize a timestamp-like value to a safe string.

    - Returns empty string if value is falsy or appears to be epoch (1970).
    - Otherwise returns str(value).
    """
    if not value:
        return ""
    s = str(value)
    if s.startswith("1970") or s == "0" or s.lower() == "none":
        return ""
    return s


def fetch_post(author: str, permlink: str) -> Optional[Dict[str, Any]]:
    """Fetch a single post by author/permlink and shape for templates.

    Returns None if the content cannot be found.
    """
    try:
        c = Comment(f"@{author}/{permlink}")
        # Ensure the object is hydrated; Comment typically lazy-loads from chain.
        try:
            c.refresh()  # may raise if not exists
        except Exception:
            # Some nectar versions auto-fetch; ignore refresh errors if data present
            pass
    except ContentDoesNotExistsException:
        return None
    except Exception:
        return None

    # Pull common fields with fallbacks
    raw_created = getattr(c, "created", None) or _safe_get(c, "created")
    raw_last_update = getattr(c, "last_update", None) or _safe_get(c, "last_update")
    raw_cashout = getattr(c, "cashout_time", None) or _safe_get(c, "cashout_time")
    raw_last_payout = getattr(c, "last_payout", None) or _safe_get(c, "last_payout")

    created_val = raw_created or raw_last_update or raw_cashout or raw_last_payout

    data = {
        "author": getattr(c, "author", author),
        "permlink": getattr(c, "permlink", permlink),
        "title": getattr(c, "title", None) or _safe_get(c, "title") or permlink,
        "body": getattr(c, "body", ""),
        "created": _normalize_ts(created_val),
        "json_metadata": getattr(c, "json_metadata", {})
        or _safe_get(c, "json_metadata", default={}),
        "active_votes": _safe_get(c, "active_votes", default=[]),
        "community": _safe_get(c, "community", default=None)
        or _safe_get(c, "community_title", default=None)
        or _safe_get(c, "category", default=None),
    }

    # Tags from json_metadata
    tags = []
    jm = data.get("json_metadata") or {}
    if isinstance(jm, dict):
        if isinstance(jm.get("tags"), list):
            tags = [str(t) for t in jm.get("tags")]
    data["tags"] = tags

    # Rough payout summary if available
    payout = _safe_get(c, "pending_payout_value") or _safe_get(c, "total_payout_value")
    data["payout"] = str(payout) if payout else None

    # Rebloggers, best-effort
    try:
        reblogged_by = list(getattr(c, "get_reblogged_by")() or [])
    except Exception:
        reblogged_by = []
    data["reblogged_by"] = reblogged_by

    return data


def fetch_user_blog(
    username: str, limit: int = 20, start: Optional[int] = None
) -> Tuple[List[Dict[str, Any]], Optional[int]]:
    """Fetch a user's blog entries.

    Returns (entries, next_cursor). Each entry contains author, permlink, title, created, summary, payout.
    """
    try:
        acc = Account(username)
    except Exception:
        return [], None

    kwargs = {}
    if start is not None:
        kwargs["start"] = start

    try:
        entries = list(acc.get_blog(limit=limit, **kwargs))
    except Exception:
        entries = []

    shaped: List[Dict[str, Any]] = []
    next_cursor: Optional[int] = None

    for e in entries:
        # In some nectar versions, get_blog returns a list of dicts directly
        # Structure might differ, checking safely
        comment = e.get("comment", e) if isinstance(e, dict) else e

        author = _safe_get(comment, "author")
        permlink = _safe_get(comment, "permlink")
        title = _safe_get(comment, "title") or permlink
        created = _safe_get(comment, "created")
        payout = _safe_get(comment, "pending_payout_value")

        # derive summary from body if available
        body = _safe_get(comment, "body") or ""
        summary = None
        if body:
            # Very basic markdown strip could go here, but truncation is a start
            summary = (body[:180] + "...") if len(body) > 180 else body

        shaped.append(
            {
                "author": author,
                "permlink": permlink,
                "title": title,
                "created": _normalize_ts(created),
                "summary": summary,
                "payout": str(payout) if payout else None,
                # If it's a reblog, 'reblogged_on' might be present in the wrapper 'e'
                "reblogged_on": _normalize_ts(e.get("reblogged_on"))
                if isinstance(e, dict) and "reblogged_on" in e
                else None,
            }
        )

        # Pagination cursor: post_id from get_blog wrapper
        post_id = _safe_get(e, "entry_id")  # In recent Nectar/Beem, it's often entry_id
        if post_id is not None:
            next_cursor = post_id

    return shaped, next_cursor


def fetch_account_wallet(username: str) -> Optional[Dict[str, Any]]:
    """Fetch account wallet balances and basic info."""
    try:
        acc = Account(username)
        # Account object has dict-like access to chain properties
        return {
            "username": acc.name,
            "hive_balance": str(acc.get("balance")),
            "hbd_balance": str(acc.get("hbd_balance")),
            "vesting_shares": str(acc.get("vesting_shares")),
            "savings_hive": str(acc.get("savings_balance")),
            "savings_hbd": str(acc.get("savings_hbd_balance")),
            "memo_key": acc.get("memo_key"),
            "created": _normalize_ts(acc.get("created")),
            "post_count": acc.get("post_count"),
            "voting_power": f"{acc.get_voting_power() / 100:.2f}%",
        }
    except Exception as e:
        logger.error(f"Failed to fetch wallet for {username}: {e}")
        return None
