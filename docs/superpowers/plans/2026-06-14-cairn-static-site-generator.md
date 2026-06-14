# Cairn Static Site Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Cairn, a minimal security-first static site generator in Python that turns Markdown + YAML frontmatter into a fast, zero-JavaScript static site with a locked-down Content Security Policy.

**Architecture:** A small installable Python package (`src/cairn/`) with one module per responsibility (config, content, security, render, feeds, build, serve, deploy, cli) plus a default zero-JS theme. The build pipeline reads `site.toml`, parses content, renders sanitized HTML through sandboxed autoescaped Jinja2 templates, and emits a `public/` directory with feeds, sitemap, robots, and per-host security headers.

**Tech Stack:** Python 3.11+, `markdown`, `jinja2`, `pygments`, `PyYAML`, `nh3`; stdlib `tomllib`, `http.server`, `xml.etree`. Tests with `pytest`.

---

## File Structure

Created by this plan:

- `pyproject.toml`: package metadata, dependencies, `cairn` console entry point
- `requirements.lock`: pinned, hashed dependency set
- `README.md`, `LICENSE`, `.gitignore`
- `src/cairn/__init__.py`: version
- `src/cairn/config.py`: `Config` dataclasses + `load_config`
- `src/cairn/content.py`: `Content` model, frontmatter parsing, discovery, filtering
- `src/cairn/security.py`: sanitization, CSP, header file, meta tag
- `src/cairn/render.py`: Markdown to HTML + Jinja2 `Renderer`
- `src/cairn/feeds.py`: RSS, JSON Feed, sitemap, robots
- `src/cairn/build.py`: `build()` pipeline + `BuildResult`
- `src/cairn/serve.py`: local preview server with `--watch`
- `src/cairn/deploy.py`: emit GitHub Pages / Cloudflare deploy config
- `src/cairn/cli.py`: argparse subcommands
- `src/cairn/scaffold.py`: `new site` / `new post` templates and writers
- `themes/default/templates/*.html` + `themes/default/static/style.css`
- `tests/test_*.py`: one test module per source module + an end-to-end test

Each module has a single responsibility and is testable in isolation. Data models (`Config`, `Content`) are defined once and reused everywhere.

---

## Task 1: Project scaffold and test harness

**Files:**
- Create: `pyproject.toml`
- Create: `src/cairn/__init__.py`
- Create: `tests/test_smoke.py`
- Create: `.gitignore`
- Create: `LICENSE` (MIT)

- [ ] **Step 1: Write the failing test**

Create `tests/test_smoke.py`:

```python
import cairn


def test_version_is_exposed():
    assert isinstance(cairn.__version__, str)
    assert cairn.__version__
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_smoke.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cairn'`.

- [ ] **Step 3: Create the package and metadata**

Create `src/cairn/__init__.py`:

```python
__version__ = "0.1.0"
```

Create `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "cairn-ssg"
version = "0.1.0"
description = "A minimal, security-first static site generator."
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
authors = [{ name = "Matt James" }]
dependencies = [
    "markdown>=3.6",
    "jinja2>=3.1",
    "pygments>=2.17",
    "PyYAML>=6.0",
    "nh3>=0.2.17",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[project.scripts]
cairn = "cairn.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
cairn = ["../../themes/default/templates/*.html", "../../themes/default/static/*"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

Create `.gitignore`:

```
__pycache__/
*.pyc
.venv/
public/
*.egg-info/
.pytest_cache/
build/
dist/
```

Create `LICENSE` with the standard MIT license text, copyright "2026 Matt James".

- [ ] **Step 4: Install dev dependencies and run the test**

Run:
```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
python -m pytest tests/test_smoke.py -v
```
Expected: PASS.

- [ ] **Step 5: Generate the locked dependency set**

Run:
```bash
pip install pip-tools
pip-compile --generate-hashes --output-file=requirements.lock pyproject.toml
```
Expected: `requirements.lock` created with pinned versions and `--hash=sha256:...` lines. (Do not hand-write hashes.)

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/cairn/__init__.py tests/test_smoke.py .gitignore LICENSE requirements.lock
git commit -m "chore: scaffold cairn package and test harness"
```

---

## Task 2: Configuration loading (`config.py`)

**Files:**
- Create: `src/cairn/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_config.py`:

```python
import textwrap
import pytest
from cairn.config import load_config, ConfigError


def write(tmp_path, body):
    p = tmp_path / "site.toml"
    p.write_text(textwrap.dedent(body), encoding="utf-8")
    return p


def test_loads_full_config(tmp_path):
    path = write(tmp_path, """
        [site]
        title = "My Cairn"
        url = "https://example.com"
        author = "Author"
        description = "A small site."
        language = "en"

        [build]
        content_dir = "content"
        output_dir = "public"
        theme = "default"
        feed_limit = 10

        [security]
        csp = "locked"
        referrer_policy = "no-referrer"
        sanitize = true
        hsts = true

        [deploy]
        target = "cloudflare"
    """)
    cfg = load_config(path)
    assert cfg.site.title == "My Cairn"
    assert cfg.build.feed_limit == 10
    assert cfg.security.sanitize is True
    assert cfg.deploy.target == "cloudflare"


def test_defaults_applied_for_optional_sections(tmp_path):
    path = write(tmp_path, """
        [site]
        title = "Minimal"
        url = "https://example.com"
        author = "Author"
        description = "d"
    """)
    cfg = load_config(path)
    assert cfg.build.output_dir == "public"
    assert cfg.build.feed_limit == 20
    assert cfg.security.csp == "locked"
    assert cfg.deploy.target == "folder"


def test_missing_required_site_field_raises(tmp_path):
    path = write(tmp_path, """
        [site]
        url = "https://example.com"
    """)
    with pytest.raises(ConfigError):
        load_config(path)


def test_unknown_deploy_target_raises(tmp_path):
    path = write(tmp_path, """
        [site]
        title = "t"
        url = "https://example.com"
        author = "a"
        description = "d"
        [deploy]
        target = "ftp"
    """)
    with pytest.raises(ConfigError):
        load_config(path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cairn.config'`.

- [ ] **Step 3: Implement `config.py`**

Create `src/cairn/config.py`:

