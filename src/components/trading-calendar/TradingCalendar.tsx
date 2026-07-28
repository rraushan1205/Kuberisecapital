"use client";

import { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { CalendarDaySummary } from "@/types/calendar";
import { calendarService } from "@/services/calendar.service";
import { CalendarDay } from "./CalendarDay";
import { DaySummaryModal } from "./DaySummaryModal";

export function TradingCalendar() {
  const [currentDate, setCurrentDate] = useState(() => new Date(2026, 6, 28));
  const [summaries, setSummaries] = useState<CalendarDaySummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Modal state
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();
  const monthStr = (month + 1).toString().padStart(2, "0");
  const monthQuery = `${year}-${monthStr}`;

  useEffect(() => {
    async function fetchMonthlyData() {
      setIsLoading(true);
      setError(null);
      try {
        const data = await calendarService.getMonthlyCalendar(monthQuery);
        setSummaries(data);
      } catch (err) {
        console.error(err);
        setError("Could not retrieve calendar data.");
      } finally {
        setIsLoading(false);
      }
    }
    fetchMonthlyData();
  }, [monthQuery]);

  // Calendar math
  const firstDayOfMonth = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const daysInPrevMonth = new Date(year, month, 0).getDate();

  const handlePrevMonth = () => setCurrentDate(new Date(year, month - 1, 1));
  const handleNextMonth = () => setCurrentDate(new Date(year, month + 1, 1));
  const handleToday = () => setCurrentDate(new Date(2026, 6, 28));

  const currentMonthName = currentDate.toLocaleDateString("en-US", { month: "long", year: "numeric" });
  const weekdays = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

  // Build cells
  const cells: { day: number; dateStr: string; isCurrentMonth: boolean; isToday: boolean; summary?: CalendarDaySummary }[] = [];

  // Previous month trailing days
  for (let i = firstDayOfMonth - 1; i >= 0; i--) {
    const prevDay = daysInPrevMonth - i;
    const pm = month === 0 ? 12 : month;
    const py = month === 0 ? year - 1 : year;
    cells.push({
      day: prevDay,
      dateStr: `${py}-${String(pm).padStart(2, "0")}-${String(prevDay).padStart(2, "0")}`,
      isCurrentMonth: false,
      isToday: false,
    });
  }

  // Current month
  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${year}-${monthStr}-${String(d).padStart(2, "0")}`;
    cells.push({
      day: d,
      dateStr,
      isCurrentMonth: true,
      isToday: year === 2026 && month === 6 && d === 28,
      summary: summaries.find((s) => s.date === dateStr),
    });
  }

  // Fill remaining cells
  const remaining = 42 - cells.length;
  for (let d = 1; d <= remaining; d++) {
    const nm = month === 11 ? 1 : month + 2;
    const ny = month === 11 ? year + 1 : year;
    cells.push({
      day: d,
      dateStr: `${ny}-${String(nm).padStart(2, "0")}-${String(d).padStart(2, "0")}`,
      isCurrentMonth: false,
      isToday: false,
    });
  }

  return (
    <div className="space-y-3">
      {/* Month header with navigation */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-[var(--ink)]">{currentMonthName}</span>
          {isLoading && (
            <span className="h-2 w-2 animate-pulse rounded-full bg-[var(--accent)]" />
          )}
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={handleToday}
            className="rounded border border-[var(--line)] px-1.5 py-0.5 text-[9px] font-medium text-[var(--ink-muted)] hover:border-[var(--line-strong)] hover:text-[var(--ink)] transition"
          >
            Today
          </button>
          <div className="flex items-center rounded border border-[var(--line)] overflow-hidden">
            <button
              type="button"
              onClick={handlePrevMonth}
              className="p-0.5 text-[var(--ink-muted)] hover:bg-[var(--line)] hover:text-[var(--ink)] transition border-r border-[var(--line)]"
              aria-label="Previous month"
            >
              <ChevronLeft size={12} />
            </button>
            <button
              type="button"
              onClick={handleNextMonth}
              className="p-0.5 text-[var(--ink-muted)] hover:bg-[var(--line)] hover:text-[var(--ink)] transition"
              aria-label="Next month"
            >
              <ChevronRight size={12} />
            </button>
          </div>
        </div>
      </div>

      {error && (
        <p className="text-[10px] text-[var(--danger)]">{error}</p>
      )}

      {/* Weekday headers */}
      <div className="grid grid-cols-7 gap-1">
        {weekdays.map((d) => (
          <div key={d} className="text-center text-[9px] font-mono font-medium text-[var(--ink-subtle)]">
            {d}
          </div>
        ))}
      </div>

      {/* Day cells — heatmap grid */}
      <div className="grid grid-cols-7 gap-2">
        {cells.map((cell, idx) => (
          <CalendarDay
            key={`${cell.dateStr}-${idx}`}
            day={cell.day}
            dateStr={cell.dateStr}
            isCurrentMonth={cell.isCurrentMonth}
            isToday={cell.isToday}
            summary={cell.summary}
            onClick={() => {
              if (cell.summary && cell.summary.trades > 0) {
                setSelectedDate(cell.dateStr);
                setIsModalOpen(true);
              }
            }}
          />
        ))}
      </div>

      <DaySummaryModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        dateStr={selectedDate}
      />
    </div>
  );
}