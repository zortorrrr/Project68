
"""A tool for calling the Binance REST API (public market data)."""
from typing import Optional, Dict, Any
import requests
from config import BINANCE_REST_BASE, REST_TIMEOUT_SEC, REST_RETRIES

def safe_api_call(path: str, params: Optional[Dict[str, Any]] = None,
                  retries: int = REST_RETRIES, timeout: int = REST_TIMEOUT_SEC):
    url = f"{BINANCE_REST_BASE}{path}"
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"REST error: {e} (attempt {attempt+1}/{retries})")
    print("All retries failed")
    return None

def get_current_price(symbol: str):
    return safe_api_call('/api/v3/ticker/price', params={'symbol': symbol.upper()})

def get_24h_stats(symbol: str):
    return safe_api_call('/api/v3/ticker/24hr', params={'symbol': symbol.upper()})

def get_order_book(symbol: str, limit: int = 10):
    return safe_api_call('/api/v3/depth', params={'symbol': symbol.upper(), 'limit': limit})

def get_klines(symbol: str, interval: str, limit: int = 50):
    return safe_api_call('/api/v3/klines', params={'symbol': symbol.upper(), 'interval': interval, 'limit': limit})
