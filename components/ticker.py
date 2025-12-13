
import tkinter as tk
from tkinter import ttk
import json
import threading
import time
import websocket 

try:
    from config import (
        ws_ticker, UP_COLOR, DOWN_COLOR, WS_UI_THROTTLE_SEC,
        BG_DARK, PANEL_BG, ACCENT, TEXT_MAIN, TEXT_DIM
    )
except Exception:
    def ws_ticker(sym: str) -> str:
        return f"wss://stream.binance.com:9443/ws/{sym}@ticker"
    UP_COLOR = "#3ecf8e"
    DOWN_COLOR = "#ff5c5c"
    WS_UI_THROTTLE_SEC = 0.08
    BG_DARK  = "#0f1a2b"
    PANEL_BG = "#152238"
    ACCENT   = "#2e3d5c"
    TEXT_MAIN = "#cfe8ff"
    TEXT_DIM  = "#9fb6cf"


def _apply_local_dark_styles():
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass

    style.configure(".", foreground=TEXT_MAIN, background=PANEL_BG, font=("Segoe UI", 10))
    style.configure("Panel.TFrame", background=PANEL_BG)
    style.configure("Card.TFrame", background=PANEL_BG)
    style.configure("Title.TLabel", font=("Segoe UI", 11, "bold"),
                    foreground=TEXT_DIM, background=PANEL_BG)
    style.configure("Value.TLabel", font=("Consolas", 24, "bold"),
                    foreground=TEXT_MAIN, background=PANEL_BG)
    style.configure("Sub.TLabel", font=("Segoe UI", 9),
                    foreground=TEXT_DIM, background=PANEL_BG)
    style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"),
                    foreground=TEXT_MAIN, background=ACCENT, padding=6)
    style.map("Accent.TButton", background=[("active", "#3b4b71")])


