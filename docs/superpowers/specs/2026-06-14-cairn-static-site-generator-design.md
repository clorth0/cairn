# Cairn: Design Specification

Date: 2026-06-14
Status: Approved (pending user review of this document)

## 1. Summary

Cairn is a minimal, security-first static site generator written in Python. It
is a spiritual successor to Pueblo (clorth0/Pueblo, itself derived from Mike
Shea's tool): Markdown in, fast static HTML out, no server, no client-side
JavaScript by default. Cairn keeps Pueblo's "thousand year blog" ethos (speed,
longevity, no attack surface) while adding a real content authoring workflow,
modern output (feeds, sitemap, social metadata, accessibility), and a deliberate
security model centered on a locked-down Content Security Policy.

The name evokes a stack of stones marking a path: a durable, minimal, human-made
marker meant to outlast its builder.

### Goals

- A reusable open-source tool that strangers can install, trust, and adopt.
- Minimal by design: small focused modules, short pinned dependency list, zero
  client JavaScript in generated output by default.
- Strong, honest security story: locked CSP, sanitized content, no arbitrary
  code execution at build time, no embedded credentials.
- Good authoring DX: YAML frontmatter, drafts, tags, scheduled posts, scaffolding
  commands, and a local preview server with rebuild-on-change.
- Modern static output: RSS, JSON Feed, sitemap, robots, Open Graph metadata,
  semantic accessible HTML5, build-time syntax highlighting, light/dark theming.

### Non-goals (v1)

- No comments, no plugin system, no databases, no admin UI.
- No client-side search, no client JavaScript framework, no web fonts by default.
- No remote push automation or credential handling in the deploy command.
- Not a wrapper over Pelican/MkDocs/Hugo; Cairn owns its small pipeline.

## 2. Distribution and naming

- Brand and GitHub repository: `cairn` (under clorth0).
- CLI command: `cairn`.
- PyPI distribution name: `cairn-ssg` (the bare `cairn` name is held by an
  abandoned 2019 version-management package; `pipx install cairn-ssg` installs
  the `cairn` command). The console-script entry point name is independent of
  the distribution name.
