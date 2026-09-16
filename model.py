"""
model.py — Data engineering + Ordinary Least Squares regression engine
======================================================================
Owners: Member 2 (Data Engineer) and Member 3 (Quantitative Modeler),
        with Member 4 (Predictive Analyst) supplying the R^2 / forecast layer.

Mathematics
-----------
For each target series y (daily High, daily Low) we map the trading
sessions to an ordinal time index x = 1, 2, ..., n and fit the line

    y_hat = m*x + c

by minimising the residual sum of squares.  Solved through the normal
equations in explicit matrix form,

    X = [1  x]          (n x 2 design matrix)
    beta = (X^T X)^-1 X^T y,      beta = [c, m]

which is algebraically identical to the closed forms

    m = ( n*sum(xy) - sum(x)*sum(y) ) / ( n*sum(x^2) - (sum(x))^2 )
    c = mean(y) - m*mean(x)

Goodness of fit is the coefficient of determination

    R^2 = 1 - SS_res / SS_tot
        = 1 - sum((y - y_hat)^2) / sum((y - mean(y))^2)

The forecast for the next session is the model evaluated at x = n + 1.
Everything is transparent arithmetic — no black-box estimator anywhere.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List, Sequence

import numpy as np
import pandas as pd

MIN_SESSIONS = 3  # two points give a perfect fit and a meaningless R^2


class ModelError(ValueError):
    """Raised when the cleaned frame cannot support a regression."""


# --------------------------------------------------------------------------
# Member 2 — data engineering
# --------------------------------------------------------------------------

def build_frame(rows: Sequence[dict], window: int = 10) -> pd.DataFrame:
    """Turn raw scraped strings into a clean, indexed time-series frame.

    Steps: coerce to numeric, drop unusable sessions, de-duplicate repeated
    dates, sort chronologically, clip to the trailing ``window`` sessions and
    attach the ordinal regression index ``t = 1..n``.
    """
    frame = pd.DataFrame(list(rows))
    if frame.empty:
        raise ModelError("no rows to model")

    for column in ("open", "high", "low", "close", "volume"):
        if column not in frame.columns:
            frame[column] = np.nan
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")

    frame = (
        frame.dropna(subset=["date", "high", "low", "close"])
             .drop_duplicates(subset="date", keep="last")
             .sort_values("date")
             .tail(window)
             .reset_index(drop=True)
    )

    if len(frame) < MIN_SESSIONS:
        raise ModelError(f"need at least {MIN_SESSIONS} clean sessions, got {len(frame)}")

    # A high below its own low means a mangled cell — repair by swapping.
    swapped = frame["high"] < frame["low"]
    if swapped.any():
        frame.loc[swapped, ["high", "low"]] = frame.loc[swapped, ["low", "high"]].values

    frame["t"] = np.arange(1, len(frame) + 1, dtype=float)
    frame["label"] = frame["date"].dt.strftime("%d %b")
    frame["range"] = frame["high"] - frame["low"]
    return frame


# --------------------------------------------------------------------------
# Member 3 — the regression itself
# --------------------------------------------------------------------------

@dataclass
class OLSFit:
    """A fitted simple-linear model plus its diagnostic statistics."""

    slope: float
    intercept: float
    r2: float
    n: int
    std_error: float      # standard error of the regression (residual sigma)
    slope_stderr: float   # standard error of the slope estimate
    t_stat: float         # slope / slope_stderr
    fitted: List[float]

    def predict(self, x) -> float | np.ndarray:
        return self.slope * np.asarray(x, dtype=float) + self.intercept

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["fitted"] = [round(v, 4) for v in self.fitted]
        return payload


def fit_ols(x: Sequence[float], y: Sequence[float]) -> OLSFit:
    """Least-squares fit of ``y = m*x + c`` via the normal equations."""
    xv = np.asarray(x, dtype=float)
    yv = np.asarray(y, dtype=float)

    if xv.shape != yv.shape:
        raise ModelError("x and y must have identical shape")
    n = xv.size
    if n < MIN_SESSIONS:
        raise ModelError(f"need at least {MIN_SESSIONS} observations, got {n}")

    # Design matrix X = [1, x]  ->  beta = (X'X)^-1 X'y, solved (not inverted).
    design = np.column_stack([np.ones(n), xv])
    gram = design.T @ design
    moment = design.T @ yv
    if abs(np.linalg.det(gram)) < 1e-12:
        raise ModelError("singular design matrix (zero variance in x)")
    intercept, slope = np.linalg.solve(gram, moment)

    fitted = slope * xv + intercept
    residuals = yv - fitted
    ss_res = float(residuals @ residuals)
    ss_tot = float(((yv - yv.mean()) ** 2).sum())

    # A perfectly flat series has no variance to explain; call that R^2 = 0.
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0

    dof = n - 2
    sigma = float(np.sqrt(ss_res / dof)) if dof > 0 else 0.0
    sxx = float(((xv - xv.mean()) ** 2).sum())
    slope_stderr = sigma / np.sqrt(sxx) if sxx > 0 else float("inf")
    t_stat = slope / slope_stderr if slope_stderr not in (0.0, float("inf")) else 0.0

    return OLSFit(
        slope=float(slope),
        intercept=float(intercept),
        r2=float(r2),
        n=int(n),
        std_error=sigma,
        slope_stderr=float(slope_stderr),
        t_stat=float(t_stat),
        fitted=[float(v) for v in fitted],
    )


# --------------------------------------------------------------------------
# Member 4 — multi-target forecasting
# --------------------------------------------------------------------------

@dataclass
class Forecast:
    """Next-session projection for both the High and the Low series."""

    horizon: int
    predicted_high: float
    predicted_low: float
    predicted_mid: float
    predicted_spread: float
    high_model: OLSFit
    low_model: OLSFit

    def to_dict(self) -> dict:
        return {
            "horizon": self.horizon,
            "predicted_high": round(self.predicted_high, 2),
            "predicted_low": round(self.predicted_low, 2),
            "predicted_mid": round(self.predicted_mid, 2),
            "predicted_spread": round(self.predicted_spread, 2),
            "high_model": self.high_model.to_dict(),
            "low_model": self.low_model.to_dict(),
        }


def forecast_next_session(frame: pd.DataFrame) -> Forecast:
    """Fit independent High and Low models and evaluate them at x = n + 1."""
    x = frame["t"].to_numpy(dtype=float)
    high_model = fit_ols(x, frame["high"].to_numpy(dtype=float))
    low_model = fit_ols(x, frame["low"].to_numpy(dtype=float))

    horizon = int(x[-1] + 1)
    predicted_high = float(high_model.predict(horizon))
    predicted_low = float(low_model.predict(horizon))

    # The two lines are fitted independently and can cross on a converging
    # series; enforce the structural invariant High >= Low before it reaches
    # the strategy layer.
    if predicted_low > predicted_high:
        predicted_high, predicted_low = predicted_low, predicted_high

    return Forecast(
        horizon=horizon,
        predicted_high=predicted_high,
        predicted_low=predicted_low,
        predicted_mid=(predicted_high + predicted_low) / 2.0,
        predicted_spread=predicted_high - predicted_low,
        high_model=high_model,
        low_model=low_model,
    )


def series_payload(frame: pd.DataFrame, forecast: Forecast) -> Dict[str, list]:
    """Chart-ready arrays: actuals for days 1..n, trendlines out to n+1."""
    x_extended = np.append(frame["t"].to_numpy(dtype=float), float(forecast.horizon))
    return {
        "labels": frame["label"].tolist() + ["Day 11"],
        "dates": frame["date"].dt.strftime("%Y-%m-%d").tolist(),
        "high": [round(v, 2) for v in frame["high"]] + [None],
        "low": [round(v, 2) for v in frame["low"]] + [None],
        "close": [round(v, 2) for v in frame["close"]] + [None],
        "high_trend": [round(float(v), 2) for v in forecast.high_model.predict(x_extended)],
        "low_trend": [round(float(v), 2) for v in forecast.low_model.predict(x_extended)],
    }
