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


def _content_attributes() -> dict[str, set[str]]:
    """nh3's default allowed attributes, plus `class` on code/formatting tags.

    Allowing `class` lets build-time Pygments highlighting survive sanitization.
    It is safe under Cairn's locked CSP (no scripts, no external/inline styles):
    a class attribute cannot execute code or load resources.
    """
    try:
        base = {tag: set(attrs) for tag, attrs in nh3.ALLOWED_ATTRIBUTES.items()}
    except AttributeError:  # pragma: no cover - older nh3 without the constant
        base = {"a": {"href", "title"}, "img": {"src", "alt", "title"}}
    for tag in ("code", "pre", "span", "div", "table", "thead", "tbody", "tr", "th", "td"):
        base.setdefault(tag, set()).add("class")
    return base


_CONTENT_ATTRIBUTES = _content_attributes()


def sanitize(html: str, allowed_tags: set[str] | None = None) -> str:
    """Strip dangerous markup from rendered HTML using nh3.

    Uses nh3's safe tag allowlist and url-scheme filtering (so `javascript:`
    URLs and event handlers are still removed), but permits `class` on
    code/formatting tags so Pygments syntax highlighting survives.
    """
    if allowed_tags is not None:
        return nh3.clean(html, tags=allowed_tags)
    return nh3.clean(html, attributes=_CONTENT_ATTRIBUTES)


def build_csp(security: SecurityConfig) -> str:
    if security.csp.strip().lower() == "locked":
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


def security_advisories(config: Config) -> list[str]:
    """Non-fatal warnings about a weakened security posture.

    Surfaced by `cairn check`. These flag deliberate-choice downgrades, not
    errors, so they never fail the build; they just make the trade-off visible.
    """
    notes: list[str] = []
    sec = config.security
    if not sec.sanitize:
        notes.append(
            "HTML sanitization is disabled (security.sanitize = false); "
            "raw HTML in content will be emitted unsanitized."
        )
    if build_csp(sec) != LOCKED_CSP:
        notes.append(
            "Content-Security-Policy is not the locked preset; "
            "verify your custom CSP is sufficiently restrictive."
        )
    return notes
