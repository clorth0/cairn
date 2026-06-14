from __future__ import annotations

from pathlib import Path

import markdown
from jinja2 import FileSystemLoader, select_autoescape
from jinja2.sandbox import SandboxedEnvironment


def markdown_to_html(text: str) -> str:
    """Convert Markdown to HTML with build-time syntax highlighting (CSS classes).

    The output may contain raw HTML present in the source Markdown. Callers MUST
    pass this through ``security.sanitize()`` before marking it safe in a template.
    """
    converter = markdown.Markdown(
        extensions=["fenced_code", "codehilite", "tables", "toc"],
        extension_configs={
            "codehilite": {"guess_lang": False, "css_class": "highlight"}
        },
        output_format="html",
    )
    return converter.convert(text)


class Renderer:
    """Sandboxed, autoescaping Jinja2 environment bound to a theme directory."""

    def __init__(self, theme_dir: str | Path):
        theme_dir = Path(theme_dir)
        self.env = SandboxedEnvironment(
            loader=FileSystemLoader(str(theme_dir / "templates")),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def render(self, template_name: str, **context) -> str:
        return self.env.get_template(template_name).render(**context)