```python
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

VALID_TARGETS = {"folder", "github-pages", "cloudflare"}


class ConfigError(Exception):
    """Raised when site.toml is missing required fields or has bad values."""


@dataclass
class SiteConfig:
    title: str
    url: str
    author: str
    description: str
    language: str = "en"


@dataclass
class BuildConfig:
    content_dir: str = "content"
    output_dir: str = "public"
    theme: str = "default"
    feed_limit: int = 20


@dataclass
class SecurityConfig:
    csp: str = "locked"
    referrer_policy: str = "no-referrer"
    sanitize: bool = True
    hsts: bool = True


@dataclass
class DeployConfig:
    target: str = "folder"


@dataclass
class Config:
    site: SiteConfig
    build: BuildConfig = field(default_factory=BuildConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    deploy: DeployConfig = field(default_factory=DeployConfig)


def _require(table: dict, key: str, where: str) -> object:
    if key not in table:
        raise ConfigError(f"[{where}] is missing required key '{key}'")
    return table[key]


def load_config(path: str | Path) -> Config:
    path = Path(path)
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"config file not found: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML in {path}: {exc}") from exc

    site_raw = data.get("site")
    if not isinstance(site_raw, dict):
        raise ConfigError("missing required [site] table")
    site = SiteConfig(
        title=str(_require(site_raw, "title", "site")),
        url=str(_require(site_raw, "url", "site")),
        author=str(_require(site_raw, "author", "site")),
        description=str(_require(site_raw, "description", "site")),
        language=str(site_raw.get("language", "en")),
    )

    build_raw = data.get("build", {})
    build = BuildConfig(
        content_dir=str(build_raw.get("content_dir", "content")),
        output_dir=str(build_raw.get("output_dir", "public")),
        theme=str(build_raw.get("theme", "default")),
        feed_limit=int(build_raw.get("feed_limit", 20)),
    )

    sec_raw = data.get("security", {})
    security = SecurityConfig(
        csp=str(sec_raw.get("csp", "locked")),
        referrer_policy=str(sec_raw.get("referrer_policy", "no-referrer")),
        sanitize=bool(sec_raw.get("sanitize", True)),
        hsts=bool(sec_raw.get("hsts", True)),
    )

    deploy_raw = data.get("deploy", {})
    target = str(deploy_raw.get("target", "folder"))
    if target not in VALID_TARGETS:
        raise ConfigError(
            f"[deploy] target '{target}' must be one of {sorted(VALID_TARGETS)}"
        )
    deploy = DeployConfig(target=target)

    return Config(site=site, build=build, security=security, deploy=deploy)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/cairn/config.py tests/test_config.py
git commit -m "feat: declarative site.toml config loading"
```

---

## Task 3: Content model, frontmatter, discovery, filtering (`content.py`)

**Files:**
- Create: `src/cairn/content.py`
- Test: `tests/test_content.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_content.py`:

```python
import datetime
import textwrap
import pytest
from cairn.content import (
    Content,
    ContentError,
    parse_frontmatter,
    slugify,
    load_content,
    discover,
    filter_content,
)


def make(tmp_path, name, body):
    p = tmp_path / name
    p.write_text(textwrap.dedent(body).lstrip("\n"), encoding="utf-8")
    return p


def test_slugify_normalizes():
    assert slugify("A Durable Marker!") == "a-durable-marker"
    assert slugify("  spaced  out  ") == "spaced-out"
    assert slugify("") == "untitled"


def test_parse_frontmatter_splits_meta_and_body():
    meta, body = parse_frontmatter("---\ntitle: Hi\n---\nHello body\n")
    assert meta == {"title": "Hi"}
    assert body.strip() == "Hello body"


def test_parse_frontmatter_without_block_returns_empty_meta():
    meta, body = parse_frontmatter("no frontmatter here")
    assert meta == {}
    assert body == "no frontmatter here"


def test_parse_frontmatter_non_mapping_raises():
    with pytest.raises(ContentError):
        parse_frontmatter("---\n- just\n- a\n- list\n---\nbody")


def test_load_post_with_date_is_post(tmp_path):
    p = make(tmp_path, "hello.md", """
        ---
        title: Hello
        date: 2026-06-14
        tags: [meta, design]
        description: A summary.
        ---
        Body text.
    """)
    c = load_content(p)
    assert c.title == "Hello"
    assert c.slug == "hello"
    assert c.date == datetime.date(2026, 6, 14)
    assert c.tags == ["meta", "design"]
    assert c.is_post is True


def test_load_page_without_date_is_not_post(tmp_path):
    p = make(tmp_path, "about.md", """
        ---
        title: About
        ---
        Who I am.
    """)
    c = load_content(p)
    assert c.is_post is False
    assert c.slug == "about"


def test_missing_title_raises(tmp_path):
    p = make(tmp_path, "bad.md", """
        ---
        date: 2026-06-14
        ---
        no title
    """)
    with pytest.raises(ContentError):
        load_content(p)


def test_bad_date_raises(tmp_path):
    p = make(tmp_path, "bad.md", """
        ---
        title: Bad
        date: not-a-date
        ---
        body
    """)
    with pytest.raises(ContentError):
        load_content(p)


def test_explicit_slug_overrides_filename(tmp_path):
    p = make(tmp_path, "whatever.md", """
        ---
        title: T
        slug: custom-slug
        ---
        body
    """)
    assert load_content(p).slug == "custom-slug"


def test_discover_finds_markdown_recursively(tmp_path):
    (tmp_path / "sub").mkdir()
    make(tmp_path, "a.md", "---\ntitle: A\n---\nx")
    make(tmp_path, "sub/b.md", "---\ntitle: B\n---\ny")
    make(tmp_path, "ignore.txt", "not markdown")
    items = discover(tmp_path)
    assert {c.title for c in items} == {"A", "B"}


def test_filter_excludes_drafts_and_future_by_default():
    today = datetime.date(2026, 6, 14)
    items = [
        Content(title="Pub", slug="pub", body="", source_path=None,
                date=datetime.date(2026, 6, 1)),
        Content(title="Draft", slug="draft", body="", source_path=None,
                date=today, is_draft=True),
        Content(title="Future", slug="future", body="", source_path=None,
                date=datetime.date(2026, 7, 1)),
    ]
    kept = filter_content(items, drafts=False, future=False, today=today)
    assert {c.title for c in kept} == {"Pub"}
    kept_all = filter_content(items, drafts=True, future=True, today=today)
    assert {c.title for c in kept_all} == {"Pub", "Draft", "Future"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_content.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cairn.content'`.

- [ ] **Step 3: Implement `content.py`**

Create `src/cairn/content.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_content.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cairn/content.py tests/test_content.py
git commit -m "feat: content model, frontmatter parsing, discovery, filtering"
```

---

## Task 4: Security primitives (`security.py`)

**Files:**
- Create: `src/cairn/security.py`
- Test: `tests/test_security.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_security.py`:

