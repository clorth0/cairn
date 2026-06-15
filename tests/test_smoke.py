import cairn


def test_version_is_exposed():
    assert isinstance(cairn.__version__, str)
    assert cairn.__version__
