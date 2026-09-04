# Translations (Spanish)

Supported locales: `en` (source), `es`. Catalog: `translations/es/LC_MESSAGES/messages.po`
(tracked). `messages.pot` and the compiled `.mo` files are gitignored.

Spanish is **Latin-American / Colombian, informal *tú***. The canonical term list
is the ES column of `docs/vocabulary.md`; `translations/glossary.es.json` mirrors
it and is what the tooling enforces.

## Refresh only (no machine translation)

```bash
./update_translations.sh          # pybabel extract + update + compile
```

Use this after changing `_()` / `_l()` strings when you'll translate by hand.
Then edit `messages.po` and re-run to compile.

## Refresh + machine-translate the gaps

```bash
export DEEPL_API_KEY=xxxxxxxx:fx   # free tier; keys end in ':fx'
uv run --no-project --with polib --with babel --with jinja2 \
    --with deepl --with python-dotenv python scripts/translate_po.py
uv run --no-project --with babel pybabel compile -d translations
```

`scripts/translate_po.py`:

1. `pybabel extract` + `pybabel update` — refresh the `.po` from source. Changed
   strings keep their old translation as a **fuzzy** starting point; a fuzzy
   translation whose `%(name)s` placeholders no longer match the source is cleared.
2. For each empty / fuzzy entry:
   - whole string equals a `force` glossary key → the ES value, fuzzy cleared
   - otherwise → **DeepL** (EN→ES), left **fuzzy** and tagged `machine-translated`
3. Every glossary term (both lists in `glossary.es.json`) is wrapped in `<g>…</g>`
   and passed to DeepL as an ignore tag, so `EcoBank`, `Hive`, `círculo`,
   `perfil digital`, etc. come back exactly as written.

Flags: `--dry-run` (counts only), `--glossary-only` (skip DeepL — no API key
needed), `--no-extract` (skip the pybabel steps).

## Reviewing

After a run, every machine-translated entry is `#, fuzzy` + `#, machine-translated`.
`pybabel compile` skips fuzzy entries (so the site shows English until reviewed).
Work through them in `messages.po`: fix the Spanish, delete the `fuzzy` flag,
recompile. `git grep -c 'machine-translated' translations/es/LC_MESSAGES/messages.po`
tracks what's left.

## Glossary

Edit `docs/vocabulary.md` (authoritative) and keep `translations/glossary.es.json`
in sync. `dont_translate` = kept verbatim; `force` = EN substring → ES rendering
(longest match first; sentence-initial capitals are preserved).

## Note on diffs

The `.po` gets reformatted the first time the tooling touches it (the committed
file was hand-formatted). That normalisation is a one-time cost; after it, review
by the `#, fuzzy` markers rather than line-by-line.
