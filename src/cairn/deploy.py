from __future__ import annotations

from pathlib import Path

from cairn.config import Config
from cairn.security import headers_file

_GH_WORKFLOW = """\
name: Deploy Cairn site to GitHub Pages
on:
  push:
    branches: [main]
permissions:
  contents: read
  pages: write
  id-token: write
jobs:
  build-deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install cairn-ssg
      - run: cairn build
      - uses: actions/upload-pages-artifact@v3
        with:
          path: public
      - id: deployment
        uses: actions/deploy-pages@v4
"""


def emit(config: Config, *, project_dir: str | Path) -> list[Path]:
    """Write deploy configuration for the configured target. Never pushes."""
    project_dir = Path(project_dir)
    written: list[Path] = []
    target = config.deploy.target

    if target == "github-pages":
        workflow = project_dir / ".github" / "workflows" / "deploy.yml"
        workflow.parent.mkdir(parents=True, exist_ok=True)
        workflow.write_text(_GH_WORKFLOW, encoding="utf-8")
        written.append(workflow)
    elif target == "cloudflare":
        out = Path(config.build.output_dir)
        out.mkdir(parents=True, exist_ok=True)
        headers = out / "_headers"
        headers.write_text(headers_file(config), encoding="utf-8")
        written.append(headers)
    # "folder": host-agnostic, nothing extra to emit.

    return written
