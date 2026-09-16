"""
app.py — Flask application server and JSON API
==============================================
Owner: Member 7 (Integration & Versioning)

Wires the four independent backend modules into one pipeline:

    scraper.get_history  ->  model.build_frame  ->  model.forecast_next_session
                         ->  strategy.evaluate_forecast  ->  JSON  ->  dashboard

Routes
------
GET  /                       the dashboard shell (server-rendered)
GET  /api/universe           configured tickers
GET  /api/analyze/<ticker>   full analysis for one symbol
GET  /api/analyze            batch analysis for the whole universe
GET  /api/health             liveness probe

Query flags accepted by the analysis routes:
    ?live=0      skip the network call and use the offline HTML corpus
    ?refresh=1   bypass the in-process cache
"""

from __future__ import annotations

import argparse
import logging
import os
import time
from typing import Any, Dict, Tuple

from flask import Flask, Response, jsonify, redirect, render_template, request, url_for

import model
import scraper
import strategy

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s %(name)s :: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("csnoai")

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

#: Live scraping is opt-in. Financial portals throttle aggressively, and a
#: classroom/demo network is exactly where that bites, so the default path is
#: the offline HTML corpus. Set CSNOAI_LIVE=1 (or pass --live) to enable.
LIVE_DEFAULT = os.environ.get("CSNOAI_LIVE", "0") == "1"

#: Absolute origin used for canonical URLs, Open Graph tags and the sitemap.
#: Unset it and the app derives the origin from the incoming request, which is
#: correct on localhost; set it once a real domain is pointed at the service:
#:     CSNOAI_SITE_URL=https://csnoai.example.edu
SITE_URL = os.environ.get("CSNOAI_SITE_URL", "").rstrip("/")

CACHE_TTL = 300  # seconds; one scrape per symbol per 5 minutes
_CACHE: Dict[Tuple[str, bool], Tuple[float, dict]] = {}


# --------------------------------------------------------------------------
# Pipeline
# --------------------------------------------------------------------------

def analyze(ticker: str, allow_live: bool) -> Dict[str, Any]:
    """Run the full scrape -> clean -> regress -> decide chain for one symbol."""
    scraped = scraper.get_history(ticker, allow_live=allow_live)
    frame = model.build_frame(scraped.rows, window=scraper.WINDOW)
    forecast = model.forecast_next_session(frame)

    last = frame.iloc[-1]
    previous_close = float(frame["close"].iloc[-2]) if len(frame) > 1 else float(last["close"])
    current_close = float(last["close"])
    change = current_close - previous_close

    signal = strategy.evaluate_forecast(current_close, forecast)

    return {
        "ticker": scraped.ticker,
        "company": scraped.company,
        "source": scraped.source,
        "source_url": scraped.url,
        "source_note": scraped.note,
        "fetched_at": scraped.fetched_at,
        "sessions": len(frame),
        "quote": {
            "date": last["date"].strftime("%Y-%m-%d"),
            "open": None if last["open"] != last["open"] else round(float(last["open"]), 2),
            "high": round(float(last["high"]), 2),
            "low": round(float(last["low"]), 2),
            "close": round(current_close, 2),
            "change": round(change, 2),
            "change_pct": round(change / previous_close * 100, 2) if previous_close else 0.0,
            "volume": None if last["volume"] != last["volume"] else int(last["volume"]),
        },
        "forecast": forecast.to_dict(),
        "signal": signal.to_dict(),
        "series": model.series_payload(frame, forecast),
        "table": [
            {
                "date": row["date"].strftime("%Y-%m-%d"),
                "t": int(row["t"]),
                "high": round(float(row["high"]), 2),
                "low": round(float(row["low"]), 2),
                "close": round(float(row["close"]), 2),
                "volume": None if row["volume"] != row["volume"] else int(row["volume"]),
            }
            for _, row in frame.iterrows()
        ],
    }


