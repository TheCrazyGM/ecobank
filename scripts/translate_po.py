"""Refresh the Spanish catalog from source and machine-translate the gaps,
protecting a locked glossary.

Developer tool, never imported by the app.

    export DEEPL_API_KEY=xxxxxxxx:fx
    uv run --no-project --with polib --with babel --with jinja2 \\
        --with deepl --with python-dotenv python scripts/translate_po.py
    uv run --no-project --with babel pybabel compile -d translations

Steps:
  1. pybabel extract  -> messages.pot
  2. pybabel update   -> refresh the .po (adds new strings, fuzzy-matches changed
     ones so their old translation carries over as a starting point)
  3. fill empty / fuzzy entries:
       - whole string == a `force` glossary key  -> ES value, fuzzy cleared
       - otherwise                               -> DeepL, kept FUZZY + tagged
         `machine-translated`
  4. glossary terms (translations/glossary.es.json) are wrapped <g>..</g> and
     sent to DeepL as ignore tags, so they come back verbatim

polib is the only writer that touches the tracked .po, so once it has been
normalised the diffs stay small.

Flags: --dry-run   --glossary-only (no API key needed)   --no-extract
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import polib
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
PO_PATH = ROOT / "translations" / "es" / "LC_MESSAGES" / "messages.po"
POT_PATH = ROOT / "messages.pot"
GLOSSARY_PATH = ROOT / "translations" / "glossary.es.json"


def load_glossary():
    data = json.loads(GLOSSARY_PATH.read_text(encoding="utf-8"))
    pairs = [(t, t) for t in data["dont_translate"]]
    pairs += list(data["force"].items())
    pairs.sort(key=lambda p: len(p[0]), reverse=True)
    return pairs, {k.strip().lower(): v for k, v in data["force"].items()}


def protect(text, pairs):
    for term, repl in pairs:

        def _sub(m, repl=repl):
            r = repl
            if m.group(0)[:1].isupper() and r[:1].islower():
                r = r[:1].upper() + r[1:]
            return f"<g>{r}</g>"

        text = re.compile(re.escape(term), re.IGNORECASE).sub(_sub, text)
    return text


def unprotect(text):
    return text.replace("<g>", "").replace("</g>", "")


def main():
    load_dotenv(ROOT / ".env")
    dry_run = "--dry-run" in sys.argv
    glossary_only = "--glossary-only" in sys.argv

    if "--no-extract" not in sys.argv:
        subprocess.run(
            [
                "pybabel",
                "extract",
                "-F",
                "babel.cfg",
                "-k",
                "_l",
                "-o",
                str(POT_PATH),
                ".",
            ],
            cwd=ROOT,
            check=True,
        )
        # no --previous: its wrapped "#| msgid" output is unparseable by polib
        subprocess.run(
            [
                "pybabel",
                "update",
                "-i",
                str(POT_PATH),
                "-d",
                str(ROOT / "translations"),
            ],
            cwd=ROOT,
            check=True,
        )

    po = polib.pofile(str(PO_PATH))
    pairs, force_exact = load_glossary()

    # pybabel's fuzzy-match can carry a translation whose %(name)s placeholders no
    # longer match the new msgid (e.g. group -> circle). Those are actively wrong;
    # clear them so they are retranslated cleanly.
    for e in po:
        if (
            e.fuzzy
            and not e.obsolete
            and _placeholders(e.msgstr) - _placeholders(e.msgid)
        ):
            e.msgstr = ""

    pending = [e for e in po if not e.obsolete and (e.fuzzy or not e.translated())]
    forced, mt = [], []
    for e in pending:
        (forced if e.msgid.strip().lower() in force_exact else mt).append(e)

    print(
        f"{len(po)} entries: {len(po) - len(pending)} done, "
        f"{len(forced)} glossary, {len(mt)} to DeepL"
    )
    if dry_run:
        return

    for e in forced:
        e.msgstr = force_exact[e.msgid.strip().lower()]
        _unfuzzy(e)

    if mt and not glossary_only:
        key = os.environ.get("DEEPL_API_KEY")
        if not key:
            sys.exit("DEEPL_API_KEY not set (free keys end in ':fx').")
        import deepl

        translator = deepl.Translator(key)

        def tr(texts):
            return translator.translate_text(
                [protect(t, pairs) for t in texts],
                source_lang="EN",
                target_lang="ES",
                tag_handling="xml",
                ignore_tags=["g"],
                preserve_formatting=True,
            )

        singles = [e for e in mt if not e.msgid_plural]
        for i in range(0, len(singles), 40):
            chunk = singles[i : i + 40]
            for e, res in zip(chunk, tr([e.msgid for e in chunk])):
                e.msgstr = unprotect(res.text)
                _mt(e)
        for e in (e for e in mt if e.msgid_plural):
            forms = tr([e.msgid, e.msgid_plural])
            e.msgstr_plural = {i: unprotect(f.text) for i, f in enumerate(forms)}
            _mt(e)

    po.save(str(PO_PATH))
    print(f"wrote {PO_PATH.relative_to(ROOT)} - review the fuzzy entries.")


def _placeholders(text):
    return set(re.findall(r"%\((\w+)\)", text or ""))


def _unfuzzy(entry):
    entry.flags = [f for f in entry.flags if f != "fuzzy"]


def _mt(entry):
    for f in ("fuzzy", "machine-translated"):
        if f not in entry.flags:
            entry.flags.append(f)


if __name__ == "__main__":
    main()
