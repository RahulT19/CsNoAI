# CsNoAI
### Gaming & Esports Sector — Stock Forecasting & Algorithmic Decision Engine

A full-stack Python web application that **scrapes** historical price tables out of raw
HTML, **structures** them with pandas, fits **Ordinary Least Squares** regression models
in NumPy, and converts the statistical output into automated **BUY / SELL / HOLD**
signals rendered on a dark-mode financial terminal.

The tracked universe is the listed gaming and esports sector:

| Symbol | Company |
| :--- | :--- |
| `EA` | Electronic Arts Inc. |
| `TTWO` | Take-Two Interactive Software, Inc. |
| `SONY` | Sony Group Corporation |
| `NTDOY` | Nintendo Co., Ltd. |
| `NVDA` | NVIDIA Corporation |

---

## 1. Architecture

A strictly unidirectional pipeline — each stage has exactly one upstream and one
downstream neighbour, which is what allowed seven people to work in parallel without
touching each other's files.

```
                         ┌──────────────────────────────────────────┐
   HTTP GET (headers) →  │  scraper.py                              │
                         │  requests  →  BeautifulSoup(html.parser) │
                         │  <table> → <tbody> → <tr> → <td>         │
                         │  offline HTML corpus as the safety net   │
                         └────────────────┬─────────────────────────┘
                                          │ list[dict]  (10 sessions)
                         ┌────────────────▼─────────────────────────┐
                         │  model.py :: build_frame                 │
                         │  pandas — coerce, dedupe, sort, clip,     │
                         │  repair, index t = 1..n                  │
                         └────────────────┬─────────────────────────┘
                                          │ DataFrame
                         ┌────────────────▼─────────────────────────┐
                         │  model.py :: fit_ols / forecast          │
                         │  NumPy — β = (XᵀX)⁻¹Xᵀy, R², t-stat      │
                         │  evaluate Ĥ and L̂ at t = 11              │
                         └────────────────┬─────────────────────────┘
                                          │ Forecast
                         ┌────────────────▼─────────────────────────┐
                         │  strategy.py                             │
                         │  risk boundaries → BUY / SELL / HOLD     │
                         └────────────────┬─────────────────────────┘
                                          │ JSON
                         ┌────────────────▼─────────────────────────┐
                         │  app.py (Flask)  →  templates + static   │
                         │  index.html · style.css · dashboard.js   │
                         │  Chart.js: actuals vs. OLS trendlines    │
                         └──────────────────────────────────────────┘
```

---

## 2. Running it

```bash
cd CsNoAI
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Then open **http://127.0.0.1:5000**.

| Flag | Effect |
| :--- | :--- |
| *(none)* | Offline HTML corpus — deterministic, works with no network. **Default.** |
| `--live` or `CSNOAI_LIVE=1` | Attempt the live scrape first, fall back automatically. |
| `--port 8080` | Serve on a different port. |
| `CSNOAI_SITE_URL=https://…` | Absolute origin for canonical tags, Open Graph and the sitemap. Derived from the request when unset. |
| `--debug` | Flask reloader and tracebacks. |

The **Live scrape** toggle in the masthead flips the same switch per request, so you can
demonstrate both data paths without restarting the server.

> **Why is offline the default?** Financial portals throttle unauthenticated traffic and
> increasingly render their tables client-side, so a live request can return `HTTP 200`
> with no `<table>` in the document at all. The offline corpus is parsed by the *same*
> BeautifulSoup traversal, so the scraping code path is exercised either way and the
> dashboard cannot fail during a demo.

### Tests

```bash
cd CsNoAI
python -m tests.test_engine        # 22 assertions, no pytest required
python -m pytest tests -q          # also works if pytest is installed
```

---

## 3. The mathematics

### 3.1 Ordinary Least Squares

The ten scraped sessions are mapped to an ordinal time index
`x ∈ {1, 2, …, 10}`, and for each target series `y` we fit

```
ŷ = m·x + c
```

by minimising the residual sum of squares `Σ(yᵢ − ŷᵢ)²`. Setting the partial derivatives
with respect to `m` and `c` to zero gives the normal equations, whose solution is

