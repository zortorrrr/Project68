
"""
features.py — Includes apply_dark_theme + HeaderBar, StatsPanel, KlinePanel
(Update: (Add 24h Change & % to StatsPanel)
"""
import tkinter as tk
from tkinter import ttk
import json
import threading
import time
import websocket
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.dates as mdates
import matplotlib.patches as patches
from datetime import datetime

# --- Config Imports ---
from config import (
    ACCENT_COLOR, UP_COLOR, DOWN_COLOR,
    ws_ticker, ws_book_ticker, ws_kline,
    VOLUME_RATIO_REFRESH_SEC, KLINE_INTERVAL_DEFAULT, KLINE_LIMIT_DEFAULT,
    BG_DARK, PANEL_BG, CARD_BG, BORDER_COLOR, TEXT_COLOR, MUTED_TEXT,
    WS_UI_THROTTLE_SEC
)
from utils.binance_api import get_klines

# ---------- 1. Theme Manager  ----------
def apply_dark_theme(root: tk.Tk):
    root.configure(bg=BG_DARK)
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('TFrame', background=BG_DARK)
    style.configure('Panel.TFrame', background=PANEL_BG, borderwidth=1, relief='flat')
    style.configure('Card.TFrame',  background=CARD_BG, borderwidth=1, relief='solid', bordercolor=BORDER_COLOR)
    style.configure('TLabel', background=BG_DARK, foreground=TEXT_COLOR, font=('Segoe UI', 10))
    style.configure('Muted.TLabel', background=BG_DARK, foreground=MUTED_TEXT, font=('Segoe UI', 9))
    style.configure('Header.TLabel', background=BG_DARK, foreground=ACCENT_COLOR, font=('Segoe UI', 20, 'bold'))
    style.configure('CardTitle.TLabel', background=CARD_BG, foreground=MUTED_TEXT, font=('Segoe UI', 10))
    style.configure('Metric.TLabel', background=CARD_BG, foreground=TEXT_COLOR, font=('Consolas', 22, 'bold'))
    style.configure('Accent.TLabel', background=ACCENT_COLOR, foreground='white', font=('Segoe UI', 8, 'bold'), padding=2)
    style.configure('Accent.TButton', background=ACCENT_COLOR, foreground='white', font=('Segoe UI', 9, 'bold'), borderwidth=0)
    style.map('Accent.TButton', background=[('active', '#2563eb')], foreground=[('active', 'white')])
    style.configure('Dark.Treeview', background=CARD_BG, fieldbackground=CARD_BG, foreground=TEXT_COLOR, borderwidth=0, rowheight=24, font=('Consolas', 10))
    style.configure('Dark.Treeview.Heading', background=PANEL_BG, foreground=ACCENT_COLOR, font=('Segoe UI', 9, 'bold'), relief='flat')
    style.map('Dark.Treeview', background=[('selected', '#1e293b')], foreground=[('selected', 'white')])
    return style

# ---------- 2. Header Bar  ----------
class HeaderBar:
    def __init__(self, parent: tk.Widget, title: str = 'BTCUSDT Dashboard'):
        self.frame = ttk.Frame(parent, padding="10 10 10 0", style='TFrame')
        ttk.Label(self.frame, text=title, style='Header.TLabel').pack(side=tk.LEFT)
        status_frame = ttk.Frame(self.frame, style='TFrame')
        status_frame.pack(side=tk.RIGHT, anchor='ne')
        tk.Label(status_frame, text=" LIVE ", bg=ACCENT_COLOR, fg="white", font=('Segoe UI', 8, 'bold')).pack(side=tk.LEFT)
        ttk.Label(status_frame, text=' Connected to LIVE', style='Muted.TLabel').pack(side=tk.LEFT)

    def pack(self, **kwargs): self.frame.pack(**kwargs)

# ---------- 3. Stats Panel  ----------
class StatCard(ttk.Frame):
    def __init__(self, parent, title: str):
        super().__init__(parent, padding=10, style='Card.TFrame')
        ttk.Label(self, text=title, style='CardTitle.TLabel').pack(anchor=tk.W, pady=(0, 5))
        
        # Main Value (Price)
        self.value_lbl = ttk.Label(self, text='Loading...', style='Metric.TLabel')
        self.value_lbl.pack(anchor=tk.W)
        
        # Sub Value 
        self.sub_lbl = ttk.Label(self, text='', style='Muted.TLabel', font=('Consolas', 11, 'bold'))
        self.sub_lbl.pack(anchor=tk.W, pady=(2, 0))

    def set_value(self, text: str, color: str | None = None, sub_text: str = None, sub_color: str = None):
        if color: self.value_lbl.config(foreground=color)
        self.value_lbl.config(text=text)
        
        
        if sub_text is not None:
            self.sub_lbl.config(text=sub_text)
            if sub_color: self.sub_lbl.config(foreground=sub_color)