```python
import pytest
from cairn.config import Config, SiteConfig, SecurityConfig
from cairn.security import (
    sanitize,
    build_csp,
    security_headers,
    headers_file,
    meta_csp_tag,
    LOCKED_CSP,
)


def cfg(**sec):
    return Config(
        site=SiteConfig(title="t", url="https://e.com", author="a", description="d"),
        security=SecurityConfig(**sec),
    )


@pytest.mark.parametrize("payload", [
    '<script>alert(1)</script>',
    '<p onclick="evil()">hi</p>',
    '<a href="javascript:alert(1)">x</a>',
    '<iframe src="http://evil"></iframe>',
])
def test_sanitize_strips_dangerous_markup(payload):
    cleaned = sanitize(payload)
    assert "<script" not in cleaned
    assert "onclick" not in cleaned
    assert "javascript:" not in cleaned
    assert "<iframe" not in cleaned


def test_sanitize_keeps_safe_markup():
    cleaned = sanitize("<p>Hello <strong>world</strong></p>")
    assert "<strong>world</strong>" in cleaned


def test_build_csp_locked_preset():
    assert build_csp(SecurityConfig(csp="locked")) == LOCKED_CSP
    assert "default-src 'none'" in build_csp(SecurityConfig(csp="locked"))


def test_build_csp_custom_passthrough():
    custom = "default-src 'self'"
    assert build_csp(SecurityConfig(csp=custom)) == custom


def test_security_headers_include_hsts_when_enabled():
    headers = security_headers(cfg(hsts=True))
    assert "Strict-Transport-Security" in headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["Referrer-Policy"] == "no-referrer"


def test_security_headers_omit_hsts_when_disabled():
    headers = security_headers(cfg(hsts=False))
    assert "Strict-Transport-Security" not in headers


def test_headers_file_uses_cloudflare_format():
    text = headers_file(cfg())
    assert text.startswith("/*")
    assert "  Content-Security-Policy:" in text


def test_meta_csp_tag_contains_policy():
    tag = meta_csp_tag(cfg())
    assert tag.startswith('<meta http-equiv="Content-Security-Policy"')
    assert "default-src 'none'" in tag
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_security.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cairn.security'`.

- [ ] **Step 3: Implement `security.py`**

Create `src/cairn/security.py`:

```python
from __future__ import annotations

import nh3

from cairn.config import Config, SecurityConfig

LOCKED_CSP = (
    "default-src 'none'; img-src 'self'; style-src 'self'; font-src 'self'; "
    "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
)

_PERMISSIONS_POLICY = (
    "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
    "magnetometer=(), microphone=(), payment=(), usb=()"
)


def sanitize(html: str, allowed_tags: set[str] | None = None) -> str:
    """Strip dangerous markup from rendered HTML using nh3's safe allowlist."""
    if allowed_tags is None:
        return nh3.clean(html)
    return nh3.clean(html, tags=allowed_tags)


def build_csp(security: SecurityConfig) -> str:
    if security.csp == "locked":
        return LOCKED_CSP
    return security.csp


def security_headers(config: Config) -> dict[str, str]:
    sec = config.security
    headers = {
        "Content-Security-Policy": build_csp(sec),
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": sec.referrer_policy,
        "Permissions-Policy": _PERMISSIONS_POLICY,
    }
    if sec.hsts:
        headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains; preload"
        )
    return headers


def headers_file(config: Config) -> str:
    """Cloudflare Pages `_headers` format: a path glob followed by indented headers."""
    lines = ["/*"]
    for key, value in security_headers(config).items():
        lines.append(f"  {key}: {value}")
    return "\n".join(lines) + "\n"


def meta_csp_tag(config: Config) -> str:
    """Fallback CSP for hosts (e.g. GitHub Pages) that cannot set HTTP headers."""
    csp = build_csp(config.security).replace('"', "&quot;")
    return f'<meta http-equiv="Content-Security-Policy" content="{csp}">'
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_security.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cairn/security.py tests/test_security.py
git commit -m "feat: CSP, security headers, and nh3 HTML sanitization"
```

---

## Task 5: Rendering (`render.py`)

**Files:**
- Create: `src/cairn/render.py`
- Test: `tests/test_render.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_render.py`:

```python
from cairn.render import markdown_to_html, Renderer


def test_markdown_converts_basic():
    html = markdown_to_html("# Title\n\nA paragraph.")
    assert "<h1" in html
    assert "<p>A paragraph.</p>" in html


def test_markdown_fenced_code_is_highlighted():
    html = markdown_to_html("```python\nprint('hi')\n```")
    assert 'class="highlight"' in html


def test_renderer_autoescapes_context(tmp_path):
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "t.html").write_text("<p>{{ value }}</p>", encoding="utf-8")
    r = Renderer(tmp_path)
    out = r.render("t.html", value="<script>x</script>")
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_renderer_marks_safe_html(tmp_path):
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "t.html").write_text("{{ body | safe }}", encoding="utf-8")
    r = Renderer(tmp_path)
    out = r.render("t.html", body="<p>ok</p>")
    assert out == "<p>ok</p>"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_render.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cairn.render'`.

- [ ] **Step 3: Implement `render.py`**

Create `src/cairn/render.py`:

```python
from __future__ import annotations

from pathlib import Path

import markdown
from jinja2 import FileSystemLoader, select_autoescape
from jinja2.sandbox import SandboxedEnvironment


def markdown_to_html(text: str) -> str:
    """Convert Markdown to HTML with build-time syntax highlighting (CSS classes)."""
    converter = markdown.Markdown(
        extensions=["fenced_code", "codehilite", "tables", "toc"],
        extension_configs={
            "codehilite": {"guess_lang": False, "css_class": "highlight"}
        },
        output_format="html",
    )
    return converter.convert(text)


class Renderer:
    """Sandboxed, autoescaping Jinja2 environment bound to a theme directory."""

    def __init__(self, theme_dir: str | Path):
        theme_dir = Path(theme_dir)
        self.env = SandboxedEnvironment(
            loader=FileSystemLoader(str(theme_dir / "templates")),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def render(self, template_name: str, **context) -> str:
        return self.env.get_template(template_name).render(**context)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_render.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cairn/render.py tests/test_render.py
git commit -m "feat: markdown rendering with highlighting and sandboxed jinja2"
```

---

## Task 6: Feeds, sitemap, robots (`feeds.py`)

**Files:**
- Create: `src/cairn/feeds.py`
- Test: `tests/test_feeds.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_feeds.py`:

