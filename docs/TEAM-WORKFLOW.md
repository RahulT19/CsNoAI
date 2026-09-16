# Team workflow — getting seven real authors into the history

The repository currently has a single author. If the submission is expected to show seven
contributors, the way to get there is for each member to genuinely own their module from
here on. Twenty minutes of everyone's time produces a history that holds up to any
question an evaluator can ask, because it is true.

Do **not** rewrite the existing commits to other people's names. Authorship metadata is
trivial to inspect — `git log --format='%an %ae %ad %cd'` shows author and committer names
and both timestamps — and a history where seven people committed from one machine inside
five minutes is more damaging than a history with one author.

## One-time setup, by each member on their own machine

```bash
git clone <repo-url> CsNoAI && cd CsNoAI
git config user.name  "Their Real Name"
git config user.email "their.email@college.edu"
```

The `user.email` is what the evaluator sees. Set it per-repository like this rather than
globally, so nobody's personal identity leaks into the coursework.

## Branch per member

| Member | Branch | Their surface |
| :--- | :--- | :--- |
| 1 | `feat/scraper` | `scraper.py` |
| 2 | `feat/data-frame` | `model.build_frame` |
| 3 | `feat/regression` | `model.fit_ols` |
| 4 | `feat/forecast` | `model.forecast_next_session`, `series_payload` |
| 5 | `feat/strategy` | `strategy.py` |
| 6 | `feat/ui` | `templates/`, `static/css/` |
| 7 | `feat/integration` | `app.py`, `static/js/` |

```bash
git switch -c feat/<yours>
# do real work on your surface — see the list below
git add <your files>
git commit -m "feat(<scope>): <what you actually changed>"
git push -u origin feat/<yours>
```

## Real work each member can own

These are genuine gaps, not busywork. Each is confined to one member's surface, so they
can all be done in parallel.

| Member | Something real to add |
| :--- | :--- |
| 1 | A second fallback source, or `robots.txt`-aware polite fetching with a retry/backoff. |
| 2 | Handle a missing trading day explicitly (holiday gaps) instead of relying on `tail`. |
| 3 | Add a confidence interval for the slope, or Theil–Sen as a robust comparison fit. |
| 4 | Report the prediction interval around `Ĥ₁₁`/`L̂₁₁`, not just the point estimate. |
| 5 | Make the thresholds configurable, and add a rule-hit counter across the universe. |
| 6 | A light theme via `prefers-color-scheme`, or a print stylesheet for the report. |
| 7 | Persist the cache to disk so a cold start is instant; add a CI workflow running the tests. |

Whoever takes a piece should also write the test for it in `tests/test_engine.py` and add
their row to the ownership table in the README.

## Merging, so the merge commits are real

Integration (Member 7) merges each branch with `--no-ff`, which forces an actual merge
commit even when the merge is trivial:

```bash
git switch main
git merge --no-ff feat/scraper -m "merge: scraper module from Member 1"
```

If two branches touch the same file, resolve it properly rather than reaching for
`--ours`:

```bash
git merge --no-ff feat/ui
# CONFLICT in templates/index.html
git diff --name-only --diff-filter=U     # what actually conflicts
# edit the file, keep both intentions
git add templates/index.html
git commit                                # writes the conflict resolution into the message
```

## Checking the result

```bash
git shortlog -sne              # commits per author — this is what gets counted
git log --graph --oneline      # the branch and merge topology
```

`git shortlog -sne` is the single command most likely to be run against your repository.
Make it tell the truth.
