# Image Upload on Profile Page — Plan of Action

## Goal

Add an "Upload Image" button to the Edit Profile page that uploads a file to the Hive
image service and populates the Avatar URL field automatically — mirroring the working
upload button in the Drafts create/edit pages.

---

## How the Existing Upload Works (Drafts)

- **API endpoint:** `POST /api/upload_image`
- Requires `group_id` in the form data — it signs the upload using a **group's linked
  Hive account** (not the user's personal account).
- Decrypts the posting key from `HiveAccount.keys_enc` using Fernet.
- Resizes image to max 2048px, converts to JPEG, uploads via `nectar.ImageUploader`.
- Returns `{ "url": "https://..." }`.
- Front-end (in draft templates) posts via `fetch()`, gets the URL back, and inserts it
  into the markdown editor.

## Why We Can't Reuse It Directly

The profile page has no group context. Sending a `group_id` would be arbitrary and
wrong. We need a dedicated endpoint for profile image uploads.

---

## Approach: Sponsor / Burner Account

Rather than signing uploads with the user's own Hive account, a single platform-level
**sponsor account** (a dedicated corporate or burner Hive account) signs all profile
picture uploads.

**Benefits over per-user approach:**
- Works for every user, even those with no linked Hive account.
- Simpler code — no per-user key lookup logic.
- Consistent attribution of uploads on the Hive side.

**Tradeoffs to be aware of:**
- All profile picture uploads are attributed to the sponsor account on Hive.
- Could be rate-limited by the Hive image service if upload volume is very high
  (unlikely for profile pictures).

---

## Key Security: Store in DB via Existing Fernet Pattern (Option 2)

The sponsor account's posting key will be stored as a `HiveAccount` record in the
database, encrypted with the existing `HIVE_ENCRYPTION_KEY` — exactly the same pattern
thecrazygm already designed for group Hive accounts. No new security mechanisms needed.

At upload time, the endpoint looks up the sponsor account by a configured username
(`HIVE_UPLOAD_ACCOUNT` env var — **username only, not the key**), then decrypts via
Fernet as normal.

**Why this over env vars (Option 1):** Storing the posting key directly in `.env` was
considered but rejected in favour of consistency — every other Hive key in the project
lives encrypted in the DB. Keeping the sponsor account the same way means no new
patterns for thecrazygm to review or maintain. Note: Hive posting keys are inherently
low-risk (can only sign posts/uploads, cannot move funds), but we still prefer the
established approach.

---

## Proposed Changes

### 1. Config / Environment — `config.py` + `sample.env`

Add one new config variable (username only):

```
HIVE_UPLOAD_ACCOUNT=ecobank.profiles
```

The sponsor account is **`ecobank.profiles`** — a dedicated Hive account created for
this purpose. Its keys are stored encrypted in the `HiveAccount` table like any other
account. No key in env.

### 2. New API Endpoint — `app/api/routes.py`

Add `POST /api/upload_image_profile`.

- Reads `HIVE_UPLOAD_ACCOUNT` from `current_app.config` to identify the sponsor record.
- Queries `HiveAccount` by username, decrypts posting key via Fernet — same pattern as
  existing `upload_image` endpoint.
- No `group_id`, no per-user account logic.
- Same image processing: resize to max 2048px, convert to JPEG at quality 85, upload
  via `nectar.ImageUploader`.
- Returns `{ "url": "..." }` on success.

**Risk level:** Tier 3 — follows the exact Fernet decrypt + upload pattern already in
the codebase. No new security patterns introduced.

### 3. Profile Template — `app/templates/main/profile.html`

Modify the Avatar URL field section (currently lines ~51–55).

**HTML changes:**
- Wrap the `<input>` in a Bootstrap input-group.
- Add a hidden `<input type="file" accept="image/*">`.
- Add an "Upload" button next to the URL input that triggers the file input.
- Show a small spinner on the button while uploading.

**JS changes (inline `<script>` block at bottom of template):**
- On file input `change`: build `FormData` with the selected file, POST to
  `/api/upload_image_profile`.
- On success: populate `#avatar_url` input with the returned URL and update the
  preview `<img>` tag live.
- On error: show an inline error message below the field.

---

## What We Are NOT Changing

- The existing `/api/upload_image` endpoint — no modifications.
- The drafts templates — no modifications.
- The profile view function (`main/routes.py`) — no backend changes needed.
- The `HiveAccount` model — no changes.
- The `User` model — no changes.

---

## Edge Cases to Handle

| Situation | Behaviour |
|---|---|
| `HIVE_UPLOAD_ACCOUNT` not configured | Endpoint returns `503 Service Unavailable` |
| Sponsor account not found in DB | Endpoint returns `503 Service Unavailable` |
| Upload succeeds | Avatar URL field and preview image update immediately |
| Upload fails (network / Hive error) | Inline error message shown below the field |
| User cancels file picker | Nothing happens |

---

## Files to Change

| File | Change |
|---|---|
| `config.py` | Add `HIVE_UPLOAD_ACCOUNT` config var |
| `sample.env` | Add the new var (blank value, with comment) |
| `app/api/routes.py` | Add new `upload_image_profile` endpoint (~40 lines) |
| `app/templates/main/profile.html` | Add upload button HTML + inline JS (~35 lines) |

---

## Prerequisites

- [x] Sponsor account decided: **`ecobank.profiles`** (created 2026-03-15).
- [ ] Import `ecobank.profiles` into the system via the normal account import flow so
      its encrypted keys are in the `HiveAccount` table.

---

## Review Checklist (for thecrazygm)

- [ ] Sponsor account stored and decrypted using existing Fernet pattern — no new
      security mechanisms
- [ ] Only the username (`HIVE_UPLOAD_ACCOUNT`) is in config — the key stays in DB
- [ ] Endpoint is `@login_required` — unauthenticated users cannot trigger uploads
- [ ] No changes to existing endpoints, models, or data
- [ ] Template change is purely additive — existing form fields/submit unchanged
- [ ] Config var documented in `sample.env`
