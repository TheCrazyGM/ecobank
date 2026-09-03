# EcoBank — "Dangerous site" review & remediation plan

**Author:** Claude (support/PM) · **For:** Alex (lead, EcoBank) · **Date:** 2026-09-03
**Status:** draft for review — not yet actioned

---

## 1. TL;DR

The site is being served a **social-engineering / phishing** warning ("Attackers on
the site... might trick you into revealing things like your password... or credit card
number"). That is Google Safe Browsing's standard `SOCIAL_ENGINEERING` wording, which
Opera consumes.

**It is not primarily a name problem.** The blacklist classifiers do not flag on
trademarks — they flag on *behaviour*. Our site currently exhibits the textbook
behavioural profile of a credential-phishing page:

- forms that ask the user to type a **"Master Password"** and **"Private Keys"**, with
  helper text *"We will derive all keys from this password"*;
- a **PayPal / credit-card** checkout;
- an **operator identity that is nowhere stated on the site** (no company name, no real
  contact, a boilerplate privacy policy, whole-site `robots.txt` block);
- brand + vocabulary ("EcoBank", "wallet", "account", "bank account") that overlaps a
  real, large financial institution.

Any one of these is a yellow flag. All of them on one domain is a near-guaranteed
classification. The name makes it worse and adds a second, separate risk (an abuse
report from the real bank's brand-protection team), but fixing the name alone would
**not** clear the warning.

**Recommended path:** keep the domain, fix the behavioural signals (Phase 1), stand up
real operator legitimacy (Phase 2), then request review (Phase 3). Rebrand only if a
review request is rejected twice with the name cited.

---

## 2. The "is the African bank still a big deal?" question

Yes — bigger than it was.

- **Ecobank Transnational Incorporated (ETI)**, HQ Lomé, Togo.
- **Total assets ~US$34.5 billion** (FY2025, +23% YoY); customer deposits ~$25.3B;
  attributable profit ~$407M.
- Operates in **34 African countries**, ~13,900 staff, **30M+ customers**.
- Publicly listed on the Nigerian, Ghanaian and BRVM (Abidjan) exchanges.

It is one of the largest banking groups in Africa. Brand awareness in the
Americas/Europe is low, but that is irrelevant to two things that matter to us:

1. **Automated classifiers** don't need the public to know the brand — some already
   map "ecobank" + login form + payment as a lookalike/impersonation pattern.
2. **ETI has an active brand-protection function** (banks always do). A site called
   "EcoBank" taking payments and collecting passwords is exactly what they file
   phishing takedowns against. If they ever file one with PhishTank / Google / our
   host, we inherit a much harder problem than an automated flag.

**Mitigating fact in our favour:** we operate **Ecobank Development Colombia SAS**, a
real registered Colombian company. We have a legitimate, documentable basis for the
name. That basis is currently invisible to visitors and to any reviewer. Surfacing it
prominently (company name, NIT/registration, Colombia, explicit "not affiliated with
Ecobank Transnational / any bank") is the single cheapest risk reducer and should
happen regardless of the rebrand decision.

**Active bug:** `app/templates/main/privacy.html:33` tells users to contact
**`info@ecobank.com`** — that is ETI's actual domain, not ours. This must be corrected
immediately; it's both a broken contact path and something that looks like
impersonation to a reviewer.

---

## 3. How the flag reaches us, and who to petition

Opera does **not** maintain its own list. Its "fraud and malware protection" pulls from
third-party blacklists — historically **Google Safe Browsing**, **PhishTank / APWG**,
and **Yandex Safe Browsing**. The warning text we're seeing is Google's.

**Phase 0 task (do before anything else):** on the warning page, click
**"Why was this blocked?"** — Opera names the specific provider. Then confirm across
providers:

| Provider | Check | Delisting path |
|---|---|---|
| Google Safe Browsing | [transparencyreport.google.com/safe-browsing/search](https://transparencyreport.google.com/safe-browsing/search) | Google Search Console → Security Issues → **Request Review** (needs verified property) |
| PhishTank | search the domain at phishtank.org | register, comment on the submission with evidence, request invalidation |
| Yandex | Yandex Webmaster → site diagnostics | request re-check in Webmaster |
| Microsoft SmartScreen | check in Edge | aka.ms report — "I believe this is safe" |

Do **not** file any review request until Phase 1 + 2 are merged and live. A rejected
request makes the next one slower and the reviewer more skeptical.

---

## 4. Root-cause findings (ranked)

### F1 — The import page looks exactly like credential harvesting  *(highest impact)*
`app/templates/account/import.html`, `app/account/routes.py:184`

- Fields labelled **"Master Password"**, **"Posting Key (Private)"**, **"Active Key
  (Private)"**, **"Memo Key (Private)"**.
- Helper text: *"We will derive all keys from this password and verify them against the
  blockchain."*
- This is the page. A classifier crawling it sees: password field + "private key" +
  "we will derive your keys" → social engineering.

The backend is actually careful (verifies against chain, never stores owner keys,
`routes.py:222`+). That nuance is invisible to a crawler and to most users. The stated
principle ("we never ask for anyone's keys") and this page contradict each other.

**Options:**
- **(a)** Drop master-password import entirely. Keep only "paste a specific private key
  you choose to delegate" with heavy in-context explanation of what each key can do and
  that owner key is never accepted. Fewer secret-shaped inputs on the page.
- **(b)** Move key import behind an authenticated, `noindex`, interstitial-gated flow
  ("I understand what I'm pasting") so crawlers never see the raw form and users get
  real informed consent.
- **(c)** Client-side key handling — derive/verify in the browser, send only the
  verification result + the encrypted-at-rest blob. Bigger change; strongest story
  ("the server never receives your master password").
- Recommend **(a) + (b)** now; consider **(c)** later.

### F2 — No operator identity anywhere on the site
`app/templates/main/about.html`, `base.html:175` footer

- Footer: "Sustainable Resource and Business Development Enterprise" — doesn't match the
  brand or the real company.
- About page: vague ("cutting edge technology for sharing and storage"). No company, no
  jurisdiction, no team, no registration number, no real contact, no ToS.
- A payment-taking site with an anonymous operator is a fraud heuristic on its own.

### F3 — Brand + vocabulary collision with a real bank
Everywhere: "EcoBank", "wallet", "bank account", "My Keys", "Wallet Management".

- `import.html:8` already carries a non-affiliation disclaimer — good instinct, but it's
  on one page only, and the framing ("manage your decentralized ecological bank
  account") still leans into "bank account".
- Decide house language: are we a **"bank"** or an **"onboarding / publishing tool for
  Hive communities"**? The latter is far easier to defend.

### F4 — Boilerplate / wrong privacy policy
`app/templates/main/privacy.html`

- Shopify-template text: "shipping address", "make a purchase", "order confirmations",
  "arranging for shipping".
- Contact = `info@ecobank.com` (see §2 — the real bank's domain).
- Needs a real policy that matches what we actually collect (email, username, encrypted
  Hive keys, PayPal order metadata) and names the real data controller.

### F5 — The site behaves evasively
`app/static/robots.txt` = `Disallow: /` · honeypot (`base.html:180`, `main/routes.py:437`)
· "Under Attack" browser-check middleware (now removed in `59409f0`, good).

- A payment site that blocks *all* crawlers while running login + checkout forms reads
  as "hiding something" to reputation systems, and prevents Google from re-crawling to
  clear a flag.
- Public marketing/info pages (`/`, `/about`, `/privacy`, `/terms`, vivero pages) should
  be crawlable. Keep `/account`, `/drafts`, `/admin`, `/api` disallowed + `noindex`.

### F6 — No CSP, unpinned third-party scripts
`base.html`, `buy_credits.html:49`

- Scripts from `cdn.jsdelivr.net` (bootstrap, easymde, dompurify) and `paypal.com` with
  no `Content-Security-Policy` and no SRI hashes.
- Not a primary trigger, but it's part of the "hygiene score" a reviewer eyeballs, and
  a supply-chain risk. Add a CSP (`flask-talisman` or a manual `after_request`), pin
  SRI on the jsdelivr tags.

### F7 — Password fields not marked, weak generated secrets
- `account/create.html:19` — the new-account "Password" is `type="text"` and the
  "Generate Random" button uses `Math.random()` (not crypto-strong) for what becomes a
  Hive master password. Security bug independent of the flag; fix while we're here.
- Login/register/import password fields should be `type="password"` with correct
  `autocomplete` attributes so browsers don't heuristically treat the page as odd.

---

## 5. Remediation plan

### Phase 0 — Diagnosis (½ day, needs thecrazygm for console access)
1. Click "Why was this blocked?" in Opera; record the provider.
2. Check the domain in: Google Safe Browsing transparency report, PhishTank,
   Yandex Webmaster, Edge/SmartScreen.
3. Verify the domain in **Google Search Console** (thecrazygm — DNS TXT or file). Read
   Security Issues + Manual Actions + Coverage.
4. Check host/registrar/PayPal inbox for any abuse notice.
5. Grep server logs for the crawler hits that preceded the flag if we have them.

**Deliverable:** one paragraph — which list(s), what they cite, what evidence they show.

### Phase 1 — Remove the social-engineering signals (small, reviewable PRs)
Branch `safety/vocab-and-phishing-signals`.

| # | Change | Status |
|---|---|---|
| 1 | Fix `info@ecobank.com` → real contact. `CONTACT_EMAIL` / `OPERATING_ENTITY` config vars, env-overridable; default `srbde@protonmail.com` (SRBDE's staffed inbox) | ✅ done |
| 2 | Rework `/account/import` → "Connect a digital profile": master-password path removed, single posting-key field + optional active, links to `tools.crypto-dreamr.com/key-recovery`, `noindex`, consent checkbox | ✅ done |
| 3 | Crypto-strong generator on `create.html` (`crypto.getRandomValues`), "saved it" confirm; `type=password` + `autocomplete=off` on connect fields | ✅ done (create.html shows the new master password by design, stays `type=text`) |
| 4 | Vocabulary pass — canonical terms in `docs/vocabulary.md`; "digital profile", "credit", "My Account", "recovery keys" | ✅ done (EN); `login.html` / `register.html` untouched (no jargon there) |
| 5 | Site-wide non-affiliation line + operator identity in footer & meta; About + Privacy rewritten; SRBDE relationship stated + cross-linked (`ecoinstats.net`, `github.com/srbde`) | ✅ done |
| 5b | `X-Robots-Tag: noindex` on every route except the public allowlist (`app/security_headers.py`) | ✅ done — effective once robots.txt is opened |
| 6 | `robots.txt`: allow public pages, disallow app routes; `sitemap.xml` for public pages | ⬜ **needs thecrazygm** (coordinate with proxy) |
| 7 | CSP + SRI; move inline `buy_credits` JS to a static file | ⬜ **needs thecrazygm** (proxy header interaction) |
| 8 | Spanish catalog: `./update_translations.sh`, translate new strings | ⬜ after EN sign-off |

Public (indexable) endpoints, per `app/security_headers.py`: `main.index`,
`main.about`, `main.privacy`, `main.token_price`, `static`. Everything else —
including Hive post/blog/wallet mirrors and `main.user_profile` — is noindexed
for now; move specific routes into the allowlist if we want them in search.

i18n: keep long strings on one line (see `feedback_po_linebreaks`).

### The key-custody model (context for Phases 2+)

EcoBank **deliberately holds users' keys** — including the master password for
profiles it creates — as a custodian during a new account's early life. This is
the product thesis, not an oversight:

- A brand-new Hive account has **no value**. The "you are sovereign from second
  zero, we never touch your keys" approach means new users routinely lose their
  keys and their account *before it is worth anything*.
- Accounts gain value over time through participation and learning. EcoBank holds
  the keys so that when the account *has* accrued value, the incentive pushes the
  user to learn, retrieve their keys, rotate them, and take full custody.
- The failure mode we're correcting for: an over-strict "safety" posture that
  leaves beginners holding a bag they don't know how to carry.

So the remediation is **not** "stop holding keys." It is: *hold them responsibly,
explain the model in plain language, and build the mechanism that hands custody
back at the right moment.* The Safe Browsing flag is about a site that looks like
it's phishing secrets — fixed by identity + de-shaping the forms + the `/security`
page below — not about custody per se.

### Phase 2 — Legitimacy scaffolding

Most of the original Phase 2 landed in Phase 1 (About, Privacy, operator identity,
SRBDE cross-links). Remaining, in order:

| # | Change | Status |
|---|---|---|
| P2-1 | **`/security` page** — custodial model stated plainly; owner key never taken for connected profiles; created profiles hold the master password on purpose (why + how to take custody); what each key does; "EcoBank will never ask you for a key"; how to remove keys. Public/indexable, linked from footer + About. | ✅ done |
| P2-1b | Reframe the money story: most users hold no keys and buy nothing (post through a shared community account); a "credit" is prepaid account creation (service fee for the ~3 HIVE network cost), not buying currency/an investment. `buy_credits.html`, homepage onboarding, nav label. `docs/vocabulary.md` — three-accounts distinction. | ✅ done |
| P2-2 | **`/terms` page**. What the service is/isn't: keys are the user's property; the custody model and how it ends; **not a financial/investment service — no deposits, no yield, no returns**; credit pricing and refund terms. | ⬜ next |
| P2-3 | Link `/security` (done) + `/terms` from footer and `about.html`. | 🟡 security done; terms pending P2-2 |
| P2-4 | **OG image check** — `img/ecobank_header.png` must not read as bank branding. | ⬜ |
| P2-5 | Honeypot review — the hidden `<a>"Constructo"` footer link + `/honey/trap`. Form-field honeypots are fine; the hidden link is cloaking-adjacent. **Deferred to thecrazygm** (it's his anti-abuse tool). | ⬜ thecrazygm |
| P2-6 | Rename the "groups" feature → **"circles"** (user-facing only; code/DB stay `Group`). See `docs/groups-to-circles.md`. | ✅ L1 (copy) + L2 (URLs + `/groups`→`/circles` 301s) done; Spanish pending |

**Custody mitigations to keep the model defensible** (some now, some ongoing):

- Encryption key (`HIVE_ENCRYPTION_KEY`) stays out of the DB / in env — confirm with thecrazygm. Envelope / per-user encryption is a later hardening.
- Viewing recovery keys already re-prompts for the EcoBank password (`verify.html`) — keep.
- **Build the "take custody" nudge** (see Phase 5) — the model is only ethical if users are actively prompted to graduate as their account gains value/age/HP.

### Phase 3 — Request review (gated: Phases 1–2 live in production and crawlable)

0. **Phase 0 first** — still outstanding. Click "Why was this blocked?" in Opera;
   record the provider. Check the domain in the GSB transparency report, PhishTank,
   Yandex Webmaster, SmartScreen.
1. Verify `ecobankdevelopment.com` in **Google Search Console** (thecrazygm). Read
   Security Issues + Manual Actions.
2. Confirm crawlability: robots.txt open, public pages 200, private pages carry
   `noindex`.
3. File: GSB → Security Issues → Request Review (plain description of what changed:
   removed the credential-style import form, stated the operator + custodial model,
   added `/security` + `/terms`, opened crawling). PhishTank → comment with evidence
   it's a registered company operated with SRBDE; request invalidation. Yandex /
   SmartScreen re-check as applicable.
4. Monitor the transparency report every few days. **Do not re-file while pending.**

### Phase 4 — Contingency (only if review is rejected twice, citing the name)

Escalate the rebrand decision. Alex's position: "only if unavoidable — I like this
domain." Cheap-insurance prep already in place: marketing copy is brand-light and
i18n-driven. thecrazygm to scope a domain move (email, DNS, PayPal app config, Hive
app metadata).

### Phase 5 — Don't regress / ongoing

- `docs/vocabulary.md` guards new user-facing strings. `app/security_headers.py`
  makes new routes `noindex` by default.
- **Small test suite**: no template uses "master password" as a bare form label;
  `X-Robots-Tag` fires for a private endpoint and not for a public one; every
  `PUBLIC_ENDPOINTS` name resolves to a real route.
- **"Take custody" nudge** (product work, own track): notifications / prompts that
  encourage a user to retrieve and rotate their keys as their profile accrues
  value — account age, HP, post count, rewards. This is the mechanism that makes
  the custodial model work as intended.
- Quarterly: re-check Safe Browsing status; watch `srbde@protonmail.com` for an
  ETI brand-protection notice (higher-stakes than an automated flag).
- Once CSP ships: watch its `report-uri`.

### Deferred — separate track, thecrazygm sign-off

**Client-side key handling for *connect*** — derive/verify keys in the browser so
the server never receives a private key for an imported profile. (Created profiles
stay custodial by design.) Strongest possible "we never see your secrets" story for
the connect path. Not Phase 1–4.

---

## 6. Open questions for thecrazygm (sysadmin)
- Is `ecobankdevelopment.com` in Google Search Console? Can we verify it now?
- What does "Why was this blocked?" in Opera name as the provider?
- Any abuse email from the host / registrar / PayPal?
- Do we retain access logs from ~the week the flag appeared?
- Is `HIVE_ENCRYPTION_KEY` stored separately from the database (env / secrets manager)?
- Current TLS / HSTS / security-header setup at the proxy (so the app-level CSP doesn't
  conflict)?
- Keep or remove the hidden `/honey/trap` footer link?

## 7. What NOT to do
- Don't file any review request before Phases 1–2 ship and the site is crawlable.
- Don't add more cloaking / anti-bot logic — counterproductive here.
- Don't "fix" the flag by dropping custody — the custodial model is the product;
  the fix is transparency + de-shaping the forms.
- Don't rush a rebrand; it's the expensive lever and probably not required.
- Don't restructure key handling in one big PR — the client-side connect path is a
  separate, later track with thecrazygm's sign-off.

---

## Sources
- [Ecobank Transnational 2025 results (africanfinancials)](https://africanfinancials.com/document/ng-eti-2025-ar-00/)
- [Ecobank Group 2025 Annual Report (MarketScreener)](https://www.marketscreener.com/news/ecobank-transnational-incorporated-2025-ecobank-group-annual-report-pdf-6-87-mb-ce7f5ad9d888f32c)
- [Opera — website incorrectly blocked as dangerous](https://security.opera.com/en/website-is-incorrectly-blocked-as-dangerous/)
- [Opera — making browsing safe from phishing](https://blogs.opera.com/security/2021/01/making-browsing-safe-from-phishing/)
- [Google Chrome Help — manage warnings about unsafe sites](https://support.google.com/chrome/answer/99020)
