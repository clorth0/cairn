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


def test_unknown_key_raises(tmp_path):
    path = write(tmp_path, """
        [site]
        title = "t"
        url = "https://example.com"
        author = "a"
        description = "d"
        bogus = "x"
    """)
    with pytest.raises(ConfigError):
        load_config(path)


def test_negative_feed_limit_raises(tmp_path):
    path = write(tmp_path, """
        [site]
        title = "t"
        url = "https://example.com"
        author = "a"
        description = "d"
        [build]
        feed_limit = -5
    """)
    with pytest.raises(ConfigError):
        load_config(path)
