from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

# ---- Risk boundary thresholds --------------------------------------------
UPSIDE_THRESHOLD = 0.015
DOWNSIDE_THRESHOLD = 0.015
R2_CONFIDENCE = 0.40

BUY, SELL, HOLD = "BUY", "SELL", "HOLD"


@dataclass
class Signal:
    action: str
    headline: str
    upside_pct: float
    downside_pct: float
    risk_reward: float | None
    confidence: float
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "headline": self.headline,
            "upside_pct": round(self.upside_pct, 2),
            "downside_pct": round(self.downside_pct, 2),
            "risk_reward": None if self.risk_reward is None else round(self.risk_reward, 2),
            "confidence": round(self.confidence, 1),
            "reasons": self.reasons,
            "thresholds": {
                "upside_pct": UPSIDE_THRESHOLD * 100,
                "downside_pct": DOWNSIDE_THRESHOLD * 100,
                "r2": R2_CONFIDENCE,
            },
        }


def evaluate(
    current_close: float,
    predicted_high: float,
    predicted_low: float,
    r2_high: float,
    r2_low: float,
    slope_high: float,
    slope_low: float,
) -> Signal:
    if current_close <= 0:
        raise ValueError("current close must be positive")

    upside = (predicted_high - current_close) / current_close
    downside = (current_close - predicted_low) / current_close

    upside_pct = upside * 100
    downside_pct = downside * 100
    confidence = max(0.0, (r2_high + r2_low) / 2.0) * 100
    risk_reward = (upside / downside) if downside > 0 else None

    reasons: List[str] = []

    if r2_high < R2_CONFIDENCE or r2_low < R2_CONFIDENCE:
        if r2_high < R2_CONFIDENCE:
            reasons.append(
                f"R^2(High) = {r2_high:.3f} is below the {R2_CONFIDENCE:.2f} confidence gate."
            )
        if r2_low < R2_CONFIDENCE:
            reasons.append(
                f"R^2(Low) = {r2_low:.3f} is below the {R2_CONFIDENCE:.2f} confidence gate."
            )
        reasons.append("Forecast is downgraded to HOLD because the 10-session trend is not reliable enough.")
        return Signal(
            HOLD, "Insufficient model confidence",
            upside_pct, downside_pct, risk_reward, confidence, reasons,
        )

    # ---- Rule 1: capital-preservation override ------------------------
    if downside >= DOWNSIDE_THRESHOLD or slope_high < 0:
        if downside >= DOWNSIDE_THRESHOLD:
            reasons.append(
                f"Downside risk {downside_pct:.2f}% breaches the "
                f"{DOWNSIDE_THRESHOLD * 100:.1f}% drawdown boundary."
            )
        if slope_high < 0:
            reasons.append(
                f"High-series slope is negative (m = {slope_high:+.4f}); "
                "the short-term trend is decaying."
            )
        reasons.append(f"Model confidence R^2(High) = {r2_high:.3f}.")
        return Signal(
            SELL, "Reduce exposure / take profit",
            upside_pct, downside_pct, risk_reward, confidence, reasons,
        )

    # ---- Rule 2: qualified entry --------------------------------------
    if upside >= UPSIDE_THRESHOLD and r2_high > R2_CONFIDENCE and slope_high > 0:
        reasons.append(
            f"Projected upside {upside_pct:.2f}% clears the "
            f"{UPSIDE_THRESHOLD * 100:.1f}% entry boundary."
        )
        reasons.append(
            f"Trend confirmed: m = {slope_high:+.4f} with R^2 = {r2_high:.3f} "
            f"(> {R2_CONFIDENCE:.2f} confidence floor)."
        )
        if downside <= 0:
            reasons.append(
                f"No projected downside: the modelled low sits "
                f"{abs(downside_pct):.2f}% above today's close."
            )
        else:
            reasons.append(f"Downside risk contained at {downside_pct:.2f}%.")
        return Signal(
            BUY, "Accumulate — trend and confidence aligned",
            upside_pct, downside_pct, risk_reward, confidence, reasons,
        )

    # ---- Rule 3: no edge ----------------------------------------------
    if upside < UPSIDE_THRESHOLD:
        reasons.append(
            f"Projected upside {upside_pct:.2f}% is below the "
            f"{UPSIDE_THRESHOLD * 100:.1f}% entry boundary."
        )
    if r2_high <= R2_CONFIDENCE:
        reasons.append(
            f"R^2 = {r2_high:.3f} fails the {R2_CONFIDENCE:.2f} confidence "
            "floor — the fit is closer to noise than to trend."
        )
    if downside <= 0:
        reasons.append(
            f"No projected downside: the modelled low sits "
            f"{abs(downside_pct):.2f}% above today's close."
        )
    else:
        reasons.append(f"Downside risk {downside_pct:.2f}% is within tolerance.")
    return Signal(
        HOLD, "No statistical edge — stay flat",
        upside_pct, downside_pct, risk_reward, confidence, reasons,
    )


def evaluate_forecast(current_close: float, forecast) -> Signal:
    return evaluate(
        current_close=current_close,
        predicted_high=forecast.predicted_high,
        predicted_low=forecast.predicted_low,
        r2_high=forecast.high_model.r2,
        r2_low=forecast.low_model.r2,
        slope_high=forecast.high_model.slope,
        slope_low=forecast.low_model.slope,
    )