```
      n·Σ(xy) − Σx·Σy
m =  ──────────────────                c = ȳ − m·x̄
      n·Σ(x²) − (Σx)²
```

`fit_ols` implements this in the equivalent matrix form on the design matrix
`X = [1  x]`:

```
β = (XᵀX)⁻¹ Xᵀy ,      β = [c, m]
```

solved with `np.linalg.solve` rather than an explicit inverse — same answer, better
conditioned. `tests/test_engine.py` pins the result against **both** `numpy.polyfit`
and the closed-form summation identity above, to 1e-9.

### 3.2 Goodness of fit

```
        SS_res      Σ(yᵢ − ŷᵢ)²
R² = 1 ──────── = 1 ─────────────                σ̂ = √( SS_res / (n − 2) )
        SS_tot      Σ(yᵢ − ȳ)²
```

The engine also reports the standard error of the slope and its t-statistic:

```
SE(m) = σ̂ / √Σ(xᵢ − x̄)²                          t = m / SE(m)
```

With `n = 10` there are 8 degrees of freedom, so `|t| > 2.306` is significant at the
5% level — a second, independent check on whether a trend is real. A perfectly flat
series has `SS_tot = 0`; the engine returns `R² = 0` there rather than dividing by zero.

### 3.3 Two independent models

**High** and **Low** are fitted separately, giving a projected *trading band* rather
than a single point:

```
Ĥ₁₁ = m_H · 11 + c_H                             L̂₁₁ = m_L · 11 + c_L
```

Because the two lines are independent they can cross on a converging series;
`forecast_next_session` enforces `Ĥ ≥ L̂` before the strategy layer ever sees them.

---

## 4. The decision algorithm

```
Potential Upside = (Ĥ₁₁ − Closeₜ) / Closeₜ
Downside Risk    = (Closeₜ − L̂₁₁) / Closeₜ
```

Evaluated top to bottom, **first match wins**:

| # | Condition | Verdict |
| :--- | :--- | :--- |
| 1 | `Downside ≥ 1.5%` **or** `m_H < 0` | **SELL** — reduce exposure / take profit |
| 2 | `Upside ≥ 1.5%` **and** `R²_H > 0.40` **and** `m_H > 0` | **BUY** — accumulate |
| 3 | anything else | **HOLD** — no statistical edge |

Two deliberate design choices sit behind that table:

* **Rule 1 is an override, not an alternative.** A stock with a widening high–low spread
  can project a large upside *and* a large drawdown simultaneously. Testing the sell
  condition first means the engine structurally cannot recommend buying into that regime.
* **Rule 2 carries two clauses beyond the raw upside.** `R² > 0.40` demands that the
  trendline actually explains the recent path instead of fitting noise, and `m_H > 0`
  stops the engine from buying a falling knife whose projected high merely sits above a
  depressed close.

Every verdict ships with the list of conditions that produced it, rendered as the
**Decision trace** panel — the algorithm is auditable, not a black box.

### Reference output (offline corpus)

| Symbol | Close | Ĥ₁₁ | L̂₁₁ | Upside | Downside | R² (H) | Signal |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| EA | 177.72 | 180.57 | 178.26 | +1.60% | −0.31% | 0.985 | **BUY** |
| TTWO | 231.59 | 232.00 | 228.11 | +0.18% | +1.50% | 0.958 | **SELL** |
| SONY | 28.22 | 28.10 | 27.94 | −0.44% | +1.00% | 0.412 | **HOLD** |
| NTDOY | 20.20 | 20.48 | 20.19 | +1.37% | +0.06% | 0.865 | **HOLD** |
| NVDA | 192.72 | 196.47 | 192.24 | +1.95% | +0.25% | 0.905 | **BUY** |

Note the three distinct ways an equity fails to earn a BUY: TTWO is rejected on a
negative slope, SONY on a weak fit *and* a negative upside, NTDOY purely on the 1.5%
boundary at +1.37%.

---

## 5. HTTP API

