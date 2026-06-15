from __future__ import annotations

import datetime
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from cairn.build import build
from cairn.config import Config


def make_handler(directory: str | Path) -> type[SimpleHTTPRequestHandler]:
    directory = str(directory)

    class Handler(SimpleHTTPRequestHandler):
        pass

    Handler.directory = directory  # consumed in __init__ below

    def __init__(self, *args, **kwargs):
        SimpleHTTPRequestHandler.__init__(self, *args, directory=directory, **kwargs)

    Handler.__init__ = __init__
    return Handler


def _snapshot(content_dir: Path) -> dict[Path, float]:
    return {p: p.stat().st_mtime for p in content_dir.rglob("*.md")}


def serve(
    config: Config, *, watch: bool = False, port: int = 8000, host: str = "127.0.0.1"
) -> None:  # pragma: no cover - long-running loop
    build(config, today=datetime.date.today())
    handler = make_handler(config.build.output_dir)
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Serving {config.build.output_dir} at http://{host}:{port}")

    if not watch:
        server.serve_forever()
        return

    import threading

    threading.Thread(target=server.serve_forever, daemon=True).start()
    content_dir = Path(config.build.content_dir)
    last = _snapshot(content_dir)
    print("Watching for changes... (Ctrl+C to stop)")
    try:
        while True:
            time.sleep(1)
            current = _snapshot(content_dir)
            if current != last:
                print("Change detected, rebuilding...")
                build(config, today=datetime.date.today())
                last = current
    except KeyboardInterrupt:
        server.shutdown()
