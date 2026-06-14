from pathlib import Path

from cairn.cli import main


def test_new_site_then_build(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["new", "site", "."]) == 0
    assert main(["build"]) == 0
    assert (tmp_path / "public" / "index.html").exists()


def test_new_post_creates_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "."])
    assert main(["new", "post", "Second Post"]) == 0
    assert (tmp_path / "content" / "second-post.md").exists()


def test_check_returns_nonzero_on_bad_content(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    main(["new", "site", "."])
    (tmp_path / "content" / "bad.md").write_text(
        "---\ndate: nope\n---\nx", encoding="utf-8"
    )
    assert main(["check"]) == 1


def test_unknown_command_returns_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["bogus"]) == 2