```python
import datetime
import json
import xml.etree.ElementTree as ET

from cairn.config import Config, SiteConfig, BuildConfig
from cairn.content import Content
from cairn.feeds import render_rss, render_json_feed, render_sitemap, render_robots


def cfg(feed_limit=20):
    return Config(
        site=SiteConfig(title="My Site", url="https://e.com/",
                        author="A", description="d"),
        build=BuildConfig(feed_limit=feed_limit),
    )


def posts(n):
    return [
        Content(title=f"Post {i}", slug=f"post-{i}", body="b", source_path=None,
                date=datetime.date(2026, 6, i + 1))
        for i in range(n)
    ]


def test_rss_is_valid_xml_with_items():
    xml = render_rss(posts(3), cfg())
    root = ET.fromstring(xml)
    assert root.tag == "rss"
    items = root.findall("./channel/item")
    assert len(items) == 3
    assert items[0].find("link").text == "https://e.com/post-0/"


def test_rss_respects_feed_limit():
    xml = render_rss(posts(30), cfg(feed_limit=5))
    assert len(ET.fromstring(xml).findall("./channel/item")) == 5


def test_json_feed_is_valid():
    data = json.loads(render_json_feed(posts(2), cfg()))
    assert data["version"].startswith("https://jsonfeed.org/version/1.1")
    assert len(data["items"]) == 2
    assert data["items"][0]["url"] == "https://e.com/post-0/"


def test_sitemap_lists_all_urls():
    xml = render_sitemap(posts(2), cfg())
    root = ET.fromstring(xml)
    locs = [el.text for el in root.iter() if el.tag.endswith("loc")]
    assert "https://e.com/post-0/" in locs


def test_robots_points_to_sitemap():
    text = render_robots(cfg())
    assert "Sitemap: https://e.com/sitemap.xml" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_feeds.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cairn.feeds'`.

- [ ] **Step 3: Implement `feeds.py`**

Create `src/cairn/feeds.py`:

```python
from __future__ import annotations

import json
import xml.etree.ElementTree as ET

from cairn.config import Config
from cairn.content import Content

_SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


def _abs_url(config: Config, slug: str) -> str:
    return f"{config.site.url.rstrip('/')}/{slug}/"


def render_rss(posts: list[Content], config: Config) -> str:
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = config.site.title
    ET.SubElement(channel, "link").text = config.site.url
    ET.SubElement(channel, "description").text = config.site.description
    for post in posts[: config.build.feed_limit]:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = post.title
        link = _abs_url(config, post.slug)
        ET.SubElement(item, "link").text = link
        guid = ET.SubElement(item, "guid")
        guid.text = link
        guid.set("isPermaLink", "true")
        if post.date:
            ET.SubElement(item, "pubDate").text = post.date.strftime(
                "%a, %d %b %Y 00:00:00 +0000"
            )
    return ET.tostring(rss, encoding="unicode", xml_declaration=True)


def render_json_feed(posts: list[Content], config: Config) -> str:
    feed = {
        "version": "https://jsonfeed.org/version/1.1",
        "title": config.site.title,
        "home_page_url": config.site.url,
        "feed_url": f"{config.site.url.rstrip('/')}/feed.json",
        "items": [
            {
                "id": _abs_url(config, post.slug),
                "url": _abs_url(config, post.slug),
                "title": post.title,
                "date_published": post.date.isoformat() if post.date else None,
            }
            for post in posts[: config.build.feed_limit]
        ],
    }
    return json.dumps(feed, indent=2)


def render_sitemap(items: list[Content], config: Config) -> str:
    urlset = ET.Element("urlset", xmlns=_SITEMAP_NS)
    for item in items:
        url = ET.SubElement(urlset, "url")
        ET.SubElement(url, "loc").text = _abs_url(config, item.slug)
        if item.date:
            ET.SubElement(url, "lastmod").text = item.date.isoformat()
    return ET.tostring(urlset, encoding="unicode", xml_declaration=True)


def render_robots(config: Config) -> str:
    sitemap = f"{config.site.url.rstrip('/')}/sitemap.xml"
    return f"User-agent: *\nAllow: /\nSitemap: {sitemap}\n"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_feeds.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cairn/feeds.py tests/test_feeds.py
git commit -m "feat: RSS, JSON Feed, sitemap, and robots generation"
```

---

## Task 7: Default theme (templates + CSS)

**Files:**
- Create: `themes/default/templates/base.html`
- Create: `themes/default/templates/index.html`
- Create: `themes/default/templates/post.html`
- Create: `themes/default/templates/page.html`
- Create: `themes/default/templates/archive.html`
- Create: `themes/default/templates/tag.html`
- Create: `themes/default/static/style.css`
- Test: `tests/test_theme.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_theme.py`:

```python
from pathlib import Path

from cairn.render import Renderer

THEME = Path("themes/default")


def test_base_template_renders_meta_csp_and_title():
    r = Renderer(THEME)
    out = r.render(
        "base.html",
        site={"title": "S", "language": "en", "author": "A"},
        page_title="Home",
        meta_csp='<meta http-equiv="Content-Security-Policy" content="default-src \'none\'">',
        meta_description="desc",
        og_tags="",
        content="<p>body</p>",
    )
    assert "<!DOCTYPE html>" in out
    assert 'lang="en"' in out
    assert "Content-Security-Policy" in out
    assert "<p>body</p>" in out
    assert "<script" not in out


def test_post_template_shows_date():
    r = Renderer(THEME)
    out = r.render(
        "post.html",
        site={"title": "S", "language": "en", "author": "A"},
        page_title="P",
        meta_csp="",
        meta_description="",
        og_tags="",
        post={"title": "P", "date": "2026-06-14", "tags": ["x"]},
        content="<p>hi</p>",
    )
    assert "2026-06-14" in out
    assert "<p>hi</p>" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_theme.py -v`
Expected: FAIL with `jinja2.exceptions.TemplateNotFound: base.html`.

- [ ] **Step 3: Create the templates**

Create `themes/default/templates/base.html`:

```html
<!DOCTYPE html>
<html lang="{{ site.language }}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{{ meta_csp | safe }}
<title>{{ page_title }} &middot; {{ site.title }}</title>
{% if meta_description %}<meta name="description" content="{{ meta_description }}">{% endif %}
{{ og_tags | safe }}
<link rel="stylesheet" href="/style.css">
<link rel="alternate" type="application/rss+xml" href="/feed.xml" title="{{ site.title }}">
</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>
<header class="site-header">
  <a class="site-title" href="/">{{ site.title }}</a>
  <nav><a href="/archive/">Archive</a></nav>
</header>
<main id="main">
{{ content | safe }}
</main>
<footer class="site-footer">
  <p>&copy; {{ site.author }}. Built with Cairn.</p>
</footer>
</body>
</html>
```

Create `themes/default/templates/index.html`:

```html
{% extends "base.html" %}
{% block_unused %}{% endblock_unused %}
```

Replace the body of `index.html` with this content (it composes `base.html` via the `content` variable supplied by the build, so index simply lists posts). Write `index.html` as:

```html
<h1>{{ site.title }}</h1>
<ul class="post-list">
{% for post in posts %}
  <li>
    <a href="/{{ post.slug }}/">{{ post.title }}</a>
    {% if post.date %}<time datetime="{{ post.date }}">{{ post.date }}</time>{% endif %}
  </li>
{% endfor %}
</ul>
```