def analyze_cached(ticker: str, allow_live: bool, refresh: bool = False) -> Dict[str, Any]:
    key = (ticker.upper(), allow_live)
    now = time.time()
    if not refresh and key in _CACHE:
        stamped, payload = _CACHE[key]
        if now - stamped < CACHE_TTL:
            return payload
    payload = analyze(ticker, allow_live)
    _CACHE[key] = (now, payload)
    return payload


def site_url() -> str:
    """Absolute origin, from configuration when set and the request otherwise."""
    return SITE_URL or request.url_root.rstrip("/")


@app.context_processor
def inject_site_context():
    """Values every template's <head> needs: canonical URL and absolute origin."""
    base = site_url()
    return {
        "site_url": base,
        "canonical": base + request.path,
        "universe": scraper.UNIVERSE,
    }


def _wants_live() -> bool:
    flag = request.args.get("live")
    if flag is None:
        return LIVE_DEFAULT
    return flag.lower() in {"1", "true", "yes", "on"}


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------

def _thresholds() -> Dict[str, float]:
    """The live threshold values, so the pages can never drift from the engine."""
    return {
        "upside": strategy.UPSIDE_THRESHOLD * 100,
        "downside": strategy.DOWNSIDE_THRESHOLD * 100,
        "r2": strategy.R2_CONFIDENCE,
    }


@app.route("/")
def index():
    return render_template("index.html", thresholds=_thresholds(), live_default=LIVE_DEFAULT)


@app.route("/methodology")
def methodology():
    return render_template("methodology.html", thresholds=_thresholds())


@app.route("/api/universe")
def api_universe():
    return jsonify(
        {
            "universe": [{"ticker": t, "company": n} for t, n in scraper.UNIVERSE.items()],
            "window": scraper.WINDOW,
            "live_default": LIVE_DEFAULT,
        }
    )


@app.route("/api/analyze/<ticker>")
def api_analyze(ticker: str):
    try:
        payload = analyze_cached(ticker, _wants_live(), request.args.get("refresh") == "1")
    except scraper.ScrapeError as exc:
        return jsonify({"error": "scrape_failed", "detail": str(exc)}), 404
    except model.ModelError as exc:
        return jsonify({"error": "model_failed", "detail": str(exc)}), 422
    except Exception as exc:                                    # pragma: no cover
        log.exception("unhandled failure for %s", ticker)
        return jsonify({"error": "internal_error", "detail": str(exc)}), 500
    return jsonify(payload)


@app.route("/api/analyze")
def api_analyze_all():
    allow_live = _wants_live()
    refresh = request.args.get("refresh") == "1"
    results, errors = [], []
    for symbol in scraper.UNIVERSE:
        try:
            results.append(analyze_cached(symbol, allow_live, refresh))
        except Exception as exc:                                # pragma: no cover
            log.warning("skipping %s: %s", symbol, exc)
            errors.append({"ticker": symbol, "detail": str(exc)})

    counts = {"BUY": 0, "SELL": 0, "HOLD": 0}
    for item in results:
        counts[item["signal"]["action"]] += 1

    return jsonify(
        {
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "window": scraper.WINDOW,
            "results": results,
            "errors": errors,
            "summary": {
                "tracked": len(results),
                "signals": counts,
                "avg_confidence": round(
                    sum(r["signal"]["confidence"] for r in results) / len(results), 1
                ) if results else 0.0,
            },
        }
    )


@app.route("/api/health")
def api_health():
    return jsonify({"status": "ok", "service": "csnoai", "cached": len(_CACHE)})


# --------------------------------------------------------------------------
# Crawler-facing documents
# --------------------------------------------------------------------------

@app.route("/favicon.ico")
def favicon_ico():
    """Browsers and crawlers probe this path even when a <link> tag is present."""
    return redirect(url_for("static", filename="favicon.svg"), code=301)


