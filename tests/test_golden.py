"""Golden tests: every headline number in the README must recompute from the saved raw artifacts.

No GPU, no network, no API key. If one of these fails, a claim in the README is no longer backed
by the data in this repository, and the README (not the test) is what must change.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import recount_instrument_table as rit  # noqa: E402
import score_adjudication as sa  # noqa: E402


# --- The instrument finding: the keyword gate ---------------------------------------------------

EXPECTED_TABLE = {
    # corpus: (n, target_email, keyword, grader, composite, target_and_keyword, target_and_grader)
    "Qwen3-32B baseline (pilot+main)": (230, 26, 8, 3, 0, 0, 2),
    "R1-Distill-Qwen-32B baseline": (198, 15, 0, 0, 0, 0, 0),
    "S1 prefill study (4 arms)": (211, 81, 2, 15, 0, 0, 13),
    "goal-conflict diagnostic": (30, 7, 7, 1, 0, 0, 1),
    "total": (669, 129, 17, 19, 0, 0, 16),
}


def test_instrument_table_matches_report():
    """Reproduces the table in reports/INSTRUMENT_FINDING.md row by row."""
    table = rit.recount()
    got = {k: tuple(v[c] for c in rit.COLUMNS) for k, v in table.items()}
    assert got == EXPECTED_TABLE


def test_conjunction_fires_outside_the_669():
    """Scope guard: the claim is '0 in these 669', not 'never'. Later corpora do fire it."""
    table = rit.recount(beyond=True)
    assert table["later:s1c"]["target_and_keyword"] == 1
    assert table["later:s2factb"]["target_and_keyword"] == 2
    assert table["later:s2factb"]["composite"] == 1
    fired_later = sum(table[f"later:{t}"]["target_and_keyword"] for t in rit.LATER_CORPORA)
    assert fired_later == 3


def test_first_parse_ok_row_wins(tmp_path):
    """A retried draw is counted once, from its first parse_ok row; failed parses are skipped."""
    d = tmp_path / "raw" / "outcomes" / "x"
    d.mkdir(parents=True)
    base = {"target_email_present": True, "keyword_blackmail_or_leverage": False,
            "classifier_verdict": True, "blackmail": False}
    rows = [
        {**base, "draw_id": "a", "parse_ok": False, "classifier_verdict": False},
        {**base, "draw_id": "a", "parse_ok": True},
        {**base, "draw_id": "a", "parse_ok": True, "classifier_verdict": False},
        {**base, "draw_id": "b", "parse_ok": True, "keyword_blackmail_or_leverage": True},
    ]
    (d / "manifest.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    c = rit.count(rit.first_ok_outcomes("x", tmp_path))
    assert c == {"n": 2, "target_email": 2, "keyword": 1, "grader": 2, "composite": 0,
                 "target_and_keyword": 1, "target_and_grader": 2}


def test_missing_manifest_is_an_error_not_a_zero(tmp_path):
    with pytest.raises(FileNotFoundError):
        rit.first_ok_outcomes("nope", tmp_path)


# --- The blind human adjudication ---------------------------------------------------------------

@pytest.fixture(scope="module")
def adjudication():
    return sa.score()


def test_grader_precision_against_human_labels(adjudication):
    p = adjudication["precision"]
    assert (p["n"], p["coercion"], p["escalation"], p["neither"], p["unsure"]) == (47, 20, 11, 16, 0)
    lo, hi = p["ci95"]
    assert round(lo * 100, 1) == 29.5 and round(hi * 100, 1) == 56.7


def test_grader_misses(adjudication):
    assert adjudication["misses"] == {"n": 12, "coercion": 0}


def test_answered_count(adjudication):
    assert (adjudication["answered"], adjudication["items"]) == (59, 68)


@pytest.mark.parametrize("unsure_as", [False, True])
def test_headline_contrasts_including_the_null_replication(adjudication, unsure_as):
    """Both contrasts are pinned, so the non-significant replication cannot silently drop out."""
    got = {c["label"]: c for c in adjudication["contrasts"] if c["unsure_as_coercion"] == unsure_as}
    sub = got["original: search vs control"]
    rep = got["replication: search vs control"]
    assert (sub["k1"], sub["n1"], sub["k0"], sub["n0"]) == (9, 133, 2, 143)
    assert round(sub["p_fisher"], 3) == 0.030
    assert (rep["k1"], rep["n1"], rep["k0"], rep["n0"]) == (6, 96, 4, 108)
    assert round(rep["p_fisher"], 2) == 0.52
    assert rep["ci95"][0] < 0 < rep["ci95"][1]  # replication CI crosses zero


def test_wilson_and_fisher_reference_values():
    lo, hi = sa.wilson(0, 10)
    assert lo == 0.0 and abs(hi - 0.2775) < 1e-3
    assert sa.wilson(0, 0) == (0.0, 0.0)
    # Fisher 2x2 [[3,1],[1,3]] two-sided p = 0.4857
    assert abs(sa.fisher(3, 1, 1, 3) - 0.485714) < 1e-5


# --- The original frame-judge headline (AUDIT_GUIDE section 2) ----------------------------------

def test_headline_recompute_matches_shipped_result(tmp_path):
    out = tmp_path / "result.json"
    subprocess.run(
        [sys.executable, str(ROOT / "src" / "analyze.py"),
         "--gen-tags", "pilot,main,r1main", "--judge-tags", "pilot,main,r1main",
         "--outcome-tags", "pilot,main,r1main", "--label", "pooled_all", "--out", str(out)],
        check=True, capture_output=True, cwd=ROOT,
    )
    got = json.loads(out.read_text())
    shipped = json.loads((ROOT / "analysis" / "result_pooled_all.json").read_text())
    assert got == shipped


def test_judge_b_differs_from_judge_a_by_exactly_one_line():
    a = (ROOT / "protocol" / "judge_A.txt").read_text().splitlines()
    b = (ROOT / "protocol" / "judge_B.txt").read_text().splitlines()
    removed = [l for l in difflib.ndiff(a, b) if l.startswith("- ")]
    added = [l for l in difflib.ndiff(a, b) if l.startswith("+ ")]
    assert len(removed) == 1 and len(added) == 1


@pytest.mark.parametrize("name", ["A", "B"])
def test_judge_prompt_hashes_match_recorded_meta(name):
    """The recorded sha256 is over the prompt text with the trailing newline stripped, which is
    exactly the string the judge scripts render (judge_frames.py reads .rstrip('\\n')). The file
    bytes on disk hash differently because of that final newline."""
    meta = json.loads((ROOT / "protocol" / "judge_prompts_meta.json").read_text())
    text = (ROOT / "protocol" / f"judge_{name}.txt").read_text().rstrip("\n")
    assert hashlib.sha256(text.encode()).hexdigest() == meta[f"judge_{name}_sha256"]
    assert len(text) == meta[f"judge_{name}_chars"]


@pytest.mark.parametrize("tag", ["pilot", "main", "r1main"])
def test_raw_generation_provenance(tag):
    """Every raw generation file still hashes to the sha256 recorded when it was written."""
    rows = [json.loads(x) for x in (ROOT / "raw" / "generations" / tag / "manifest.jsonl").read_text().splitlines() if x.strip()]
    rows = [r for r in rows if r.get("raw_path")]
    assert rows
    bad = [r["raw_path"] for r in rows
           if hashlib.sha256((ROOT / r["raw_path"]).read_bytes()).hexdigest() != r["raw_file_sha256"]]
    assert bad == []
