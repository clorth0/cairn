from __future__ import annotations

import datetime
import yaml
from pathlib import Path

from cairn.content import slugify

_SITE_TOML = """\
[site]
title = "My Cairn"
url = "https://example.com"
author = "Your Name"
description = "A small, durable site built with Cairn."
language = "en"

[build]
content_dir = "content"
output_dir = "public"
theme = "default"
feed_limit = 20

[security]
csp = "locked"
referrer_policy = "no-referrer"
sanitize = true
hsts = true

[deploy]
target = "folder"
"""

_SAMPLE_POST = """\
---
title: Hello, Cairn
date: {date}
tags: [meta]
description: The first post on a brand new Cairn site.
---

Welcome to your new site. Edit `content/` and run `cairn build`.
"""

_POST_TEMPLATE = """\
---
{title_line}
date: {date}
tags: []
draft: true
description: ""
---

Write your post here.
"""


def new_site(path: str | Path) -> Path:
    path = Path(path)
    (path / "content").mkdir(parents=True, exist_ok=True)
    (path / "site.toml").write_text(_SITE_TOML, encoding="utf-8")
    today = datetime.date.today().isoformat()
    (path / "content" / "hello-cairn.md").write_text(
        _SAMPLE_POST.format(date=today), encoding="utf-8"
    )
    return path


def new_post(
    content_dir: str | Path, title: str, *, today: datetime.date | None = None
) -> Path:
    content_dir = Path(content_dir)
    content_dir.mkdir(parents=True, exist_ok=True)
    today = today or datetime.date.today()
    path = content_dir / f"{slugify(title)}.md"
    title_line = yaml.safe_dump(
        {"title": title}, default_flow_style=False, allow_unicode=True
    ).strip()
    path.write_text(
        _POST_TEMPLATE.format(title_line=title_line, date=today.isoformat()),
        encoding="utf-8",
    )
    return path
