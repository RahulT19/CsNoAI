# db.py
from __future__ import annotations

from datetime import datetime, timezone
import math
import os
from typing import Any

try:
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError
except ImportError:
    MongoClient = None
    PyMongoError = Exception

# Your live MongoDB Atlas connection string
MONGO_URI = os.environ.get("CSNOAI_MONGO_URI", "mongodb+srv://rahulrohit192005_db_user:SjZ7feb8w8VNV2Ct@rahul19.bouv8j5.mongodb.net/?appName=Rahul19")
DATABASE_NAME = os.environ.get("CSNOAI_MONGO_DATABASE", "csnoai_gaming_db")
_client: Any = None
_database: Any = None
_connection_checked = False
_memory_history: dict[str, dict] = {}
_memory_predictions: list[dict] = []


def configure_connection(connection_string: str | None = None, database_name: str | None = None):
    global MONGO_URI, DATABASE_NAME, _client, _database, _connection_checked
    if connection_string:
        MONGO_URI = connection_string
    if database_name:
        DATABASE_NAME = database_name
    _client = _database = None
    _connection_checked = False


def get_db(connection_string: str | None = None, database_name: str | None = None):
    global _client, _database, _connection_checked
    if connection_string or database_name:
        configure_connection(connection_string, database_name)
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
    symbol = ticker.upper().strip()
    document = {"ticker": symbol, "company": company, "rows": _clean_rows(rows),
                "source": source, "updated_at": datetime.now(timezone.utc)}
    database = get_db()
    if database is not None:
        try:
            # Uses $set so we update history without deleting the prediction alongside it
            database.stock_history.update_one({"ticker": symbol}, {"$set": document}, upsert=True)
            return True
        except PyMongoError:
            pass
    _memory_history[symbol] = document
    return False


def get_history(ticker: str) -> list:
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
    symbol = ticker.upper().strip()
    
    # Flatten the data so it's actually useful and readable in Atlas
    useful_prediction = {
        "ticker": symbol,
        "action": signal_data.get("action"),
        "predicted_high": forecast_data.get("predicted_high"),
        "predicted_low": forecast_data.get("predicted_low"),
        "upside_pct": signal_data.get("upside_pct"),
        "downside_pct": signal_data.get("downside_pct"),
        "confidence": signal_data.get("confidence"),
        "reasons": signal_data.get("reasons"),
        "created_at": datetime.now(timezone.utc)
    }
    
    database = get_db()
    if database is not None:
        try:
            # 1. Save it to the predictions audit log
            database.predictions.insert_one(useful_prediction.copy())
            
            # 2. Attach this prediction ALONGSIDE the stock history document
            database.stock_history.update_one(
                {"ticker": symbol}, 
                {"$set": {"latest_prediction": useful_prediction}}
            )
            return True
        except PyMongoError:
            pass
            
    _memory_predictions.append(useful_prediction)
    return False