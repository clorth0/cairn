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
