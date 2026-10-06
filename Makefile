# One-command reproduce. Needs Python 3.11 and `pip install -r requirements.txt`. No GPU, network or API key.
PY ?= python3

.PHONY: reproduce test figures cases page

reproduce: test          ## run the tests, then recompute every number in the README's results table
	$(PY) scripts/reproduce.py

test:                    ## golden tests over the saved artifacts
	$(PY) -m pytest -q

figures:                 ## redraw the three README figures from the saved artifacts (needs matplotlib)
	$(PY) figures/make_readme_figures.py

cases:                   ## rewrite docs/cases.md
	$(PY) docs/make_cases.py

page: cases              ## rewrite the static project page docs/index.html
	$(PY) docs/make_page.py
