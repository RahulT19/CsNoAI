from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

import db
import model
import scraper
import strategy

ACTION_COLOURS = {"BUY": "#27ae60", "SELL": "#e74c3c", "HOLD": "#f39c12"}


class CsNoAIApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CsNoAI - Gaming Equity Forecast")
        self.geometry("1040x760")
        self.minsize(900, 650)
        self.current = None
        self.ticker, self.use_live = tk.StringVar(value="EA"), tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="Ready. Choose a ticker and run analysis.")
        self._build_ui()

    def _build_ui(self):
        controls = ttk.Frame(self, padding=12); controls.pack(fill="x")
        ttk.Label(controls, text="Ticker:").pack(side="left")
        ttk.Combobox(controls, textvariable=self.ticker, values=list(scraper.UNIVERSE), state="readonly", width=10).pack(side="left", padx=(6, 16))
        ttk.Checkbutton(controls, text="Use Live Scraping", variable=self.use_live).pack(side="left")
        ttk.Button(controls, text="Run Analysis", command=self.run_analysis).pack(side="left", padx=12)
        ttk.Button(controls, text="Save to MongoDB", command=self.save_to_db).pack(side="left")
        self.verdict = tk.Label(self, text="Run an analysis", fg="white", bg="#34495e", font=("Segoe UI", 18, "bold"), padx=18, pady=14)
        self.verdict.pack(fill="x", padx=12, pady=(0, 10))
        metrics = ttk.LabelFrame(self, text="Model Metrics", padding=10); metrics.pack(fill="x", padx=12)
        self.high_metrics, self.low_metrics = tk.StringVar(value="High: —"), tk.StringVar(value="Low: —")
        ttk.Label(metrics, textvariable=self.high_metrics).pack(anchor="w")
        ttk.Label(metrics, textvariable=self.low_metrics).pack(anchor="w", pady=(5, 0))
        table_box = ttk.LabelFrame(self, text="Price History (10 sessions)", padding=8); table_box.pack(fill="both", expand=True, padx=12, pady=10)
        columns = ("t", "date", "high", "low", "close", "volume")
        self.table = ttk.Treeview(table_box, columns=columns, show="headings", height=10)
        for column, width in zip(columns, (45, 125, 110, 110, 110, 160)):
            self.table.heading(column, text=column.title()); self.table.column(column, width=width, anchor="center")
        self.table.pack(fill="both", expand=True)
        audit_box = ttk.LabelFrame(self, text="Decision Audit Log", padding=8); audit_box.pack(fill="x", padx=12, pady=(0, 10))
        self.audit = tk.Text(audit_box, height=5, wrap="word", state="disabled"); self.audit.pack(fill="x")
        ttk.Label(self, textvariable=self.status, relief="sunken", anchor="w", padding=(8, 4)).pack(fill="x", side="bottom")

    def run_analysis(self):
        try:
            scraped = scraper.get_history(self.ticker.get(), allow_live=self.use_live.get())
            frame = model.build_frame(scraped.rows, window=scraper.WINDOW)
            forecast = model.forecast_next_session(frame)
            signal = strategy.evaluate_forecast(float(frame["close"].iloc[-1]), forecast)
        except Exception as exc:
            messagebox.showerror("Analysis failed", str(exc)); self.status.set(f"Analysis failed: {exc}"); return
        self.current = (scraped, frame, forecast, signal); self._render(*self.current)

    def _render(self, scraped, frame, forecast, signal):
        self.verdict.configure(text=f"{signal.action}  |  Upside {signal.upside_pct:+.2f}%  |  Downside {signal.downside_pct:+.2f}%  |  Confidence {signal.confidence:.1f}%", bg=ACTION_COLOURS[signal.action])
        self.high_metrics.set(self._metrics_text("High", forecast.high_model, forecast.horizon)); self.low_metrics.set(self._metrics_text("Low", forecast.low_model, forecast.horizon))
        self.table.delete(*self.table.get_children())
        for _, row in frame.iterrows():
            volume = "—" if row["volume"] != row["volume"] else f"{int(row['volume']):,}"
            self.table.insert("", "end", values=(int(row["t"]), row["date"].strftime("%Y-%m-%d"), f"{row['high']:.2f}", f"{row['low']:.2f}", f"{row['close']:.2f}", volume))
        self.audit.configure(state="normal"); self.audit.delete("1.0", "end"); self.audit.insert("1.0", "\n".join(f"• {reason}" for reason in signal.reasons)); self.audit.configure(state="disabled")
        origin = {"live": "Live Scrape", "fallback": "Offline Fallback", "cache": "MongoDB Cache"}[scraped.source]
        database = "MongoDB connected" if db.is_connected() else "MongoDB offline (in-memory fallback)"
        self.status.set(f"{origin} | {database}")

    @staticmethod
    def _metrics_text(name, fit, horizon):
        return f"{name}: y = {fit.slope:.4f} * x + {fit.intercept:.4f}  |  slope SE = {fit.slope_stderr:.4f}  |  intercept SE = {fit.intercept_stderr:.4f}  |  R² = {fit.r2:.4f}  |  Day {horizon} forecast SE = {fit.prediction_stderr(horizon):.4f}"

    def save_to_db(self):
        if self.current is None:
            messagebox.showinfo("No analysis", "Run an analysis before saving."); return
        scraped, frame, forecast, signal = self.current
        rows = [{"date": row["date"].strftime("%Y-%m-%d"), "open": row["open"], "high": row["high"], "low": row["low"], "close": row["close"], "volume": row["volume"]} for _, row in frame.iterrows()]
        history_ok = db.save_history(scraped.ticker, scraped.company, rows, scraped.source)
        prediction_ok = db.save_prediction(scraped.ticker, forecast.to_dict(), signal.to_dict())
        self.status.set("Saved to MongoDB." if history_ok and prediction_ok else "MongoDB offline: saved to in-memory fallback.")


if __name__ == "__main__":
    CsNoAIApp().mainloop()
