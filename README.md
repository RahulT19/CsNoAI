## CsNoAI — Gaming & Esports Sector Forecast Engine

CsNoAI is a standalone desktop application built with Python's native Tkinter and PyMongo that automates quantitative forecasting and signal generation for listed gaming and esports equities. The system ingests raw HTML price tables, cleans and indexes rolling historical sessions using pandas, computes independent Ordinary Least Squares (OLS) regression models for daily High and Low prices in NumPy, and executes a rule-based decision algorithm yielding actionable BUY, SELL, or HOLD signals.

The system tracks five listed gaming and technology equities:

* `EA`: Electronic Arts Inc.


* `TTWO`: Take-Two Interactive Software, Inc.


* `SONY`: Sony Group Corporation


* `NTDOY`: Nintendo Co., Ltd.


* `NVDA`: NVIDIA Corporation



---

## Architecture & Data Pipeline

The application employs a strictly decoupled, unidirectional pipeline where each stage has a single upstream source and downstream consumer:

```
[ HTML Scraper / Corpus ]  (requests + BeautifulSoup / _FALLBACK_PAGES)
           │
           ▼  raw session dicts
[ Data Engineering ]       (pandas: cleaning, repair, ordinal indexing t = 1..10)
           │
           ▼  cleaned DataFrame
[ Quantitative Engine ]    (NumPy OLS: slope, intercept, R², forecast at t = 11)
           │
           ▼  Forecast dataclass
[ Algorithmic Strategy ]   (Risk boundaries & capital-preservation override)
           │
           ▼  Signal dataclass
[ Presentation & Storage ] (Tkinter UI + PyMongo persistence)

```

1. **Extraction (`scraper.py`)**: Fetches raw HTML tables using `requests` with desktop browser headers, traversing the DOM with `BeautifulSoup` (`html.parser`). Non-price rows (dividends, stock splits) are ignored. When live network access is disabled or throttled, an embedded offline snapshot corpus (`_FALLBACK_PAGES`) parses through the identical extraction logic to guarantee zero runtime failures during demonstrations.


2. **Data Engineering (`model.py`)**: Coerces scraped strings into numeric types, eliminates missing data, de-duplicates session dates, clips observations to a rolling 10-session window ($n = 10$), repairs inverted High/Low anomalies, and assigns an ordinal regression index $t \in \{1, 2, \dots, 10\}$.


3. **Quantitative Modeling (`model.py`)**: Fits two independent Ordinary Least Squares linear trendlines for daily High and Low series against ordinal time $t$. Evaluates goodness of fit ($R^2$), slope standard error, and projects price boundaries for the next trading session ($t = 11$).


4. **Decision Engine (`strategy.py`)**: Computes potential percentage upside and downside against the latest close ($Close_t$), evaluating hierarchical risk boundaries.


5. **Desktop UI & Persistence (`main.py`, `db.py`)**: Presents interactive controls, tabular historical prices, model equations, and visual signal badges in Tkinter, persisting run records to MongoDB.



---

## Quantitative Methodology

### 1. Ordinary Least Squares (OLS)

For each price series $y$ (High and Low independently), the engine minimizes the residual sum of squares $\sum (y_i - \hat{y}_i)^2$ for the line $\hat{y} = m \cdot t + c$:

$$m = \frac{n \sum (t \cdot y) - \sum t \sum y}{n \sum t^2 - (\sum t)^2}, \quad c = \bar{y} - m\bar{t}$$

The implementation solves the normal equations over the design matrix $X = [\mathbf{1} \quad \mathbf{t}]$ via NumPy's matrix solver rather than manual inversion, maximizing numerical stability.

### 2. Goodness of Fit & Variance Protection

Model explanatory power is captured via the coefficient of determination:

$$R^2 = 1 - \frac{SS_{\text{res}}}{SS_{\text{tot}}} = 1 - \frac{\sum (y_i - \hat{y}_i)^2}{\sum (y_i - \bar{y})^2}$$