class StatsPanel:
    def __init__(self, parent: tk.Widget, symbol: str = 'btcusdt'):
        self.parent = parent; self.symbol = symbol
        self.ws_ticker = None; self.ws_book = None; self.is_active = False
        self.last_update_time = 0.0

        self.frame = ttk.Frame(parent, padding="10 5", style='Panel.TFrame')
        
        # 1. Price Card 
        self.card_last = StatCard(self.frame, 'Last Price & 24h Change')
        self.card_last.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        # 2. BBO Card
        card_bbo = ttk.Frame(self.frame, padding=10, style='Card.TFrame')
        card_bbo.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        ttk.Label(card_bbo, text='Best Bid / Ask & Spread', style='CardTitle.TLabel').pack(anchor=tk.W, pady=(0,5))
        
        row_vals = ttk.Frame(card_bbo, style='Card.TFrame', borderwidth=0); row_vals.pack(fill=tk.X, anchor=tk.W)
        self.bid_lbl = ttk.Label(row_vals, text='BID --', style='Metric.TLabel', font=('Consolas', 18, 'bold'))
        self.bid_lbl.pack(side=tk.LEFT, padx=(0, 15))
        ttk.Label(row_vals, text='|', foreground=BORDER_COLOR, font=('Arial', 18)).pack(side=tk.LEFT)
        self.ask_lbl = ttk.Label(row_vals, text='ASK --', style='Metric.TLabel', font=('Consolas', 18, 'bold'))
        self.ask_lbl.pack(side=tk.LEFT, padx=(15, 0))
        self.spread_lbl = ttk.Label(card_bbo, text='Spread: --', style='Muted.TLabel', font=('Consolas', 10))
        self.spread_lbl.pack(anchor=tk.W, pady=(5,0))

        # 3. Volume Cards
        self.card_5m = StatCard(self.frame, '5 Min Vol & Ratio')
        self.card_5m.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        self.card_1h = StatCard(self.frame, '1 Hour Vol & Ratio')
        self.card_1h.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

    def start(self):
        if self.is_active: return
        self.is_active = True
        self.ws_ticker = websocket.WebSocketApp(ws_ticker(self.symbol), on_message=self.on_ticker)
        threading.Thread(target=self.ws_ticker.run_forever, daemon=True).start()
        self.ws_book = websocket.WebSocketApp(ws_book_ticker(self.symbol), on_message=self.on_book)
        threading.Thread(target=self.ws_book.run_forever, daemon=True).start()
        self.reload_volume_cards()

    def stop(self):
        self.is_active = False
        if self.ws_ticker: self.ws_ticker.close()
        if self.ws_book: self.ws_book.close()

    def on_ticker(self, ws, message: str):
        if not self.is_active: return
        now = time.time()
        if (now - self.last_update_time) < WS_UI_THROTTLE_SEC: return
        self.last_update_time = now

        try:
            data = json.loads(message)
            last = float(data['c'])
            change = float(data['p'])      # 24h change amount
            percent = float(data['P'])     # 24h change percent
            
            
            color = UP_COLOR if change >= 0 else DOWN_COLOR
            
            sign = "+" if change >= 0 else ""
            change_text = f"{sign}{change:,.2f} ({sign}{percent:.2f}%)"
            
            self.parent.after(0, lambda: self.card_last.set_value(f"${last:,.2f}", color, change_text, color))
        except: pass

    def on_book(self, ws, message: str):
        if not self.is_active: return
        try:
            data = json.loads(message); bid = float(data['b']); ask = float(data['a']); spread = ask - bid
            def update():
                self.bid_lbl.config(text=f"BID {bid:,.2f}", foreground=UP_COLOR)
                self.ask_lbl.config(text=f"ASK {ask:,.2f}", foreground=DOWN_COLOR)
                self.spread_lbl.config(text=f"Spread: {spread:.4f}")
            self.parent.after(0, update)
        except: pass

    def reload_volume_cards(self):
        def _fmt(k):
            if not k: return "--"
            v, buy = float(k[0][5]), float(k[0][9]); ratio = (buy/v) if v>0 else 0
            return f"Buy: {buy:,.1f}  Sell: {(v-buy):,.1f}\nRatio: {ratio:.3f}"
        
        k5 = get_klines(self.symbol.upper(), '5m', 1)
        k1 = get_klines(self.symbol.upper(), '1h', 1)
        if k5: self.card_5m.set_value(_fmt(k5))
        if k1: self.card_1h.set_value(_fmt(k1))

    def pack(self, **kwargs): self.frame.pack(**kwargs)

# ---------- Helper: Time Convert  ----------
def _epoch_to_num(ts: float):
    try: return mdates.epoch2num(ts)
    except: return mdates.date2num(datetime.fromtimestamp(ts))