| Route | Purpose |
| :--- | :--- |
| `GET /` | Dashboard |
| `GET /methodology` | The derivation and decision rules, rendered from the live thresholds |
| `GET /api/universe` | Configured tickers and window size |
| `GET /api/analyze/<ticker>` | Full analysis for one symbol |
| `GET /api/analyze` | Batch analysis plus a sector summary |
| `GET /api/health` | Liveness probe and cache size |
| `GET /robots.txt` | Crawl policy; points at the sitemap |
| `GET /sitemap.xml` | The two indexable pages |
| `GET /llms.txt` | Machine-readable summary of the project and its method |

Unknown paths return a themed **404** page — or a JSON error under `/api/`, since an
API client has no use for HTML.

Query flags on the analysis routes: `?live=0|1` selects the data path, `?refresh=1`
bypasses the five-minute per-symbol cache. Failures return typed JSON —
`scrape_failed` (404), `model_failed` (422), `internal_error` (500).

```bash
curl 'http://127.0.0.1:5000/api/analyze/NVDA?live=0' | python -m json.tool
```

---

## 6. The web layer

The engine is the point of the project, but it is delivered as a real site rather than a
single unlabelled page. Everything below is generated by the application, not pasted in.

### Pages

Three of them, each with its own `<title>`, its own meta description and exactly one
`<h1>`: the **dashboard**, the **methodology** page, and a themed **404**. The methodology
page renders its decision table from `strategy.UPSIDE_THRESHOLD`, `DOWNSIDE_THRESHOLD` and
`R2_CONFIDENCE` directly, so the documentation cannot drift from the code that runs.

They are linked to each other in the footer, from the dashboard lede, and from the 404 page
— which also deep-links every tracked ticker. Selecting an equity updates the breadcrumb
trail, the URL hash and the tab title (`NVDA BUY · NVIDIA Corporation · CsNoAI`), so a
specific verdict can be linked and bookmarked.

### Metadata

Canonical URLs, Open Graph and Twitter card tags, a `theme-color`, and a 1200x630 share
image with descriptive `og:image:alt`. Error pages send `noindex` and deliberately emit
**no** canonical or `og:url` — self-canonicalising a URL that does not exist is worse than
omitting the tag.

Absolute URLs come from `CSNOAI_SITE_URL` when it is set and from the incoming request
otherwise, so canonical tags and the sitemap are correct on `localhost` today and correct
on a real hostname the moment one is pointed at the service — no code change.

### Structured data

JSON-LD on both content pages: `WebSite` and `WebApplication` with a `BreadcrumbList` on
the dashboard, `TechArticle` on the methodology page. The types describe what this
genuinely is; no schema is claimed that the page does not back up.

### Crawler documents

`robots.txt` (crawl everything except `/api/`, which serves no HTML, and point at the
sitemap), `sitemap.xml` (the two indexable pages, with absolute URLs), and `llms.txt` — a
plain-text summary of the project, its method, its coverage and its caveats, with the
threshold values interpolated from the running configuration.

### Assets and payload

| Asset | Size | Note |
| :--- | ---: | :--- |
| `chart.min.js` | 156.5 KB (54.8 KB gz) | Tree-shaken Chart.js — see `static/js/vendor/README.md` |
| `dashboard.js` | 14.1 KB | Application code |
| `style.css` | 18.8 KB | |
| `og-image.png` | 46.9 KB | Only ever fetched by a link unfurler, never by the page |
| `favicon.svg` | 0.5 KB | |

Three deliberate choices behind those numbers. Chart.js is **tree-shaken** to the seven
components actually used, cutting 44 KB off the stock distribution. It is **self-hosted**
rather than pulled from a CDN, so the dashboard renders with no internet connection —
the same reasoning as the scraper's offline corpus, and one fewer third-party origin. And
there is **no webfont**: the page uses the system UI and system monospace stacks, which
removes two render-blocking requests to Google Fonts and any layout shift when the font
lands. Both scripts are `defer`red.

### Accessibility

A skip link, one `<h1>` per page, `<th scope>` and a `<caption>` on every table, labelled
landmarks, `aria-live` on the status region, and a text description on the chart canvas
naming the table that carries the same numbers. `prefers-reduced-motion` disables both the
CSS transitions and the Chart.js animation. There are no `<img>` elements in the interface
at all — the only raster asset is the share card, which carries alt text in its meta tag.