Create `themes/default/templates/post.html`:

```html
<article class="post">
  <h1>{{ post.title }}</h1>
  {% if post.date %}<time datetime="{{ post.date }}">{{ post.date }}</time>{% endif %}
  {% if post.tags %}
  <ul class="tags">
  {% for tag in post.tags %}<li><a href="/tags/{{ tag }}/">{{ tag }}</a></li>{% endfor %}
  </ul>
  {% endif %}
  <div class="post-body">{{ content | safe }}</div>
</article>
```

Create `themes/default/templates/page.html`:

```html
<article class="page">
  <h1>{{ page.title }}</h1>
  <div class="page-body">{{ content | safe }}</div>
</article>
```

Create `themes/default/templates/archive.html`:

```html
<h1>Archive</h1>
<ul class="archive-list">
{% for post in posts %}
  <li>
    {% if post.date %}<time datetime="{{ post.date }}">{{ post.date }}</time>{% endif %}
    <a href="/{{ post.slug }}/">{{ post.title }}</a>
  </li>
{% endfor %}
</ul>
```

Create `themes/default/templates/tag.html`:

```html
<h1>Posts tagged "{{ tag }}"</h1>
<ul class="post-list">
{% for post in posts %}
  <li><a href="/{{ post.slug }}/">{{ post.title }}</a></li>
{% endfor %}
</ul>
```

**Note for the build:** `index.html`, `post.html`, `page.html`, `archive.html`, and
`tag.html` produce inner HTML. The build renders one of them first, then passes the
result as the `content` variable into `base.html`. The test above renders
`post.html` directly (without `base.html`), so it must stand alone, which it does.

The first `index.html` snippet (`extends base.html`) is incorrect; delete it and use
only the second `index.html` snippet (the post-list fragment).

- [ ] **Step 4: Create the stylesheet**

Create `themes/default/static/style.css`:

```css
:root {
  color-scheme: light dark;
  --bg: #fdfdfb; --fg: #1a1a1a; --muted: #666; --link: #225; --rule: #e2e2dc;
  --font: ui-serif, Georgia, "Times New Roman", serif;
  --mono: ui-monospace, SFMono-Regular, Menlo, monospace;
}
@media (prefers-color-scheme: dark) {
  :root { --bg: #16161a; --fg: #e8e8e6; --muted: #9a9a9a; --link: #9db4ff; --rule: #2a2a30; }
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--fg);
  font-family: var(--font); line-height: 1.6;
  max-width: 42rem; padding: 2rem 1.25rem; margin-inline: auto;
}
a { color: var(--link); }
.skip-link { position: absolute; left: -999px; }
.skip-link:focus { left: 1rem; top: 1rem; }
.site-header { display: flex; justify-content: space-between; align-items: baseline;
  border-bottom: 1px solid var(--rule); padding-bottom: 1rem; margin-bottom: 2rem; }
.site-title { font-weight: 700; text-decoration: none; font-size: 1.25rem; }
.post-list, .archive-list, .tags { list-style: none; padding: 0; }
.post-list time, .archive-list time { color: var(--muted); font-size: .85rem; margin-left: .5rem; }
.tags { display: flex; gap: .5rem; }
time { color: var(--muted); }
pre, code { font-family: var(--mono); }
pre { overflow-x: auto; padding: 1rem; border: 1px solid var(--rule); border-radius: 6px; }
.highlight { background: transparent; }
.site-footer { margin-top: 3rem; border-top: 1px solid var(--rule);
  padding-top: 1rem; color: var(--muted); font-size: .85rem; }
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_theme.py -v`
Expected: PASS. (Ensure `index.html` contains only the post-list fragment.)

- [ ] **Step 6: Commit**

```bash
git add themes/default tests/test_theme.py
git commit -m "feat: default zero-JS theme with light/dark CSS"
```

---

## Task 8: Build pipeline (`build.py`)

**Files:**
- Create: `src/cairn/build.py`
- Test: `tests/test_build.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_build.py`:

```python
import datetime
import textwrap
from pathlib import Path

from cairn.config import Config, SiteConfig, BuildConfig
from cairn.build import build, BuildResult

THEME = Path("themes/default").resolve()


def setup_site(tmp_path):
    content = tmp_path / "content"
    content.mkdir()
    (content / "hello.md").write_text(textwrap.dedent("""
        ---
        title: Hello World
        date: 2026-06-10
        tags: [intro]
        description: First post.
        ---
        # Hello

        Some **bold** text.
    """).lstrip("\n"), encoding="utf-8")
    (content / "about.md").write_text(textwrap.dedent("""
        ---
        title: About
        ---
        About page.
    """).lstrip("\n"), encoding="utf-8")
    return Config(
        site=SiteConfig(title="Test", url="https://e.com",
                        author="A", description="d"),
        build=BuildConfig(
            content_dir=str(content),
            output_dir=str(tmp_path / "public"),
            theme=str(THEME),
        ),
    )


def test_build_emits_expected_files(tmp_path):
    cfg = setup_site(tmp_path)
    result = build(cfg, today=datetime.date(2026, 6, 14))
    out = Path(cfg.build.output_dir)
    assert isinstance(result, BuildResult)
    assert (out / "index.html").exists()
    assert (out / "hello" / "index.html").exists()
    assert (out / "about" / "index.html").exists()
    assert (out / "archive" / "index.html").exists()
    assert (out / "tags" / "intro" / "index.html").exists()
    assert (out / "feed.xml").exists()
    assert (out / "feed.json").exists()
    assert (out / "sitemap.xml").exists()
    assert (out / "robots.txt").exists()
    assert (out / "_headers").exists()
    assert (out / "style.css").exists()


def test_post_page_is_sanitized_and_has_csp(tmp_path):
    cfg = setup_site(tmp_path)
    build(cfg, today=datetime.date(2026, 6, 14))
    html = (Path(cfg.build.output_dir) / "hello" / "index.html").read_text()
    assert "<strong>bold</strong>" in html
    assert "Content-Security-Policy" in html
    assert "<script" not in html


def test_clean_removes_stale_files(tmp_path):
    cfg = setup_site(tmp_path)
    out = Path(cfg.build.output_dir)
    out.mkdir(parents=True)
    (out / "stale.html").write_text("old", encoding="utf-8")
    build(cfg, today=datetime.date(2026, 6, 14), clean=True)
    assert not (out / "stale.html").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_build.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cairn.build'`.

- [ ] **Step 3: Implement `build.py`**

Create `src/cairn/build.py`:

