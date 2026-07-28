"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { X, Calendar, TrendingUp, TrendingDown, RefreshCw, BarChart2 } from "lucide-react";
import { TradingDayDetails } from "@/types/calendar";
import { calendarService } from "@/services/calendar.service";
import { TradeCard } from "./TradeCard";
import { PnlBadge } from "./PnlBadge";

interface DaySummaryModalProps {
  isOpen: boolean;
  onClose: () => void;
  dateStr: string | null;
}

export function DaySummaryModal({ isOpen, onClose, dateStr }: DaySummaryModalProps) {
  const [details, setDetails] = useState<TradingDayDetails | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !dateStr) {
      setDetails(null);
      return;
    }

    const activeDate = dateStr;

    async function fetchDetails() {
      setIsLoading(true);
      setError(null);
      try {
        const data = await calendarService.getTradingDay(activeDate);
        setDetails(data);
      } catch (err) {
        console.error(err);
        setError("Failed to load trading details for this date.");
      } finally {
        setIsLoading(false);
      }
    }

    fetchDetails();
  }, [isOpen, dateStr]);

  // Format the date header (e.g., "July 18, 2026")
  const formattedDate = dateStr
    ? new Date(dateStr).toLocaleDateString("en-US", {
        weekday: "long",
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : "";

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-end overflow-hidden">
          {/* Backdrop */}
          <motion.button
            type="button"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 h-full w-full bg-[#071015]/45 backdrop-blur-sm cursor-default outline-none"
            aria-label="Close panel overlay"
          />

          {/* Drawer Panel */}
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="relative z-10 flex h-full w-full max-w-lg flex-col border-l border-[var(--line)] bg-[var(--panel-raised)] shadow-2xl"
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-[var(--line)] bg-[var(--panel)] px-6 py-5">
              <div className="flex items-center gap-2.5">
                <Calendar size={18} className="text-[var(--accent)]" />
                <div>
                  <h2 className="text-base font-semibold text-[var(--ink)]">Trading Journal</h2>
                  <p className="text-xs text-[var(--ink-muted)]">{formattedDate}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="rounded-lg p-1.5 text-[var(--ink-muted)] hover:bg-[var(--line)] hover:text-[var(--ink)] focus:outline-none focus:ring-2 focus:ring-[var(--focus)]"
                aria-label="Close panel"
              >
                <X size={18} />
              </button>
            </div>

            {/* Content Area */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {isLoading && (
                <div className="flex h-64 flex-col items-center justify-center gap-3">
                  <RefreshCw size={24} className="animate-spin text-[var(--accent)]" />
                  <p className="text-xs font-medium text-[var(--ink-muted)]">Retrieving journal entries...</p>
                </div>
              )}

              {error && (
                <div className="rounded-xl border border-[var(--danger)]/30 bg-[var(--danger-soft)] p-4 text-center">
                  <p className="text-sm font-medium text-[var(--danger)]">{error}</p>
                  <button
                    type="button"
                    onClick={() => {
                      if (dateStr) {
                        setIsLoading(true);
                        calendarService.getTradingDay(dateStr).then(setDetails).catch(() => {}).finally(() => setIsLoading(false));
                      }
                    }}
                    className="mt-2 text-xs font-semibold text-[var(--accent)] hover:underline"
                  >
                    Retry loading
                  </button>
                </div>
              )}

              {!isLoading && !error && details && (
                <>
                  {/* Summary Cards */}
                  <div className="grid grid-cols-2 gap-4">
                    {/* Net PnL Card */}
                    <div className="col-span-2 rounded-xl border border-[var(--line)] bg-[var(--panel)] p-5 text-center">
                      <p className="font-mono text-[10px] font-medium uppercase tracking-widest text-[var(--ink-subtle)] mb-1">
                        NET PROFIT / LOSS
                      </p>
                      <div className="mt-2 flex justify-center">
                        <PnlBadge pnl={details.netPnl} showIcon className="text-lg px-4 py-1.5 rounded-lg" />
                      </div>
                    </div>

                    {/* Trades Stats */}
                    <div className="rounded-xl border border-[var(--line)] bg-[var(--panel)] p-4">
                      <div className="flex items-center gap-2 text-[var(--ink-muted)] mb-1">
                        <BarChart2 size={14} />
                        <p className="text-[10px] font-mono font-medium uppercase tracking-wider">TOTAL TRADES</p>
                      </div>
                      <p className="text-xl font-bold text-[var(--ink)]">{details.totalTrades}</p>
                    </div>

                    <div className="rounded-xl border border-[var(--line)] bg-[var(--panel)] p-4">
                      <div className="flex items-center justify-between text-[var(--ink-muted)] mb-1">
                        <div className="flex items-center gap-1.5">
                          <TrendingUp size={14} className="text-[#10b981]" />
                          <span className="text-[10px] font-mono font-medium uppercase tracking-wider">WIN / LOSS</span>
                        </div>
                      </div>
                      <p className="text-xl font-bold text-[var(--ink)]">
                        <span className="text-[#10b981]">{details.winningTrades}</span>
                        <span className="mx-1 text-[var(--ink-subtle)]">/</span>
                        <span className="text-[#ef4444]">{details.losingTrades}</span>
                      </p>
                    </div>
                  </div>

                  {/* Trade Details Section */}
                  <div className="space-y-3">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--ink-muted)]">
                      Executed Orders ({details.trades.length})
                    </h3>
                    
                    {details.trades.length === 0 ? (
                      <div className="rounded-xl border border-dashed border-[var(--line)] p-8 text-center text-[var(--ink-muted)]">
                        <p className="text-sm">No recorded trades for this session.</p>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {details.trades.map((trade) => (
                          <TradeCard key={trade.id} trade={trade} />
                        ))}
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
