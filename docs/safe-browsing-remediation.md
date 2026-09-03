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
| 1 | Fix `info@ecobank.com` → real contact (`CONTACT_EMAIL` config, env-overridable) | ✅ done — **default is a guess, set the env var** |
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

### Phase 2 — Legitimacy scaffolding
| # | Change |
|---|---|
| 8 | Rewrite **About**: what EcoBank is, that it's operated by **Ecobank Development Colombia SAS** (Colombia, registration/NIT), who we are, contact email on our own domain, link to Hive docs. Explicit "not affiliated with Ecobank Transnational Incorporated or any licensed bank; 'EcoBank' here = ecological restoration + Hive, not deposit-taking." |
| 9 | Real **Privacy Policy** matching actual data flows; name the data controller. |
| 10 | Add **Terms of Service** (`/terms`) — what the service does, that keys are user property, custody model, no financial/investment service, dispute/refund terms for credits. |
| 11 | Add a **Security page** (`/security`): key custody (Fernet at rest, owner keys never stored), what each Hive key can do, "we will never DM/email you for your keys", how to remove keys (already built — `account/view`). |
| 12 | Real **contact** route + monitored inbox. |

### Phase 3 — Request review
Only after Phase 1+2 are live and crawlable:
1. Google Search Console → Security Issues → Request Review; describe the changes
   plainly (removed the credential-style import form, added operator identity + policies,
   opened crawling). Turnaround: days to ~2 weeks.
2. PhishTank: comment on the submission with evidence it's our own registered company;
   request invalidation.
3. Yandex / SmartScreen re-check as applicable.
4. Track: re-check the transparency report every few days; don't re-file while pending.

### Phase 4 — If review is rejected twice with the name cited
Escalate the rebrand decision. Prep work to make that cheap: keep the public marketing
copy brand-light in Phase 1, keep templates i18n-driven, and have thecrazygm confirm
what a domain move would cost (email, DNS, PayPal app config, Hive app metadata).

---

## 6. Open questions for thecrazygm (sysadmin)
- Is the domain in Google Search Console? Can we verify it today?
- Any abuse email from the host / registrar / PayPal?
- Do we retain access logs from ~the week the flag appeared?
- Where does mail for our real domain land — is there a monitored inbox for
  `security@` / `abuse@` / `info@`?
- Current TLS / HSTS / security-header setup at the proxy (so the app-level CSP doesn't
  conflict)?

## 7. What NOT to do
- Don't file any review request before Phase 1+2 ship.
- Don't add more cloaking/anti-bot logic — it's counterproductive here.
- Don't rush a rebrand; it's the expensive lever and probably not required.
- Don't make sweeping architectural changes to key handling in one PR — stage F1
  option (c) separately, later, with thecrazygm's sign-off.

---

## Sources
- [Ecobank Transnational 2025 results (africanfinancials)](https://africanfinancials.com/document/ng-eti-2025-ar-00/)
- [Ecobank Group 2025 Annual Report (MarketScreener)](https://www.marketscreener.com/news/ecobank-transnational-incorporated-2025-ecobank-group-annual-report-pdf-6-87-mb-ce7f5ad9d888f32c)
- [Opera — website incorrectly blocked as dangerous](https://security.opera.com/en/website-is-incorrectly-blocked-as-dangerous/)
- [Opera — making browsing safe from phishing](https://blogs.opera.com/security/2021/01/making-browsing-safe-from-phishing/)
- [Google Chrome Help — manage warnings about unsafe sites](https://support.google.com/chrome/answer/99020)
