from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from nectar import Hive
from nectar.account import Account
from nectar.amount import Amount
from nectar.comment import Comment
from nectar.discussions import Discussions, Query
from nectar.exceptions import ContentDoesNotExistsException

from app.utils.markdown_render import render_markdown_preview

logger = logging.getLogger(__name__)


def _extract_val(obj: Any, key: str, default=None) -> Any:
    """Safely extract value from dict or object."""
    if obj is None:
        return default
    # Try dict access
    try:
        return obj[key]
    except (TypeError, KeyError, IndexError):
        pass
    # Try attribute access
    try:
        return getattr(obj, key, default)
    except AttributeError:
        return default


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


def fetch_user_profile(username: str) -> Optional[Dict[str, Any]]:
    """Fetch detailed user profile metadata and stats."""
    try:
        acc = Account(username)

        # Parse metadata
        # It can be in 'posting_json_metadata' or 'json_metadata'
        meta_str = acc.get("posting_json_metadata") or acc.get("json_metadata") or "{}"
        meta = {}
        try:
            meta = json.loads(meta_str)
        except json.JSONDecodeError:
            pass

        profile = meta.get("profile", {})

        return {
            "username": acc.name,
            "display_name": profile.get("name", acc.name),
            "about": profile.get("about", ""),
            "location": profile.get("location", ""),
            "website": profile.get("website", ""),
            "profile_image": profile.get("profile_image", ""),
            "cover_image": profile.get("cover_image", ""),
            "post_count": acc.get("post_count", 0),
            "reputation": _rep_log10(acc.get("reputation", 0)),
            "created": _normalize_ts(acc.get("created")),
        }
    except Exception as e:
        logger.error(f"Failed to fetch profile for {username}: {e}")
        return None


def _rep_log10(rep_raw):
    """Convert raw reputation score to human readable log10 score (e.g. 25-70+)."""
    try:
        import math

        rep = int(rep_raw)
        if rep == 0:
            return 25
        score = max(math.log10(abs(rep)) - 9, 0) * 9 + 25
        if rep < 0:
            score = 50 - score
        return int(score)
    except Exception:
        return 25


def fetch_post(author: str, permlink: str) -> Optional[Dict[str, Any]]:
    """Fetch a single post by author/permlink and shape for templates.

    Returns None if the content cannot be found.
    """
    try:
        c = Comment(f"@{author}/{permlink}")
        try:
            c.refresh()  # may raise if not exists
        except Exception:
            pass
    except ContentDoesNotExistsException:
        return None
    except Exception:
        return None

    # Pull common fields with fallbacks
    raw_created = getattr(c, "created", None) or _extract_val(c, "created")
    raw_last_update = getattr(c, "last_update", None) or _extract_val(c, "last_update")
    raw_cashout = getattr(c, "cashout_time", None) or _extract_val(c, "cashout_time")
    raw_last_payout = getattr(c, "last_payout", None) or _extract_val(c, "last_payout")

    created_val = raw_created or raw_last_update or raw_cashout or raw_last_payout

    data = {
        "author": getattr(c, "author", author),
        "permlink": getattr(c, "permlink", permlink),
        "title": getattr(c, "title", None) or _extract_val(c, "title") or permlink,
        "body": getattr(c, "body", ""),
        "created": _normalize_ts(created_val),
        "json_metadata": getattr(c, "json_metadata", {})
        or _extract_val(c, "json_metadata", default={}),
        "active_votes": _extract_val(c, "active_votes", default=[]),
        "community": _extract_val(c, "community", default=None)
        or _extract_val(c, "community_title", default=None)
        or _extract_val(c, "category", default=None),
    }

    # Tags from json_metadata
    tags = []
    jm = data.get("json_metadata") or {}
    if isinstance(jm, dict):
        if isinstance(jm.get("tags"), list):
            tags = [str(t) for t in jm.get("tags")]  # type: ignore
    data["tags"] = tags

    # Rough payout summary if available
    payout = _extract_val(c, "pending_payout_value") or _extract_val(
        c, "total_payout_value"
    )
    data["payout"] = str(payout) if payout else None

    # Rebloggers, best-effort
    try:
        reblogged_by = list(getattr(c, "get_reblogged_by")() or [])
    except Exception:
        reblogged_by = []
    data["reblogged_by"] = reblogged_by

    return data


