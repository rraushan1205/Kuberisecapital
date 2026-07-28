"use client";

import { useEffect, useState } from "react";
import { MOCK_MARKET_TICKER } from "@/features/dashboard/lib/mock-data";

export function MarketTicker() {
  const [tickerData, setTickerData] = useState(MOCK_MARKET_TICKER);

  // Simulate live price updates
  useEffect(() => {
    const interval = setInterval(() => {
      setTickerData((prev) =>
        prev.map((item) => {
          // Randomly update prices slightly for demo effect
          const changeNum = parseFloat(item.change.replace(/[+%]/g, ""));
          const variation = (Math.random() - 0.5) * 0.2; // Small random variation
          const newChange = (changeNum + variation).toFixed(2);
          const newChangeNum = parseFloat(newChange);
          return {
            ...item,
            change: `${newChangeNum >= 0 ? "+" : ""}${newChange}%`,
          };
        })
      );
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="relative overflow-hidden border-b border-[var(--line)] bg-[var(--panel)]">
      <div className="flex animate-ticker gap-8 py-2 px-4">
        {/* Duplicate the ticker items for seamless loop */}
        {[...tickerData, ...tickerData].map((item, index) => {
          const changeValue = parseFloat(item.change.replace(/[+%]/g, ""));
          const isPositive = changeValue >= 0;
          return (
            <div key={`${item.symbol}-${index}`} className="flex items-center gap-2 whitespace-nowrap">
              <span className="font-mono text-[11px] font-medium text-[var(--ink)]">{item.symbol}</span>
              <span className="text-[11px] text-[var(--ink-muted)]">{item.price}</span>
              <span
                className={`text-[10px] font-medium ${
                  isPositive ? "text-green-500" : "text-red-500"
                }`}
              >
                {item.change}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