* If a series exhibits zero variance ($SS_{\text{tot}} \approx 0$), the engine forces $R^2 = 0.0$ to eliminate divide-by-zero exceptions.


* Residual variance ($\hat{\sigma}$) and slope standard error determine parameter stability across the 8 degrees of freedom ($n - 2$).



### 3. Horizon Forecast

Both fitted lines project forward to session $t = 11$:

$$\hat{H}_{11} = m_H \cdot 11 + c_H, \quad \hat{L}_{11} = m_L \cdot 11 + c_L$$

Because the High and Low models are fitted independently, lines can cross on converging series; the engine structurally enforces $\hat{H}_{11} \ge \hat{L}_{11}$ before passing forecasts to the strategy layer.

---

## Decision Algorithm

Signals are evaluated relative to the current closing price:

$$\text{Potential Upside} = \frac{\hat{H}_{11} - Close_t}{Close_t} \times 100, \quad \text{Downside Risk} = \frac{Close_t - \hat{L}_{11}}{Close_t} \times 100$$

Evaluated strictly top-to-bottom (**first matching condition triggers the signal**):

| Priority | Condition | Verdict | Justification |
| --- | --- | --- | --- |
| **1** | $\text{Downside Risk} \ge 1.5\%$ **or** $m_H < 0$<br> | **SELL**<br> | **Capital Preservation Override**: Halts purchases into decaying trends ($m_H < 0$) or widening high-low spreads with significant drawdown potential.

 |
| **2** | $\text{Upside} \ge 1.5\%$ **and** $R^2_H > 0.40$ **and** $m_H > 0$<br> | **BUY**<br> | **Qualified Entry**: Requires demonstrable upward drift, positive trajectory, and statistical confidence above random noise.

 |
| **3** | All other market conditions

 | **HOLD**<br> | **Neutral Stance**: Price volatility sits within the noise band; no statistical edge exists.

 |

---

## Installation & Execution

### Prerequisites

* Python 3.10+ (Ensure **Add Python to PATH** is checked during installation)
* MongoDB Community Server (Optional; default port `27017`)

### Setup Commands (PowerShell)

```powershell
cd CSNoAI
py -m pip install -r requirements.txt
py main.py

```

*(If the `py` launcher is unconfigured, run `python main.py` directly.)*

### Operational Controls

* **Use Live Scraping Checkbox**: Disabled by default. Running with it unchecked parses the bundled HTML fallback corpus, enabling completely deterministic and offline evaluations without network dependencies.


* **MongoDB Integration**: Connects to `mongodb://localhost:27017/` on database `csnoai_gaming_db`. If MongoDB is not running, `db.py` automatically degrades to an in-memory fallback without interrupting analysis or throwing fatal errors.

---

## Verification & Test Suite

Run the built-in regression test harness directly from PowerShell:

```powershell
py -m tests.test_engine

```

The test runner utilizes standard Python `assert` statements without third-party test framework requirements:

* Validates HTML price table parsing, coordinate scraping, and fallback loading.


* Validates data engineering pipelines, column coersion, and monotonic index generation.


* Pins OLS regression outputs ($m$, $c$, $R^2$) against `numpy.polyfit` to a numerical tolerance of $10^{-9}$.


* Validates boundary decisions, sell overrides, and edge handling across all five tracked equities.



---

## Project Limitations

* **Linear Horizon Limit**: Linear extrapolation over 10 trading sessions captures immediate directional momentum only. It does not incorporate mean reversion, earnings surprises, or non-linear macroeconomic volatility.


* **Sample Size**: Fitting across $n = 10$ sessions leaves 8 degrees of freedom—sufficient for directional screening, but sensitive to individual outlier sessions.


* **Academic Scope**: Outputs are educational signals derived from quantitative coursework rules and do not constitute financial advice.
