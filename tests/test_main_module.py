import subprocess
import sys


def test_python_m_cairn_is_runnable():
    # `python -m cairn` with no command prints help and exits 2 (same as the
    # `cairn` console script). This guards the __main__ entry point.
    result = subprocess.run(
        [sys.executable, "-m", "cairn"], capture_output=True, text=True
    )
    assert result.returncode == 2
    assert "usage" in (result.stdout + result.stderr).lower()
