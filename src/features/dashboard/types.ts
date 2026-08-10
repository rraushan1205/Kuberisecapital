export type DashboardSnapshot = {
  profile?: {
    name?: string | null;
    subscriptionStatus?: string | null;
  } | null;
  strategy?: {
    status?: string | null;
    selectedName?: string | null;
    scriptFileName?: string | null;
  } | null;
  pnl?: {
    daily?: string | null;
    overall?: string | null;
  } | null;
  positions?: {
    open?: number | null;
    closed?: number | null;
  } | null;
  subscription?: {
    status?: string | null;
  } | null;
  preferences?: {
    lotSize?: string | null;
    riskSettings?: string | null;
  } | null;
  broker?: {
    provider?: string | null;
    status?: string | null;
  } | null;
};

export type MarketplaceStrategy = {
  id: string;
  name: string;
  status?: string | null;
  scriptFileName?: string | null;
};

export type StrategyFileView = {
  filename: string;
  content: string;
  readonly: boolean;
  message: string;
};

// Admin-managed strategy types (user view)
export type UserStrategyPermission = {
  id: number;
  strategy_def_id: number;
  strategy_name: string;
  strategy_description: string;
  config: Record<string, any>;
  is_active: boolean;
  error_message: string | null;
  assigned_at: string;
  // Execution state
  is_running?: boolean;
  has_open_position?: boolean;
  position_details?: {
    symbol?: string;
    qty?: number;
    entry_price?: number;
    current_pnl?: number;
  } | null;
};

export type StrategyControlResponse = {
  success: boolean;
  message: string;
  is_running: boolean;
};
