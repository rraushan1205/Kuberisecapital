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

export type ConnectedUser = {
  user_id: string;
  email: string;
  full_name: string | null;
  provider: string;
  status: "CONNECTED" | "DISCONNECTED";
  connected_at: string | null;
};

export type AdminStrategy = {
  id: string;
  name: string;
  script_filename: string;
  status: "STOPPED" | "RUNNING";
  created_at: string;
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
