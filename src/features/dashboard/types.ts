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
