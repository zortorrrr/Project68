
import tkinter as tk
from tkinter import ttk
import threading
import json
import websocket
from config import ws_depth, ORDERBOOK_DEFAULT_LEVELS, ORDERBOOK_MAX_LEVELS

class OrderBookPanel:
    def __init__(self, parent: tk.Widget, symbol: str, limit: int = ORDERBOOK_DEFAULT_LEVELS):
        self.parent = parent; self.symbol = symbol.lower(); self.limit = limit
        self.ws = None; self.is_active = False
        self.frame = ttk.Frame(parent, padding=8, style='Panel.TFrame')
        header = ttk.Frame(self.frame, style='Panel.TFrame'); header.pack(fill=tk.X)
        ttk.Label(header, text='Order Book Snapshot', style='CardTitle.TLabel').pack(side=tk.LEFT)
        self.toggle_btn = ttk.Button(header, text=f'Show All {ORDERBOOK_MAX_LEVELS} Levels', style='Accent.TButton', command=self.toggle_levels)
        self.toggle_btn.pack(side=tk.RIGHT)

        tables = ttk.Frame(self.frame, style='Panel.TFrame'); tables.pack(fill=tk.BOTH, expand=True)
        left = ttk.Frame(tables, style='Panel.TFrame'); left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,6))
        ttk.Label(left, text='BIDS (Buys - Highest to Lowest Price)', style='CardTitle.TLabel').pack(anchor=tk.W)
        self.bids_tree = ttk.Treeview(left, columns=('price','qty'), show='headings', height=self.limit, style='Dark.Treeview')
        self.bids_tree.heading('price', text='Price'); self.bids_tree.heading('qty', text='Quantity')
        self.bids_tree.column('price', width=120, anchor=tk.E); self.bids_tree.column('qty', width=100, anchor=tk.E)
        self.bids_tree.pack(fill=tk.BOTH, expand=True)

        right = ttk.Frame(tables, style='Panel.TFrame'); right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6,0))
        ttk.Label(right, text='ASKS (Sells - Lowest to Highest Price)', style='CardTitle.TLabel').pack(anchor=tk.W)
        self.asks_tree = ttk.Treeview(right, columns=('price','qty'), show='headings', height=self.limit, style='Dark.Treeview')
        self.asks_tree.heading('price', text='Price'); self.asks_tree.heading('qty', text='Quantity')
        self.asks_tree.column('price', width=120, anchor=tk.E); self.asks_tree.column('qty', width=100, anchor=tk.E)
        self.asks_tree.pack(fill=tk.BOTH, expand=True)

    def start(self):
        if self.is_active: return
        self.is_active = True
        self.ws = websocket.WebSocketApp(ws_depth(self.symbol), on_message=self.on_message,
                                         on_error=lambda ws,e: print('orderbook error', e),
                                         on_close=lambda ws,s,m: print('orderbook closed'))
        threading.Thread(target=self.ws.run_forever, daemon=True).start()

    def stop(self):
        self.is_active = False
        if self.ws:
            try: self.ws.close()
            except Exception: pass
            self.ws = None

    def on_message(self, ws, message: str):
        if not self.is_active: return
        try:
            data = json.loads(message); bids = data.get('b', [])[:self.limit]; asks = data.get('a', [])[:self.limit]
        except Exception as e: print('orderbook parse error', e); return
        self.parent.after(0, self.update_tables, bids, asks)

    def update_tables(self, bids, asks):
        for t in (self.bids_tree, self.asks_tree):
            for i in t.get_children(): t.delete(i)
        for p, q in bids:
            self.bids_tree.insert('', tk.END, values=(f"{float(p):,.2f}", f"{float(q):,.4f}"))
        for p, q in asks:
            self.asks_tree.insert('', tk.END, values=(f"{float(p):,.2f}", f"{float(q):,.4f}"))

    def toggle_levels(self):
        if self.limit == ORDERBOOK_DEFAULT_LEVELS:
            self.limit = ORDERBOOK_MAX_LEVELS
            self.toggle_btn.config(text=f'Show Top {ORDERBOOK_DEFAULT_LEVELS} Levels')
        else:
            self.limit = ORDERBOOK_DEFAULT_LEVELS
            self.toggle_btn.config(text=f'Show All {ORDERBOOK_MAX_LEVELS} Levels')

    def pack(self, **kwargs): self.frame.pack(**kwargs)
