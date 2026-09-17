"""Offline-safe local MongoDB persistence for CsNoAI."""
from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any

try:
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError
except ImportError:
    MongoClient = None
    PyMongoError = Exception

MONGO_URI = "mongodb://localhost:27017/"
DATABASE_NAME = "csnoai_gaming_db"
_client: Any = None
_database: Any = None
_connection_checked = False
_memory_history: dict[str, dict] = {}
_memory_predictions: list[dict] = []


def get_db():
    """Return the configured Mongo database, or None if its daemon is offline."""
    global _client, _database, _connection_checked
    if _connection_checked:
        return _database
    _connection_checked = True
    if MongoClient is None:
        return None
    try:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=500)
        _client.admin.command("ping")
        _database = _client[DATABASE_NAME]
    except (PyMongoError, OSError):
        _client = _database = None
    return _database


def is_connected() -> bool:
    return get_db() is not None


def _number(value):
    try:
        number = None if value is None else float(value)
        return number if number is None or math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _clean_rows(rows: list) -> list[dict]:
    return [{"date": str(row.get("date", "")), "open": _number(row.get("open")),
             "high": _number(row.get("high")), "low": _number(row.get("low")),
             "close": _number(row.get("close")), "volume": _number(row.get("volume"))}
            for row in rows[-10:]]


def save_history(ticker: str, company: str, rows: list, source: str) -> bool:
    """Upsert ten cleaned sessions; use memory when MongoDB is unavailable."""
    symbol = ticker.upper().strip()
    document = {"ticker": symbol, "company": company, "rows": _clean_rows(rows),
                "source": source, "updated_at": datetime.now(timezone.utc)}
    database = get_db()
    if database is not None:
        try:
            database.stock_history.update_one({"ticker": symbol}, {"$set": document}, upsert=True)
            return True
        except PyMongoError:
            pass
    _memory_history[symbol] = document
    return False


def get_history(ticker: str) -> list:
    """Retrieve stored sessions for a ticker from MongoDB or local memory."""
    symbol = ticker.upper().strip()
    database = get_db()
    if database is not None:
        try:
            document = database.stock_history.find_one({"ticker": symbol}, {"_id": 0, "rows": 1})
            if document and document.get("rows"):
                return document["rows"]
        except PyMongoError:
            pass
    return list(_memory_history.get(symbol, {}).get("rows", []))


def save_prediction(ticker: str, forecast_data: dict, signal_data: dict) -> bool:
    """Log model parameters, Day 11 bounds and the final verdict."""
    document = {"ticker": ticker.upper().strip(), "forecast": forecast_data,
                "signal": signal_data, "created_at": datetime.now(timezone.utc)}
    database = get_db()
    if database is not None:
        try:
            database.predictions.insert_one(document)
            return True
        except PyMongoError:
            pass
    _memory_predictions.append(document)
    return False