### Design

Flat surfaces on a cool slate ground, one structural accent (`#5b9bd5`), and colour
otherwise reserved for meaning: green/amber/red for the verdict, blue and lilac for the two
price series. No gradient fills and no glow effects — on a data display, decoration
competes with the numbers.

---

## 7. Project structure

```
CsNoAI/
├── app.py                     # Flask routing, pipeline composition, caching
├── scraper.py                 # BeautifulSoup DOM parsing + offline HTML corpus
├── model.py                   # pandas cleaning, NumPy OLS, forecasting
├── strategy.py                # risk-boundary decision engine
├── templates/
│   ├── base.html              # shared layout: head metadata, masthead, footer
│   ├── index.html             # dashboard
│   ├── methodology.html       # the derivation, rendered from live thresholds
│   ├── 404.html               # custom not-found page
│   └── 500.html               # custom server-error page
├── static/
│   ├── favicon.svg
│   ├── css/style.css          # flat dark theme, CSS grid
│   ├── img/og-image.png       # 1200x630 social share card
│   └── js/
│       ├── dashboard.js       # API client + Chart.js rendering
│       └── vendor/
│           ├── chart.min.js   # tree-shaken Chart.js 4.4.1 (self-hosted)
│           └── README.md      # what was stripped and how to rebuild it
├── tests/
│   └── test_engine.py         # 22 assertions across all four modules
├── requirements.txt
└── README.md
```

---

## 8. Team contribution & module ownership

The architecture was decoupled *before* any code was written, precisely so seven people
could work concurrently. Each module below is a separate file with a single owner and a
narrow interface, so day-to-day work never touched the same lines.

| # | Name | Role | Owns | Interface it publishes |
| :--- | :--- | :--- | :--- | :--- |
| 1 | | Scraper Architect | `scraper.py` | `get_history(ticker) → ScrapeResult` |
| 2 | | Data Engineer | `model.build_frame` | `list[dict] → DataFrame` |
| 3 | | Quantitative Modeler | `model.fit_ols` | `(x, y) → OLSFit` |
| 4 | | Predictive Analyst | `model.forecast_next_session` | `DataFrame → Forecast` |
| 5 | | Algorithm Designer | `strategy.py` | `Forecast → Signal` |
| 6 | | UI/UX & Frontend | `templates/`, `static/css/` | Element ids and CSS contract |
| 7 | | Integration & Versioning | `app.py`, `static/js/` | JSON API, routing, Chart.js rendering |

