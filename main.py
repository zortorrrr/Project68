import tkinter as tk
from tkinter import ttk
import threading
import websocket
import json
from functools import partial


from components.features import apply_dark_theme, HeaderBar, StatsPanel, KlinePanel
from components.orderbook import OrderBookPanel
from config import (
    APP_TITLE, WINDOW_SIZE, ORDERBOOK_DEFAULT_LEVELS, 
    KLINE_INTERVAL_DEFAULT, KLINE_LIMIT_DEFAULT, 
    DEFAULT_SYMBOLS, BG_DARK, PANEL_BG, ACCENT_COLOR, 
    TEXT_COLOR, UP_COLOR, DOWN_COLOR, ws_ticker, CARD_BG
)

# 1. Mini Ticker Widget 
class MiniTickerWidget(tk.Frame):
    def __init__(self, parent, symbol):
        super().__init__(parent, bg=CARD_BG, highlightbackground=BG_DARK, highlightthickness=1)
        self.symbol = symbol
        self.is_active = False
        self.ws = None
        
        #Layout
        self.display_name = symbol.replace("USDT", "")
        
        # Frame
        container = tk.Frame(self, bg=CARD_BG)
        container.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)

        # 1. Name coin
        self.symbol_lbl = tk.Label(container, text=self.display_name, 
                                   font=('Segoe UI', 14, 'bold'),
                                   fg='#94a3b8', bg=CARD_BG)       
        self.symbol_lbl.pack(side=tk.TOP, pady=(2, 0))
        
        # 2.price
        self.price_lbl = tk.Label(container, text="--", 
                                  font=('Consolas', 12, 'bold'), 
                                  fg=TEXT_COLOR, bg=CARD_BG)
        self.price_lbl.pack(side=tk.TOP, pady=(2, 0))

        # 3. percentage
        self.percent_lbl = tk.Label(container, text="--%", 
                                    font=('Segoe UI', 9, 'bold'), 
                                    fg=TEXT_COLOR, bg=CARD_BG)
        self.percent_lbl.pack(side=tk.TOP, pady=(0, 2))

    def start_stream(self):
        self.is_active = True
        threading.Thread(target=self._run_socket, daemon=True).start()

    def _run_socket(self):
        try:
            url = ws_ticker(self.symbol)
            self.ws = websocket.WebSocketApp(url, on_message=self.on_message)
            self.ws.run_forever()
        except Exception as e:
            print(f"Socket error {self.symbol}: {e}")

    def stop_stream(self):
        self.is_active = False
        if self.ws:
            try: self.ws.close()
            except: pass

    def on_message(self, ws, message):
        if not self.is_active: return
        try:
            data = json.loads(message)
            last_price = float(data['c'])
            percent = float(data['P'])
            self.after(0, lambda: self._update_ui(last_price, percent))
        except: pass

    def _update_ui(self, price, percent):
        color = UP_COLOR if percent >= 0 else DOWN_COLOR
        sign = "+" if percent >= 0 else ""
        
        self.price_lbl.config(text=f"{price:,.2f}", fg=color)
        
        self.percent_lbl.config(text=f"{sign}{percent:.2f}%", fg=color)


# 2.(Simple Button)
class SimpleCoinButton(tk.Button):
    def __init__(self, parent, symbol, command_callback):
        super().__init__(parent)
        self.symbol = symbol
        self.callback = command_callback
        self.is_selected = False
        
        display_text = symbol.replace("USDT", "")
        
        self.config(
            text=display_text,
            font=('Segoe UI', 10, 'bold'),
            relief='flat',
            bd=0,
            cursor='hand2',
            width=10,
            height=1,  
            command=self._on_click
        )
        self.update_style()

    def _on_click(self):
        if self.callback:
            self.callback(self.symbol)

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self.update_style()

    def update_style(self):
        if self.is_selected:
            bg_color = ACCENT_COLOR
            fg_color = 'white'
        else:
            bg_color = PANEL_BG
            fg_color = TEXT_COLOR   
        self.config(bg=bg_color, fg=fg_color, activebackground=BG_DARK, activeforeground=fg_color)
    
    def start_stream(self): pass
    def stop_stream(self): pass


