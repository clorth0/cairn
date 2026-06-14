from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cairn.build import build, check
from cairn.config import ConfigError, load_config
from cairn.deploy import emit
from cairn.scaffold import new_post, new_site
from cairn.security import security_advisories
from cairn.serve import serve

CONFIG_NAME = "site.toml"


def _bundled_default_theme() -> str:
    """Resolve the packaged default theme (works for wheel and editable installs)."""
    from importlib.resources import files

    return str(files("cairn").joinpath("themes", "default"))


def _load(args) -> "Config":
    cfg = load_config(Path(CONFIG_NAME))
    if cfg.build.theme == "default":
        cfg.build.theme = _bundled_default_theme()
    return cfg


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cairn")
    sub = parser.add_subparsers(dest="command")

    p_new = sub.add_parser("new", help="scaffold a site or post")
    new_sub = p_new.add_subparsers(dest="kind")
    p_new_site = new_sub.add_parser("site")
    p_new_site.add_argument("path", nargs="?", default=".")
    p_new_post = new_sub.add_parser("post")
    p_new_post.add_argument("title")

    p_build = sub.add_parser("build")
    p_build.add_argument("--drafts", action="store_true")
    p_build.add_argument("--future", action="store_true")
    p_build.add_argument("--clean", action="store_true")

    p_serve = sub.add_parser("serve")
    p_serve.add_argument("--watch", action="store_true")
    p_serve.add_argument("--port", type=int, default=8000)

    sub.add_parser("check")

    p_deploy = sub.add_parser("deploy")
    p_deploy.add_argument("target", nargs="?")

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 2

    if args.command is None:
        parser.print_help()
        return 2

    try:
        if args.command == "new":
            if args.kind == "site":
                new_site(args.path)
                print(f"Created a new Cairn site in {args.path}")
                return 0
            if args.kind == "post":
                cfg = _load(args)
                path = new_post(cfg.build.content_dir, args.title)
                print(f"Created {path}")
                return 0
            p_new.print_help()
            return 2

        if args.command == "build":
            cfg = _load(args)
            result = build(cfg, drafts=args.drafts, future=args.future,
                           clean=args.clean)
            print(f"Built {result.page_count} pages into {result.output_dir}")
            return 0

        if args.command == "serve":
            cfg = _load(args)
            serve(cfg, watch=args.watch, port=args.port)
            return 0

        if args.command == "check":
            cfg = _load(args)
            errors = check(cfg)
            for note in security_advisories(cfg):
                print(f"warning: {note}", file=sys.stderr)
            if errors:
                for err in errors:
                    print(f"error: {err}", file=sys.stderr)
                return 1
            print("All content valid.")
            return 0

        if args.command == "deploy":
            cfg = _load(args)
            target = args.target or cfg.deploy.target
            cfg.deploy.target = target
            written = emit(cfg, project_dir=".")
            if written:
                for path in written:
                    print(f"Wrote {path}")
            else:
                print("Folder target: deploy the output directory however you like.")
            return 0
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 1

    parser.print_help()
    return 2
