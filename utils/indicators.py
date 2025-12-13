
# -*- coding: utf-8 -*-
"""Basic indicators: SMA/EMA"""
from typing import List

def sma(values: List[float], period: int) -> List[float]:
    if period <= 0:
        raise ValueError('period must be > 0')
    out = []
    window = []
    for v in values:
        window.append(float(v))
        if len(window) > period:
            window.pop(0)
        out.append(sum(window)/period if len(window) == period else None)
    return out

def ema(values: List[float], period: int) -> List[float]:
    if period <= 0:
        raise ValueError('period must be > 0')
    k = 2/(period+1)
    out = []
    ema_val = None
    for v in values:
        v = float(v)
        ema_val = v if ema_val is None else v*k + ema_val*(1-k)
        out.append(ema_val)
