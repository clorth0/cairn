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


def test_check_reports_image_without_alt(tmp_path):
    config, content = cfg(tmp_path)
    (content / "noalt.md").write_text(
        '---\ntitle: NoAlt\n---\n<img src="x.png">\n', encoding="utf-8"
    )
    errors = check(config)
    assert any("alt" in e for e in errors)


def test_check_reports_malformed_content(tmp_path):
    config, content = cfg(tmp_path)
    (content / "bad.md").write_text("---\ndate: nope\n---\nbody", encoding="utf-8")
    errors = check(config)
    assert errors
    assert any("bad.md" in e for e in errors)