# ---------- 4. Kline Chart Panel  ----------
class KlinePanel:
    def __init__(self, parent: tk.Widget, symbol: str = 'BTCUSDT', interval: str = KLINE_INTERVAL_DEFAULT, limit: int = KLINE_LIMIT_DEFAULT):
        self.parent = parent
        self.symbol = symbol
        self.interval = interval
        self.limit = limit
        self.is_active = False
        self.ws = None
        
        self.frame = ttk.Frame(parent, padding=0, style='Card.TFrame') 
        header = ttk.Frame(self.frame, style='Card.TFrame', padding=5)
        header.pack(fill=tk.X)
        ttk.Label(header, text=f"{symbol} {interval} Candlestick Chart (Last {limit})", style='CardTitle.TLabel').pack(side=tk.LEFT)

        self.fig = Figure(figsize=(8, 5), dpi=100)
        self.fig.patch.set_facecolor(CARD_BG)
        self.fig.subplots_adjust(left=0.15, right=0.95, top=0.90, bottom=0.25, hspace=0.05)
        
        gs = self.fig.add_gridspec(2, 1, height_ratios=[3, 1])
        self.ax_price = self.fig.add_subplot(gs[0])
        self.ax_vol = self.fig.add_subplot(gs[1], sharex=self.ax_price)
        
        self._apply_chart_style()
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        self.data = []
        self.load_initial()

    def _apply_chart_style(self):
        for ax in (self.ax_price, self.ax_vol):
            ax.set_facecolor(CARD_BG)
            ax.grid(True, color=BORDER_COLOR, linestyle='--', linewidth=0.5, alpha=0.5)
            ax.tick_params(axis='x', colors=MUTED_TEXT, labelsize=8)
            ax.tick_params(axis='y', colors=MUTED_TEXT, labelsize=8)
            for spine in ax.spines.values(): spine.set_edgecolor(BORDER_COLOR)
        self.ax_price.tick_params(labelbottom=False)
        self.ax_price.set_ylabel('Price', color=MUTED_TEXT, fontsize=9, labelpad=10)
        self.ax_vol.set_ylabel('Volume', color=MUTED_TEXT, fontsize=9, labelpad=10)

    def load_initial(self):
        kl = get_klines(self.symbol, self.interval, self.limit)
        if not kl: return
        self.data = [(int(k[0])/1000.0, float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])) for k in kl]
        self.redraw()

    def redraw(self):
        self.ax_price.clear(); self.ax_vol.clear(); self._apply_chart_style()
        if not self.data: return
        xs = [_epoch_to_num(t) for (t,_,_,_,_,_) in self.data]
        if len(xs) > 1:
            min_diff = min([xs[i+1] - xs[i] for i in range(len(xs)-1)])
            width = min_diff * 0.6
        else: width = 0.02 
        volumes = []
        for x, (t, o, h, l, c, v) in zip(xs, self.data):
            volumes.append(v)
            color = UP_COLOR if c >= o else DOWN_COLOR
            self.ax_price.vlines(x, l, h, color=TEXT_COLOR, linewidth=1, alpha=0.8)
            rect_h = abs(c - o)
            if rect_h == 0: rect_h = (h-l)*0.01 if (h-l) > 0 else 0.0001
            self.ax_price.add_patch(patches.Rectangle((x - width/2, min(o, c)), width, rect_h, facecolor=color, edgecolor=color))
            self.ax_vol.add_patch(patches.Rectangle((x - width/2, 0), width, v, facecolor=color, edgecolor=color, alpha=0.6))
        if volumes:
            max_vol = max(volumes)
            if max_vol > 0: self.ax_vol.set_ylim(0, max_vol * 1.2)
        self.ax_vol.xaxis_date()
        self.ax_vol.xaxis.set_major_formatter(mdates.DateFormatter('%b %d, %H:%M'))
        self.fig.autofmt_xdate(rotation=45)
        self.canvas.draw()

    def start(self):
        if self.is_active: return
        self.is_active = True
        self.ws = websocket.WebSocketApp(ws_kline(self.symbol, self.interval), on_message=self.on_message)
        threading.Thread(target=self.ws.run_forever, daemon=True).start()

    def stop(self):
        self.is_active = False
        if self.ws: self.ws.close()

    def on_message(self, ws, message: str):
        if not self.is_active: return
        try:
            data = json.loads(message); k = data['k']
            t, o, h, l, c, v = int(k['t'])/1000.0, float(k['o']), float(k['h']), float(k['l']), float(k['c']), float(k['v'])
            is_final = bool(k['x'])
            def update():
                if not self.data: return
                self.data[-1] = (t,o,h,l,c,v)
                if is_final:
                    self.data.append((t,c,c,c,c,0.0))
                    if len(self.data) > self.limit: self.data.pop(0)
                self.redraw()
            self.parent.after(0, update)
        except: pass

    def pack(self, **kwargs): self.frame.pack(**kwargs)