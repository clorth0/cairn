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