class CryptoTicker:
    """
    Stat-card style ตาม workshop:
      - card 1: Last Traded Price (The large numbers change color accordingly. up/down)
      - card 2: Best Bid / Ask + Spread
      - Status bar in the upper right corner: Connected/Offline + Latest time

    NOTE:
      Use only one stream, @ticker. ('c','p','P','b','a' etc)
    """

    def __init__(self, parent: tk.Widget, symbol: str, display_name: str):
        _apply_local_dark_styles() 
        self.parent = parent
        self.symbol = symbol.lower()
        self.display_name = display_name

        self.is_active = False
        self.ws = None

        # throttling UI
        self.last_update = 0.0
        self.update_interval = float(WS_UI_THROTTLE_SEC)

        # ------- Main Panel -------
        self.frame = ttk.Frame(parent, style="Panel.TFrame")
        self._border = tk.Canvas(self.frame, bg=PANEL_BG, highlightthickness=0)
        self._border.pack(fill=tk.BOTH, expand=True)
        self._border.bind("<Configure>", self._draw_border)

        self.inner = ttk.Frame(self._border, style="Panel.TFrame")
        self.inner.place(relx=0.02, rely=0.04, relwidth=0.96, relheight=0.92)

        header = ttk.Frame(self.inner, style="Panel.TFrame")
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        ttk.Label(header, text=self.display_name, style="Title.TLabel").pack(side=tk.LEFT)
        self.conn_lbl = ttk.Label(header, text="Connected: OFFLINE", style="Sub.TLabel")
        self.conn_lbl.pack(side=tk.RIGHT, padx=(6, 0))
        self.ts_lbl = ttk.Label(header, text="Last update: --:--:--", style="Sub.TLabel")
        self.ts_lbl.pack(side=tk.RIGHT)

        # ------- Stat Cards -------
        # Card 1: Last Traded Price
        self.card_price = ttk.Frame(self.inner, style="Card.TFrame")
        self.card_price.grid(row=1, column=0, sticky="nsew", padx=(0, 8), pady=(8, 6))
        ttk.Label(self.card_price, text="Last Traded Price", style="Title.TLabel").pack(anchor="w")
        self.price_label = tk.Label(self.card_price, text="--",
                                    font=("Consolas", 34, "bold"), bg=PANEL_BG, fg=TEXT_MAIN)
        self.price_label.pack(anchor="w", pady=(2, 0))
        self.change_label = ttk.Label(self.card_price, text="--", style="Sub.TLabel")
        self.change_label.pack(anchor="w")

        # Card 2: Best Bid / Ask & Spread
        self.card_ba = ttk.Frame(self.inner, style="Card.TFrame")
        self.card_ba.grid(row=1, column=1, sticky="nsew", padx=(8, 0), pady=(8, 6))
        ttk.Label(self.card_ba, text="Best Bid / Ask & Spread", style="Title.TLabel").pack(anchor="w")
        self.bid_label = ttk.Label(self.card_ba, text="BID (Buy) --", style="Value.TLabel")
        self.ask_label = ttk.Label(self.card_ba, text="ASK (Sell) --", style="Value.TLabel")
        self.bid_label.pack(anchor="w", pady=(2, 0))
        self.ask_label.pack(anchor="w", pady=(0, 2))
        self.spread_label = ttk.Label(self.card_ba, text="Spread --", style="Sub.TLabel")
        self.spread_label.pack(anchor="w")

        self.inner.grid_columnconfigure(0, weight=1)
        self.inner.grid_columnconfigure(1, weight=1)
        self.inner.grid_rowconfigure(1, weight=1)

        self._last_price = None

    # ----- border drawing -----
    def _draw_border(self, event=None):
        self._border.delete("all")
        w = self._border.winfo_width()
        h = self._border.winfo_height()
        self._border.create_rectangle(1, 1, w - 1, h - 1, outline=ACCENT, width=2)

    # ----- WS lifecycle -----
    def start(self):
        if self.is_active:
            return
        self.is_active = True
        self._set_connected(True)
        self.ws = websocket.WebSocketApp(
            ws_ticker(self.symbol),
            on_message=self.on_message,
            on_error=lambda ws, e: self._on_error(e),
            on_close=lambda ws, s, m: self._on_closed()
        )
        threading.Thread(target=self.ws.run_forever, daemon=True).start()

    def stop(self):
        self.is_active = False
        self._set_connected(False)
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
            self.ws = None

    def _on_error(self, e):
        print(f"{self.symbol} error:", e)
        self.parent.after(0, self._set_connected, False)

    def _on_closed(self):
        print(f"{self.symbol} closed")
        self.parent.after(0, self._set_connected, False)

    # ----- WS message -----
    def on_message(self, ws, message: str):
        if not self.is_active:
            return
        now = time.time()
        if (now - self.last_update) < self.update_interval:
            return

        try:
            data = json.loads(message)
            price = float(data["c"])
            change = float(data["p"])
            percent = float(data["P"])

            bid = float(data.get("b", "nan"))
            ask = float(data.get("a", "nan"))
            spread = (ask - bid) if (not (bid != bid or ask != ask)) else float("nan")  # ตรวจ nan

            ts_ms = data.get("E")
            ts_text = time.strftime("%H:%M:%S", time.localtime(ts_ms / 1000)) if ts_ms else time.strftime("%H:%M:%S")

        except Exception as e:
            print("ticker parse error:", e)
            return

        self.last_update = now
        self.parent.after(0, self.update_display, price, change, percent, bid, ask, spread, ts_text)

    # ----- UI update -----
    def update_display(self, price: float, change: float, percent: float,
                       bid: float, ask: float, spread: float, ts_text: str):
        if not self.is_active:
            return

        color = UP_COLOR if (self._last_price is None or price >= self._last_price) else DOWN_COLOR
        self.price_label.config(text=f"{price:,.2f}", fg=color)
        self._last_price = price

        sign = "+" if change >= 0 else ""
        self.change_label.config(text=f"{sign}{change:,.2f} ({sign}{percent:.2f}%)",
                                 foreground=(UP_COLOR if change >= 0 else DOWN_COLOR))

        # BID / ASK + spread
        if not self._is_nan(bid):
            self.bid_label.config(text=f"BID (Buy)  {bid:,.2f}", foreground=UP_COLOR)
        else:
            self.bid_label.config(text="BID (Buy)  --", foreground=TEXT_DIM)

        if not self._is_nan(ask):
            self.ask_label.config(text=f"ASK (Sell) {ask:,.2f}", foreground=DOWN_COLOR)
        else:
            self.ask_label.config(text="ASK (Sell) --", foreground=TEXT_DIM)

        if not self._is_nan(spread):
            self.spread_label.config(text=f"Spread  {spread:,.4f}", foreground=TEXT_DIM)
        else:
            self.spread_label.config(text=f"Spread  --", foreground=TEXT_DIM)

        self.ts_lbl.config(text=f"Last update: {ts_text}")

    def _is_nan(self, v: float) -> bool:
        return (v != v)  

    # ----- connected indicator -----
    def _set_connected(self, is_on: bool):
        self.conn_lbl.configure(
            text=f"Connected: {'LIVE' if is_on else 'OFFLINE'}",
            foreground=(UP_COLOR if is_on else DOWN_COLOR)
        )

    # ----- pack helpers -----
    def pack(self, **kwargs):
        self.frame.pack(padx=10, pady=8, fill=kwargs.pop("fill", tk.BOTH), expand=kwargs.pop("expand", True))

    def pack_forget(self):
        self.frame.pack_forget()
