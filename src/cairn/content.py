from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)
_NON_SLUG = re.compile(r"[^\w\s-]")
_SPACES = re.compile(r"[\s_]+")
_DASHES = re.compile(r"-+")


class ContentError(Exception):
    """Raised when a content file is malformed or missing required frontmatter."""


@dataclass
class Content:
    title: str
    slug: str
    body: str  # raw Markdown
    source_path: Path | None
    description: str | None = None
    date: datetime.date | None = None
    tags: list[str] = field(default_factory=list)
    is_draft: bool = False

    @property
    def is_post(self) -> bool:
        return self.date is not None


def slugify(value: str) -> str:
    value = _NON_SLUG.sub("", value.strip().lower())
    value = _SPACES.sub("-", value)
    value = _DASHES.sub("-", value).strip("-")
    return value or "untitled"


def parse_frontmatter(text: str) -> tuple[dict, str]:
    match = _FRONTMATTER.match(text)
    if not match:
        return {}, text
    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        raise ContentError(f"invalid YAML frontmatter: {exc}") from exc
    if not isinstance(meta, dict):
        raise ContentError("frontmatter must be a mapping of key: value pairs")
    return meta, match.group(2)


def load_content(path: str | Path) -> Content:
    path = Path(path)
    meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))

    title = meta.get("title")
    if not title:
        raise ContentError(f"{path}: missing required 'title' in frontmatter")

    date = meta.get("date")
    if isinstance(date, datetime.datetime):
        date = date.date()
    if date is not None and not isinstance(date, datetime.date):
        raise ContentError(f"{path}: 'date' must be a date (YYYY-MM-DD), got {date!r}")

    tags = meta.get("tags") or []
    if not isinstance(tags, list):
        raise ContentError(f"{path}: 'tags' must be a list")

    return Content(
        title=str(title),
        slug=str(meta.get("slug") or slugify(path.stem)),
        body=body,
        source_path=path,
        description=meta.get("description"),
        date=date,
        tags=[str(t) for t in tags],
        is_draft=bool(meta.get("draft", False)),
    )


def discover(content_dir: str | Path) -> list[Content]:
    content_dir = Path(content_dir)
    return [load_content(p) for p in sorted(content_dir.rglob("*.md"))]


def filter_content(
    items: list[Content],
    *,
    drafts: bool = False,
    future: bool = False,
    today: datetime.date | None = None,
) -> list[Content]:
    today = today or datetime.date.today()
    kept = []
    for item in items:
        if item.is_draft and not drafts:
            continue
        if item.date and item.date > today and not future:
            continue
        kept.append(item)
    return kept
