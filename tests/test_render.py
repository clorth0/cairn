from cairn.render import markdown_to_html, Renderer


def test_markdown_converts_basic():
    html = markdown_to_html("# Title\n\nA paragraph.")
    assert "<h1" in html
    assert "<p>A paragraph.</p>" in html


def test_markdown_fenced_code_is_highlighted():
    html = markdown_to_html("```python\nprint('hi')\n```")
    assert 'class="highlight"' in html


def test_renderer_autoescapes_context(tmp_path):
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "t.html").write_text("<p>{{ value }}</p>", encoding="utf-8")
    r = Renderer(tmp_path)
    out = r.render("t.html", value="<script>x</script>")
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_renderer_marks_safe_html(tmp_path):
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "t.html").write_text("{{ body | safe }}", encoding="utf-8")
    r = Renderer(tmp_path)
    out = r.render("t.html", body="<p>ok</p>")
    assert out == "<p>ok</p>"
