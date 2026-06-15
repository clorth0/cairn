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


def test_new_post_with_special_chars_is_loadable(tmp_path):
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    path = new_post(content_dir, 'Tricky: A "Quoted" Title',
                    today=datetime.date(2026, 6, 14))
    item = load_content(path)
    assert item.title == 'Tricky: A "Quoted" Title'
    assert item.date == datetime.date(2026, 6, 14)