@app.route("/robots.txt")
def robots_txt():
    """Everything is crawlable except the JSON API, which serves no HTML."""
    base = site_url()
    body = "\n".join(
        [
            "User-agent: *",
            "Disallow: /api/",
            "",
            f"Sitemap: {base}{url_for('sitemap_xml')}",
            "",
        ]
    )
    return Response(body, mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap_xml():
    """The two indexable pages. The API is excluded; it returns no HTML."""
    base = site_url()
    today = time.strftime("%Y-%m-%d")
    pages = [
        (url_for("index"), "daily", "1.0"),
        (url_for("methodology"), "monthly", "0.7"),
    ]
    entries = "\n".join(
        f"  <url>\n"
        f"    <loc>{base}{path}</loc>\n"
        f"    <lastmod>{today}</lastmod>\n"
        f"    <changefreq>{freq}</changefreq>\n"
        f"    <priority>{priority}</priority>\n"
        f"  </url>"
        for path, freq, priority in pages
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{entries}\n"
        "</urlset>\n"
    )
    return Response(xml, mimetype="application/xml")


@app.route("/llms.txt")
def llms_txt():
    """Machine-readable summary for language models, per the llms.txt convention."""
    base = site_url()
    body = f"""# CsNoAI

> A gaming and esports sector stock-forecasting dashboard. It scrapes ten
> trading sessions out of a raw HTML price table, fits independent ordinary
> least squares models to the daily high and the daily low, projects both one
> session ahead, and converts the result into a buy, sell or hold signal.

Built as academic coursework. Deliberately transparent: no machine-learning
library, no API wrapper, no hidden state. Given the same ten rows the
arithmetic is reproducible by hand.

## Pages

- [Dashboard]({base}/): live signals for all five tracked equities.
- [Methodology]({base}/methodology): the full derivation and the decision rules.

## Method

- Extraction: `requests` + `BeautifulSoup(html, "html.parser")`, walking
  `<table>` to `<tbody>` to `<tr>` to `<td>`. One static page per symbol, no
  crawling. Falls back to an offline HTML snapshot parsed by the same code.
- Structuring: `pandas` cleans, de-duplicates and clips to the trailing ten
  sessions, indexed t = 1..n.
- Model: ordinary least squares, y = m*x + c, solved as
  beta = (X'X)^-1 X'y with `numpy`. Reports slope, intercept, R^2, residual
  sigma, standard error of the slope and its t-statistic.
- Forecast: both fitted lines evaluated at t = 11.
- Decision: SELL if downside >= {strategy.DOWNSIDE_THRESHOLD * 100:.1f}% or slope < 0;
  else BUY if upside >= {strategy.UPSIDE_THRESHOLD * 100:.1f}% and R^2 > {strategy.R2_CONFIDENCE:.2f} and slope > 0;
  else HOLD.

## Coverage

{chr(10).join(f"- {sym}: {name}" for sym, name in scraper.UNIVERSE.items())}

## API

- `{base}/api/analyze` — every tracked equity plus a sector summary.
- `{base}/api/analyze/<ticker>` — one symbol.
- `{base}/api/universe` — the configured tickers.
- `{base}/api/health` — liveness.

Query flags: `?live=0|1` selects the live scrape or the offline corpus,
`?refresh=1` bypasses the five-minute cache.

## Caveats

Linear extrapolation over ten sessions. Not investment advice. The offline
corpus is realistically shaped but synthetic, not a live market record.
"""
    return Response(body, mimetype="text/plain")


# --------------------------------------------------------------------------
# Error pages
# --------------------------------------------------------------------------

@app.errorhandler(404)
def page_not_found(error):
    """HTML for browsers, JSON for anything under /api/."""
    if request.path.startswith("/api/"):
        return jsonify({"error": "not_found", "detail": "no such endpoint"}), 404
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_error(error):                                      # pragma: no cover
    if request.path.startswith("/api/"):
        return jsonify({"error": "internal_error", "detail": "unhandled failure"}), 500
    return render_template("500.html"), 500


def main() -> None:
    parser = argparse.ArgumentParser(description="CsNoAI dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--live", action="store_true", help="attempt live scraping by default")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    global LIVE_DEFAULT
    LIVE_DEFAULT = LIVE_DEFAULT or args.live

    log.info("CsNoAI starting on http://%s:%s", args.host, args.port)
    log.info("live scraping default: %s", "ON" if LIVE_DEFAULT else "OFF (offline HTML corpus)")
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