- License: MIT (matching Pueblo's lineage).
- Python support: 3.11+ (relies on stdlib `tomllib`).

## 3. Architecture

A proper installable Python package. Each module has one purpose, a clear
interface, and is testable in isolation.

```
cairn/
  pyproject.toml          # PEP 621 metadata, pinned deps, console_scripts entry point
  README.md
  LICENSE
  requirements.lock       # pinned, hashed dependency set for reproducible installs
  src/cairn/
    __init__.py
    config.py             # load + validate site.toml -> Config dataclass
    content.py            # discover .md, parse YAML frontmatter, Page/Post models
    render.py             # Jinja2 (autoescape + SandboxedEnvironment), highlighting
    feeds.py              # RSS 2.0 + JSON Feed + sitemap.xml + robots.txt
    security.py           # CSP builder, _headers writer, <meta> fallback, sanitization
    build.py              # pipeline orchestration: clean->load->parse->render->emit
    serve.py              # stdlib preview server + --watch rebuild
    deploy.py             # emit GitHub Pages workflow / Cloudflare _headers config
    cli.py                # argument parsing: new | build | serve | check | deploy
  themes/
    default/              # Jinja2 templates + minimal CSS, zero JS, light/dark
      templates/
        base.html
        index.html
        post.html
        page.html
        archive.html
        tag.html
      static/
        style.css
  tests/
  docs/
```

### Module responsibilities and interfaces

- `config.py`: `load_config(path) -> Config`. Parses and validates `site.toml`
  into a typed `Config` dataclass. Rejects unknown keys and invalid values with
  clear messages. No code execution (data only).
- `content.py`: `discover(content_dir) -> list[Source]`, then
  `parse(source) -> Page | Post`. Splits YAML frontmatter from Markdown body,
  validates required fields, computes slug, classifies as Page (standalone) or
  Post (dated; participates in feeds/archive/tags). Applies draft and
  future-date filtering based on build flags.
- `render.py`: `Renderer(config, theme)` exposing `render(item, context) -> str`.
  Wraps a Jinja2 `SandboxedEnvironment` with autoescape on. Converts Markdown to
  HTML and applies Pygments highlighting at build time (CSS classes, no runtime
  JS). Hands HTML to `security.sanitize` before templating into pages.
- `feeds.py`: `build_feeds(posts, config) -> dict[path, bytes]`. Produces RSS
  2.0, JSON Feed 1.1, `sitemap.xml`, and `robots.txt`. XML built with a safe
  serializer (no untrusted entity expansion).
- `security.py`: `csp_header(config) -> str`, `write_headers(output, config)`,
  `meta_csp_tag(config) -> str`, `sanitize(html, policy) -> str`. Owns the
  security posture described in section 6.
- `build.py`: `build(config, *, drafts, future, clean) -> BuildResult`. The
  orchestrator: clean output, load content, render pages, generate feeds and
  sitemap, write security artifacts, copy theme/static assets. Returns a summary
  (counts, warnings) for the CLI and tests.
- `serve.py`: `serve(config, *, watch)`. A stdlib `http.server` bound to
  localhost serving the output directory; with `--watch`, polls source mtimes
  and rebuilds on change. Local preview only; not a production server.
- `deploy.py`: `emit(config, target)`. Writes deploy configuration for the chosen
  target (GitHub Pages Actions workflow, Cloudflare `_headers`). Emits files
  only; never pushes and never handles credentials.
- `cli.py`: argument parsing and command dispatch; thin layer over the modules.

## 4. Content model

- Content lives under `content/` as `**/*.md` with YAML frontmatter:

```markdown
---
title: A Durable Marker
date: 2026-06-14
tags: [meta, design]
draft: false
description: Short summary used for meta and Open Graph tags.
slug: durable-marker   # optional; defaults to a slug derived from the filename
---

Body in Markdown. Raw HTML is sanitized on output.
```

- Posts have a `date` and participate in the index, archive, tag pages, and
  feeds. Pages omit `date` and render standalone (for example an About page).
- `draft: true` items are excluded from builds unless `--drafts` is passed.
- Future-dated posts are excluded unless `--future` is passed (this is the
  "scheduled posts" feature: publish by building after the date passes).
- Slugs come from `slug:` if present, else a normalized form of the filename.
- Required frontmatter: `title` (and `date` for posts). Missing or malformed
  frontmatter is a `cairn check` error and a build warning.

## 5. Configuration (`site.toml`)

Declarative configuration, parsed as data via stdlib `tomllib`. No executable
Python config file (this removes Pueblo's arbitrary-code-on-build risk).

```toml
[site]
title = "My Cairn"
url = "https://example.com"
author = "Author Name"
description = "A small, durable site."
language = "en"

[build]
content_dir = "content"
output_dir = "public"
theme = "default"
feed_limit = 20

[security]
csp = "locked"                 # "locked" preset, or a custom CSP string
referrer_policy = "no-referrer"
sanitize = true                # run rendered HTML through the nh3 allowlist
hsts = true                    # emitted only for header-capable hosts

[deploy]
target = "folder"              # folder | github-pages | cloudflare
```

## 6. Security model

The headline feature. Zero-JS output enables a maximally restrictive policy.

### Content Security Policy

The `locked` preset emits:

```
default-src 'none'; img-src 'self'; style-src 'self'; font-src 'self';
base-uri 'none'; form-action 'none'; frame-ancestors 'none'
```

Additional response headers on header-capable hosts: `X-Content-Type-Options:
nosniff`, `Referrer-Policy: no-referrer`, a deny-all `Permissions-Policy`, and
`Strict-Transport-Security` (when `hsts = true`).

### Per-host delivery

- Cloudflare Pages: write a `_headers` file into the output with the full header
  set (preferred path; all directives honored).
- GitHub Pages: cannot set custom HTTP headers, so inject a
  `<meta http-equiv="Content-Security-Policy">` fallback into every page.
  Documented caveat: `frame-ancestors` and `Strict-Transport-Security` are
  ignored when delivered via meta tag.
- Folder (host-agnostic default): write `_headers`, inject the meta fallback,
  and print a header reference table so the operator can configure any host.

### Content sanitization

Markdown may contain raw HTML. When `sanitize = true` (default), rendered HTML is
passed through `nh3` (Rust-backed Ammonia bindings) with a safe allowlist that
strips `<script>`, inline event handlers, `<iframe>`, `javascript:` URLs, and
similar vectors. The allowlist is configurable for authors who need more tags.

### Build-time and supply-chain hygiene

- Templating uses Jinja2 with autoescape enabled and a `SandboxedEnvironment`.
- Configuration is data (`tomllib`), never executed.
- Dependencies are pinned with hashes in `requirements.lock` for reproducible
  installs. The set is intentionally short: `markdown`, `jinja2`, `pygments`,
  `PyYAML`, `nh3`.
- No web fonts by default (system font stack), so no third-party fetch and a
  tighter CSP.
- `cairn check` validates content and security configuration before publish.
- Automated SBOM generation and signed releases are noted for the backlog.

## 7. CLI

```
cairn new site [path]          # scaffold a project: site.toml, theme, sample content
cairn new post "Title"         # scaffold a frontmatter-stamped Markdown file
cairn build [--drafts] [--future] [--clean]
cairn serve [--watch]          # local preview at http://localhost:<port>
cairn check                    # lint content + validate security config
cairn deploy <target>          # emit deploy config only (no push, no credentials)
```

`cairn deploy` writes artifacts (a GitHub Pages Actions workflow, or a Cloudflare
`_headers` file) and then prints next steps. The actual publish uses the host's
own mechanism (git push, Cloudflare connect). This keeps Cairn free of secrets
and side effects.

## 8. Output and theming

- Generated pages: index (recent posts), per-post pages, a dated archive, and
  per-tag index pages, plus any standalone pages.
- Feeds and discovery: RSS 2.0, JSON Feed 1.1, `sitemap.xml`, `robots.txt`.
- Metadata: per-page `<meta name="description">`, Open Graph, and Twitter card
  tags populated from frontmatter.
- Markup: semantic HTML5 with a skip link, landmark regions, and enforced image
  alt text (checked by `cairn check`).
- Default theme: minimal CSS, system font stack, light/dark via
  `prefers-color-scheme`, zero JavaScript. Pygments highlighting via CSS classes.
- Theming: templates and CSS in `themes/default/` are overridable; a site can
  point `[build].theme` at its own theme directory.

## 9. Build pipeline

`build()` runs these stages in order:

1. Clean the output directory (when `--clean`).
2. Load and validate `site.toml`.
3. Discover content; parse frontmatter and body; apply draft/future filters.
4. Render pages, posts, archive, and tag pages (Markdown to HTML, highlight,
   sanitize, template).
5. Generate feeds, sitemap, and robots.
6. Write security artifacts (`_headers`, meta fallback already inlined).
7. Copy theme static assets into the output.

v1 performs a full rebuild on each invocation; `serve --watch` polls source
mtimes and triggers a rebuild. Incremental hashed builds are in the backlog.

## 10. Testing

pytest, unit tests per module plus an end-to-end golden build:

- `config`: valid/invalid TOML, unknown keys, type errors.
- `content`: frontmatter parsing including malformed input, slug derivation,
  draft/future filtering, page vs post classification.
- `render`: Markdown-to-HTML correctness, highlighting output, autoescaping.
- `security`: CSP string generation for presets and custom values; sanitizer
  tested against an XSS payload corpus (script tags, event handlers, javascript:
  URLs, malformed markup); `_headers` and meta tag content.
- `feeds`: RSS and JSON Feed validity, sitemap well-formedness, feed_limit.
- end-to-end: build a sample site into a temp dir and assert against golden
  output (page set, feed presence, header files).

## 11. Dependencies

Pinned with hashes in `requirements.lock`:

- `markdown` (Markdown to HTML)
- `jinja2` (templating; sandboxed, autoescaped)
- `pygments` (build-time syntax highlighting)
- `PyYAML` (frontmatter parsing)
- `nh3` (HTML sanitization, Ammonia bindings)

Standard library: `tomllib` (config), `http.server` (preview), `xml`/manual
serialization for feeds.

## 12. Scope

### v1 (this specification)

Config (TOML), content (Markdown + YAML frontmatter, drafts, tags, scheduled
posts), render with build-time highlighting, feeds (RSS + JSON Feed + sitemap +
robots), per-page metadata and Open Graph, the full security model (locked CSP,
`_headers`, meta fallback, sanitization), the default zero-JS light/dark theme,
the CLI (`new`, `build`, `serve --watch`, `check`, `deploy`), first-class
support for GitHub Pages, Cloudflare Pages, and folder output, the test suite,
and quickstart documentation.

### Backlog (deferred, named)

Incremental hashed builds; automated SBOM and signed releases; a multi-theme
ecosystem; pagination and related-posts; opt-in client-side search; Vercel and
Netlify deploy targets; image optimization.

## 13. Risks and open questions

- `nh3` is a compiled (Rust) wheel. It ships prebuilt wheels for common
  platforms, so this is acceptable; if a target platform lacks a wheel, `bleach`
  is the pure-Python fallback. Decide at implementation time whether to make the
  sanitizer pluggable.
- The GitHub Pages meta-CSP fallback cannot enforce `frame-ancestors` or HSTS.
  This is documented as a known limitation of that host, not a Cairn defect.
- `serve --watch` uses mtime polling to avoid an extra dependency (`watchfiles`).
  If polling proves inadequate, revisit in the backlog.