```python
from __future__ import annotations

import datetime
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from cairn.config import Config
from cairn.content import Content, discover, filter_content
from cairn.feeds import render_json_feed, render_robots, render_rss, render_sitemap
from cairn.render import Renderer, markdown_to_html
from cairn.security import headers_file, meta_csp_tag, sanitize


@dataclass
class BuildResult:
    output_dir: Path
    page_count: int = 0
    warnings: list[str] = field(default_factory=list)


def _og_tags(config: Config, title: str, description: str | None) -> str:
    parts = [
        f'<meta property="og:site_name" content="{config.site.title}">',
        f'<meta property="og:title" content="{title}">',
        '<meta name="twitter:card" content="summary">',
    ]
    if description:
        parts.append(f'<meta property="og:description" content="{description}">')
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

    # Tag pages
    tags: dict[str, list[Content]] = {}
    for post in posts:
        for tag in post.tags:
            tags.setdefault(tag, []).append(post)
    for tag, tagged in tags.items():
        inner = renderer.render("tag.html", site=config.site, tag=tag, posts=tagged)
        _write(out / "tags" / tag / "index.html",
               page_shell(f"Tagged {tag}", None, inner))

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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_build.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cairn/build.py tests/test_build.py
git commit -m "feat: build pipeline emitting pages, feeds, and security headers"
```

---

## Task 9: Scaffolding (`scaffold.py`)

**Files:**
- Create: `src/cairn/scaffold.py`
- Test: `tests/test_scaffold.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_scaffold.py`:

```python
import datetime
from pathlib import Path

from cairn.config import load_config
from cairn.content import load_content
from cairn.scaffold import new_site, new_post


def test_new_site_creates_loadable_project(tmp_path):
    new_site(tmp_path)
    cfg = load_config(tmp_path / "site.toml")
    assert cfg.site.title
    assert (tmp_path / "content").is_dir()
    assert list((tmp_path / "content").glob("*.md"))


def test_new_post_creates_loadable_content(tmp_path):
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    path = new_post(content_dir, "My First Post", today=datetime.date(2026, 6, 14))
    assert path == content_dir / "my-first-post.md"
    item = load_content(path)
    assert item.title == "My First Post"
    assert item.date == datetime.date(2026, 6, 14)
    assert item.is_draft is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_scaffold.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cairn.scaffold'`.

- [ ] **Step 3: Implement `scaffold.py`**

Create `src/cairn/scaffold.py`:

```python
from __future__ import annotations

import datetime
from pathlib import Path

from cairn.content import slugify

_SITE_TOML = """\
[site]
title = "My Cairn"
url = "https://example.com"
author = "Your Name"
description = "A small, durable site built with Cairn."
language = "en"

[build]
content_dir = "content"
output_dir = "public"
theme = "default"
feed_limit = 20

[security]
csp = "locked"
referrer_policy = "no-referrer"
sanitize = true
hsts = true

[deploy]
target = "folder"
"""

_SAMPLE_POST = """\
---
title: Hello, Cairn
date: {date}
tags: [meta]
description: The first post on a brand new Cairn site.
---

Welcome to your new site. Edit `content/` and run `cairn build`.
"""

_POST_TEMPLATE = """\
---
title: {title}
date: {date}
tags: []
draft: true
description: ""
---

Write your post here.
"""


def new_site(path: str | Path) -> Path:
    path = Path(path)
    (path / "content").mkdir(parents=True, exist_ok=True)
    (path / "site.toml").write_text(_SITE_TOML, encoding="utf-8")
    today = datetime.date.today().isoformat()
    (path / "content" / "hello-cairn.md").write_text(
        _SAMPLE_POST.format(date=today), encoding="utf-8"
    )
    return path


def new_post(
    content_dir: str | Path, title: str, *, today: datetime.date | None = None
) -> Path:
    content_dir = Path(content_dir)
    content_dir.mkdir(parents=True, exist_ok=True)
    today = today or datetime.date.today()
    path = content_dir / f"{slugify(title)}.md"
    path.write_text(
        _POST_TEMPLATE.format(title=title, date=today.isoformat()), encoding="utf-8"
    )
    return path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_scaffold.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cairn/scaffold.py tests/test_scaffold.py
git commit -m "feat: project and post scaffolding"
```

---

## Task 10: Deploy config emission (`deploy.py`)

**Files:**
- Create: `src/cairn/deploy.py`
- Test: `tests/test_deploy.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_deploy.py`:

```python
from pathlib import Path

from cairn.config import Config, SiteConfig, BuildConfig, DeployConfig
from cairn.deploy import emit


def cfg(tmp_path, target):
    return Config(
        site=SiteConfig(title="t", url="https://e.com", author="a", description="d"),
        build=BuildConfig(output_dir=str(tmp_path / "public")),
        deploy=DeployConfig(target=target),
    )


def test_github_pages_emits_workflow(tmp_path):
    written = emit(cfg(tmp_path, "github-pages"), project_dir=tmp_path)
    workflow = tmp_path / ".github" / "workflows" / "deploy.yml"
    assert workflow in written
    assert workflow.exists()
    assert "actions/deploy-pages" in workflow.read_text()


def test_cloudflare_emits_headers_note(tmp_path):
    written = emit(cfg(tmp_path, "cloudflare"), project_dir=tmp_path)
    assert any(p.name == "_headers" for p in written)


def test_folder_target_emits_nothing(tmp_path):
    written = emit(cfg(tmp_path, "folder"), project_dir=tmp_path)
    assert written == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_deploy.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cairn.deploy'`.

- [ ] **Step 3: Implement `deploy.py`**

Create `src/cairn/deploy.py`:

```python
from __future__ import annotations

from pathlib import Path

from cairn.config import Config
from cairn.security import headers_file

_GH_WORKFLOW = """\
name: Deploy Cairn site to GitHub Pages
on:
  push:
    branches: [main]
permissions:
  contents: read
  pages: write
  id-token: write
jobs:
  build-deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install cairn-ssg
      - run: cairn build
      - uses: actions/upload-pages-artifact@v3
        with:
          path: public
      - id: deployment
        uses: actions/deploy-pages@v4
"""


def emit(config: Config, *, project_dir: str | Path) -> list[Path]:
    """Write deploy configuration for the configured target. Never pushes."""
    project_dir = Path(project_dir)
    written: list[Path] = []
    target = config.deploy.target

    if target == "github-pages":
        workflow = project_dir / ".github" / "workflows" / "deploy.yml"
        workflow.parent.mkdir(parents=True, exist_ok=True)
        workflow.write_text(_GH_WORKFLOW, encoding="utf-8")
        written.append(workflow)
    elif target == "cloudflare":
        out = Path(config.build.output_dir)
        out.mkdir(parents=True, exist_ok=True)
        headers = out / "_headers"
        headers.write_text(headers_file(config), encoding="utf-8")
        written.append(headers)
    # "folder": host-agnostic, nothing extra to emit.

    return written
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_deploy.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cairn/deploy.py tests/test_deploy.py
git commit -m "feat: emit GitHub Pages and Cloudflare deploy config (no push)"
```

