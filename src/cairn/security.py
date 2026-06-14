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
