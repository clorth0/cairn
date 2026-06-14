from pathlib import Path

from cairn.render import Renderer

THEME = Path("src/cairn/themes/default")


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
