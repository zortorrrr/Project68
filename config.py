
"""
config.py — Central setting for Crypto Dashboard
"""

# -----------------------------
# Binance API Base URLs
# -----------------------------
BINANCE_REST_BASE = "https://api.binance.com"
BINANCE_WS_BASE   = "wss://stream.binance.com:9443/ws"

# -----------------------------
# Helpers for WebSocket streams
# -----------------------------
def ws_ticker(symbol: str) -> str:
    return f"{BINANCE_WS_BASE}/{symbol.lower()}@ticker"

def ws_book_ticker(symbol: str) -> str:
    return f"{BINANCE_WS_BASE}/{symbol.lower()}@bookTicker"

def ws_depth(symbol: str, fast_100ms: bool = False) -> str:
    return f"{BINANCE_WS_BASE}/{symbol.lower()}@depth@100ms" if fast_100ms else f"{BINANCE_WS_BASE}/{symbol.lower()}@depth"

def ws_kline(symbol: str, interval: str) -> str:
    return f"{BINANCE_WS_BASE}/{symbol.lower()}@kline_{interval}"

# -----------------------------
# Defaults
# -----------------------------
DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"] 
PRIMARY_DASHBOARD_SYMBOL = "BTCUSDT"

APP_TITLE   = "Real-Time Binance Dashboard"
WINDOW_SIZE = "1280x800"

# -----------------------------
# Colors & Theme (Dark)
# -----------------------------
UP_COLOR      = "#10b981"  # green-500
DOWN_COLOR    = "#ef4444"  # red-500
NEUTRAL_COLOR = "#e5e7eb"
ACCENT_COLOR  = "#3b82f6"  # blue-500
GRID_COLOR    = "#4b5563"  # gray-600
AMBER_COLOR   = "#f59e0b"  # amber-500

# ---- Dark Theme Palette  ----
BG_DARK      = "#1f2937"   # slate-800
PANEL_BG     = "#111827"   # gray-900
CARD_BG      = "#0f172a"   # slate-900
BORDER_COLOR = "#374151"   # gray-700
TEXT_COLOR   = "#e5e7eb"   # gray-200
MUTED_TEXT   = "#9ca3af"   # gray-400
HEADER_TITLE = "#38bdf8"   # sky-400
LIVE_BADGE_BG = ACCENT_COLOR
LIVE_BADGE_FG = "#ffffff"

# -----------------------------
# Data & Charts
# -----------------------------
KLINE_INTERVAL_DEFAULT   = "1h"
KLINE_LIMIT_DEFAULT      = 50
ORDERBOOK_DEFAULT_LEVELS = 10
ORDERBOOK_MAX_LEVELS     = 20  
VOLUME_RATIO_REFRESH_SEC = 30

# -----------------------------
# Networking & UI throttle
# -----------------------------
REST_TIMEOUT_SEC   = 10
REST_RETRIES       = 3
WS_UI_THROTTLE_SEC = 0.10
MATPLOTLIB_FONT    = "Arial"
