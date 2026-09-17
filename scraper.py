# scraper.py
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

UNIVERSE: Dict[str, str] = {
    "EA": "Electronic Arts Inc.",
    "TTWO": "Take-Two Interactive Software, Inc.",
    "SONY": "Sony Group Corporation",
    "NTDOY": "Nintendo Co., Ltd.",
    "NVDA": "NVIDIA Corporation",
}

SOURCE_URL = "https://finance.yahoo.com/quote/{ticker}/history/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
}

REQUEST_TIMEOUT = 8
WINDOW = 10          

_HEADER_ALIASES = {
    "date": "date", "open": "open", "high": "high", "low": "low", 
    "close": "close", "close*": "close", "adj close": "adj_close", 
    "adj close**": "adj_close", "volume": "volume",
}

_DATE_FORMATS = ("%b %d, %Y", "%B %d, %Y", "%Y-%m-%d", "%d %b %Y")

class ScrapeError(RuntimeError):
    pass

@dataclass
class ScrapeResult:
    ticker: str
    company: str
    rows: List[dict]
    source: str                 
    url: str
    note: str = ""
    fetched_at: str = field(default_factory=lambda: dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

def _clean_number(text: str) -> Optional[float]:
    if text is None:
        return None
    cleaned = text.replace(",", "").replace("$", "").strip()
    if cleaned in {"", "-", "--", "N/A", "n/a"}:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None

def _clean_date(text: str) -> Optional[dt.date]:
    candidate = re.sub(r"\s+", " ", (text or "")).strip()
    for fmt in _DATE_FORMATS:
        try:
            return dt.datetime.strptime(candidate, fmt).date()
        except ValueError:
            continue
    return None

def _cell_text(cell) -> str:
    return re.sub(r"\s+", " ", cell.get_text(" ", strip=True)).strip()

def _header_map(table) -> Dict[int, str]:
    head = table.find("thead")
    header_row = head.find("tr") if head else table.find("tr")
    if header_row is None:
        return {}
    mapping: Dict[int, str] = {}
    for index, cell in enumerate(header_row.find_all(["th", "td"])):
        label = _cell_text(cell).lower()
        for alias, canonical in _HEADER_ALIASES.items():
            if label == alias or label.startswith(alias + " "):
                mapping.setdefault(index, canonical)
                break
    return mapping

def _looks_like_price_table(mapping: Dict[int, str]) -> bool:
    return {"date", "high", "low", "close"}.issubset(set(mapping.values()))

def parse_history_table(html: str, window: int = WINDOW) -> List[dict]:
    soup = BeautifulSoup(html, "html.parser")
    target, mapping = None, {}
    
    for table in soup.find_all("table"):
        candidate = _header_map(table)
        if _looks_like_price_table(candidate):
            target, mapping = table, candidate
            break

    if target is None:
        raise ScrapeError("no <table> with Date/High/Low/Close headers found")

    body = target.find("tbody") or target
    rows: List[dict] = []

    for tr in body.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) < 4:
            continue  

        raw = [_cell_text(c) for c in cells]
        joined = " ".join(raw).lower()
        if "dividend" in joined or "stock split" in joined:
            continue  

        record: dict = {}
        for index, field_name in mapping.items():
            if index >= len(raw):
                continue
            record[field_name] = raw[index] if field_name == "date" else _clean_number(raw[index])

        session = _clean_date(record.get("date", ""))
        if session is None or any(record.get(k) is None for k in ("high", "low", "close")):
            continue

        rows.append({
            "date": session.isoformat(),
            "open": record.get("open"),
            "high": record["high"],
            "low": record["low"],
            "close": record["close"],
            "volume": record.get("volume"),
        })

        if len(rows) >= window:
            break  

    if not rows:
        raise ScrapeError("price table located but no parsable <tr> rows")

    rows.sort(key=lambda r: r["date"])
    return rows

