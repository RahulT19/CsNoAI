# model.py
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List, Sequence

import numpy as np
import pandas as pd

MIN_SESSIONS = 3

class ModelError(ValueError):
    pass

def build_frame(rows: Sequence[dict], window: int = 10) -> pd.DataFrame:
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

    swapped = frame["high"] < frame["low"]
    if swapped.any():
        frame.loc[swapped, ["high", "low"]] = frame.loc[swapped, ["low", "high"]].values

    frame["t"] = np.arange(1, len(frame) + 1, dtype=float)
    frame["label"] = frame["date"].dt.strftime("%d %b")
    frame["range"] = frame["high"] - frame["low"]
    return frame

@dataclass
class OLSFit:
    slope: float
    intercept: float
    r2: float
    n: int
    std_error: float
    slope_stderr: float
    intercept_stderr: float
    slope_intercept_covariance: float
    t_stat: float
    fitted: List[float]

    def predict(self, x) -> float | np.ndarray:
        return self.slope * np.asarray(x, dtype=float) + self.intercept

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["fitted"] = [round(v, 4) for v in self.fitted]
        return payload

    def prediction_stderr(self, x: float) -> float:
        mean_variance = (
            (x ** 2) * (self.slope_stderr ** 2)
            + self.intercept_stderr ** 2
            + 2 * x * self.slope_intercept_covariance
        )
        return float(np.sqrt(max(0.0, mean_variance) + self.std_error ** 2))


def fit_ols(x: Sequence[float], y: Sequence[float]) -> OLSFit:
    xv = np.asarray(x, dtype=float)
    yv = np.asarray(y, dtype=float)

    if xv.shape != yv.shape:
        raise ModelError("x and y must have identical shape")
    n = xv.size
    if n < MIN_SESSIONS:
        raise ModelError(f"need at least {MIN_SESSIONS} observations, got {n}")

    if np.ptp(xv) < 1e-12:
        raise ModelError("singular design matrix (zero variance in x)")
        
    coefficients, covariance = np.polyfit(xv, yv, 1, cov=True)
    slope, intercept = coefficients

    fitted = slope * xv + intercept
    residuals = yv - fitted
    ss_res = float(residuals @ residuals)
    ss_tot = float(((yv - yv.mean()) ** 2).sum())

    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0

    dof = n - 2
    sigma = float(np.sqrt(ss_res / dof)) if dof > 0 else 0.0
    slope_stderr = float(np.sqrt(max(0.0, covariance[0, 0])))
    intercept_stderr = float(np.sqrt(max(0.0, covariance[1, 1])))
    slope_intercept_covariance = float(covariance[0, 1])
    t_stat = slope / slope_stderr if slope_stderr not in (0.0, float("inf")) else 0.0

    return OLSFit(
        slope=float(slope),
        intercept=float(intercept),
        r2=float(r2),
        n=int(n),
        std_error=sigma,
        slope_stderr=slope_stderr,
        intercept_stderr=intercept_stderr,
        slope_intercept_covariance=slope_intercept_covariance,
        t_stat=float(t_stat),
        fitted=[float(v) for v in fitted],
    )

@dataclass
class Forecast:
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
    x = frame["t"].to_numpy(dtype=float)
    high_model = fit_ols(x, frame["high"].to_numpy(dtype=float))
    low_model = fit_ols(x, frame["low"].to_numpy(dtype=float))

    horizon = int(x[-1] + 1)
    predicted_high = float(high_model.predict(horizon))
    predicted_low = float(low_model.predict(horizon))

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