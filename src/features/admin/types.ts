export type AdminSession = { user_id: string; email: string; role: "SUPER_ADMIN" };

export type AdminUser = {
  id: string;
  email: string;
  full_name: string | null;
  role: "USER" | "ADMIN" | "SUPER_ADMIN";
  email_verified: boolean;
  account_status: "PENDING" | "APPROVED" | "REJECTED";
  subscription_status: "INACTIVE" | "ACTIVE";
  created_at: string;
};

// Legacy strategy type (deprecated - kept for backward compatibility)
export type AdminStrategy = {
  id: string;
  name: string;
  script_filename: string;
  status: "STOPPED" | "RUNNING";
  created_at: string;
};

// New admin-managed strategy system types
export type StrategyDefinition = {
  id: number;
  name: string;
  description: string;
  code: string;
  created_by_id: string;
  created_at: string;
  updated_at: string;
};

export type StrategyDefinitionCreate = {
  name: string;
  description: string;
  code: string;
};

export type StrategyDefinitionUpdate = {
  name?: string;
  description?: string;
  code?: string;
};

export type UserStrategyAssignment = {
  id: number;
  user_id: string;
  strategy_def_id: number;
  config: Record<string, any>;
  is_active: boolean;
  error_message: string | null;
  assigned_by_id: string;
  created_at: string;
  updated_at: string;
  // Joined data
  user_email?: string;
  strategy_name?: string;
  strategy_description?: string;
};

export type UserStrategyAssignmentCreate = {
  user_id: string;
  strategy_def_id: number;
  config?: Record<string, any>;
};

export type UserStrategyAssignmentUpdate = {
  config?: Record<string, any>;
  is_active?: boolean;
};

export type AdminExecutionLog = {
  id: string;
  action: "STRATEGY_STARTED" | "STRATEGY_STOPPED" | "FORCE_SQUARE_OFF";
  message: string;
  strategy_id: string | null;
  initiated_by_id: string;
  created_at: string;
};

export type AdminAnnouncement = {
  id: string;
  title: string;
  message: string;
  created_by_id: string;
  created_at: string;
};

export type SubscriptionPlanTier = "BASIC" | "PLUS" | "PRO" | "ELITE" | "MAX";

export type AdminSubscriptionPlan = {
  id: string;
  tier: SubscriptionPlanTier;
  capital: number;
  nifty_lots: number;
  sensex_lots: number;
  bank_nifty_lots: number;
  is_active: boolean;
};

export type SubscriptionPlanInput = {
  tier: SubscriptionPlanTier;
  capital: number;
  nifty_lots: number;
  sensex_lots: number;
  bank_nifty_lots: number;
  is_active: boolean;
};

export type AdminUserDetail = {
  id: string;
  email: string;
  full_name: string | null;
  role: "USER" | "ADMIN" | "SUPER_ADMIN";
  email_verified: boolean;
  account_status: "PENDING" | "APPROVED" | "REJECTED";
  subscription_status: "INACTIVE" | "ACTIVE";
  created_at: string;
  last_login_at: string | null;
  
  // Current subscription plan details
  current_plan_id: string | null;
  current_plan_tier: string | null;
  current_plan_capital: number | null;
  current_plan_nifty_lots: number | null;
  current_plan_sensex_lots: number | null;
  current_plan_bank_nifty_lots: number | null;

  // Subscription request history
  pending_request_id: string | null;
  pending_request_plan_tier: string | null;
};

export type UpdateUserSubscriptionInput = {
  plan_id: string;
  notes?: string;
};

export type BrokerAccount = {
  id: string;
  user_id: string;
  provider: string;
  status: "connected" | "disconnected";
  connected_at: string | null;
  token_expires_at: string | null;
  broker_user_id: string | null;
};

export type BrokerAccountsResponse = {
  total: number;
  skip: number;
  limit: number;
  items: BrokerAccount[];
};