def fetch_user_blog(
    username: str,
    limit: int = 20,
    start_author: Optional[str] = None,
    start_permlink: Optional[str] = None,
    mode: str = "all",
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, str]]]:
    """Fetch a user's blog entries using Bridge API via Nectar.

    mode: 'all' (default), 'posts' (only original), 'reblogs' (only reblogs)

    Returns (entries, next_cursor_dict).
    """
    # Cap fetch_limit to Bridge API's maximum of 20
    fetch_limit = min(limit, 20)

    # We might need to fetch more if we are filtering, but Bridge API limit is 20.
    # If mode is not 'all', we might fetch 20 and filter down to fewer.
    if mode != "all" and limit < 20:
        fetch_limit = min(limit * 2, 20)
    elif mode == "all":
        fetch_limit = min(limit, 20)
    else:
        fetch_limit = 20

    entries = []
    try:
        # Use specific nodes to ensure connectivity
        hive = Hive(
            node=[
                "https://api.hive.blog",
                "https://api.deathwing.me",
                "https://anyx.io",
            ]
        )
        acc = Account(username.strip(), blockchain_instance=hive)

        # Use get_account_posts (Bridge API)
        # Only pass pagination params if set
        post_kwargs = {"sort": "blog", "limit": fetch_limit, "raw_data": True}

        if start_author:
            post_kwargs["start_author"] = start_author
        if start_permlink:
            post_kwargs["start_permlink"] = start_permlink

        entries = list(acc.get_account_posts(**post_kwargs))

    except Exception as e:
        logger.error(f"fetch_user_blog: Error fetching blog for {username}: {e}")
        entries = []

    shaped: List[Dict[str, Any]] = []
    next_cursor: Optional[Dict[str, str]] = None

    # Normalize target username for comparison
    target_username = username.lower()

    # Bridge API returns posts. If paginating, the first item might be the previous last item.
    if start_author and start_permlink and entries:
        first = entries[0]
        if (
            _extract_val(first, "author") == start_author
            and _extract_val(first, "permlink") == start_permlink
        ):
            entries.pop(0)

    count = 0
    for e in entries:
        # Bridge API returns flat dicts
        author = _extract_val(e, "author")

        # Filtering Logic
        if not author:
            continue

        is_reblog = author.lower() != target_username

        if mode == "posts" and is_reblog:
            continue
        if mode == "reblogs" and not is_reblog:
            continue

        permlink = _extract_val(e, "permlink")
        title = _extract_val(e, "title") or permlink
        created = _extract_val(e, "created")
        payout = _extract_val(e, "pending_payout_value")

        # derive summary from body if available
        body = _extract_val(e, "body") or ""
        summary = None
        if body:
            summary = render_markdown_preview(body, limit=180)

        # Extract thumbnail
        json_meta = _extract_val(e, "json_metadata") or {}
        if isinstance(json_meta, str):
            try:
                json_meta = json.loads(json_meta)
            except Exception:
                json_meta = {}

        thumbnail = None
        if isinstance(json_meta, dict):
            images = json_meta.get("image")
            if isinstance(images, list) and images:
                thumbnail = images[0]

        shaped.append(
            {
                "author": author,
                "permlink": permlink,
                "title": title,
                "created": _normalize_ts(created),
                "summary": summary,
                "thumbnail": thumbnail,
                "payout": str(payout) if payout else None,
                "reblogged_on": "yes" if is_reblog else None,
            }
        )
        count += 1
        if count >= limit:
            break

    # Determine cursor for NEXT page
    if entries:
        last_entry = entries[-1]
        next_cursor = {
            "author": _extract_val(last_entry, "author"),
            "permlink": _extract_val(last_entry, "permlink"),
        }

    return shaped, next_cursor


def fetch_account_wallet(username: str) -> Optional[Dict[str, Any]]:
    """Fetch account wallet balances and basic info."""
    try:
        acc = Account(username)
        hive = Hive()

        # Calculate Hive Power (HP) from VESTS
        vests = Amount(acc.get("vesting_shares"))  # type: ignore
        dgpo = hive.get_dynamic_global_properties()
        total_vesting_fund = Amount(dgpo["total_vesting_fund_hive"])  # type: ignore
        total_vesting_shares = Amount(dgpo["total_vesting_shares"])  # type: ignore

        hive_power = 0.0
        if total_vesting_shares.amount > 0:
            hive_power = vests.amount * (
                total_vesting_fund.amount / total_vesting_shares.amount
            )

        # Account object has dict-like access to chain properties
        return {
            "username": acc.name,
            "hive_balance": str(acc.get("balance")),
            "hbd_balance": str(acc.get("hbd_balance")),
            "vesting_shares": str(acc.get("vesting_shares")),
            "hive_power": f"{hive_power:.3f} HP",
            "savings_hive": str(acc.get("savings_balance")),
            "savings_hbd": str(acc.get("savings_hbd_balance")),
            "memo_key": acc.get("memo_key"),
            "created": _normalize_ts(acc.get("created")),
            "post_count": acc.get("post_count"),
            # get_voting_power() appears to return percentage (0-100) in this version
            "voting_power": f"{acc.get_voting_power():.2f}%",
        }
    except Exception as e:
        logger.error(f"Failed to fetch wallet for {username}: {e}")
        return None


