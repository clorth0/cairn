import datetime
import subprocess
import sys
from pathlib import Path

from cairn.cli import main


def test_full_site_lifecycle(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["new", "site", "."]) == 0
    assert main(["new", "post", "A Second Post"]) == 0
    assert main(["check"]) == 0
    # The new post is a draft; build without --drafts excludes it.
    assert main(["build"]) == 0
    out = tmp_path / "public"
    index = (out / "index.html").read_text()
    assert "hello-cairn" in index
    assert "a-second-post" not in index
    # Building with --drafts includes it.
    assert main(["build", "--drafts", "--clean"]) == 0
    assert "a-second-post" in (out / "index.html").read_text()
    # Security artifacts present.
    assert "Content-Security-Policy" in (out / "_headers").read_text()
    assert (out / "feed.xml").exists()


def test_full_test_suite_passes():
    # Sanity: the whole suite runs green from a clean invocation.
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q",
         "--ignore", str(Path("tests") / "test_e2e.py")],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
