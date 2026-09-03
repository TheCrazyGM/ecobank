# EcoBank vocabulary — canonical terms

Single source of truth for user-facing wording. When you add or change a
user-facing string, make it match this table. Goal: **one word per concept**,
friendly but not vague, and nothing that reads like a phishing page.

Spanish column is filled **after** the English is settled, then
`./update_translations.sh` is run.

---

## Three accounts — never conflate them

Most people who use EcoBank hold **no keys at all**. They log in and participate
through a shared account a community runs. "Get your own profile" is an optional
later step, not the starting point.

| # | Thing | Term | Who has it |
|---|---|---|---|
| 1 | Your EcoBank login | **your EcoBank account** / "My Account" | everyone, free |
| 2 | A Hive account a group owns and shares | **community profile** (or "the community's shared account") | most participants post through one of these; they hold no keys |
| 3 | A Hive account that is yours alone | **your digital profile** | optional — created or connected when you're ready to run your own |

Terms 2 and 3 are both "digital profiles" (Hive accounts) in the generic sense;
qualify which one you mean whenever it isn't obvious.

## Core concepts

| Concept | Use | Do NOT use | ES |
|---|---|---|---|
| A Hive account (`@name`), personal or community-shared | **digital profile** | "Hive account", "wallet", "your keys", "bank account" | _(later)_ |
| — same, in help/tooltip text where precision matters | "your digital profile (a Hive blockchain account)" | — | _(later)_ |
| The secrets that control a digital profile | **recovery keys** — only ever shown inside a security/backup screen | "master password", "private key", "WIF" as a bare field label | _(later)_ |
| The specific key that lets EcoBank publish for you | **posting key** | "your password" | _(later)_ |
| Prepaid one-time cost of creating a Hive account (EcoBank fronts the ~3 HIVE network cost) | **credit** — "prepaid account creation" | "account creation key", "ticket" (user-facing); anything that implies buying currency, a token, or an investment | _(later)_ |
| Screen showing HIVE / HP / HBD balances | **Wallet** (page title: "Wallet dashboard") | "bank", "balance sheet" | _(later)_ |
| The EcoBank user's own settings/bio page | **My Account** | "Profile" (now means the Hive thing) | _(later)_ |
| A set of people sharing one Hive account | **circle** ("join a circle", "the circle's shared account") | "group" (kept only in internal code / DB / `Group` model); "community" (that's Hive's *native* feature) | _(later)_ |
| Adding an existing digital profile to EcoBank | **Connect** ("Connect a digital profile") | "Import keys", "Import account" | _(later)_ |
| Making a brand-new digital profile | **Create** ("Create a digital profile") | "Create keys" | _(later)_ |
| EcoBank storing your recovery keys encrypted | **managed for you** / "EcoBank looks after the keys" | "custody", "we hold your keys" | _(later)_ |

## Action verbs

| Action | Verb | ES |
|---|---|---|
| Add existing profile | **Connect** | _(later)_ |
| Make new profile | **Create** | _(later)_ |
| Remove profile's keys from EcoBank | **Remove from EcoBank** | _(later)_ |
| Save a local copy of the keys | **Download backup** | _(later)_ |
| Publish a draft to Hive | **Publish** | _(later)_ |

## Standing disclaimers (use verbatim)

- **What the name means:** "Eco" = ecological restoration. "Bank" = a *bank of projects* (as in a seed bank or land bank), not a financial bank. The mission is community-led sustainable development; Hive is one tool it uses, not the point.
- **Non-affiliation (short, site-wide):**
  "EcoBank supports ecological restoration projects and is operated by Ecobank Development Colombia SAS. It is not a financial institution and is not affiliated with any bank."
- **Non-affiliation (long, About/import):**
  "EcoBank does not take deposits, hold money for you, or offer any financial service, and it is not affiliated with Ecobank Transnational Incorporated or any other bank. 'Bank' here means a bank of restoration projects."
- **Operator vs builder:** operated by Ecobank Development Colombia SAS; built and run on infrastructure by SRBDE (EcoBank is a client of SRBDE). Links: ecoinstats.net, github.com/srbde.
- **The model is inverted from most crypto:** you don't buy in and then hold value. You get an account and *earn* over time by participating. Hive transactions are essentially free; the only thing with a price here is creating the account itself (~3 HIVE network cost, which EcoBank covers). Nobody funds a balance, buys a token, or makes an investment on EcoBank.
- **What the posting key can do (on the connect form):**
  "A posting key lets EcoBank publish posts as your profile. It cannot move funds, change your password, or recover your profile."

## External tools (link out, never rebuild on-site)

| Need | Link |
|---|---|
| Turn a master password into individual keys | https://tools.crypto-dreamr.com/key-recovery |
| Update / rotate keys on-chain | https://keys.crypto-dreamr.com |

Rationale: EcoBank must never host a form that asks for a master password.
Users who only have a master password are sent to the deriver, then bring
back just the posting key.

## Notes

- Keep long translatable strings on **one line** in templates (pybabel
  extraction breaks on wrapped `_()` calls). See
  `memory/feedback_po_linebreaks`.
- "Hive" is fine to say — it's the network name, not jargon we're hiding.
  We just don't lead with "Hive account".
