# One-command reproduce. Needs Python 3.11 and `pip install -r requirements.txt`. No GPU, network or API key.
PY ?= python3

.PHONY: reproduce test rescore figures cases rows page

reproduce: test          ## run the tests, then recompute every number in the README's results table
	$(PY) scripts/reproduce.py

test:                    ## golden tests over the saved artifacts
	$(PY) -m pytest -q

rescore:                 ## re-score the 68 blind-labelled responses from their text (standard library, no GPU, no network)
	$(PY) scripts/rescore_sample.py

rows:                    ## rewrite docs/rows.md (which saved rows produce which README number)
	$(PY) docs/make_rows.py

figures:                 ## redraw the three README figures from the saved artifacts (needs matplotlib)
	$(PY) figures/make_readme_figures.py

cases:                   ## rewrite docs/cases.md
	$(PY) docs/make_cases.py

page: cases              ## rewrite the static project page docs/index.html
	$(PY) docs/make_page.py
