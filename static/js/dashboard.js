/* ==========================================================================
   dashboard.js — client controller + dependency-free SVG chart
   Talks to the Flask JSON API, renders the KPI cards, the regression
   diagnostics, the decision trace, the scraped window and the sector board,
   and draws the 10-session actuals against the OLS trendlines projected to
   t = 11 using hand-built SVG (no external charting library).
   ========================================================================== */

(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const els = {
    rail: $("tickerRail"),
    board: $("board"),
    loader: $("loader"),
    error: $("errorBox"),
    refresh: $("refreshBtn"),
    live: $("liveToggle"),
    modeCorpus: $("modeCorpus"),
    modeLive: $("modeLive"),
    calcBtn: $("calcBtn"),
    calcPanel: $("calcPanel"),
    sourceNote: $("sourceNote"),
    chartFallback: $("chartFallback"),
  };

  const state = { data: new Map(), active: null, busy: false };

  /* ---------------------------------------------------------------- utils */

  const money = (v) =>
    v === null || v === undefined
      ? "—"
      : v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  const pct = (v) => `${v > 0 ? "+" : ""}${v.toFixed(2)}%`;

  const volume = (v) => {
    if (v === null || v === undefined) return "—";
    if (v >= 1e9) return `${(v / 1e9).toFixed(2)}B`;
    if (v >= 1e6) return `${(v / 1e6).toFixed(2)}M`;
    if (v >= 1e3) return `${(v / 1e3).toFixed(1)}K`;
    return String(v);
  };

  const signed = (m) => `${m >= 0 ? "+" : "−"}${Math.abs(m).toFixed(4)}`;

  const equation = (fit) =>
    `ŷ = ${fit.slope.toFixed(4)}·x ${fit.intercept >= 0 ? "+" : "−"} ${Math.abs(fit.intercept).toFixed(4)}`;

  function setText(id, text, cls) {
    const node = $(id);
    if (!node) return;
    node.textContent = text;
    if (cls !== undefined) node.className = cls;
  }

  /* ------------------------------------------------------------ data load */

  async function load({ refresh = false } = {}) {
    if (state.busy) return;
    state.busy = true;
    els.refresh.disabled = true;
    els.error.hidden = true;
    els.loader.hidden = false;
    els.board.hidden = true;

    const params = new URLSearchParams({ live: els.live.checked ? "1" : "0" });
    if (refresh) params.set("refresh", "1");

    try {
      const response = await fetch(`/api/analyze?${params.toString()}`);
      if (!response.ok) throw new Error(`API responded ${response.status}`);
      const payload = await response.json();
      if (!payload.results || !payload.results.length) {
        throw new Error("the engine returned no analysable equities");
      }

      state.data.clear();
      payload.results.forEach((item) => state.data.set(item.ticker, item));

      renderSummary(payload.summary);
      renderRail();
      renderSector();
      updateSourceNote(payload.results);

      const hashed = decodeURIComponent(window.location.hash.replace("#", "")).toUpperCase();
      const first = state.data.has(hashed)
        ? hashed
        : state.active && state.data.has(state.active)
          ? state.active
          : payload.results[0].ticker;
      select(first);

      els.board.hidden = false;
    } catch (err) {
      els.error.textContent = `Engine error: ${err.message}. The offline sample corpus is always available — switch the source to “Sample corpus” and refresh.`;
      els.error.hidden = false;
    } finally {
      els.loader.hidden = true;
      els.refresh.disabled = false;
      state.busy = false;
    }
  }

  function updateSourceNote(results) {
    if (!els.sourceNote) return;
    const live = results.some((r) => r.source === "live");
    els.sourceNote.textContent = live
      ? "Source: live DOM scrape"
      : "Source: offline sample corpus";
  }

  /* -------------------------------------------------------------- summary */

  function renderSummary(summary) {
    setText("sumTracked", summary.tracked);
    setText("sumBuy", summary.signals.BUY);
    setText("sumHold", summary.signals.HOLD);
    setText("sumSell", summary.signals.SELL);
    setText("sumConf", `${summary.avg_confidence.toFixed(1)}%`);
  }

  function renderRail() {
    els.rail.querySelectorAll(".chip").forEach((chip) => {
      const item = state.data.get(chip.dataset.ticker);
      const badge = chip.querySelector('[data-role="signal"]');
      if (!item) {
        badge.textContent = "n/a";
        badge.className = "chip-signal";
        chip.disabled = true;
        return;
      }
      badge.textContent = item.signal.action;
      badge.className = `chip-signal ${item.signal.action}`;
    });
  }

  /* ------------------------------------------------------------ selection */

  function select(ticker) {
    const item = state.data.get(ticker);
    if (!item) return;
    state.active = ticker;

    els.rail.querySelectorAll(".chip").forEach((chip) =>
      chip.classList.toggle("active", chip.dataset.ticker === ticker)
    );
    document.querySelectorAll("#sectorBody tr").forEach((row) =>
      row.classList.toggle("row-active", row.dataset.ticker === ticker)
    );

    if (window.location.hash.slice(1).toUpperCase() !== ticker) {
      history.replaceState(null, "", `#${ticker}`);
    }

    document.title = `${ticker} ${item.signal.action} · ${item.company} · CsNoAI`;

    renderKpis(item);
    renderDiagnostics(item);
    renderTrace(item);
    renderTable(item);
    renderChart(item);
  }

  /* ------------------------------------------------------------------ KPI */

  function renderKpis(item) {
    const q = item.quote;
    const s = item.signal;
    const f = item.forecast;

    setText("quoteDate", q.date);
    setText("kpiClose", `$${money(q.close)}`);
    setText(
      "kpiChange",
      `${q.change >= 0 ? "▲" : "▼"} ${money(Math.abs(q.change))} (${pct(q.change_pct)}) vs prior close`,
      `kpi-sub stat-sub ${q.change >= 0 ? "pos" : "neg"}`
    );

    setText("kpiHigh", `$${money(f.predicted_high)}`);
    setText("kpiUpside", `Potential upside ${pct(s.upside_pct)}`,
      `kpi-sub stat-sub ${s.upside_pct >= 0 ? "pos" : "neg"}`);

    setText("kpiLow", `$${money(f.predicted_low)}`);
    setText("kpiDownside", `Downside risk ${pct(s.downside_pct)}`,
      `kpi-sub stat-sub ${s.downside_pct > 0 ? "neg" : "pos"}`);

    $("verdictCard").className = `verdict ${s.action}`;
    setText("kpiSignal", s.action);
    setText("verdictConf", `R² confidence ${s.confidence.toFixed(1)}%`);
    setText("verdictHeadline", s.headline);
  }

  /* ---------------------------------------------------------- diagnostics */

  function renderDiagnostics(item) {
    const { high_model: hi, low_model: lo } = item.forecast;

    setText("chartTitle", `${item.ticker} — ${item.company}`);

    setText("eqHigh", equation(hi));
    setText("mHigh", signed(hi.slope));
    setText("cHigh", hi.intercept.toFixed(4));
    setText("r2High", hi.r2.toFixed(4));
    setText("tHigh", signed(hi.t_stat));
    $("barHigh").style.width = `${Math.max(0, Math.min(1, hi.r2)) * 100}%`;

    setText("eqLow", equation(lo));
    setText("mLow", signed(lo.slope));
    setText("cLow", lo.intercept.toFixed(4));
    setText("r2Low", lo.r2.toFixed(4));
    setText("tLow", signed(lo.t_stat));
    $("barLow").style.width = `${Math.max(0, Math.min(1, lo.r2)) * 100}%`;

    const live = item.source === "live";
    $("provenance").innerHTML =
      `source: <span class="${item.source}">${live ? "LIVE DOM SCRAPE" : "OFFLINE SAMPLE CORPUS"}</span><br>` +
      `url: ${item.source_url}<br>` +
      `parsed: ${item.sessions} sessions · ${item.fetched_at}` +
      (item.source_note ? `<br>fallback reason: ${item.source_note}` : "");
  }

  /* ---------------------------------------------------------------- trace */

  function renderTrace(item) {
    const list = $("trace");
    list.innerHTML = "";
    item.signal.reasons.forEach((reason, i) => {
      const li = document.createElement("li");
      li.className = "trace-item";
      li.innerHTML = `<span class="dot-num">${i + 1}</span><span>${reason}</span>`;
      list.appendChild(li);
    });

    const rr = item.signal.risk_reward;
    setText(
      "riskReward",
      rr === null
        ? "Risk / reward: undefined — the model projects no downside for the next session."
        : `Risk / reward ratio: ${rr.toFixed(2)}× (upside ÷ downside)`
    );
  }

  /* ---------------------------------------------------------------- table */

  function renderTable(item) {
    const body = $("dataBody");
    body.innerHTML = "";
    item.table.forEach((row, index) => {
      const tr = document.createElement("tr");
      if (index === item.table.length - 1) tr.className = "latest";
      tr.innerHTML =
        `<td class="num">${row.t}</td><td>${row.date}</td>` +
        `<td class="num">${money(row.high)}</td><td class="num">${money(row.low)}</td>` +
        `<td class="num">${money(row.close)}</td><td class="num">${volume(row.volume)}</td>`;
      body.appendChild(tr);
    });
  }

  function renderSector() {
    const body = $("sectorBody");
    body.innerHTML = "";
    state.data.forEach((item) => {
      const s = item.signal;
      const tr = document.createElement("tr");
      tr.dataset.ticker = item.ticker;
      tr.innerHTML =
        `<td class="sym">${item.ticker}</td>` +
        `<td>${item.company}</td>` +
        `<td class="num">${money(item.quote.close)}</td>` +
        `<td class="num">${money(item.forecast.predicted_high)}</td>` +
        `<td class="num">${money(item.forecast.predicted_low)}</td>` +
        `<td class="num ${s.upside_pct >= 0 ? "pos" : "neg"}">${pct(s.upside_pct)}</td>` +
        `<td class="num ${s.downside_pct > 0 ? "neg" : "pos"}">${pct(s.downside_pct)}</td>` +
        `<td class="num">${item.forecast.high_model.r2.toFixed(3)}</td>` +
        `<td><span class="tag ${s.action}">${s.action}</span></td>`;
      tr.addEventListener("click", () => select(item.ticker));
      body.appendChild(tr);
    });
  }

  /* ---------------------------------------------------------------- chart */

  const SVG_NS = "http://www.w3.org/2000/svg";
  const W = 720, H = 340;
  const PAD = { top: 18, right: 16, bottom: 30, left: 46 };

  function renderChart(item) {
    const svg = $("mainChart");
    if (!svg) return;
    const series = item.series;

    const highs = series.high.filter((v) => v !== null);
    const lows = series.low.filter((v) => v !== null);
    const trends = series.high_trend.concat(series.low_trend);
    const all = highs.concat(lows, trends).filter((v) => Number.isFinite(v));

    if (!all.length) {
      svg.innerHTML = "";
      if (els.chartFallback) els.chartFallback.hidden = false;
      return;
    }
    if (els.chartFallback) els.chartFallback.hidden = true;

    let min = Math.min(...all);
    let max = Math.max(...all);
    const span = max - min || 1;
    min -= span * 0.08;
    max += span * 0.08;

    const n = series.labels.length;                 // 11 points
    const plotW = W - PAD.left - PAD.right;
    const plotH = H - PAD.top - PAD.bottom;
    const xAt = (i) => PAD.left + (plotW * i) / (n - 1);
    const yAt = (v) => PAD.top + plotH * (1 - (v - min) / (max - min));

    const parts = [];

    // horizontal grid + y labels
    const ticks = 4;
    for (let t = 0; t <= ticks; t++) {
      const v = min + ((max - min) * t) / ticks;
      const y = yAt(v);
      parts.push(`<line class="grid-line" x1="${PAD.left}" y1="${y.toFixed(1)}" x2="${W - PAD.right}" y2="${y.toFixed(1)}"/>`);
      parts.push(`<text class="axis-text" x="${PAD.left - 8}" y="${(y + 3).toFixed(1)}" text-anchor="end">$${v.toFixed(2)}</text>`);
    }

    // x labels
    series.labels.forEach((label, i) => {
      parts.push(`<text class="axis-text" x="${xAt(i).toFixed(1)}" y="${H - 10}" text-anchor="middle">${label}</text>`);
    });

    // forecast divider at t = 11
    parts.push(`<line class="forecast-marker" x1="${xAt(n - 1).toFixed(1)}" y1="${PAD.top}" x2="${xAt(n - 1).toFixed(1)}" y2="${PAD.top + plotH}"/>`);

    // area between actual high and low
    const areaPts = [];
    series.high.forEach((v, i) => { if (v !== null) areaPts.push([xAt(i), yAt(v)]); });
    for (let i = series.low.length - 1; i >= 0; i--) {
      const v = series.low[i];
      if (v !== null) areaPts.push([xAt(i), yAt(v)]);
    }
    if (areaPts.length > 2) {
      parts.push(`<polygon class="area-high" points="${areaPts.map((p) => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ")}"/>`);
    }

    const polyline = (arr, cls) => {
      const pts = [];
      arr.forEach((v, i) => { if (v !== null && Number.isFinite(v)) pts.push(`${xAt(i).toFixed(1)},${yAt(v).toFixed(1)}`); });
      if (pts.length > 1) parts.push(`<polyline class="${cls}" points="${pts.join(" ")}"/>`);
    };

    polyline(series.high, "line-actual-high");
    polyline(series.low, "line-actual-low");
    polyline(series.high_trend, "line-trend-high");
    polyline(series.low_trend, "line-trend-low");

    // dots on actuals
    const dot = (v, i, color, projected) => {
      if (v === null || !Number.isFinite(v)) return;
      parts.push(`<circle class="dot${projected ? " projected" : ""}" cx="${xAt(i).toFixed(1)}" cy="${yAt(v).toFixed(1)}" r="${projected ? 4.5 : 3}" fill="${color}"/>`);
    };
    series.high.forEach((v, i) => dot(v, i, "#6fb0e6", false));
    series.low.forEach((v, i) => dot(v, i, "#a795ee", false));
    // projected endpoints
    dot(series.high_trend[n - 1], n - 1, "#6fb0e6", true);
    dot(series.low_trend[n - 1], n - 1, "#a795ee", true);

    svg.innerHTML = parts.join("");
  }

  /* ----------------------------------------------------------------- wire */

  els.rail.querySelectorAll(".chip").forEach((chip) =>
    chip.addEventListener("click", () => select(chip.dataset.ticker))
  );
  els.refresh.addEventListener("click", () => load({ refresh: true }));

  window.addEventListener("hashchange", () => {
    const ticker = decodeURIComponent(window.location.hash.replace("#", "")).toUpperCase();
    if (state.data.has(ticker) && ticker !== state.active) select(ticker);
  });

  // Data-source segmented control drives the hidden checkbox the loader reads.
  function setMode(live) {
    els.live.checked = live;
    els.modeLive.setAttribute("aria-pressed", String(live));
    els.modeCorpus.setAttribute("aria-pressed", String(!live));
    load({ refresh: true });
  }
  els.modeCorpus.addEventListener("click", () => setMode(false));
  els.modeLive.addEventListener("click", () => setMode(true));

  // "How it's calculated" disclosure.
  els.calcBtn.addEventListener("click", () => {
    const open = els.calcPanel.hidden;
    els.calcPanel.hidden = !open;
    els.calcBtn.setAttribute("aria-expanded", String(open));
    if (open) els.calcPanel.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth", block: "nearest" });
  });

  // Reflect the server's default source in the segmented control.
  if (els.live.checked) {
    els.modeLive.setAttribute("aria-pressed", "true");
    els.modeCorpus.setAttribute("aria-pressed", "false");
  }

  load();
})();