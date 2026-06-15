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