# Main Application
class DashboardApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        apply_dark_theme(root)
        
        self.root.title(APP_TITLE)
        self.root.geometry(WINDOW_SIZE)

        self.current_symbol = None
        
        self.stats = None
        self.orderbook = None
        self.kline = None
        self.mid_frame = None
        
        self.nav_buttons = {}
        self.ticker_widgets = []

        # --- View Control Variables ---
        self.show_chart_var = tk.BooleanVar(value=True)
        self.show_book_var = tk.BooleanVar(value=True)

        # --- Layout ---
        
        # 1. Top Ticker Bar
        self.create_ticker_bar()

        # 2. Navigation Bar
        self.nav_bar = tk.Frame(root, bg=PANEL_BG)
        self.nav_bar.pack(side=tk.TOP, fill=tk.X, pady=(0, 2))
        self.create_nav_buttons()

        # 3. Content Area
        self.content_area = tk.Frame(root, bg=BG_DARK)
        self.content_area.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.change_symbol(DEFAULT_SYMBOLS[0])

    def create_ticker_bar(self):
        bar_frame = tk.Frame(self.root, bg=BG_DARK, pady=2)
        bar_frame.pack(side=tk.TOP, fill=tk.X)
        
        for symbol in DEFAULT_SYMBOLS:
            tw = MiniTickerWidget(bar_frame, symbol)
            tw.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=1)
            tw.start_stream()
            self.ticker_widgets.append(tw)

    def create_nav_buttons(self):
        lbl = tk.Label(self.nav_bar, text=" SELECT COIN: ", bg=PANEL_BG, fg=TEXT_COLOR, 
                       font=('Segoe UI', 10, 'bold'))
        lbl.pack(side=tk.LEFT, padx=(10, 5))

        for symbol in DEFAULT_SYMBOLS:
            btn = SimpleCoinButton(self.nav_bar, symbol, command_callback=self.change_symbol)
            btn.pack(side=tk.LEFT, padx=1, pady=5) 
            self.nav_buttons[symbol] = btn

    def change_symbol(self, symbol: str):
        if self.current_symbol == symbol: return

        self.current_symbol = symbol
        for sym, btn in self.nav_buttons.items():
            btn.set_selected(sym == symbol)

        self.stop_current_panels()
        for widget in self.content_area.winfo_children():
            widget.destroy()

        self.build_dashboard_ui(symbol)

    def stop_current_panels(self):
        if self.stats: self.stats.stop()
        if self.orderbook: self.orderbook.stop()
        if self.kline: self.kline.stop()

    def build_dashboard_ui(self, symbol: str):
        # 1. Header
        header = HeaderBar(self.content_area, title=f'{symbol} Dashboard')
        header.pack(fill=tk.X)

        # 2. Controls Toolbar 
        controls = tk.Frame(self.content_area, bg=BG_DARK)
        controls.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        self.create_toggle_button(controls, "Hide/Show Candle Chart", self.show_chart_var)
        self.create_toggle_button(controls, "Hide/Show Order Book (Top 20)", self.show_book_var)

        # 3. Stats Cards 
        self.stats = StatsPanel(self.content_area, symbol=symbol)
        self.stats.pack(fill=tk.X, padx=8, pady=(0, 8))
        self.stats.start()

        # 4. Middle Section
        self.mid_frame = ttk.Frame(self.content_area, style='TFrame')
        self.mid_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        self.orderbook = OrderBookPanel(self.mid_frame, symbol, limit=ORDERBOOK_DEFAULT_LEVELS)
        self.orderbook.start()

        self.kline = KlinePanel(self.mid_frame, symbol, interval=KLINE_INTERVAL_DEFAULT, limit=KLINE_LIMIT_DEFAULT)
        self.kline.start()

        self.refresh_mid_layout()

    def create_toggle_button(self, parent, text, variable):
        cb = ttk.Checkbutton(
            parent, 
            text=text, 
            variable=variable, 
            command=self.refresh_mid_layout,
            style='Switch.TCheckbutton'
        )
        cb.pack(side=tk.LEFT, padx=(0, 15))

    def refresh_mid_layout(self):
        self.orderbook.frame.pack_forget()
        self.kline.frame.pack_forget()

        show_ob = self.show_book_var.get()
        show_chart = self.show_chart_var.get()

        if show_ob and show_chart:
            self.orderbook.frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
            self.kline.frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        elif show_ob and not show_chart:
            self.orderbook.frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        elif not show_ob and show_chart:
            self.kline.frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def on_closing(self):
        self.stop_current_panels()
        for tw in self.ticker_widgets:
            tw.stop_stream()
        for btn in self.nav_buttons.values():
            btn.stop_stream()
        self.root.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    
    style = ttk.Style()
    style.configure('TCheckbutton', background=BG_DARK, foreground=TEXT_COLOR, font=('Segoe UI', 10))
    style.map('TCheckbutton', background=[('active', BG_DARK)])

    app = DashboardApp(root)
    root.protocol('WM_DELETE_WINDOW', app.on_closing)
    root.mainloop()