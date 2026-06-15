from pathlib import Path

from cairn.serve import make_handler


def test_handler_class_is_bound_to_directory(tmp_path):
    (tmp_path / "index.html").write_text("<p>hi</p>", encoding="utf-8")
    handler_cls = make_handler(tmp_path)
    # SimpleHTTPRequestHandler subclasses accept a `directory` kwarg via partial;
    # make_handler binds it so the class can be used directly by ThreadingHTTPServer.
    assert handler_cls.directory == str(tmp_path)
