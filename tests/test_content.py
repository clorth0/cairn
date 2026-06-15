import datetime
import textwrap
import pytest
from cairn.content import (
    Content,
    ContentError,
    parse_frontmatter,
    slugify,
    load_content,
    discover,
    filter_content,
)


def make(tmp_path, name, body):
    p = tmp_path / name
    p.write_text(textwrap.dedent(body).lstrip("\n"), encoding="utf-8")
    return p


def test_slugify_normalizes():
    assert slugify("A Durable Marker!") == "a-durable-marker"
    assert slugify("  spaced  out  ") == "spaced-out"
    assert slugify("") == "untitled"


def test_parse_frontmatter_splits_meta_and_body():
    meta, body = parse_frontmatter("---\ntitle: Hi\n---\nHello body\n")
    assert meta == {"title": "Hi"}
    assert body.strip() == "Hello body"


def test_parse_frontmatter_without_block_returns_empty_meta():
    meta, body = parse_frontmatter("no frontmatter here")
    assert meta == {}
    assert body == "no frontmatter here"


def test_parse_frontmatter_non_mapping_raises():
    with pytest.raises(ContentError):
        parse_frontmatter("---\n- just\n- a\n- list\n---\nbody")


def test_load_post_with_date_is_post(tmp_path):
    p = make(tmp_path, "hello.md", """
        ---
        title: Hello
        date: 2026-06-14
        tags: [meta, design]
        description: A summary.
        ---
        Body text.
    """)
    c = load_content(p)
    assert c.title == "Hello"
    assert c.slug == "hello"
    assert c.date == datetime.date(2026, 6, 14)
    assert c.tags == ["meta", "design"]
    assert c.is_post is True


def test_load_page_without_date_is_not_post(tmp_path):
    p = make(tmp_path, "about.md", """
        ---
        title: About
        ---
        Who I am.
    """)
    c = load_content(p)
    assert c.is_post is False
    assert c.slug == "about"


def test_missing_title_raises(tmp_path):
    p = make(tmp_path, "bad.md", """
        ---
        date: 2026-06-14
        ---
        no title
    """)
    with pytest.raises(ContentError):
        load_content(p)


def test_bad_date_raises(tmp_path):
    p = make(tmp_path, "bad.md", """
        ---
        title: Bad
        date: not-a-date
        ---
        body
    """)
    with pytest.raises(ContentError):
        load_content(p)


def test_explicit_slug_overrides_filename(tmp_path):
    p = make(tmp_path, "whatever.md", """
        ---
        title: T
        slug: custom-slug
        ---
        body
    """)
    assert load_content(p).slug == "custom-slug"


def test_discover_finds_markdown_recursively(tmp_path):
    (tmp_path / "sub").mkdir()
    make(tmp_path, "a.md", "---\ntitle: A\n---\nx")
    make(tmp_path, "sub/b.md", "---\ntitle: B\n---\ny")
    make(tmp_path, "ignore.txt", "not markdown")
    items = discover(tmp_path)
    assert {c.title for c in items} == {"A", "B"}


def test_datetime_frontmatter_is_coerced_to_date(tmp_path):
    p = make(tmp_path, "ts.md", """
        ---
        title: Stamped
        date: 2026-06-14 12:30:00
        ---
        body
    """)
    c = load_content(p)
    assert c.date == datetime.date(2026, 6, 14)
    assert type(c.date) is datetime.date


def test_malicious_slug_is_sanitized(tmp_path):
    p = make(tmp_path, "evil.md", """
        ---
        title: Evil
        slug: ../../../etc/passwd
        ---
        body
    """)
    c = load_content(p)
    assert "/" not in c.slug
    assert ".." not in c.slug


def test_filter_excludes_drafts_and_future_by_default():
    today = datetime.date(2026, 6, 14)
    items = [
        Content(title="Pub", slug="pub", body="", source_path=None,
                date=datetime.date(2026, 6, 1)),
        Content(title="Draft", slug="draft", body="", source_path=None,
                date=today, is_draft=True),
        Content(title="Future", slug="future", body="", source_path=None,
                date=datetime.date(2026, 7, 1)),
    ]
    kept = filter_content(items, drafts=False, future=False, today=today)
    assert {c.title for c in kept} == {"Pub"}
    kept_all = filter_content(items, drafts=True, future=True, today=today)
    assert {c.title for c in kept_all} == {"Pub", "Draft", "Future"}
