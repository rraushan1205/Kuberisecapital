export interface CalendarDaySummary {
  date: string; // YYYY-MM-DD
  pnl: number;
  trades: number;
}

export interface Trade {
  id: string;
  symbol: string;
  side: "BUY" | "SELL";
  quantity: number;
  entryTime: string;
  exitTime: string;
  pnl: number;
}

export interface TradingDayDetails {
  date: string;
  netPnl: number;
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  trades: Trade[];
}
