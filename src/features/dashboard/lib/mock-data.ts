/**
 * Mock data for dashboard - simulates real API responses
 * 
 * TODO: Replace with actual API calls to:
 * - GET /api/v1/client/dashboard for snapshot data
 * - GET /api/v1/client/positions for position details
 * - GET /api/v1/client/executions for execution logs
 * - GET /api/v1/client/pnl/history for P&L chart data
 */

import type { DashboardSnapshot, MarketplaceStrategy } from "@/features/dashboard/types";

export const MOCK_DASHBOARD_SNAPSHOT: DashboardSnapshot = {
  profile: {
    name: "Raj",
    subscriptionStatus: "Pro · Active",
  },
  strategy: {
    status: "Running",
    selectedName: "Momentum Breakout",
    scriptFileName: "momentum_breakout_v3.py",
  },
  pnl: {
    daily: "₹4,285.50",
    overall: "₹1,18,940.75",
  },
  positions: {
    open: 3,
    closed: 27,
  },
  subscription: {
    status: "Pro · renews 15 Aug 2026",
  },
  preferences: {
    lotSize: "2 lots · NIFTY",
    riskSettings: "Max loss ₹5,000/day · 5 pos. cap",
  },
};

export const MOCK_MARKETPLACE_STRATEGIES: MarketplaceStrategy[] = [
  {
    id: "momentum-breakout",
    name: "Momentum Breakout",
    status: "Active",
    scriptFileName: "momentum_breakout_v3.py",
  },
  {
    id: "mean-reversion",
    name: "Mean Reversion Strategy",
    status: "Available",
    scriptFileName: "mean_reversion_v2.py",
  },
  {
    id: "options-iron-condor",
    name: "Iron Condor Options",
    status: "Beta",
    scriptFileName: "iron_condor_weekly.py",
  },
  {
    id: "scalping-ema",
    name: "EMA Scalping",
    status: "Available",
    scriptFileName: "ema_scalping_5min.py",
  },
];

export type Position = {
  id: string;
  symbol: string;
  type: "LONG" | "SHORT";
  quantity: number;
  entryPrice: number;
  currentPrice: number;
  pnl: number;
  pnlPercent: number;
  status: "open" | "closed";
};

export type ExecutionLog = {
  id: string;
  timestamp: string;
  type: "ORDER" | "SIGNAL" | "SYSTEM" | "ERROR";
  message: string;
  status: "Filled" | "Executed" | "Info" | "Warning" | "Failed";
  details?: string;
};

export const MOCK_OPEN_POSITIONS: Position[] = [
  {
    id: "1",
    symbol: "NIFTY 24800 CE",
    type: "LONG",
    quantity: 50,
    entryPrice: 142.30,
    currentPrice: 156.45,
    pnl: 707.50,
    pnlPercent: 9.94,
    status: "open",
  },
  {
    id: "2",
    symbol: "BANKNIFTY 53000 PE",
    type: "SHORT",
    quantity: 30,
    entryPrice: 89.20,
    currentPrice: 76.80,
    pnl: 372.00,
    pnlPercent: 13.90,
    status: "open",
  },
  {
    id: "3",
    symbol: "RELIANCE FUT",
    type: "LONG",
    quantity: 250,
    entryPrice: 2834.60,
    currentPrice: 2849.20,
    pnl: 3650.00,
    pnlPercent: 0.51,
    status: "open",
  },
];

export const MOCK_CLOSED_POSITIONS: Position[] = [
  {
    id: "4",
    symbol: "NIFTY 24700 PE",
    type: "SHORT",
    quantity: 50,
    entryPrice: 128.50,
    currentPrice: 95.30,
    pnl: 1660.00,
    pnlPercent: 25.84,
    status: "closed",
  },
  {
    id: "5",
    symbol: "BANKNIFTY 52900 CE",
    type: "LONG",
    quantity: 30,
    entryPrice: 156.80,
    currentPrice: 189.40,
    pnl: 978.00,
    pnlPercent: 20.79,
    status: "closed",
  },
];

export const MOCK_EXECUTION_LOGS: ExecutionLog[] = [
  {
    id: "1",
    timestamp: "10:42 AM",
    type: "ORDER",
    message: "BOUGHT 1 lot NIFTY 24800 CE @ ₹142.30",
    status: "Filled",
    details: "Order ID: 240722001234 · Executed at NSE",
  },
  {
    id: "2",
    timestamp: "10:15 AM",
    type: "ORDER",
    message: "SOLD 2 lots BANKNIFTY 52900 PE @ ₹88.10",
    status: "Filled",
    details: "Order ID: 240722001189 · Executed at NSE",
  },
  {
    id: "3",
    timestamp: "09:48 AM",
    type: "SIGNAL",
    message: "Strategy signal: entry conditions met on RELIANCE FUT",
    status: "Executed",
    details: "Price crossed above EMA20 with volume confirmation",
  },
  {
    id: "4",
    timestamp: "09:20 AM",
    type: "SYSTEM",
    message: "Daily risk check passed · exposure at 34% of cap",
    status: "Info",
    details: "Max daily loss: ₹1,700 / ₹5,000 cap",
  },
  {
    id: "5",
    timestamp: "09:15 AM",
    type: "SYSTEM",
    message: "Strategy started · momentum_breakout_v3.py loaded",
    status: "Info",
    details: "Running with NIFTY & BANKNIFTY options · Intraday · Risk tier: Moderate",
  },
];

// Simulated P&L history data for charts
export const MOCK_PNL_DAILY_CHART = [
  { time: "09:15", value: 0 },
  { time: "09:30", value: 450 },
  { time: "10:00", value: 1240 },
  { time: "10:30", value: 2100 },
  { time: "11:00", value: 2850 },
  { time: "11:30", value: 3320 },
  { time: "12:00", value: 3680 },
  { time: "12:30", value: 3890 },
  { time: "13:00", value: 4100 },
  { time: "13:30", value: 4285.50 },
];

export const MOCK_PNL_OVERALL_CHART = [
  { date: "Feb 2026", value: 0 },
  { date: "Mar", value: 22450 },
  { date: "Apr", value: 48920 },
  { date: "May", value: 67340 },
  { date: "Jun", value: 95670 },
  { date: "Jul", value: 118940.75 },
];

export const MOCK_MARKET_TICKER = [
  { symbol: "NIFTY", price: "24,812.35", change: "+0.64%" },
  { symbol: "BANKNIFTY", price: "53,204.10", change: "+0.58%" },
  { symbol: "SENSEX", price: "81,204.10", change: "+0.58%" },
  { symbol: "INFY", price: "1,614.80", change: "+0.47%" },
  { symbol: "TCS", price: "3,822.15", change: "+0.09%" },
  { symbol: "HDFC", price: "1,742.05", change: "-0.34%" },
  { symbol: "ICICI", price: "1,258.60", change: "-0.15%" },
];

/**
 * Feature flag to toggle between mock data and real API
 * Set to false once API endpoints are ready
 */
export const USE_MOCK_DATA = false;
