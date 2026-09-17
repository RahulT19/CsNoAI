# CsNoAI - Gaming & Esports Sector Forecast Engine

CsNoAI is a standalone desktop application built with Python's Tkinter and
PyMongo. It parses stock-history HTML, cleans the sessions with pandas, fits
independent Ordinary Least Squares (OLS) models for High and Low prices with
NumPy, and produces an explainable BUY, SELL, or HOLD signal.

Tracked equities:

- `EA` — Electronic Arts Inc.
- `TTWO` — Take-Two Interactive Software, Inc.
- `SONY` — Sony Group Corporation.
- `NTDOY` — Nintendo Co., Ltd.
- `NVDA` — NVIDIA Corporation.

> This is an academic stock-analysis demonstration, not a trading system or
> investment advice. A 10-session linear model cannot reliably predict markets.

## Files to understand

| File | Responsibility |
| --- | --- |
| `main.py` | Tkinter window, controls, results table, metrics, verdict card, audit log, and status bar. |
| `scraper.py` | HTML parser, five-ticker universe, live request logic, MongoDB cache lookup, and offline fallback pages. |
| `model.py` | Data cleaning, OLS fitting, R-squared, parameter uncertainty, and Day 11 forecast uncertainty. |
| `strategy.py` | BUY, SELL, HOLD thresholds and human-readable audit reasons. |
| `db.py` | Configurable MongoDB connection, history cache, prediction logging, and in-memory fallback. |
| `tests/test_engine.py` | Plain-assert tests for parsing, cleaning, model math, strategy rules, and persistence. |

## Architecture

```text
HTML scraper / fallback corpus
        |
        v
pandas cleaning and t = 1..10 indexing
        |
        v
NumPy OLS models for High and Low
        |
        v
Strategy confidence gate and BUY / SELL / HOLD decision
        |
        v
Tkinter presentation and MongoDB persistence
```

The scraper first checks stored history. If no cache is available, it attempts
live scraping only when enabled; otherwise, or after a failure, it uses the
bundled fallback HTML. This keeps demonstrations deterministic and usable
without internet access.

## Quantitative methodology

For High and Low independently, the app fits a line:

```text
y = m * t + c
```

`m` is the slope (average movement per session) and `c` is the intercept.
The app uses `numpy.polyfit(t, y, 1, cov=True)`: it returns the fitted slope,
intercept, and a covariance matrix. The covariance diagonal supplies slope and
intercept standard errors. The model also computes:

- `R-squared`: how closely the line fits these ten observations.
- Residual standard error.
- Day 11 prediction standard error: uncertainty around the next-session point
  estimate, not a guaranteed price range.

The High and Low lines are evaluated at `t = 11`. If they cross, the output is
reordered so predicted High is never below predicted Low.

## Decision algorithm

The current closing price is compared with the predicted Day 11 bounds:

```text
upside   = (predicted_high - close) / close
downside = (close - predicted_low) / close
```

| Priority | Condition | Result |
| --- | --- | --- |
| 1 | Either High or Low R-squared is below `0.40` | HOLD — insufficient confidence |
| 2 | Downside is at least `1.5%`, or High slope is negative | SELL |
| 3 | Upside is at least `1.5%`, High R-squared is above `0.40`, and High slope is positive | BUY |
| 4 | Anything else | HOLD |

The confidence gate intentionally comes first: an attractive-looking price
boundary is not trusted when either 10-session regression is weak.

## Installation and execution

Install Python 3.10+ and select **Add Python to PATH** during installation.
Then run this in PowerShell:

```powershell
cd C:\Users\raksh\Desktop\my-code\CSNoAI
py -m pip install -r requirements.txt
py main.py
```

Leave **Use Live Scraping** unchecked for the most reliable demonstration. The
included fallback data works without network access.

## MongoDB setup

MongoDB is optional. If no server is reachable, the app stays usable with an
in-memory fallback for the current run.

By default, `db.py` uses local MongoDB at `mongodb://localhost:27017/` and
database `csnoai_gaming_db`. It stores clean sessions in `stock_history` and
forecast/signal snapshots in `predictions`.

For MongoDB Atlas or another MongoDB server, set the URI outside the codebase:

```powershell
$env:CSNOAI_MONGO_URI = 'your-mongodb-connection-string'
$env:CSNOAI_MONGO_DATABASE = 'csnoai_gaming_db'
py main.py
```

Never commit a connection string or password. `.env` is ignored by Git. If a
credential was pasted into a chat, terminal recording, or Git commit, rotate
the database password before using it.

## Tests

```powershell
cd C:\Users\raksh\Desktop\my-code\CSNoAI
py -m tests.test_engine
```

The test runner uses standard `assert` statements; pytest is not required.

## Demonstration plan

1. Start the app with live scraping off and select `EA`.
2. Click **Run Analysis** and point out the status-bar source.
3. Show the ten cleaned sessions and explain `t = 1..10`.
4. Explain the High/Low equations, R-squared, and forecast standard error.
5. Read the audit log to show why the result is BUY, SELL, or HOLD.
6. Click **Save to MongoDB** and explain that history and the prediction are
   persisted when MongoDB is connected.
7. Optionally enable live scraping and explain the offline fallback safety net.

## Limitations and common questions

**Why ten sessions?** It makes the model easy to explain and demo, but it is a
small sample with only eight residual degrees of freedom.

**Why separate High and Low models?** Their Day 11 estimates create a possible
range for calculating upside and downside relative to the latest close.

**Does high R-squared mean the forecast is correct?** No. It measures fit to
the ten observations only; it does not account for news, earnings, market
events, mean reversion, or nonlinear volatility.

**What happens if MongoDB or the internet is unavailable?** The application
falls back safely: stored cache when present, otherwise offline HTML data, and
in-memory persistence when MongoDB is offline.
