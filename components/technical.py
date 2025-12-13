
import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from utils.binance_api import get_klines
from utils.indicators import sma, ema
from config import CARD_BG, BORDER_COLOR, TEXT_COLOR, ACCENT_COLOR, AMBER_COLOR

class TechnicalAnalysisPanel:
    def __init__(self, parent: tk.Widget, symbol: str, interval: str = '1h', limit: int = 100):
        self.parent = parent; self.symbol = symbol.upper(); self.interval = interval; self.limit = limit
        self.frame = ttk.Frame(parent, padding=8, style='Panel.TFrame')
        ttk.Label(self.frame, text=f"Technical: {self.symbol} ({self.interval})", style='CardTitle.TLabel').pack(anchor=tk.W)
        ttk.Button(self.frame, text='Reload', style='Accent.TButton', command=self.reload).pack(anchor=tk.W)

        self.fig = Figure(figsize=(6.5, 3.0), dpi=100, facecolor=CARD_BG)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor(CARD_BG); self.ax.grid(True, color=BORDER_COLOR, alpha=0.3); self.ax.tick_params(colors=TEXT_COLOR)
        self.ax.set_title(f"{self.symbol} Price with SMA/EMA", color=TEXT_COLOR)
        self.ax.set_xlabel('Candle', color=TEXT_COLOR); self.ax.set_ylabel('Price (USDT)', color=TEXT_COLOR)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.reload()

    def reload(self):
        kl = get_klines(self.symbol, self.interval, self.limit)
        if not kl: return
        closes = [float(c[4]) for c in kl]

        self.ax.clear()
        self.ax.set_facecolor(CARD_BG); self.ax.grid(True, color=BORDER_COLOR, alpha=0.3); self.ax.tick_params(colors=TEXT_COLOR)

        self.ax.plot(closes, label='Close', color=TEXT_COLOR)
        s = sma(closes, period=10); e = ema(closes, period=20)
        s_plot = [v if v is not None else float('nan') for v in s]
        self.ax.plot(s_plot, label='SMA(10)', color=ACCENT_COLOR)
        self.ax.plot(e, label='EMA(20)', color=AMBER_COLOR)
        self.ax.legend(facecolor=CARD_BG, edgecolor=BORDER_COLOR)

        self.canvas.draw()