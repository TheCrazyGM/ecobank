# EcoBank vocabulary — canonical terms

Single source of truth for user-facing wording. When you add or change a
user-facing string, make it match this table. Goal: **one word per concept**,
friendly but not vague, and nothing that reads like a phishing page.

Spanish is Latin-American / Colombian, informal **tú**. The ES column below is
the **locked glossary** — `translations/glossary.es.json` mirrors it, and
`scripts/translate_po.py` forces these exact renderings. See `docs/translations.md`.

**Never translated:** EcoBank, Hive, SRBDE, HIVE, HIVE Power, HP, HBD, HBD Savings,
Ecobank Development Colombia SAS, Ecobank Transnational Incorporated, PayPal,
Fernet, VESTS, RC, Resource Credits.

---

## Three accounts — never conflate them

Most people who use EcoBank hold **no keys at all**. They log in and participate
through a shared account a community runs. "Get your own profile" is an optional
later step, not the starting point.

| # | Thing | Term (EN) | Term (ES) | Who has it |
|---|---|---|---|---|
| 1 | Your EcoBank login | **your EcoBank account** / "My Account" | **tu cuenta de EcoBank** / "Mi cuenta" | everyone, free |
| 2 | A Hive account a circle shares | **the circle's shared account** | **la cuenta compartida del círculo** | most participants post through one of these; they hold no keys |
| 3 | A Hive account that is yours alone | **your digital profile** | **tu perfil digital** | optional — created or connected when you're ready to run your own |

Terms 2 and 3 are both "digital profiles" (Hive accounts) in the generic sense;
qualify which one you mean whenever it isn't obvious.

## Core concepts

| Concept | Use (EN) | ES (locked) | Do NOT use |
|---|---|---|---|
| A Hive account (`@name`), personal or shared | **digital profile** | **perfil digital** | "Hive account", "wallet", "your keys", "bank account" |
| — with precision, in help text | "your digital profile (a Hive blockchain account)" | "tu perfil digital (una cuenta de la cadena de bloques Hive)" | — |
| The secrets that control a digital profile | **recovery keys** | **claves de recuperación** | "master password", "private key", "WIF" as a bare label |
| The master password itself (where it must be named) | **master password** | **contraseña maestra** | — |
| The key that lets EcoBank publish for you | **posting key** | **clave de publicación** | "your password" |
| The key that can move funds | **active key** | **clave activa** | — |
| The key for full control / recovery | **owner key** | **clave de propietario** | — |
| Prepaid one-time cost of creating a Hive account | **credit** ("prepaid account creation") | **crédito** ("creación de cuenta prepagada") | "account creation key", "ticket"; anything implying buying currency / a token / an investment |
| Screen showing HIVE / HP / HBD balances | **Wallet** ("Wallet dashboard") | **Billetera** ("Panel de billetera") | "bank", "balance sheet" |
| The EcoBank user's own settings/bio page | **My Account** | **Mi cuenta** | "Profile" (that's the Hive thing) |
| A set of people sharing one Hive account | **circle** | **círculo** | "group" (internal code/DB only); "community" (Hive's *native* feature) |
| Hive's native communities feature | **community** | **comunidad** | using it for a circle |
| Adding an existing digital profile to EcoBank | **Connect** ("Connect a digital profile") | **Conectar** ("Conectar un perfil digital") | "Import keys", "Import account" |
| Making a brand-new digital profile | **Create** ("Create a digital profile") | **Crear** ("Crear un perfil digital") | "Create keys" |
| EcoBank storing your recovery keys encrypted | "EcoBank looks after the keys" | "EcoBank cuida las claves por ti" | "custody", "we hold your keys" |

## Action verbs

| Action | EN | ES (locked) |
|---|---|---|
| Add existing profile | **Connect** | **Conectar** |
| Make new profile | **Create** | **Crear** |
| Remove a profile from EcoBank | **Remove from EcoBank** | **Quitar de EcoBank** |
| Save a local copy of the keys | **Download backup** | **Descargar copia de seguridad** |
| Publish a draft to Hive | **Publish** | **Publicar** |
| Join a circle | **Join** | **Unirse** |
| Ask to join a circle | **Request to join** | **Solicitar unirse** |

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
- Spanish translation workflow: `docs/translations.md`. The ES terms above are
  authoritative; `translations/glossary.es.json` is generated to match.
