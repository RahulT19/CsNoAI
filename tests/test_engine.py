"""
tests/test_engine.py — regression tests for the CsNoAI engine
=================================================================
Run from the project root:  python -m tests.test_engine
                       or:  python -m pytest tests -q   (pytest optional)

The suite is written with plain ``assert`` statements and a tiny runner so it
executes with or without pytest installed — a deliberate choice so an
evaluator can verify the maths on any machine.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import model
import scraper
import strategy
import db


# ---- Member 1: DOM parsing ------------------------------------------------

def test_parser_extracts_ten_sessions():
    for ticker in scraper.UNIVERSE:
        rows = scraper.parse_history_table(scraper._FALLBACK_PAGES[ticker])
        assert len(rows) == 10, f"{ticker}: expected 10 rows, got {len(rows)}"
        assert rows == sorted(rows, key=lambda r: r["date"]), f"{ticker}: not chronological"
        for row in rows:
            assert row["high"] >= row["low"], f"{ticker}: high below low on {row['date']}"


def test_parser_skips_corporate_action_rows():
    html = """
    <table><thead><tr><th>Date</th><th>Open</th><th>High</th><th>Low</th>
    <th>Close</th><th>Volume</th></tr></thead><tbody>
      <tr><td>Sep 4, 2026</td><td>10.00</td><td>11.00</td><td>9.50</td><td>10.50</td><td>1,000</td></tr>
      <tr><td>Sep 3, 2026</td><td colspan="5">0.35 Dividend</td></tr>
      <tr><td>Sep 2, 2026</td><td>9.00</td><td>10.00</td><td>8.80</td><td>9.60</td><td>2,000</td></tr>
    </tbody></table>"""
    rows = scraper.parse_history_table(html)
    assert len(rows) == 2
    assert [r["date"] for r in rows] == ["2026-09-02", "2026-09-04"]


def test_parser_rejects_a_page_with_no_price_table():
    try:
        scraper.parse_history_table("<html><body><table><tr><td>nope</td></tr></table></body></html>")
    except scraper.ScrapeError:
        return
    raise AssertionError("expected ScrapeError on a page with no price table")


def test_fallback_engages_when_live_is_disabled():
    original_get_history = scraper.db.get_history
    scraper.db.get_history = lambda ticker: []
    try:
        result = scraper.get_history("NVDA", allow_live=False)
    finally:
        scraper.db.get_history = original_get_history
    assert result.source == "fallback"
    assert result.company == "NVIDIA Corporation"
    assert len(result.rows) == 10


# ---- Member 2: data engineering -------------------------------------------

def test_frame_cleans_sorts_and_indexes():
    messy = [
        {"date": "2026-09-02", "open": None, "high": "12.5", "low": "11.0", "close": "12.0", "volume": None},
        {"date": "2026-09-01", "open": None, "high": 11.0, "low": 10.0, "close": 10.8, "volume": 5},
        {"date": "2026-09-03", "open": None, "high": None, "low": 11.5, "close": 12.4, "volume": 6},
        {"date": "2026-09-02", "open": None, "high": 12.9, "low": 11.2, "close": 12.2, "volume": 7},
        {"date": "2026-09-04", "open": None, "high": 12.0, "low": 13.0, "close": 12.6, "volume": 8},
    ]
    frame = model.build_frame(messy)
    assert len(frame) == 3, "row with a missing high and the duplicate should be removed"
    assert list(frame["t"]) == [1.0, 2.0, 3.0]
    assert frame["date"].is_monotonic_increasing
    assert float(frame["high"].iloc[1]) == 12.9, "the later duplicate should win"
    assert float(frame["high"].iloc[2]) == 13.0, "inverted high/low should be repaired"


def test_frame_clips_to_the_window():
    rows = [
        {"date": f"2026-01-{d:02d}", "open": 1, "high": 2 + d, "low": 1 + d, "close": 1.5 + d, "volume": 10}
        for d in range(1, 21)
    ]
    frame = model.build_frame(rows, window=10)
    assert len(frame) == 10
    assert frame["date"].iloc[0].strftime("%Y-%m-%d") == "2026-01-11"


def test_frame_rejects_too_few_sessions():
    try:
        model.build_frame([{"date": "2026-09-01", "open": 1, "high": 2, "low": 1, "close": 1.5, "volume": 1}])
    except model.ModelError:
        return
    raise AssertionError("expected ModelError for a single session")


# ---- Member 3: the regression maths ---------------------------------------

def test_ols_recovers_an_exact_line():
    x = np.arange(1, 11, dtype=float)
    fit = model.fit_ols(x, 2.5 * x + 7.0)
    assert abs(fit.slope - 2.5) < 1e-9
    assert abs(fit.intercept - 7.0) < 1e-9
    assert abs(fit.r2 - 1.0) < 1e-12


def test_ols_matches_numpy_polyfit():
    rng = np.random.default_rng(7)
    x = np.arange(1, 11, dtype=float)
    for _ in range(40):
        y = 3.0 * x + 12.0 + rng.normal(0, 2.5, size=x.size)
        fit = model.fit_ols(x, y)
        slope, intercept = np.polyfit(x, y, 1)
        assert abs(fit.slope - slope) < 1e-9
        assert abs(fit.intercept - intercept) < 1e-9


def test_ols_matches_the_closed_form_summation_identity():
    x = np.arange(1, 11, dtype=float)
    y = np.array([12, 14, 13, 17, 16, 19, 21, 20, 24, 26], dtype=float)
    n = x.size
    m = (n * (x * y).sum() - x.sum() * y.sum()) / (n * (x ** 2).sum() - x.sum() ** 2)
    c = y.mean() - m * x.mean()
    fit = model.fit_ols(x, y)
    assert abs(fit.slope - m) < 1e-10
    assert abs(fit.intercept - c) < 1e-10


def test_r2_is_zero_for_a_flat_series():
    x = np.arange(1, 11, dtype=float)
    fit = model.fit_ols(x, np.full(10, 42.0))
    assert fit.r2 == 0.0
    assert abs(fit.slope) < 1e-12


def test_forecast_evaluates_at_the_next_index():
    frame = model.build_frame(
        [
            {"date": f"2026-03-{d:02d}", "open": None, "high": 100 + d, "low": 95 + d,
             "close": 98 + d, "volume": 1}
            for d in range(1, 11)
        ]
    )
    forecast = model.forecast_next_session(frame)
    assert forecast.horizon == 11
    assert abs(forecast.predicted_high - 111.0) < 1e-9
    assert abs(forecast.predicted_low - 106.0) < 1e-9
    assert forecast.predicted_high >= forecast.predicted_low


def test_series_payload_shape():
    frame = model.build_frame(
        [
            {"date": f"2026-03-{d:02d}", "open": None, "high": 100 + d, "low": 95 + d,
             "close": 98 + d, "volume": 1}
            for d in range(1, 11)
        ]
    )
    forecast = model.forecast_next_session(frame)
    payload = model.series_payload(frame, forecast)
    assert len(payload["labels"]) == 11
    assert len(payload["high"]) == 11 and payload["high"][-1] is None
    assert len(payload["high_trend"]) == 11 and payload["high_trend"][-1] is not None


# ---- Member 5: the decision table -----------------------------------------

def _signal(close, high, low, r2=0.9, slope=1.0):
    return strategy.evaluate(close, high, low, r2, r2, slope, slope).action


def test_buy_requires_upside_confidence_and_trend():
    assert _signal(100, 102.0, 99.5) == strategy.BUY
    assert _signal(100, 101.4, 99.5) == strategy.HOLD
    assert _signal(100, 102.0, 99.5, r2=0.30) == strategy.HOLD
    assert _signal(100, 102.0, 99.5, slope=-0.4) == strategy.SELL


def test_boundaries_are_inclusive():
    assert _signal(100, 101.5, 99.5) == strategy.BUY
    assert _signal(100, 100.4, 98.5) == strategy.SELL


def test_sell_overrides_a_tempting_upside():
    assert _signal(100, 103.0, 97.0) == strategy.SELL


def test_hold_when_nothing_triggers():
    assert _signal(100, 100.8, 99.6) == strategy.HOLD


def test_signal_reports_percentages_and_risk_reward():
    signal = strategy.evaluate(100, 102.0, 99.0, 0.9, 0.9, 1.0, 1.0)
    assert abs(signal.upside_pct - 2.0) < 1e-9
    assert abs(signal.downside_pct - 1.0) < 1e-9
    assert abs(signal.risk_reward - 2.0) < 1e-9
    assert signal.risk_reward is not None


def test_risk_reward_is_none_without_downside():
    signal = strategy.evaluate(100, 103.0, 100.5, 0.9, 0.9, 1.0, 1.0)
    assert signal.risk_reward is None


def test_rejects_a_non_positive_close():
    try:
        strategy.evaluate(0, 1, 1, 0.9, 0.9, 1.0, 1.0)
    except ValueError:
        return
    raise AssertionError("expected ValueError for a non-positive close")


# ---- Persistence and end to end ------------------------------------------

def test_db_history_round_trip():
    rows = scraper.parse_history_table(scraper._FALLBACK_PAGES["TTWO"])
    db.save_history("TEST", "Test Company", rows, "test")
    restored = db.get_history("TEST")
    assert len(restored) == 10
    assert restored[-1]["date"] == rows[-1]["date"]


def test_full_pipeline_for_every_tracked_equity():
    for ticker in scraper.UNIVERSE:
        scraped = scraper.get_history(ticker, allow_live=False)
        frame = model.build_frame(scraped.rows)
        forecast = model.forecast_next_session(frame)
        signal = strategy.evaluate_forecast(float(frame["close"].iloc[-1]), forecast)
        assert len(frame) == 10
        assert signal.action in {strategy.BUY, strategy.SELL, strategy.HOLD}
        assert forecast.predicted_high >= forecast.predicted_low
        assert len(model.series_payload(frame, forecast)["high_trend"]) == 11


# ---- runner ---------------------------------------------------------------

def _main() -> int:
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    failures = 0
    for name, func in tests:
        try:
            func()
        except Exception as exc:
            failures += 1
            print(f"  FAIL  {name}\n        {type(exc).__name__}: {exc}")
        else:
            print(f"  pass  {name}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_main())
