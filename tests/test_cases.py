"""The reader-facing case browser (docs/cases.md, Oct 2026) must match what its generator writes."""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_cases_page_is_current():
    before = (ROOT / "docs" / "cases.md").read_bytes()
    subprocess.run([sys.executable, str(ROOT / "docs" / "make_cases.py")], check=True, capture_output=True, cwd=ROOT)
    assert (ROOT / "docs" / "cases.md").read_bytes() == before
