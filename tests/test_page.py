"""The static project page (docs/index.html) must match its generator and load nothing external."""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_page_is_current():
    before = (ROOT / "docs" / "index.html").read_bytes()
    subprocess.run([sys.executable, str(ROOT / "docs" / "make_page.py")], check=True, capture_output=True, cwd=ROOT)
    assert (ROOT / "docs" / "index.html").read_bytes() == before


def test_page_loads_nothing_external():
    page = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    for pattern in (r"<script", r"<link\b", r"<iframe", r"@import", r"url\(", r"\bsrc=\"(?!img/)"):
        assert re.search(pattern, page) is None, pattern
    for src in re.findall(r'src="([^"]+)"', page):
        assert (ROOT / "docs" / src).is_file(), src
