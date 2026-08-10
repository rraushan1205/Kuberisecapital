"""
Reference Strategy - Simple Moving Average Crossover
This is a placeholder strategy for testing. Replace with actual strategy logic.
"""
import pandas as pd
from typing import Dict, Optional
from app.models.domain import StrategyState
from app.services.strategy_execution.context import StrategyConfig
from app.services.strategy_adapter import StrategyAdapter


async def check_for_signal(
    index_df: pd.DataFrame,
    state: StrategyState,
    config: StrategyConfig,
    adapter: StrategyAdapter,
    token: str
) -> Optional[Dict]:
    """
    Generate trading signals based on moving average crossover.
    
    Entry Signal: 5-MA crosses above 20-MA (bullish) → BUY
    Exit Signal: Position open and 5-MA crosses below 20-MA → SELL
    
    Args:
        index_df: OHLCV data for index (5min candles)
        state: Current strategy state (position info)
        config: Strategy configuration (symbols, params)
        adapter: Strategy adapter for broker calls
        token: Broker access token
    
    Returns:
        Signal dict or None
        Example: {"type": "BUY", "symbol": "NSE:NIFTY50-INDEX"}
                 {"type": "SELL"}
    """
    
    # Need at least 20 candles for 20-MA
    if len(index_df) < 20:
        return None
    
    # Calculate moving averages
    index_df['ma5'] = index_df['close'].rolling(window=5).mean()
    index_df['ma20'] = index_df['close'].rolling(window=20).mean()
    
    # Get current and previous candles
    current = index_df.iloc[-1]
    previous = index_df.iloc[-2]
    
    # Check if we already have an open position
    has_position = state and state.has_open_position
    
    # ENTRY SIGNAL: Bullish crossover
    if not has_position:
        if current['ma5'] > current['ma20'] and previous['ma5'] <= previous['ma20']:
            # MA crossover detected - generate entry signal
            
            # For this simple strategy, use a default option symbol
            # In real strategy, you'd resolve ATM options based on spot price
            symbol = config.symbols.get('option_ce', 'NSE:NIFTY50-INDEX')
            
            return {
                "type": "BUY",
                "symbol": symbol,
                "reason": f"MA crossover: 5MA={current['ma5']:.2f} > 20MA={current['ma20']:.2f}"
            }
    
    # EXIT SIGNAL: Bearish crossover
    if has_position:
        if current['ma5'] < current['ma20'] and previous['ma5'] >= previous['ma20']:
            return {
                "type": "SELL",
                "reason": f"Exit: 5MA={current['ma5']:.2f} < 20MA={current['ma20']:.2f}"
            }
    
    return None


# Alternative: Time-based entry strategy (9:30 AM entry example)
async def check_for_time_based_signal(
    index_df: pd.DataFrame,
    state: StrategyState,
    config: StrategyConfig,
    adapter: StrategyAdapter,
    token: str
) -> Optional[Dict]:
    """
    Simple time-based strategy: Enter at 9:30 AM if no position.
    This mimics the behavior described in Phase 2 analysis.
    """
    from datetime import datetime
    import pytz
    
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    
    # Check if it's entry time (9:30 AM)
    entry_hour = 9
    entry_minute = 30
    
    if now.hour == entry_hour and now.minute == entry_minute:
        if not (state and state.has_open_position):
            # Check if we already signaled this candle
            if state and state.last_signal_candle:
                last_signal_time = state.last_signal_candle.replace(tzinfo=pytz.UTC).astimezone(ist)
                if last_signal_time.date() == now.date():
                    return None  # Already signaled today
            
            # Generate entry signal
            symbol = config.symbols.get('option_ce', 'NSE:NIFTY50-INDEX')
            
            return {
                "type": "BUY",
                "symbol": symbol,
                "reason": "Time-based entry at 9:30 AM"
            }
    
    # Exit at 3:00 PM if position open
    exit_hour = 15
    exit_minute = 0
    
    if now.hour == exit_hour and now.minute == exit_minute:
        if state and state.has_open_position:
            return {
                "type": "SELL",
                "reason": "Time-based exit at 3:00 PM"
            }
    
    return None
