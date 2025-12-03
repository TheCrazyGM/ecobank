from __future__ import annotations

import html as _html
import re
import unicodedata
from typing import Any

from markupsafe import Markup, escape

# Optional dependencies with graceful fallbacks
try:  # Prefer Python-Markdown if available
    import markdown as _markdown  # type: ignore
except Exception:  # pragma: no cover - safe fallback if not installed
    _markdown = None  # type: ignore

try:
    import bleach  # type: ignore
except Exception:  # pragma: no cover
    bleach = None  # type: ignore

try:
    import mdformat as _mdformat  # type: ignore
except Exception:  # pragma: no cover
    _mdformat = None  # type: ignore


_IMG_EXT_RE = re.compile(
    r"\.(?:png|jpg|jpeg|gif|webp|bmp|svg)(?:\?[^\s)]*)?\s*$", re.IGNORECASE
)


def _preprocess_markdown(
    md_src: str, *, max_len: int = 20000, max_images: int = 50
) -> str:
    """Best-effort cleanup of user Markdown before formatting.

    - Unicode normalize and strip control chars
    - Unescape HTML entities
    - Normalize code-fence language labels and unescape fence bodies
    - Normalize <hr> to markdown rules; strip <center> wrappers
    - Convert bare image URLs to markdown images
    - Deduplicate consecutive identical URLs/HRs
    - Optionally cap number of images
    """
    s = unicodedata.normalize("NFC", str(md_src))
    s = re.sub(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]", "", s)
    if len(s) > max_len:
        s = s[:max_len]

    s = _html.unescape(s)

    def _unescape_deep(txt: str, rounds: int = 2) -> str:
        out = txt
        for _ in range(max(1, rounds)):
            out = _html.unescape(out)
        return out

    _LANG_ALIASES = {
        "py": "python",
        "js": "javascript",
        "ts": "typescript",
        "sh": "bash",
        "shell": "bash",
        "yml": "yaml",
        "md": "markdown",
        "c#": "csharp",
        "csharp": "csharp",
        "html": "html",
        "xml": "xml",
        "go": "go",
        "rust": "rust",
    }

    def _fix_fence(m: re.Match) -> str:
        opener = m.group(1)
        lang = (m.group(2) or "").strip()
        body = m.group(3)
        closer = m.group(4)
        lang_norm = _LANG_ALIASES.get(lang.lower(), lang)
        return f"{opener}{lang_norm}\n{_unescape_deep(body)}{closer}"

    fence_re_backtick = re.compile(
        r"(^```)([^\n]*)\n(.*?)(\n```)", re.MULTILINE | re.DOTALL
    )
    fence_re_tilde = re.compile(
        r"(^~~~)([^\n]*)\n(.*?)(\n~~~)", re.MULTILINE | re.DOTALL
    )
    s = fence_re_backtick.sub(_fix_fence, s)
    s = fence_re_tilde.sub(_fix_fence, s)

    s = re.sub(r"\s*</?center\s*>\s*", "\n\n", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*<hr\s*/?>\s*", "\n\n---\n\n", s, flags=re.IGNORECASE)

    def _convert_bare_image_urls(m: re.Match) -> str:
        url = m.group(0).strip()
        alt = url.rsplit("/", 1)[-1]
        return f"![{alt}]({url})"

    s = re.sub(
        r"(?:(?<=\s)|^) (https?://\S+)",
        lambda m: _convert_bare_image_urls(m)
        if _IMG_EXT_RE.search(m.group(1))
        else m.group(0),
        s,
    )

    lines = s.splitlines()
    out_lines: list[str] = []
    last = None
    for ln in lines:
        cur = ln.strip()
        if (
            last is not None
            and cur
            and cur == last
            and (cur.startswith("http") or cur == "---")
        ):
            continue
        out_lines.append(ln)
        last = cur
    s = "\n".join(out_lines)

    img_count = 0

    def _cap_images(m: re.Match) -> str:
        nonlocal img_count
        img_count += 1
        if img_count > max_images:
            alt, url = m.group(1), m.group(2)
            return f"{alt} ({url})"
        return m.group(0)

    s = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", _cap_images, s)
    return s


def render_markdown(text: Any) -> Markup:
    """Render Markdown to safe HTML with preprocessing, formatting, and sanitization.

    Pipeline:
    1) Normalize unicode + strip control chars + clamp size
    2) mdformat to normalize markdown (if available)
    3) Render with Python-Markdown (if available)
    4) Sanitize final HTML with Bleach and linkify (if available)
    Falls back to a minimal safe HTML conversion.
    """
    if not text:
        return Markup("")

    try:
        md_src = _preprocess_markdown(str(text))

        if _markdown is not None:
            html = _markdown.markdown(
                md_src,
                extensions=[
                    "extra",
                    "sane_lists",
                ],
                output_format="html5",
            )

            # Fix entities inside <code> while not breaking structure
            def _fix_code_entities(match: re.Match) -> str:
                open_tag, inner, close_tag = (
                    match.group(1),
                    match.group(2),
                    match.group(3),
                )
                for _ in range(3):
                    new_inner = inner.replace("&amp;amp;", "&amp;")
                    if new_inner == inner:
                        break
                    inner = new_inner
                inner = inner.replace("&amp;quot;", '"').replace("&quot;", '"')
                inner = inner.replace("&#34;", '"').replace("&amp;#34;", '"')
                inner = (
                    inner.replace("&apos;", "'")
                    .replace("&#39;", "'")
                    .replace("&amp;#39;", "'")
                )
                inner = inner.replace("&amp;lt;", "<").replace("&lt;", "<")
                inner = inner.replace("&amp;gt;", ">").replace("&gt;", ">")
                inner = inner.replace("&#60;", "<").replace("&amp;#60;", "<")
                inner = inner.replace("&#62;", ">").replace("&amp;#62;", ">")
                return f"{open_tag}{inner}{close_tag}"

            html = re.sub(
                r"(<pre>\s*<code[^>]*>)(.*?)(</code>\s*</pre>)",
                _fix_code_entities,
                html,
                flags=re.DOTALL | re.IGNORECASE,
            )
            html = re.sub(
                r"(<code[^>]*>)(.*?)(</code>)",
                _fix_code_entities,
                html,
                flags=re.DOTALL | re.IGNORECASE,
            )

            if bleach is not None:
                html = bleach.clean(
                    html,
                    tags=[
                        "p",
                        "br",
                        "strong",
                        "em",
                        "ul",
                        "ol",
                        "li",
                        "code",
                        "pre",
                        "a",
                        "blockquote",
                        "h1",
                        "h2",
                        "h3",
                        "hr",
                        "table",
                        "thead",
                        "tbody",
                        "tr",
                        "th",
                        "td",
                        "img",
                        "sup",
                        "sub",
                    ],
                    attributes={
                        "a": ["href", "title", "rel"],
                        "img": ["src", "alt", "title"],
                        "code": ["class"],
                        "pre": ["class"],
                        "th": ["colspan", "rowspan", "align"],
                        "td": ["colspan", "rowspan", "align"],
                    },
                    protocols=["http", "https", "mailto", "ipfs"],
                    strip=True,
                )
                html = bleach.linkify(
                    html,
                    callbacks=[
                        bleach.callbacks.nofollow,
                        bleach.callbacks.target_blank,
                    ],
                    skip_tags=["pre", "code"],
                )
            return Markup(html)
    except Exception:
        # In case of any error, fall back to minimal safe HTML conversion below
        pass

    escaped = escape(str(text))
    paragraphs = [p.replace("\n", "<br>") for p in escaped.split("\n\n")]
    html = "".join(f"<p>{p}</p>" for p in paragraphs)
    return Markup(html)


def render_markdown_preview(text: Any, limit: int = 250) -> Markup:
    """Render a preview-only plain text from Markdown (no HTML tags)."""
    if not text:
        return Markup("")
    try:
        md_src = _preprocess_markdown(str(text))
        if _mdformat is not None:
            md_src = _mdformat.text(md_src)
        if _markdown is not None:
            html = _markdown.markdown(
                md_src, extensions=["extra", "sane_lists"], output_format="html5"
            )
        else:
            html = escape(str(text))

        if bleach is not None:
            txt = bleach.clean(
                html,
                tags=[],
                attributes={},
                protocols=[],
                strip=True,
                strip_comments=True,
            )
        else:
            # crude text extraction: strip tags
            txt = re.sub(r"<[^>]+>", " ", str(html))
        txt = re.sub(r"https?://\S+", "[link]", txt)
        txt = re.sub(r"(?:\\[link\\]\s*){2,}", "[link] ", txt)
        txt = re.sub(r"\s+", " ", txt).strip()
        lim = max(0, int(limit))
        if lim and len(txt) > lim:
            cut = txt.rfind(" ", 0, lim)
            if cut == -1:
                cut = lim
            txt = txt[:cut].rstrip() + "…"
        return Markup(escape(txt))
    except Exception:
        s = escape(str(text))
        if limit and len(s) > limit:
            s = s[: limit - 1] + "…"
        return Markup(s)
