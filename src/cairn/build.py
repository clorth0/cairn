from __future__ import annotations

import datetime
import html
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from cairn.config import Config
from cairn.content import Content, ContentError, discover, filter_content, load_content, slugify
from cairn.feeds import render_json_feed, render_robots, render_rss, render_sitemap
from cairn.render import Renderer, markdown_to_html
from cairn.security import headers_file, meta_csp_tag, sanitize

_IMG_TAG = re.compile(r"<img\b[^>]*>", re.IGNORECASE)


@dataclass
class BuildResult:
    output_dir: Path
    page_count: int = 0
    warnings: list[str] = field(default_factory=list)


def _og_tags(config: Config, title: str, description: str | None) -> str:
    site_name = html.escape(config.site.title, quote=True)
    esc_title = html.escape(title, quote=True)
    parts = [
        f'<meta property="og:site_name" content="{site_name}">',
        f'<meta property="og:title" content="{esc_title}">',
        '<meta name="twitter:card" content="summary">',
    ]
    if description:
        esc_desc = html.escape(description, quote=True)
        parts.append(f'<meta property="og:description" content="{esc_desc}">')
    return "\n".join(parts)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _content_html(item: Content, config: Config) -> str:
    html = markdown_to_html(item.body)
    return sanitize(html) if config.security.sanitize else html


def build(
    config: Config,
    *,
    drafts: bool = False,
    future: bool = False,
    clean: bool = False,
    today: datetime.date | None = None,
) -> BuildResult:
    out = Path(config.build.output_dir)
    if clean and out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    renderer = Renderer(config.build.theme)
    meta_csp = meta_csp_tag(config)
    result = BuildResult(output_dir=out)

    items = filter_content(
        discover(config.build.content_dir),
        drafts=drafts, future=future, today=today,
    )
    posts = sorted(
        (c for c in items if c.is_post), key=lambda c: c.date, reverse=True
    )
    pages = [c for c in items if not c.is_post]

    def page_shell(page_title, description, inner):
        return renderer.render(
            "base.html",
            site=config.site,
            page_title=page_title,
            meta_csp=meta_csp,
            meta_description=description or config.site.description,
            og_tags=_og_tags(config, page_title, description),
            content=inner,
        )

    # Index
    inner = renderer.render("index.html", site=config.site, posts=posts)
    _write(out / "index.html", page_shell(config.site.title, None, inner))
    result.page_count += 1

    # Posts
    for post in posts:
        inner = renderer.render(
            "post.html", site=config.site, post=post,
            content=_content_html(post, config),
        )
        _write(out / post.slug / "index.html",
               page_shell(post.title, post.description, inner))
        result.page_count += 1

    # Pages
    for page in pages:
        inner = renderer.render(
            "page.html", site=config.site, page=page,
            content=_content_html(page, config),
        )
        _write(out / page.slug / "index.html",
               page_shell(page.title, page.description, inner))
        result.page_count += 1

    # Archive
    inner = renderer.render("archive.html", site=config.site, posts=posts)
    _write(out / "archive" / "index.html", page_shell("Archive", None, inner))
    result.page_count += 1

    # Tag pages
    tags: dict[str, list[Content]] = {}
    for post in posts:
        for tag in post.tags:
            tags.setdefault(tag, []).append(post)
    for tag, tagged in tags.items():
        inner = renderer.render("tag.html", site=config.site, tag=tag, posts=tagged)
        _write(out / "tags" / slugify(tag) / "index.html",
               page_shell(f"Tagged {tag}", None, inner))
        result.page_count += 1

    # Feeds and discovery files
    _write(out / "feed.xml", render_rss(posts, config))
    _write(out / "feed.json", render_json_feed(posts, config))
    _write(out / "sitemap.xml", render_sitemap(posts + pages, config))
    _write(out / "robots.txt", render_robots(config))

    # Security header file
    _write(out / "_headers", headers_file(config))

    # Static assets
    static_dir = Path(config.build.theme) / "static"
    if static_dir.is_dir():
        for asset in static_dir.iterdir():
            if asset.is_file():
                shutil.copyfile(asset, out / asset.name)

    return result


def check(config: Config) -> list[str]:
    """Validate all content; return a list of error strings (empty == OK).

    Reports malformed frontmatter and images that are missing alt text.
    """
    errors: list[str] = []
    content_dir = Path(config.build.content_dir)
    for path in sorted(content_dir.rglob("*.md")):
        try:
            item = load_content(path)
        except ContentError as exc:
            errors.append(str(exc))
            continue
        rendered = markdown_to_html(item.body)
        for tag in _IMG_TAG.findall(rendered):
            if not re.search(r"\balt\s*=", tag, re.IGNORECASE):
                errors.append(f"{path}: image is missing alt text: {tag}")
    return errors