def fetch_posts_by_tag(
    tag: str,
    limit: int = 20,
    start_author: Optional[str] = None,
    start_permlink: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, str]]]:
    """Fetch posts by tag (discussion)."""
    try:
        d = Discussions()
        # Use 'created' to get latest posts in that tag
        query = Query(limit=limit, tag=tag)
        if start_author and start_permlink:
            query["start_author"] = start_author
            query["start_permlink"] = start_permlink

        posts = list(d.get_discussions("created", query, limit=limit))
    except Exception as e:
        logger.error(f"Failed to fetch posts by tag {tag}: {e}")
        return [], None

    shaped = []
    next_cursor = None

    if posts:
        # Prepare cursor from last item
        last_post = posts[-1]
        # Only if we got a full page, there might be more
        if len(posts) == limit:
            next_cursor = {
                "author": _extract_val(last_post, "author"),
                "permlink": _extract_val(last_post, "permlink"),
            }

    for p in posts:
        # Filter out the exact start post if it appears (pagination overlap)
        if start_author and start_permlink:
            if (
                _extract_val(p, "author") == start_author
                and _extract_val(p, "permlink") == start_permlink
            ):
                continue

        author = _extract_val(p, "author")
        permlink = _extract_val(p, "permlink")
        title = _extract_val(p, "title") or permlink
        created = _extract_val(p, "created")
        payout = _extract_val(p, "pending_payout_value")
        body = _extract_val(p, "body") or ""
        summary = render_markdown_preview(body, limit=180)

        # Extract thumbnail
        json_meta = _extract_val(p, "json_metadata") or {}
        if isinstance(json_meta, str):
            try:
                json_meta = json.loads(json_meta)
            except Exception:
                json_meta = {}

        thumbnail = None
        if isinstance(json_meta, dict):
            images = json_meta.get("image")
            if isinstance(images, list) and images:
                thumbnail = images[0]

        shaped.append(
            {
                "author": author,
                "permlink": permlink,
                "title": title,
                "created": _normalize_ts(created),
                "summary": summary,
                "thumbnail": thumbnail,
                "payout": str(payout) if payout else None,
            }
        )

    return shaped, next_cursor


def fetch_pending_claimed_accounts(username: str) -> int:
    """Fetch the pending claimed accounts count for a user."""
    try:
        acc = Account(username)
        return int(acc.get("pending_claimed_accounts", 0))
    except Exception as e:
        logger.error(f"Failed to fetch pending claimed accounts for {username}: {e}")
        return 0


def fetch_active_delegations(username: str) -> List[Dict[str, Any]]:
    """Fetch active delegations made by the user."""
    try:
        acc = Account(username)
        # get_vesting_delegations returns list of dicts
        delegations = acc.get_vesting_delegations()

        # Need to convert VESTS to HP for display
        hive = Hive()
        dgpo = hive.get_dynamic_global_properties()
        total_vesting_fund = Amount(dgpo["total_vesting_fund_hive"])
        total_vesting_shares = Amount(dgpo["total_vesting_shares"])

        result = []
        for d in delegations:
            vests = Amount(d["vesting_shares"])
            hp = 0.0
            if total_vesting_shares.amount > 0:
                hp = vests.amount * (
                    total_vesting_fund.amount / total_vesting_shares.amount
                )

            result.append(
                {
                    "delegatee": d["delegatee"],
                    "vesting_shares": str(vests),
                    "hive_power": f"{hp:.3f} HP",
                    "min_delegation_time": d["min_delegation_time"],
                }
            )
        return result
    except Exception as e:
        logger.error(f"Failed to fetch delegations for {username}: {e}")
        return []


def hp_to_vests(hp_amount: float) -> float:
    """Converts a given HP amount to VESTS."""
    try:
        hive = Hive()
        dgpo = hive.get_dynamic_global_properties()
        total_vesting_fund = Amount(dgpo["total_vesting_fund_hive"]).amount
        total_vesting_shares = Amount(dgpo["total_vesting_shares"]).amount
        if total_vesting_fund > 0:
            return (hp_amount * total_vesting_shares) / total_vesting_fund
    except Exception as e:
        logger.error(f"Failed to convert HP to VESTS: {e}")
    return 0.0


def delegate_vesting(
    delegator_account: str,
    delegator_key: str,
    delegatee_account: str,
    vests_amount: float,
) -> bool:
    """Delegates vesting shares from delegator_account to delegatee_account."""
    try:
        hive = Hive(keys=[delegator_key])
        hive.delegate_vesting_shares(
            delegator_account, delegatee_account, f"{vests_amount:.6f} VESTS"
        )
        logger.info(
            f"Delegated {vests_amount:.6f} VESTS from {delegator_account} to {delegatee_account}"
        )
        return True
    except Exception as e:
        logger.error(
            f"Failed to delegate {vests_amount:.6f} VESTS from {delegator_account} to {delegatee_account}: {e}"
        )
        return False


def claim_account(claimer_account: str, claimer_key: str) -> bool:
    """Claims an account using the claimer_account RC."""
    try:
        hive = Hive(keys=[claimer_key])
        # claim_account(creator, fee) - fee is '0.000 HIVE' when using RC
        hive.claim_account(claimer_account, "0.000 HIVE")
        logger.info(f"Claimed new account ticket for {claimer_account}")
        return True
    except Exception as e:
        logger.error(f"Failed to claim account ticket for {claimer_account}: {e}")
        return False
