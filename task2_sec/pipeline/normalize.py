"""Normalize 10-K HTML to a canonical plain-text body for char-offset segmentation."""

from __future__ import annotations

import re
import unicodedata

from bs4 import BeautifulSoup, NavigableString, Tag

_IX_TAG = re.compile(r"^ix:", re.I)
_BLOCK_TAGS = frozenset({"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr", "br"})


def normalize(html: str) -> str:
    """Strip iXBRL noise, unwrap inline tags, unify whitespace."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(["script", "style", "noscript"]):
        tag.decompose()
    _unwrap_ixbrl(soup)
    text = _render_text(soup.body or soup)
    text = text.replace("\xa0", " ")
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def _unwrap_ixbrl(root: Tag) -> None:
    for tag in list(root.find_all(True)):
        name = tag.name or ""
        if _IX_TAG.match(name):
            tag.unwrap()


def _render_text(node: Tag) -> str:
    parts: list[str] = []

    def walk(el: Tag | NavigableString) -> None:
        if isinstance(el, NavigableString):
            parts.append(str(el))
            return
        name = (el.name or "").lower()
        if name == "br":
            parts.append("\n")
            return
        for child in el.children:
            walk(child)
        if name in _BLOCK_TAGS:
            parts.append("\n")

    walk(node)
    return "".join(parts)