---

## Task 11: Content + config checks (`check` in `build.py`)

**Files:**
- Modify: `src/cairn/build.py` (add `check` function at end of file)
- Test: `tests/test_check.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_check.py`:

```python
import textwrap
from pathlib import Path

from cairn.config import Config, SiteConfig, BuildConfig
from cairn.build import check


def cfg(tmp_path):
    content = tmp_path / "content"
    content.mkdir()
    return Config(
        site=SiteConfig(title="t", url="https://e.com", author="a", description="d"),
        build=BuildConfig(content_dir=str(content), output_dir=str(tmp_path / "out")),
    ), content


def test_check_passes_for_valid_content(tmp_path):
    config, content = cfg(tmp_path)
    (content / "ok.md").write_text(
        "---\ntitle: OK\ndate: 2026-06-14\n---\nbody", encoding="utf-8"
    )
    errors = check(config)
    assert errors == []


def test_check_reports_malformed_content(tmp_path):
    config, content = cfg(tmp_path)
    (content / "bad.md").write_text("---\ndate: nope\n---\nbody", encoding="utf-8")
    errors = check(config)
    assert errors
    assert any("bad.md" in e for e in errors)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_check.py -v`
Expected: FAIL with `ImportError: cannot import name 'check'`.

- [ ] **Step 3: Add `check` to `build.py`**

Append to `src/cairn/build.py` (after the `build` function), and add `from cairn.content import ContentError, load_content` to the existing content import line so it reads `from cairn.content import Content, ContentError, discover, filter_content, load_content`:

```python
def check(config: Config) -> list[str]:
    """Validate all content and return a list of error strings (empty == OK)."""
    errors: list[str] = []
    content_dir = Path(config.build.content_dir)
    for path in sorted(content_dir.rglob("*.md")):
        try:
            load_content(path)
        except ContentError as exc:
            errors.append(str(exc))
    return errors
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_check.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cairn/build.py tests/test_check.py
git commit -m "feat: cairn check validates content files"
```

---

## Task 12: Preview server (`serve.py`)

**Files:**
- Create: `src/cairn/serve.py`
- Test: `tests/test_serve.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_serve.py`:

```python
from pathlib import Path

from cairn.serve import make_handler


def test_handler_class_is_bound_to_directory(tmp_path):
    (tmp_path / "index.html").write_text("<p>hi</p>", encoding="utf-8")
    handler_cls = make_handler(tmp_path)
    # SimpleHTTPRequestHandler subclasses accept a `directory` kwarg via partial;
    # make_handler binds it so the class can be used directly by ThreadingHTTPServer.
    assert handler_cls.directory == str(tmp_path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_serve.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cairn.serve'`.

- [ ] **Step 3: Implement `serve.py`**

Create `src/cairn/serve.py`:

```python
from __future__ import annotations

import datetime
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from cairn.build import build
from cairn.config import Config


def make_handler(directory: str | Path) -> type[SimpleHTTPRequestHandler]:
    directory = str(directory)

    class Handler(SimpleHTTPRequestHandler):
        pass

    Handler.directory = directory  # consumed in __init__ below

    def __init__(self, *args, **kwargs):
        SimpleHTTPRequestHandler.__init__(self, *args, directory=directory, **kwargs)

    Handler.__init__ = __init__
    return Handler


def _snapshot(content_dir: Path) -> dict[Path, float]:
    return {p: p.stat().st_mtime for p in content_dir.rglob("*.md")}


def serve(
    config: Config, *, watch: bool = False, port: int = 8000, host: str = "127.0.0.1"
) -> None:  # pragma: no cover - long-running loop
    build(config, today=datetime.date.today())
    handler = make_handler(config.build.output_dir)
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Serving {config.build.output_dir} at http://{host}:{port}")

    if not watch:
        server.serve_forever()
        return

    import threading

    threading.Thread(target=server.serve_forever, daemon=True).start()
    content_dir = Path(config.build.content_dir)
    last = _snapshot(content_dir)
    print("Watching for changes... (Ctrl+C to stop)")
    try:
        while True:
            time.sleep(1)
            current = _snapshot(content_dir)
            if current != last:
                print("Change detected, rebuilding...")
                build(config, today=datetime.date.today())
                last = current
    except KeyboardInterrupt:
        server.shutdown()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_serve.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cairn/serve.py tests/test_serve.py
git commit -m "feat: local preview server with watch-rebuild"
```

---

## Task 13: CLI (`cli.py`)

**Files:**
- Create: `src/cairn/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_cli.py`:

```python
from pathlib import Path

from cairn.cli import main


def test_new_site_then_build(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["new", "site", "."]) == 0
    assert main(["build"]) == 0
    assert (tmp_path / "public" / "index.html").exists()


def test_new_post_creates_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "."])
    assert main(["new", "post", "Second Post"]) == 0
    assert (tmp_path / "content" / "second-post.md").exists()


def test_check_returns_nonzero_on_bad_content(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "."])
    (tmp_path / "content" / "bad.md").write_text(
        "---\ndate: nope\n---\nx", encoding="utf-8"
    )
    assert main(["check"]) == 1


def test_unknown_command_returns_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["bogus"]) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cairn.cli'`.

- [ ] **Step 3: Implement `cli.py`**

Create `src/cairn/cli.py`:

