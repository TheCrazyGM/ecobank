# Rename: "groups" → "circles" (user-facing)

**Decision (2026-09):** the feature currently called **Group** becomes **Circle**
in everything a user sees. Internal code, model classes, and the database keep
`group` / `Group`. Scope is **Layer 1 + Layer 2** below; Layer 3 is explicitly
out.

## Why "circle" and not "community"

Hive has a *native* Communities feature (`hive-125xxx`), and EcoBank already
surfaces it (`/<community>/@user/<permlink>`, `post.get("community")`). Calling
EcoBank's shared-account groups "communities" would put two different
"communities" in one product. "Circle" is unambiguous, warm, and carries no
crypto baggage. Bonus: in Spanish, *grupo* (m) → *círculo* (m) — same gender, so
the `es` catalog update is nearly mechanical (*el grupo* → *el círculo*,
*añadido al grupo* → *añadido al círculo*).

A **circle** = a set of people who share one Hive account (a "digital profile")
to publish together. See `docs/vocabulary.md`.

---

## Layer 1 — user-facing copy (low risk)

Every `_()` string containing "group". No code/route/URL/DB change.

### Templates

| File | Strings |
|---|---|
| `templates/base.html` | nav "My Groups" → "My Circles" |
| `templates/index.html` | "My Groups" quick link; "request access to their group" (sponsor alert); the L1 pass also unifies "Find a community" (added earlier) → "Find a circle" |
| `templates/groups/list.html` | "My Groups", "Create Group", "You are not a member of any groups." |
| `templates/groups/create.html` | "Create New Group", "Group Name", "Create Group" |
| `templates/groups/view.html` | breadcrumb "Groups"; "Group Settings"; "Group Name"; "Share one of your Hive keys with this group…" |
| `templates/drafts/create.html` | "For Group:", "Select Group", "Choose a group…", "Select a group first" |
| `templates/drafts/edit.html` | "Group:" |
| `templates/drafts/view.html` | "Member of %(group)s" |
| `templates/main/user_profile.html` | card header "Groups" |
| `templates/admin/dashboard.html` | "Groups", "Active groups", "Users Without a Group", "All users belong to at least one group." |
| `templates/admin/groups.html` | "Group Manager" (+ rename file? no — templates keep `groups/` path) |
| `templates/admin/group_edit.html` | "Edit Group: %(name)s" |
| `templates/admin/posts.html` | column "Group" |
| `templates/admin/user_edit.html` | "…drafts, notifications, or group memberships." |

### Python flash / notification strings

| File | Strings |
|---|---|
| `groups/routes.py` | "Group name is required", "Group name already exists", `Group "%(name)s" created!`, "Group settings updated.", "You are not a member of this group.", "You are already a member of this group.", "Your request has been sent to the group owner.", "You have been added to group '%(name)s'" |
| `drafts/routes.py` | "You must belong to a group to create a draft.", "Invalid group selected", "Invalid hive account selected for this group" |
| `admin/routes.py` | "Group %(name)s updated successfully." |
| `account/verify.html` | (already fixed to "profile") — n/a |
| `main/about.html` | "…so a group can speak with one voice…" → "…so a circle…" |

### Adjacent — "sponsor"

`index.html` / `main.find_sponsor` uses "Find Sponsor" / "request access to their
group". Fold into this pass: "sponsor" → the person who runs the circle (e.g.
"Find the circle" / "request to join"). Keep the `find_sponsor` route name.

### i18n

~35 English strings, ~38 in `translations/es`. After L1: `./update_translations.sh`,
translate (*grupo*→*círculo*, keep masculine articles). One line per string
(`memory/feedback_po_linebreaks`).

---

## Layer 2 — URLs (medium risk)

### Chosen approach: change the URL prefix, keep the blueprint identifier

The blueprint stays named `groups` (consistent with keeping `Group` the model).
Only the public URL changes.

1. `app/__init__.py`: `register_blueprint(groups_bp, url_prefix="/circles")`
   — add a comment: *"blueprint id stays `groups`; user-facing name is `circle`."*
2. **Redirect shim** for old links (bookmarks, already-sent notification emails —
   `groups/routes.py:189,374` pass `url_for("groups.view")` into notifications).
   New `app/redirects.py` (same shape as `security_headers.py`):
   ```python
   def init_app(app):
       @app.route("/groups/", defaults={"path": ""})
       @app.route("/groups/<path:path>")
       def _groups_legacy(path):
           from flask import redirect, request
           qs = f"?{request.query_string.decode()}" if request.query_string else ""
           return redirect(f"/circles/{path}{qs}", code=301)
   ```
3. `~45` `url_for("groups.*")` call sites: **no change** — the blueprint id is
   unchanged, so they keep working and now emit `/circles/...`.
4. API route `/api/group/<int:group_id>/accounts` (`api/routes.py:186`) and its
   caller (`drafts/create.html:82` `fetch('/api/group/...')`): **leave as-is** —
   internal XHR, not user-facing, and "group" is fine for an internal endpoint.
5. `security_headers.py`: `/circles/*` is under no public endpoint — already
   `noindex` by default. The `/groups/*` redirect is also non-public. Nothing to
   change.

### Alternative (rejected): full blueprint rename `groups` → `circles`
Cleaner name in code, but forces editing all ~45 `url_for` sites and risks a
missed one → `BuildError`. Not worth it while the model stays `Group`.

### Test checklist for L2
- `GET /circles/list` → 200
- `GET /groups/list` → 301 → `/circles/list`
- `GET /groups/5?tab=history` → 301 → `/circles/5?tab=history` (query preserved)
- create a circle, add a member, link a resource, create+publish a draft from it —
  every redirect lands on a `/circles/...` URL
- notification "join request" link resolves

---

## Layer 3 — code + DB (OUT OF SCOPE)

Not doing: `Group`/`GroupMember`/`GroupResource` class renames, table/column
migration (`group_id` → `circle_id`), template vars (`has_groups`, `owned_groups`),
and the `ecobank.group_id` / `group_name` keys in on-chain post `json_metadata`
(`drafts/routes.py:658`). The metadata keys in particular are immutable history on
already-published posts; renaming would permanently split old vs new. If we ever
revisit, add `circle_*` keys alongside and keep both.

---

## Rollout

1. **L1 copy** (English) — ✅ done. Commit `refactor(vocab): rename 'groups' -> 'circles' in user-facing copy`.
2. **L2 URLs** — ✅ done. `url_prefix` `/groups` → `/circles`; `admin` routes `/admin/groups*` → `/admin/circles*` (endpoint names unchanged); new `app/redirects.py` 301s both old prefixes (query string preserved). Verified: `/groups/5?tab=history` → `/circles/5?tab=history`, `/admin/groups/edit/5` → `/admin/circles/edit/5`.
3. **Spanish** — ⬜ `update_translations.sh`, translate the delta (*grupo* → *círculo*, masculine articles unchanged).

`docs/vocabulary.md` row updated to `circle`.

### Not touched (as planned)
Blueprint id `groups`; `Group`/`GroupMember`/`GroupResource`; `group_id` columns and
FKs; `/api/group/<id>/accounts` (internal XHR); `ecobank.group_id` / `group_name`
in on-chain post metadata; template vars `has_groups` / `owned_groups`.