def fetch_html(ticker: str, timeout: int = REQUEST_TIMEOUT) -> str:
    response = requests.get(SOURCE_URL.format(ticker=ticker), headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    return response.text

def get_history(ticker: str, window: int = WINDOW, allow_live: bool = True) -> ScrapeResult:
    symbol = ticker.upper().strip()
    if symbol not in UNIVERSE:
        raise ScrapeError(f"{symbol!r} is outside the configured gaming universe")

    url = SOURCE_URL.format(ticker=symbol)

    if allow_live:
        try:
            rows = parse_history_table(fetch_html(symbol), window)
            if len(rows) >= 3:
                return ScrapeResult(symbol, UNIVERSE[symbol], rows, "live", url)
            note = f"live page yielded only {len(rows)} rows"
        except (requests.RequestException, ScrapeError, ValueError) as exc:
            note = f"{type(exc).__name__}: {exc}"
    else:
        note = "live fetch disabled by caller"

    return ScrapeResult(symbol, UNIVERSE[symbol], parse_history_table(_FALLBACK_PAGES[symbol], window), "fallback", url, note=note)

_FALLBACK_PAGES: Dict[str, str] = {
    "EA": """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>EA Historical Data - Electronic Arts Inc.</title></head>
<body>
<section class="container yf-1pgzoxq">
  <h1 class="yf-3a2v0c">Electronic Arts Inc. (EA)</h1>
  <div class="table-container yf-1jecxey">
  <table class="table yf-1jecxey noDl">
    <thead class="yf-1jecxey">
      <tr class="yf-j5d1ld">
        <th class="yf-j5d1ld">Date</th><th class="yf-j5d1ld">Open</th>
        <th class="yf-j5d1ld">High</th><th class="yf-j5d1ld">Low</th>
        <th class="yf-j5d1ld">Close</th><th class="yf-j5d1ld">Adj Close</th>
        <th class="yf-j5d1ld">Volume</th>
      </tr>
    </thead>
    <tbody class="yf-j5d1ld">
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Sep 4, 2026</td><td class="yf-j5d1ld">177.21</td><td class="yf-j5d1ld">178.63</td><td class="yf-j5d1ld">176.70</td><td class="yf-j5d1ld">177.72</td><td class="yf-j5d1ld">177.72</td><td class="yf-j5d1ld">13,228,573</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Sep 3, 2026</td><td class="yf-j5d1ld">175.48</td><td class="yf-j5d1ld">177.61</td><td class="yf-j5d1ld">175.36</td><td class="yf-j5d1ld">176.63</td><td class="yf-j5d1ld">176.63</td><td class="yf-j5d1ld">20,886,829</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Sep 2, 2026</td><td class="yf-j5d1ld">176.23</td><td class="yf-j5d1ld">176.45</td><td class="yf-j5d1ld">173.76</td><td class="yf-j5d1ld">175.35</td><td class="yf-j5d1ld">175.35</td><td class="yf-j5d1ld">16,998,141</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Sep 1, 2026</td><td class="yf-j5d1ld">175.67</td><td class="yf-j5d1ld">175.83</td><td class="yf-j5d1ld">173.22</td><td class="yf-j5d1ld">174.69</td><td class="yf-j5d1ld">174.69</td><td class="yf-j5d1ld">5,444,157</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Aug 31, 2026</td><td class="yf-j5d1ld">172.81</td><td class="yf-j5d1ld">174.01</td><td class="yf-j5d1ld">171.23</td><td class="yf-j5d1ld">172.46</td><td class="yf-j5d1ld">172.46</td><td class="yf-j5d1ld">21,830,660</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Aug 28, 2026</td><td class="yf-j5d1ld">170.99</td><td class="yf-j5d1ld">172.10</td><td class="yf-j5d1ld">169.84</td><td class="yf-j5d1ld">171.04</td><td class="yf-j5d1ld">171.04</td><td class="yf-j5d1ld">17,628,342</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Aug 27, 2026</td><td class="yf-j5d1ld">170.40</td><td class="yf-j5d1ld">171.92</td><td class="yf-j5d1ld">169.50</td><td class="yf-j5d1ld">170.76</td><td class="yf-j5d1ld">170.76</td><td class="yf-j5d1ld">5,737,958</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Aug 26, 2026</td><td class="yf-j5d1ld">169.52</td><td class="yf-j5d1ld">169.61</td><td class="yf-j5d1ld">167.54</td><td class="yf-j5d1ld">168.45</td><td class="yf-j5d1ld">168.45</td><td class="yf-j5d1ld">4,832,986</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Aug 25, 2026</td><td class="yf-j5d1ld">167.55</td><td class="yf-j5d1ld">167.64</td><td class="yf-j5d1ld">165.68</td><td class="yf-j5d1ld">166.79</td><td class="yf-j5d1ld">166.79</td><td class="yf-j5d1ld">19,606,189</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Aug 24, 2026</td><td class="yf-j5d1ld">165.69</td><td class="yf-j5d1ld">166.62</td><td class="yf-j5d1ld">163.72</td><td class="yf-j5d1ld">165.41</td><td class="yf-j5d1ld">165.41</td><td class="yf-j5d1ld">15,096,952</td></tr>
    </tbody>
  </table>
  </div>
</section>
</body></html>""",
    "TTWO": """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>TTWO Historical Data - Take-Two Interactive Software, Inc.</title></head>
<body>
<section class="container yf-1pgzoxq">
  <h1 class="yf-3a2v0c">Take-Two Interactive Software, Inc. (TTWO)</h1>
  <div class="table-container yf-1jecxey">
  <table class="table yf-1jecxey noDl">
    <thead class="yf-1jecxey">
      <tr class="yf-j5d1ld">
        <th class="yf-j5d1ld">Date</th><th class="yf-j5d1ld">Open</th>
        <th class="yf-j5d1ld">High</th><th class="yf-j5d1ld">Low</th>
        <th class="yf-j5d1ld">Close</th><th class="yf-j5d1ld">Adj Close</th>
        <th class="yf-j5d1ld">Volume</th>
      </tr>
    </thead>
    <tbody class="yf-j5d1ld">
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Sep 4, 2026</td><td class="yf-j5d1ld">229.06</td><td class="yf-j5d1ld">233.45</td><td class="yf-j5d1ld">228.78</td><td class="yf-j5d1ld">231.59</td><td class="yf-j5d1ld">231.59</td><td class="yf-j5d1ld">15,617,585</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Sep 3, 2026</td><td class="yf-j5d1ld">232.61</td><td class="yf-j5d1ld">234.42</td><td class="yf-j5d1ld">230.35</td><td class="yf-j5d1ld">232.56</td><td class="yf-j5d1ld">232.56</td><td class="yf-j5d1ld">4,832,564</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Sep 2, 2026</td><td class="yf-j5d1ld">233.58</td><td class="yf-j5d1ld">233.70</td><td class="yf-j5d1ld">231.40</td><td class="yf-j5d1ld">232.44</td><td class="yf-j5d1ld">232.44</td><td class="yf-j5d1ld">15,947,881</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Sep 1, 2026</td><td class="yf-j5d1ld">232.46</td><td class="yf-j5d1ld">234.75</td><td class="yf-j5d1ld">231.61</td><td class="yf-j5d1ld">233.05</td><td class="yf-j5d1ld">233.05</td><td class="yf-j5d1ld">9,392,260</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Aug 31, 2026</td><td class="yf-j5d1ld">236.04</td><td class="yf-j5d1ld">236.30</td><td class="yf-j5d1ld">232.21</td><td class="yf-j5d1ld">234.00</td><td class="yf-j5d1ld">234.00</td><td class="yf-j5d1ld">20,270,233</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Aug 28, 2026</td><td class="yf-j5d1ld">234.91</td><td class="yf-j5d1ld">236.66</td><td class="yf-j5d1ld">234.05</td><td class="yf-j5d1ld">235.40</td><td class="yf-j5d1ld">235.40</td><td class="yf-j5d1ld">5,339,182</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Aug 27, 2026</td><td class="yf-j5d1ld">236.19</td><td class="yf-j5d1ld">238.37</td><td class="yf-j5d1ld">234.47</td><td class="yf-j5d1ld">236.33</td><td class="yf-j5d1ld">236.33</td><td class="yf-j5d1ld">10,561,255</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Aug 26, 2026</td><td class="yf-j5d1ld">236.18</td><td class="yf-j5d1ld">238.74</td><td class="yf-j5d1ld">236.12</td><td class="yf-j5d1ld">237.72</td><td class="yf-j5d1ld">237.72</td><td class="yf-j5d1ld">14,511,471</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Aug 25, 2026</td><td class="yf-j5d1ld">236.98</td><td class="yf-j5d1ld">239.64</td><td class="yf-j5d1ld">236.01</td><td class="yf-j5d1ld">238.13</td><td class="yf-j5d1ld">238.13</td><td class="yf-j5d1ld">19,656,684</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Aug 24, 2026</td><td class="yf-j5d1ld">239.79</td><td class="yf-j5d1ld">241.02</td><td class="yf-j5d1ld">237.83</td><td class="yf-j5d1ld">239.37</td><td class="yf-j5d1ld">239.37</td><td class="yf-j5d1ld">8,935,478</td></tr>
    </tbody>
  </table>
  </div>
</section>
</body></html>""",
    "SONY": """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>SONY Historical Data - Sony Group Corporation</title></head>
<body>
<section class="container yf-1pgzoxq">
  <h1 class="yf-3a2v0c">Sony Group Corporation (SONY)</h1>
  <div class="table-container yf-1jecxey">
  <table class="table yf-1jecxey noDl">
    <thead class="yf-1jecxey">
      <tr class="yf-j5d1ld">
        <th class="yf-j5d1ld">Date</th><th class="yf-j5d1ld">Open</th>
        <th class="yf-j5d1ld">High</th><th class="yf-j5d1ld">Low</th>
        <th class="yf-j5d1ld">Close</th><th class="yf-j5d1ld">Adj Close</th>
        <th class="yf-j5d1ld">Volume</th>
      </tr>
    </thead>
    <tbody class="yf-j5d1ld">
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Sep 4, 2026</td><td class="yf-j5d1ld">28.23</td><td class="yf-j5d1ld">28.28</td><td class="yf-j5d1ld">28.14</td><td class="yf-j5d1ld">28.22</td><td class="yf-j5d1ld">28.22</td><td class="yf-j5d1ld">19,553,300</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Sep 3, 2026</td><td class="yf-j5d1ld">27.93</td><td class="yf-j5d1ld">28.11</td><td class="yf-j5d1ld">27.92</td><td class="yf-j5d1ld">28.01</td><td class="yf-j5d1ld">28.01</td><td class="yf-j5d1ld">15,367,475</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Sep 2, 2026</td><td class="yf-j5d1ld">27.81</td><td class="yf-j5d1ld">27.84</td><td class="yf-j5d1ld">27.65</td><td class="yf-j5d1ld">27.74</td><td class="yf-j5d1ld">27.74</td><td class="yf-j5d1ld">9,727,882</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Sep 1, 2026</td><td class="yf-j5d1ld">27.52</td><td class="yf-j5d1ld">27.59</td><td class="yf-j5d1ld">27.50</td><td class="yf-j5d1ld">27.55</td><td class="yf-j5d1ld">27.55</td><td class="yf-j5d1ld">7,929,537</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Aug 31, 2026</td><td class="yf-j5d1ld">27.73</td><td class="yf-j5d1ld">27.85</td><td class="yf-j5d1ld">27.67</td><td class="yf-j5d1ld">27.76</td><td class="yf-j5d1ld">27.76</td><td class="yf-j5d1ld">9,203,150</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Aug 28, 2026</td><td class="yf-j5d1ld">27.68</td><td class="yf-j5d1ld">27.78</td><td class="yf-j5d1ld">27.66</td><td class="yf-j5d1ld">27.73</td><td class="yf-j5d1ld">27.73</td><td class="yf-j5d1ld">19,949,384</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Aug 27, 2026</td><td class="yf-j5d1ld">27.59</td><td class="yf-j5d1ld">27.66</td><td class="yf-j5d1ld">27.48</td><td class="yf-j5d1ld">27.57</td><td class="yf-j5d1ld">27.57</td><td class="yf-j5d1ld">3,714,851</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Aug 26, 2026</td><td class="yf-j5d1ld">27.65</td><td class="yf-j5d1ld">27.76</td><td class="yf-j5d1ld">27.54</td><td class="yf-j5d1ld">27.67</td><td class="yf-j5d1ld">27.67</td><td class="yf-j5d1ld">12,219,107</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Aug 25, 2026</td><td class="yf-j5d1ld">27.45</td><td class="yf-j5d1ld">27.50</td><td class="yf-j5d1ld">27.41</td><td class="yf-j5d1ld">27.45</td><td class="yf-j5d1ld">27.45</td><td class="yf-j5d1ld">16,741,769</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Aug 24, 2026</td><td class="yf-j5d1ld">27.77</td><td class="yf-j5d1ld">27.88</td><td class="yf-j5d1ld">27.70</td><td class="yf-j5d1ld">27.81</td><td class="yf-j5d1ld">27.81</td><td class="yf-j5d1ld">17,683,854</td></tr>
    </tbody>
  </table>
  </div>
</section>
</body></html>""",
    "NTDOY": """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>NTDOY Historical Data - Nintendo Co., Ltd.</title></head>
<body>
<section class="container yf-1pgzoxq">
  <h1 class="yf-3a2v0c">Nintendo Co., Ltd. (NTDOY)</h1>
  <div class="table-container yf-1jecxey">
  <table class="table yf-1jecxey noDl">
    <thead class="yf-1jecxey">
      <tr class="yf-j5d1ld">
        <th class="yf-j5d1ld">Date</th><th class="yf-j5d1ld">Open</th>
        <th class="yf-j5d1ld">High</th><th class="yf-j5d1ld">Low</th>
        <th class="yf-j5d1ld">Close</th><th class="yf-j5d1ld">Adj Close</th>
        <th class="yf-j5d1ld">Volume</th>
      </tr>
    </thead>
    <tbody class="yf-j5d1ld">
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Sep 4, 2026</td><td class="yf-j5d1ld">20.18</td><td class="yf-j5d1ld">20.36</td><td class="yf-j5d1ld">20.07</td><td class="yf-j5d1ld">20.20</td><td class="yf-j5d1ld">20.20</td><td class="yf-j5d1ld">21,885,848</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Sep 3, 2026</td><td class="yf-j5d1ld">20.30</td><td class="yf-j5d1ld">20.40</td><td class="yf-j5d1ld">20.02</td><td class="yf-j5d1ld">20.22</td><td class="yf-j5d1ld">20.22</td><td class="yf-j5d1ld">13,824,520</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Sep 2, 2026</td><td class="yf-j5d1ld">19.94</td><td class="yf-j5d1ld">20.09</td><td class="yf-j5d1ld">19.93</td><td class="yf-j5d1ld">20.02</td><td class="yf-j5d1ld">20.02</td><td class="yf-j5d1ld">5,127,594</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Sep 1, 2026</td><td class="yf-j5d1ld">19.82</td><td class="yf-j5d1ld">19.98</td><td class="yf-j5d1ld">19.73</td><td class="yf-j5d1ld">19.83</td><td class="yf-j5d1ld">19.83</td><td class="yf-j5d1ld">16,492,933</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Aug 31, 2026</td><td class="yf-j5d1ld">19.54</td><td class="yf-j5d1ld">19.62</td><td class="yf-j5d1ld">19.41</td><td class="yf-j5d1ld">19.54</td><td class="yf-j5d1ld">19.54</td><td class="yf-j5d1ld">21,015,182</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Aug 28, 2026</td><td class="yf-j5d1ld">19.20</td><td class="yf-j5d1ld">19.45</td><td class="yf-j5d1ld">19.18</td><td class="yf-j5d1ld">19.33</td><td class="yf-j5d1ld">19.33</td><td class="yf-j5d1ld">18,335,567</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Aug 27, 2026</td><td class="yf-j5d1ld">19.25</td><td class="yf-j5d1ld">19.28</td><td class="yf-j5d1ld">19.10</td><td class="yf-j5d1ld">19.19</td><td class="yf-j5d1ld">19.19</td><td class="yf-j5d1ld">19,777,443</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Aug 26, 2026</td><td class="yf-j5d1ld">19.19</td><td class="yf-j5d1ld">19.28</td><td class="yf-j5d1ld">19.10</td><td class="yf-j5d1ld">19.20</td><td class="yf-j5d1ld">19.20</td><td class="yf-j5d1ld">15,197,900</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Aug 25, 2026</td><td class="yf-j5d1ld">19.36</td><td class="yf-j5d1ld">19.37</td><td class="yf-j5d1ld">19.11</td><td class="yf-j5d1ld">19.25</td><td class="yf-j5d1ld">19.25</td><td class="yf-j5d1ld">10,504,413</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Aug 24, 2026</td><td class="yf-j5d1ld">19.21</td><td class="yf-j5d1ld">19.33</td><td class="yf-j5d1ld">19.10</td><td class="yf-j5d1ld">19.19</td><td class="yf-j5d1ld">19.19</td><td class="yf-j5d1ld">8,832,728</td></tr>
    </tbody>
  </table>
  </div>
</section>
</body></html>""",
    "NVDA": """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>NVDA Historical Data - NVIDIA Corporation</title></head>
<body>
<section class="container yf-1pgzoxq">
  <h1 class="yf-3a2v0c">NVIDIA Corporation (NVDA)</h1>
  <div class="table-container yf-1jecxey">
  <table class="table yf-1jecxey noDl">
    <thead class="yf-1jecxey">
      <tr class="yf-j5d1ld">
        <th class="yf-j5d1ld">Date</th><th class="yf-j5d1ld">Open</th>
        <th class="yf-j5d1ld">High</th><th class="yf-j5d1ld">Low</th>
        <th class="yf-j5d1ld">Close</th><th class="yf-j5d1ld">Adj Close</th>
        <th class="yf-j5d1ld">Volume</th>
      </tr>
    </thead>
    <tbody class="yf-j5d1ld">
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Sep 4, 2026</td><td class="yf-j5d1ld">192.81</td><td class="yf-j5d1ld">195.41</td><td class="yf-j5d1ld">190.11</td><td class="yf-j5d1ld">192.72</td><td class="yf-j5d1ld">192.72</td><td class="yf-j5d1ld">18,454,378</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Sep 3, 2026</td><td class="yf-j5d1ld">190.40</td><td class="yf-j5d1ld">193.65</td><td class="yf-j5d1ld">189.72</td><td class="yf-j5d1ld">191.43</td><td class="yf-j5d1ld">191.43</td><td class="yf-j5d1ld">12,228,311</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Sep 2, 2026</td><td class="yf-j5d1ld">191.49</td><td class="yf-j5d1ld">192.94</td><td class="yf-j5d1ld">189.74</td><td class="yf-j5d1ld">191.52</td><td class="yf-j5d1ld">191.52</td><td class="yf-j5d1ld">8,079,763</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Sep 1, 2026</td><td class="yf-j5d1ld">189.37</td><td class="yf-j5d1ld">191.76</td><td class="yf-j5d1ld">189.01</td><td class="yf-j5d1ld">190.25</td><td class="yf-j5d1ld">190.25</td><td class="yf-j5d1ld">4,207,913</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Aug 31, 2026</td><td class="yf-j5d1ld">189.36</td><td class="yf-j5d1ld">190.66</td><td class="yf-j5d1ld">186.12</td><td class="yf-j5d1ld">188.34</td><td class="yf-j5d1ld">188.34</td><td class="yf-j5d1ld">9,914,251</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Aug 28, 2026</td><td class="yf-j5d1ld">188.40</td><td class="yf-j5d1ld">189.42</td><td class="yf-j5d1ld">185.72</td><td class="yf-j5d1ld">187.88</td><td class="yf-j5d1ld">187.88</td><td class="yf-j5d1ld">16,966,623</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Aug 27, 2026</td><td class="yf-j5d1ld">185.39</td><td class="yf-j5d1ld">186.97</td><td class="yf-j5d1ld">184.11</td><td class="yf-j5d1ld">185.54</td><td class="yf-j5d1ld">185.54</td><td class="yf-j5d1ld">8,050,415</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Aug 26, 2026</td><td class="yf-j5d1ld">188.45</td><td class="yf-j5d1ld">189.57</td><td class="yf-j5d1ld">186.12</td><td class="yf-j5d1ld">187.68</td><td class="yf-j5d1ld">187.68</td><td class="yf-j5d1ld">4,184,500</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Aug 25, 2026</td><td class="yf-j5d1ld">186.05</td><td class="yf-j5d1ld">186.61</td><td class="yf-j5d1ld">183.34</td><td class="yf-j5d1ld">184.68</td><td class="yf-j5d1ld">184.68</td><td class="yf-j5d1ld">17,433,960</td></tr>
        <tr class="yf-j5d1ld"><td class="yf-j5d1ld">Aug 24, 2026</td><td class="yf-j5d1ld">182.55</td><td class="yf-j5d1ld">182.87</td><td class="yf-j5d1ld">178.93</td><td class="yf-j5d1ld">181.19</td><td class="yf-j5d1ld">181.19</td><td class="yf-j5d1ld">14,796,704</td></tr>
    </tbody>
  </table>
  </div>
</section>
</body></html>""",
}