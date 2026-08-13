"""
SENSEX EMA Crossover Strategy
Dual-confirmation strategy using 15min index signal + 5min option entry confirmation.
Extracted from gg_bot_sensex.py and adapted for Kuberise Capital multi-user architecture.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Strategy Parameters (configurable per user)
DEFAULT_CONFIG = {
    "index": "SENSEX",
    "index_symbol": "BSE:SENSEX-INDEX",
    "timeframe_index": "15",      # 15-minute candles for index signal
    "timeframe_option": "5",       # 5-minute candles for option entry
    "ema_fast": 9,
    "ema_slow": 21,
    "min_index_bars": 23,          # EMA_SLOW + 2
    "min_option_bars": 23,
    "target_points": 80,           # SENSEX: 80 points target
    "sl_points": 40,               # SENSEX: 40 points stop-loss
    "entry_start_time": "09:20",
    "entry_end_time": "14:30",
    "square_off_time": "15:15",
}


def compute_ema_pair(df: pd.DataFrame, fast: int = 9, slow: int = 21):
    """
    Compute fast and slow EMAs on close prices.
    
    Args:
        df: DataFrame with 'close' column
        fast: Fast EMA period (default 9)
        slow: Slow EMA period (default 21)
    
    Returns:
        Tuple of (ema_fast, ema_slow) Series
    """
    close = df["close"].astype(float)
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    return ema_fast, ema_slow


def compute_index_signal(df: pd.DataFrame, config: dict = None) -> str:
    """
    Compute index-level signal from 15min candles.
    Uses EMA9/EMA21 crossover on the second-to-last closed candle.
    
    Args:
        df: DataFrame with OHLCV data, indexed by datetime
        config: Strategy configuration (optional)
    
    Returns:
        Signal string: "BUY_CE", "BUY_PE", or "WAIT"
    """
    cfg = config or DEFAULT_CONFIG
    min_bars = cfg.get("min_index_bars", 23)
    
    if len(df) < min_bars:
        logger.debug(f"Index signal: not enough bars ({len(df)} < {min_bars})")
        return "WAIT"
    
    ema_fast, ema_slow = compute_ema_pair(
        df, 
        fast=cfg.get("ema_fast", 9),
        slow=cfg.get("ema_slow", 21)
    )
    
    # Use second-to-last candle to avoid partial candle issues
    idx = -2 if len(df) >= 2 else -1
    fast_val = ema_fast.iloc[idx]
    slow_val = ema_slow.iloc[idx]
    
    if fast_val > slow_val:
        logger.info(f"Index signal: BUY_CE (EMA{cfg.get('ema_fast')}={fast_val:.2f} > EMA{cfg.get('ema_slow')}={slow_val:.2f})")
        return "BUY_CE"
    elif fast_val < slow_val:
        logger.info(f"Index signal: BUY_PE (EMA{cfg.get('ema_fast')}={fast_val:.2f} < EMA{cfg.get('ema_slow')}={slow_val:.2f})")
        return "BUY_PE"
    else:
        logger.debug("Index signal: WAIT (EMAs equal)")
        return "WAIT"


def compute_option_entry_signal(
    df: pd.DataFrame, 
    direction: str, 
    last_seen_candle: datetime = None,
    config: dict = None
) -> tuple[str, datetime]:
    """
    Compute option-level entry signal from 5min candles.
    Detects fresh EMA9/EMA21 bullish crossover (confirmation signal).
    
    Args:
        df: DataFrame with OHLCV data for the option, indexed by datetime
        direction: Expected direction from index ("UP" for CE, "DOWN" for PE)
        last_seen_candle: Timestamp of last processed candle (to detect new crosses)
        config: Strategy configuration (optional)
    
    Returns:
        Tuple of (signal, new_timestamp):
            signal: "BUY" if fresh cross detected, "WAIT" otherwise
            new_timestamp: Timestamp of the candle just checked
    """
    cfg = config or DEFAULT_CONFIG
    min_bars = cfg.get("min_option_bars", 23)
    
    if len(df) < min_bars:
        logger.debug(f"Option signal: not enough bars ({len(df)} < {min_bars})")
        return "WAIT", last_seen_candle
    
    ema_fast, ema_slow = compute_ema_pair(
        df,
        fast=cfg.get("ema_fast", 9),
        slow=cfg.get("ema_slow", 21)
    )
    
    # Use second-to-last closed candle
    idx = -2 if len(df) >= 2 else -1
    closed_ts = df.index[idx]
    
    # Don't reprocess the same candle
    if last_seen_candle is not None and closed_ts <= last_seen_candle:
        return "WAIT", last_seen_candle
    
    # Detect fresh bullish crossover: EMA9 crosses above EMA21
    now_up = ema_fast.iloc[idx] > ema_slow.iloc[idx]
    prev_up = ema_fast.iloc[idx - 1] >= ema_slow.iloc[idx - 1] if idx > 0 else False
    
    if now_up and not prev_up:
        logger.info(
            f"Option entry signal: BUY (fresh EMA{cfg.get('ema_fast')}/EMA{cfg.get('ema_slow')} "
            f"bullish cross at {closed_ts.strftime('%H:%M')})"
        )
        return "BUY", closed_ts
    
    logger.debug(f"Option signal: WAIT (no fresh cross, now_up={now_up}, prev_up={prev_up})")
    return "WAIT", closed_ts


def check_option_flip_exit(
    df: pd.DataFrame,
    entry_candle_ts: datetime,
    config: dict = None
) -> bool:
    """
    Check if option has flipped bearish (EMA9 crossed below EMA21).
    Used for early exit if enabled.
    
    Args:
        df: DataFrame with OHLCV data for the option
        entry_candle_ts: Timestamp when position was entered
        config: Strategy configuration (optional)
    
    Returns:
        True if bearish flip detected, False otherwise
    """
    cfg = config or DEFAULT_CONFIG
    min_bars = cfg.get("min_option_bars", 23)
    
    if len(df) < min_bars:
        return False
    
    ema_fast, ema_slow = compute_ema_pair(
        df,
        fast=cfg.get("ema_fast", 9),
        slow=cfg.get("ema_slow", 21)
    )
    
    idx = -2 if len(df) >= 2 else -1
    closed_ts = df.index[idx]
    
    # Don't check candles before entry
    if entry_candle_ts is not None and closed_ts <= entry_candle_ts:
        return False
    
    # Check if EMA9 is now below EMA21 (bearish)
    is_bearish = ema_fast.iloc[idx] < ema_slow.iloc[idx]
    
    if is_bearish:
        logger.info(
            f"Option flip detected: EMA{cfg.get('ema_fast')} crossed below "
            f"EMA{cfg.get('ema_slow')} at {closed_ts.strftime('%H:%M')}"
        )
    
    return is_bearish


def get_strategy_config(index: str = "SENSEX") -> dict:
    """
    Get strategy configuration for specified index.
    
    Args:
        index: Index name ("SENSEX", "NIFTY", etc.)
    
    Returns:
        Configuration dictionary
    """
    # Default is SENSEX config
    if index == "SENSEX":
        return DEFAULT_CONFIG.copy()
    
    # NIFTY config (if needed in future)
    elif index == "NIFTY":
        return {
            **DEFAULT_CONFIG,
            "index": "NIFTY",
            "index_symbol": "NSE:NIFTY50-INDEX",
            "target_points": 50,   # NIFTY has smaller moves
            "sl_points": 25,
        }
    
    else:
        logger.warning(f"Unknown index {index}, using SENSEX defaults")
        return DEFAULT_CONFIG.copy()


# Export main functions
__all__ = [
    "compute_index_signal",
    "compute_option_entry_signal",
    "check_option_flip_exit",
    "get_strategy_config",
    "DEFAULT_CONFIG",
]
