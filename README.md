# CsNoAI

CsNoAI is a Tkinter desktop application that analyses five gaming-sector
equities: EA, TTWO, SONY, NTDOY, and NVDA. It parses an HTML price-history
table, cleans ten sessions with pandas, fits transparent NumPy OLS models for
High and Low prices, then issues an auditable BUY, SELL, or HOLD signal.

## Run

```powershell
cd CSNoAI
py -m pip install -r requirements.txt
py main.py
```

The **Use Live Scraping** checkbox is off by default. With it off, the
application uses the bundled HTML fallback corpus, making demonstrations and
tests deterministic even without network access.

## MongoDB

The optional local database is `mongodb://localhost:27017/`, database
`csnoai_gaming_db`. Start MongoDB before launching the app to persist price
history and prediction snapshots. If it is unavailable, `db.py` safely uses
an in-memory fallback and the status bar reports that state.

## Tests

```powershell
py -m tests.test_engine
```

The test module uses ordinary `assert` statements and does not require pytest.
