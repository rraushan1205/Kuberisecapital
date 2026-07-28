import { CalendarDaySummary, TradingDayDetails, Trade } from "@/types/calendar";

// Simple deterministic pseudo-random generator based on seed (date string)
function seedRandom(str: string) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  return Math.abs(hash);
}

function getTradesForDate(dateStr: string): Trade[] {
  const dateObj = new Date(dateStr);
  const dayOfWeek = dateObj.getDay(); // 0 is Sunday, 6 is Saturday
  
  // Weekend: no trading
  if (dayOfWeek === 0 || dayOfWeek === 6) {
    return [];
  }

  const seed = seedRandom(dateStr);
  
  // Deterministic "no trade" days on weekdays (about 15% of weekdays)
  if (seed % 7 === 0) {
    return [];
  }

  const numTrades = (seed % 4) + 1; // 1 to 4 trades
  const trades: Trade[] = [];

  const symbols = ["BANKNIFTY", "NIFTY", "FINNIFTY", "SENSEX"];
  const isOverallProfitable = seed % 3 !== 0; // ~66% winning days

  for (let i = 0; i < numTrades; i++) {
    const tradeSeed = seed + i * 113;
    const symbol = symbols[tradeSeed % symbols.length];
    
    // Side
    const side = tradeSeed % 2 === 0 ? "BUY" : "SELL";
    
    // Lots & quantities
    let lotSize = 15;
    if (symbol === "NIFTY") lotSize = 25;
    else if (symbol === "FINNIFTY") lotSize = 40;
    else if (symbol === "SENSEX") lotSize = 10;
    
    const numLots = (tradeSeed % 5) + 1; // 1 to 5 lots
    const quantity = numLots * lotSize;

    // Time generation between 09:15 and 15:30 IST
    const entryHour = 9 + (tradeSeed % 6); // 9 to 14
    const entryMin = 15 + (tradeSeed % 40); // 15 to 55
    const durationMin = 15 + (tradeSeed % 90); // 15 to 104 mins
    
    let exitHour = entryHour;
    let exitMin = entryMin + durationMin;
    if (exitMin >= 60) {
      exitHour += Math.floor(exitMin / 60);
      exitMin = exitMin % 60;
    }
    // Cap exit time at 15:30
    if (exitHour > 15 || (exitHour === 15 && exitMin > 30)) {
      exitHour = 15;
      exitMin = 30;
    }

    const pad = (n: number) => n.toString().padStart(2, "0");
    const entryTime = `${pad(entryHour)}:${pad(entryMin)}:00`;
    const exitTime = `${pad(exitHour)}:${pad(exitMin)}:00`;

    // Individual trade P&L calculation
    let pnl = 0;
    const baseVal = (tradeSeed % 300) + 50; // Base value per unit trade
    if (isOverallProfitable) {
      // High chance of profit
      const isWin = (tradeSeed % 10) < 8; // 80% winning trades on profitable days
      pnl = isWin ? baseVal * quantity : -baseVal * 0.6 * quantity;
    } else {
      // High chance of loss
      const isWin = (tradeSeed % 10) < 3; // 30% winning trades on losing days
      pnl = isWin ? baseVal * quantity * 0.5 : -baseVal * quantity;
    }

    // Round P&L to 2 decimals
    pnl = Math.round(pnl * 100) / 100;

    trades.push({
      id: `tr_${dateStr}_${i}`,
      symbol,
      side,
      quantity,
      entryTime,
      exitTime,
      pnl,
    });
  }

  return trades;
}

export const calendarService = {
  /**
   * Fetches the calendar days summaries for a given month (YYYY-MM).
   */
  async getMonthlyCalendar(month: string): Promise<CalendarDaySummary[]> {
    // Simulate API delay
    await new Promise((resolve) => setTimeout(resolve, 300));

    const [yearStr, monthStr] = month.split("-");
    const year = parseInt(yearStr, 10);
    const monthIndex = parseInt(monthStr, 10) - 1; // 0-based

    const numDays = new Date(year, monthIndex + 1, 0).getDate();
    const summaries: CalendarDaySummary[] = [];

    for (let day = 1; day <= numDays; day++) {
      const dateStr = `${yearStr}-${monthStr}-${day.toString().padStart(2, "0")}`;
      const trades = getTradesForDate(dateStr);
      
      const pnl = trades.reduce((sum, t) => sum + t.pnl, 0);
      summaries.push({
        date: dateStr,
        pnl: Math.round(pnl * 100) / 100,
        trades: trades.length,
      });
    }

    return summaries;
  },

  /**
   * Fetches detailed trading information for a specific day (YYYY-MM-DD).
   */
  async getTradingDay(date: string): Promise<TradingDayDetails> {
    // Simulate API delay
    await new Promise((resolve) => setTimeout(resolve, 200));

    const trades = getTradesForDate(date);
    const netPnl = trades.reduce((sum, t) => sum + t.pnl, 0);
    const winningTrades = trades.filter((t) => t.pnl > 0).length;
    const losingTrades = trades.filter((t) => t.pnl < 0).length;

    return {
      date,
      netPnl: Math.round(netPnl * 100) / 100,
      totalTrades: trades.length,
      winningTrades,
      losingTrades,
      trades,
    };
  }
};