```python
from __future__ import annotations

import argparse
import importlib.resources
import sys
from pathlib import Path

from cairn.build import build, check
from cairn.config import ConfigError, load_config
from cairn.deploy import emit
from cairn.scaffold import new_post, new_site
from cairn.serve import serve

CONFIG_NAME = "site.toml"


def _bundled_default_theme() -> str:
    """Resolve the packaged default theme path (repo layout: themes/default)."""
    repo_theme = Path(__file__).resolve().parents[2] / "themes" / "default"
    return str(repo_theme)


def _load(args) -> "Config":
    cfg = load_config(Path(CONFIG_NAME))
    if cfg.build.theme == "default":
        cfg.build.theme = _bundled_default_theme()
    return cfg


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cairn")
    sub = parser.add_subparsers(dest="command")

    p_new = sub.add_parser("new", help="scaffold a site or post")
    new_sub = p_new.add_subparsers(dest="kind")
    p_new_site = new_sub.add_parser("site")
    p_new_site.add_argument("path", nargs="?", default=".")
    p_new_post = new_sub.add_parser("post")
    p_new_post.add_argument("title")

    p_build = sub.add_parser("build")
    p_build.add_argument("--drafts", action="store_true")
    p_build.add_argument("--future", action="store_true")
    p_build.add_argument("--clean", action="store_true")

    p_serve = sub.add_parser("serve")
    p_serve.add_argument("--watch", action="store_true")
    p_serve.add_argument("--port", type=int, default=8000)

    sub.add_parser("check")

    p_deploy = sub.add_parser("deploy")
    p_deploy.add_argument("target", nargs="?")

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 2

    try:
        if args.command == "new":
            if args.kind == "site":
                new_site(args.path)
                print(f"Created a new Cairn site in {args.path}")
                return 0
            if args.kind == "post":
                cfg = _load(args)
                path = new_post(cfg.build.content_dir, args.title)
                print(f"Created {path}")
                return 0
            p_new.print_help()
            return 2

        if args.command == "build":
            cfg = _load(args)
            result = build(cfg, drafts=args.drafts, future=args.future,
                           clean=args.clean)
            print(f"Built {result.page_count} pages into {result.output_dir}")
            return 0

        if args.command == "serve":
            cfg = _load(args)
            serve(cfg, watch=args.watch, port=args.port)
            return 0

        if args.command == "check":
            cfg = _load(args)
            errors = check(cfg)
            if errors:
                for err in errors:
                    print(f"error: {err}", file=sys.stderr)
                return 1
            print("All content valid.")
            return 0

        if args.command == "deploy":
            cfg = _load(args)
            target = args.target or cfg.deploy.target
            cfg.deploy.target = target
            written = emit(cfg, project_dir=".")
            if written:
                for path in written:
                    print(f"Wrote {path}")
            else:
                print("Folder target: deploy the output directory however you like.")
            return 0
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 1

    parser.print_help()
    return 2
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cli.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cairn/cli.py tests/test_cli.py
git commit -m "feat: cairn CLI (new, build, serve, check, deploy)"
```

---

## Task 14: End-to-end golden build + README

**Files:**
- Create: `tests/test_e2e.py`
- Create: `README.md`

- [ ] **Step 1: Write the end-to-end test**

Create `tests/test_e2e.py`:

```python
import datetime
import subprocess
import sys
from pathlib import Path

from cairn.cli import main


def test_full_site_lifecycle(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["new", "site", "."]) == 0
    assert main(["new", "post", "A Second Post"]) == 0
    assert main(["check"]) == 0
    # The new post is a draft; build without --drafts excludes it.
    assert main(["build"]) == 0
    out = tmp_path / "public"
    index = (out / "index.html").read_text()
    assert "hello-cairn" in index
    assert "a-second-post" not in index
    # Building with --drafts includes it.
    assert main(["build", "--drafts", "--clean"]) == 0
    assert "a-second-post" in (out / "index.html").read_text()
    # Security artifacts present.
    assert "Content-Security-Policy" in (out / "_headers").read_text()
    assert (out / "feed.xml").exists()


def test_full_test_suite_passes():
    # Sanity: the whole suite runs green from a clean invocation.
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q",
         "--ignore", str(Path("tests") / "test_e2e.py")],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
```

- [ ] **Step 2: Run test to verify it fails (or passes if all prior tasks done)**

Run: `python -m pytest tests/test_e2e.py::test_full_site_lifecycle -v`
Expected: PASS if Tasks 1-13 complete. If it fails, fix the offending module before continuing.

- [ ] **Step 3: Write the README**

Create `README.md`:

```markdown
# Cairn

A minimal, security-first static site generator. Markdown in, fast zero-JavaScript
HTML out, with a locked-down Content Security Policy by default.

Cairn is a spiritual successor to [Pueblo](https://github.com/clorth0/Pueblo):
same "spend less time maintaining, more time writing" ethos, with a real
authoring workflow and a deliberate security posture.

## Install

    pipx install cairn-ssg

This provides the `cairn` command.

## Quick start

    cairn new site myblog
    cd myblog
    cairn new post "Hello World"
    cairn build
    cairn serve --watch

`cairn build` writes a static site to `public/`. `cairn serve --watch` previews it
locally and rebuilds on change.

## Configuration

A site is configured with a declarative `site.toml` (data only, never executed).
See `[site]`, `[build]`, `[security]`, and `[deploy]` sections.

## Security

- Zero JavaScript in output by default.
- Locked CSP: `default-src 'none'` with a small `self` allowlist.
- Rendered HTML is sanitized with `nh3`.
- Per-host header delivery: Cloudflare `_headers`, GitHub Pages `<meta>` fallback,
  or a host-agnostic folder with a documented header table.

## Deploy targets

`cairn deploy github-pages` writes a GitHub Actions workflow. `cairn deploy
cloudflare` writes a `_headers` file. The `folder` target emits nothing extra;
deploy `public/` however you like. Cairn never pushes for you or handles
credentials.

## License

MIT.
```

- [ ] **Step 4: Run the full suite**

Run: `python -m pytest -v`
Expected: PASS (all tests across all modules).

- [ ] **Step 5: Commit**

```bash
git add tests/test_e2e.py README.md
git commit -m "test: end-to-end site lifecycle; docs: add README"
```

---

## Self-Review Notes

- **Spec coverage:** config (Task 2), content model + drafts/tags/scheduled (Task 3),
  security/CSP/sanitize/headers (Task 4), render + highlighting + sandbox (Task 5),
  feeds/sitemap/robots (Task 6), theme zero-JS light/dark (Task 7), build pipeline +
  OG/meta (Task 8), scaffolding `new` (Task 9), deploy emit (Task 10), `check`
  (Task 11), serve + watch (Task 12), CLI (Task 13), e2e + README (Task 14). All v1
  spec sections map to a task.
- **Theme note:** the `index.html` template must contain only the post-list fragment
  (Task 7, Step 3); the `extends base.html` snippet shown first is explicitly
  discarded because the build composes `base.html` separately via the `content`
  variable.
- **Type consistency:** `Content`, `Config` (and nested `SiteConfig`/`BuildConfig`/
  `SecurityConfig`/`DeployConfig`), `BuildResult`, `Renderer.render`, `build()`,
  `check()`, `emit()`, `new_site()`, `new_post()`, `sanitize()`, `build_csp()`,
  `headers_file()`, `meta_csp_tag()` are used with identical signatures across tasks.
- **XML safety:** `feeds.py` only *serializes* XML via `ElementTree` (building
  `feed.xml`/`sitemap.xml` from Cairn's own data); it never *parses* untrusted XML,
  so there is no XXE or billion-laughs surface. Content input is Markdown plus YAML
  parsed with `yaml.safe_load`. The only `ET.fromstring` calls live in tests, parsing
  Cairn's own trusted output. Implementers must NOT add untrusted XML parsing; if a
  future feature ever needs to parse external XML, use `defusedxml`.
- **Backlog (not in this plan):** incremental hashed builds, automated SBOM/signed
  releases, multi-theme ecosystem, pagination/related-posts, opt-in search,
  Vercel/Netlify targets, image optimization.
```