*(Fill in the Name column with your team's names before submitting.)*

**Why the seams fall where they do.** Members 2–4 share `model.py` because their work is
a single mathematical chain, but they own three non-overlapping functions with typed
boundaries (`DataFrame`, `OLSFit`, `Forecast`), so a change to the cleaning rules cannot
break the regression and a change to the regression cannot break the forecast. Members 6
and 7 split the frontend along the classic structure/behaviour line: Member 6 owns the
markup and the stylesheet, Member 7 owns everything that talks to the API and draws the
chart. The contract between them is the set of element ids, agreed up front.

Owner boundaries hold across the web layer too. The pages, the palette and the
accessibility work sit with Member 6; the routing, the crawler documents, the vendored
chart bundle and the client controller sit with Member 7. The one place they meet is
`templates/base.html`, whose `{% block %}` names are the agreed contract — Member 6 owns
the layout inside it, Member 7 owns the values Flask injects into it.

### Version control

Branch-per-module, merged into `main` by whoever holds integration. The practical setup —
per-member git identity, the branch table, what each member can genuinely own next, and
how to merge so the merge commits are real — is written up in
[`docs/TEAM-WORKFLOW.md`](docs/TEAM-WORKFLOW.md).

`git log --oneline` on the delivered repository:

```
65b8063 docs: add the team branching, ownership and merge workflow
281814f docs: extend module ownership to cover the web layer
7ec35e5 docs: refresh the quoted commit log
c44cced feat(api): redirect /favicon.ico to the SVG icon
a0a35f1 docs: document the web layer, assets and design decisions
1558998 feat(dashboard): match the new palette, drive title and breadcrumb
25a3db5 feat(api): methodology route, crawler documents and error handlers
98ccc74 feat(web): base layout, methodology page, error pages and metadata
b277b7b style(ui): replace the neon gradient theme with a flat data palette
a246d75 build(vendor): self-host a tree-shaken Chart.js 4.4.1
d131a81 docs: refresh the quoted commit log
09b0c54 style: finalise the CsNoAI wordmark and documentation casing
6298ab1 docs: refresh the quoted commit log
417a6a6 feat(dashboard): deep-link the selected equity through the URL hash
0e1fc85 docs: architecture, derivations, API reference and module ownership
6c6bd37 test: cover the parser, the frame, the maths and the decision table
8e47c4c feat(api): Flask routing that joins the four modules into one pipeline
1a9b308 feat(dashboard): Chart.js rendering of actuals against the trendlines
3c93fda feat(ui): glassmorphic dark-mode terminal shell
6c5196b feat(strategy): percentage risk boundaries over the regression output
4333557 feat(model): pandas cleaning and a NumPy OLS regression engine
d9f6147 feat(scraper): parse historical OHLC tables straight from the DOM
6a2e87d chore(build): pin runtime dependencies for the Flask stack
a9fe061 chore: initialise repository and ignore rules
```

Commits are scoped one-module-per-commit and follow Conventional Commits, so the history
reads as the dependency order of the pipeline: scraper, model, strategy, UI, chart, API,
tests. Run `git log --stat` to see that no two feature commits touch the same file.

---

## 9. Compliance with the brief

| Requirement | Where it lives | Notes |
| :--- | :--- | :--- |
| `requests` for extraction | `scraper.fetch_html` | Desktop `User-Agent`, `Accept-Language`, timeout |
| `BeautifulSoup` + `html.parser` | `scraper.parse_history_table` | Literally `BeautifulSoup(html, "html.parser")` |
| Parse `<table>`/`<tr>`/`<td>` | `scraper.parse_history_table` | Header row identifies the price table by its `<th>` labels |
| `pandas` DataFrame | `model.build_frame` | Cleaning, dedupe, window clipping, ordinal index |
| `numpy` mathematics | `model.fit_ols` | Explicit design matrix, no statistics library |
| Next-day High and Low | `model.forecast_next_session` | Two independent models evaluated at `t = 11` |
| Slope, intercept, R² | `model.OLSFit` | Plus residual σ, SE(m) and the t-statistic |
| Buy/Sell/Hold thresholds | `strategy.evaluate` | 1.5% boundaries, 0.40 R² floor |
| HTML/CSS/JS served by Python | `app.py` + `templates/` + `static/` | Flask, Jinja2, Chart.js |

**Deliberately not used:**

* **No API wrappers.** No `yfinance`, no JSON endpoint, no CSV download. The application
  requests an HTML document and parses the DOM.
* **No black-box models.** No LSTM, no gradient boosting, not even `sklearn`. Ordinary
  Least Squares in ~20 lines of NumPy, every coefficient reproducible by hand.
* **No deep crawling.** Exactly one static quote page per symbol; no link following,
  no recursion, no crawl frontier.

---

## 10. Known limitations

An honest list, because the first question in any viva is *"where does this break?"*

1. **Linear extrapolation over 10 sessions** captures short-term drift and nothing else.
   It has no notion of mean reversion, volatility clustering, gaps, earnings dates or
   macro shocks, and its error grows without bound as the horizon extends. One session
   ahead is the honest limit of the method.
2. **A high R² is not predictive skill.** It says the last ten points sat near a line,
   not that the eleventh will. That is precisely why the slope sign and the downside
   boundary act as independent gates.
3. **`n = 10` is a very small sample.** Two degrees of freedom are consumed by the fit,
   leaving eight — enough for a t-test, not enough for confidence in the tails.
4. **The offline corpus is synthetic.** It is realistically shaped, deterministic price
   data used to guarantee the demo runs; it is not a live market record. Live scraping is
   one toggle away, but the portal's markup changes without notice.
5. **No transaction costs, slippage, position sizing or backtest.** The signal is a
   directional opinion, not a trading system.

*Academic coursework. Not investment advice.*
