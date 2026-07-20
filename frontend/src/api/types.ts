export type User = {
  id: string;
  username: string;
  role: string;
  is_active: boolean;
};

export type PurchaseAssetGenerationResult = {
  purchase_id: string;
  purchase_no: string;
  purchase_type: string;
  created_accounts: number;
  created_servers: number;
  created_proxy_pools: number;
  skipped_reason?: string | null;
};

export type PurchaseAccountJsonBindItem = {
  account_id?: string | null;
  account_no?: string | null;
  email?: string | null;
  status: string;
  message: string;
};

export type PurchaseAccountJsonBindResult = {
  purchase_id: string;
  import_batch_no: string;
  total_json_accounts: number;
  bound_count: number;
  skipped_count: number;
  failed_count: number;
  items: PurchaseAccountJsonBindItem[];
};

export type PurchaseAccountJsonBindRequest = {
  file_id?: string | null;
  payload: Record<string, unknown> | Record<string, unknown>[];
  overwrite_existing: boolean;
  account_type?: string | null;
  plan_type?: string | null;
  remark?: string | null;
};

export type DashboardOverview = {
  revenue: number;
  all_cost: number;
  real_cost: number;
  profit: number;
  real_profit: number;
  test_loss: number;
  available_accounts: number;
  unavailable_accounts: number;
};

export type ExpiringAssetRow = {
  asset_id: string;
  asset_type: string;
  name: string;
  status: string;
  expired_at: string;
  days_left: number;
  include_real_cost: boolean;
};

export type MonthlyProfitRow = {
  month: string;
  revenue: number;
  all_cost: number;
  real_cost: number;
  profit: number;
  real_profit: number;
  test_loss: number;
};

export type SupplierRankingRow = {
  supplier_id?: string | null;
  supplier_name: string;
  purchase_count: number;
  all_cost: number;
  real_cost: number;
  test_loss: number;
  avg_score?: number | null;
};

export type SupplierMultiplierRow = {
  supplier_id: string;
  supplier_name: string;
  batch_count: number;
  purchase_quantity: number;
  effective_account_count: number;
  effective_rate: number;
  avg_score: number;
  real_effective_unit_cost: number;
  target_margin: number;
  base_multiplier: number;
  risk_buffer: number;
  loss_buffer: number;
  score_buffer: number;
  recommended_multiplier: number;
  suggested_sale_price: number;
  stability_level: string;
  reason: string;
};

export type AIPricingRecommendationRow = {
  account_type: string;
  batch_count: number;
  purchase_quantity: number;
  effective_account_count: number;
  effective_rate: number;
  real_effective_unit_cost: number;
  target_margin: number;
  recommended_multiplier: number;
  suggested_sale_price: number;
  projected_revenue: number;
  projected_profit: number;
  projected_margin: number;
  risk_level: string;
  reason: string;
};

export type AccountTypeProfitRow = {
  account_type: string;
  batch_count: number;
  purchase_quantity: number;
  effective_account_count: number;
  effective_rate: number;
  all_cost: number;
  effective_cost: number;
  test_loss: number;
  real_effective_unit_cost?: number | null;
  avg_score?: number | null;
};

export type PurchaseBatchProfitRow = {
  batch_id: string;
  batch_no: string;
  supplier_id?: string | null;
  supplier_name?: string | null;
  account_type: string;
  purchase_quantity: number;
  effective_account_count: number;
  effective_rate: number;
  purchase_total_price: number;
  nominal_unit_price?: number | null;
  real_effective_unit_price?: number | null;
  test_loss: number;
  overall_score?: number | null;
  conclusion?: string | null;
};

export type Supplier = {
  id: string;
  name: string;
  type: string;
  contact_name?: string | null;
  purchase_url?: string | null;
  login_url?: string | null;
  country_region?: string | null;
  continue_cooperation: boolean;
  monitor_shop: boolean;
  preferred_product_tags: string[];
  status: string;
  remark?: string | null;
  has_login_account: boolean;
  has_login_secret: boolean;
  created_at: string;
  updated_at: string;
};

export type ShopProduct = {
  id: string;
  external_product_id: string;
  goods_type: string;
  category_id?: string | null;
  category_name?: string | null;
  standard_category_key?: string | null;
  standard_category_name?: string | null;
  category_duplicate_status: string;
  name: string;
  price: string | number;
  market_price?: string | number | null;
  stock_count: number;
  is_out_of_stock: boolean;
  created_at: string;
  updated_at: string;
};

export type ShopMonitor = {
  id: string;
  supplier_id?: string | null;
  name: string;
  shop_url: string;
  shop_token: string;
  platform: string;
  enabled: boolean;
  last_synced_at?: string | null;
  last_sync_status: string;
  last_sync_message?: string | null;
  products: ShopProduct[];
  created_at: string;
  updated_at: string;
};

export type ShopMonitorSyncResult = {
  monitor_id: string;
  product_count: number;
  out_of_stock_count: number;
  status: string;
  message?: string | null;
};

export type ShopMonitorImportResult = {
  created_count: number;
  skipped_count: number;
};

export type SupplierSecret = {
  id: string;
  login_account?: string | null;
  login_secret?: string | null;
};

export type OperationsPlatform = {
  id: string;
  name: string;
  type: string;
  login_url?: string | null;
  bound_email?: string | null;
  bound_phone?: string | null;
  is_core: boolean;
  has_expiry: boolean;
  expired_at?: string | null;
  include_cost: boolean;
  status: string;
  remark?: string | null;
  has_login_account: boolean;
  has_login_secret: boolean;
  created_at: string;
  updated_at: string;
};

export type OperationsPlatformSecret = {
  id: string;
  login_account?: string | null;
  login_secret?: string | null;
};

export type Purchase = {
  id: string;
  purchase_no: string;
  purchase_type: string;
  supplier_id?: string | null;
  product_name: string;
  product_type?: string | null;
  quantity: string | number;
  unit_price: string | number;
  total_price: string | number;
  currency: string;
  payment_method?: string | null;
  purchased_at: string;
  order_url?: string | null;
  purchaser_id?: string | null;
  voucher_file_id?: string | null;
  include_all_cost: boolean;
  include_real_cost: boolean;
  cost_status: string;
  asset_generated: boolean;
  generated_asset_count: number;
  bound_account_count: number;
  imported_account_count: number;
  abnormal_account_count: number;
  remark?: string | null;
  created_at: string;
  updated_at: string;
};

export type FileRecord = {
  id: string;
  original_name: string;
  content_type?: string | null;
  size_bytes?: number | null;
  uploaded_by?: string | null;
  created_at: string;
  updated_at: string;
};

export type Account = {
  id: string;
  account_no: string;
  name?: string | null;
  supplier_id?: string | null;
  purchase_id?: string | null;
  sub2api_instance_id?: string | null;
  account_type: string;
  plan_type?: string | null;
  login_account?: string | null;
  authorized_email?: string | null;
  sub2api_account_id?: string | null;
  import_file_id?: string | null;
  import_batch_no?: string | null;
  raw_payload?: Record<string, unknown> | null;
  status: string;
  participate_operation: boolean;
  include_real_cost: boolean;
  cost_unit_price?: string | number | null;
  available_days?: number | null;
  has_login_password: boolean;
  has_sub2api_key: boolean;
  has_raw_credentials: boolean;
  first_seen_alive_at?: string | null;
  last_seen_alive_at?: string | null;
  first_abnormal_at?: string | null;
  last_checked_at?: string | null;
  last_sub2api_status_code?: number | null;
  last_sub2api_error_code?: string | null;
  last_sub2api_message?: string | null;
  survival_seconds?: number | null;
  created_at: string;
  updated_at: string;
};

export type AccountItem = {
  id: string;
  account_id: string;
  purchase_id?: string | null;
  item_no: string;
  item_index: number;
  email?: string | null;
  platform?: string | null;
  plan_type?: string | null;
  remote_account_id?: string | null;
  status: string;
  import_batch_no?: string | null;
  raw_payload?: Record<string, unknown> | null;
  last_checked_at?: string | null;
  last_sub2api_status_code?: number | null;
  last_sub2api_error_code?: string | null;
  last_sub2api_message?: string | null;
  first_seen_alive_at?: string | null;
  last_seen_alive_at?: string | null;
  first_abnormal_at?: string | null;
  survival_seconds?: number | null;
  remark?: string | null;
  created_at: string;
  updated_at: string;
};

export type AccountSecret = {
  id: string;
  login_account?: string | null;
  login_password?: string | null;
  authorized_email?: string | null;
  sub2api_account_id?: string | null;
  sub2api_key?: string | null;
};

export type AccountBulkDeleteResult = {
  deleted_count: number;
};

export type AccountCheckBatch = {
  id: string;
  batch_no: string;
  name?: string | null;
  source: string;
  endpoint_url?: string | null;
  method: string;
  checked_by?: string | null;
  sub2api_instance_id?: string | null;
  total_count: number;
  alive_count: number;
  abnormal_count: number;
  status_401_count: number;
  status_403_count: number;
  status_429_count: number;
  started_at?: string | null;
  finished_at?: string | null;
  request_config?: Record<string, unknown> | null;
  remark?: string | null;
  created_at: string;
  updated_at: string;
};

export type AccountCheckRecord = {
  id: string;
  batch_id?: string | null;
  account_id: string;
  checked_at: string;
  http_status?: number | null;
  sub2api_status?: string | null;
  is_alive: boolean;
  error_code?: string | null;
  error_message?: string | null;
  response_ms?: number | null;
  survived_seconds?: number | null;
  raw_response?: Record<string, unknown> | null;
  remark?: string | null;
  created_at: string;
  updated_at: string;
};

export type Sub2APIInstance = {
  id: string;
  name: string;
  base_url: string;
  is_active: boolean;
  has_admin_key: boolean;
  last_probe_at?: string | null;
  last_probe_status?: string | null;
  last_probe_message?: string | null;
  detected_accounts_path?: string | null;
  detected_version?: string | null;
  adapter: string;
  extra?: Record<string, unknown> | null;
  remark?: string | null;
  created_at: string;
  updated_at: string;
};

export type Sub2APIProbeResult = {
  ok: boolean;
  status: string;
  message: string;
  accounts_path?: string | null;
  version?: string | null;
  sample_count: number;
};

export type Sub2APIGroup = {
  id: number;
  name: string;
  platform: string;
  status?: string | null;
  is_exclusive?: boolean | null;
};

export type Sub2APIProxy = {
  id: number;
  name: string;
  protocol?: string | null;
  host?: string | null;
  port?: number | null;
  username?: string | null;
  status?: string | null;
  latency_ms?: number | null;
  latency_status?: string | null;
  account_count?: number | null;
};

export type Sub2APIImportBatch = {
  id: string;
  batch_no: string;
  instance_id: string;
  instance_name?: string | null;
  created_by?: string | null;
  retry_of_batch_id?: string | null;
  group_ids: number[];
  duplicate_policy: "skip" | "update";
  status: "running" | "completed" | "partial" | "failed";
  total_count: number;
  success_count: number;
  failed_count: number;
  skipped_count: number;
  started_at?: string | null;
  finished_at?: string | null;
  remark?: string | null;
  created_at: string;
  updated_at: string;
};

export type Sub2APIImportCreateRequest = {
  instance_id: string;
  purchase_id?: string;
  select_all: boolean;
  account_ids: string[];
  group_ids: number[];
  proxy_id?: number | null;
  duplicate_policy: "skip" | "update";
  remark?: string;
};

export type Sub2APIImportItem = {
  id: string;
  batch_id: string;
  account_id: string;
  account_no?: string | null;
  account_type?: string | null;
  action: "create" | "update" | "skip";
  status: "pending" | "success" | "failed" | "skipped";
  remote_account_id?: string | null;
  error_message?: string | null;
  attempted_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type ServerAsset = {
  id: string;
  name: string;
  supplier_id?: string | null;
  purchase_id?: string | null;
  login_host?: string | null;
  ssh_username?: string | null;
  console_url?: string | null;
  cpu?: string | null;
  memory?: string | null;
  disk?: string | null;
  bandwidth?: string | null;
  region?: string | null;
  monthly_cost?: string | number | null;
  expired_at?: string | null;
  usage?: string | null;
  status: string;
  include_real_cost: boolean;
  remark?: string | null;
  has_ssh_secret: boolean;
  created_at: string;
  updated_at: string;
};

export type ServerSecret = {
  id: string;
  login_host?: string | null;
  ssh_username?: string | null;
  ssh_secret?: string | null;
};

export type ProxyPool = {
  id: string;
  supplier_id?: string | null;
  purchase_id?: string | null;
  proxy_type: string;
  region?: string | null;
  quantity_or_traffic?: string | null;
  unit_price?: string | number | null;
  total_price?: string | number | null;
  expired_at?: string | null;
  success_rate?: string | number | null;
  latency_ms?: number | null;
  suitable_for_login: boolean;
  suitable_for_api: boolean;
  status: string;
  continue_purchase: boolean;
  include_real_cost: boolean;
  remark?: string | null;
  created_at: string;
  updated_at: string;
};

export type EvaluationBatch = {
  id: string;
  batch_no: string;
  supplier_id?: string | null;
  account_type: string;
  purchase_id?: string | null;
  purchase_quantity: number;
  purchase_total_price: string | number;
  initial_pass_count: number;
  day7_available_count: number;
  day30_available_count: number;
  banned_count: number;
  refund_count: number;
  effective_account_count: number;
  nominal_unit_price?: string | number | null;
  real_effective_unit_price?: string | number | null;
  overall_score?: string | number | null;
  conclusion?: string | null;
  created_at: string;
  updated_at: string;
};

export type AccountEvaluation = {
  id: string;
  batch_id: string;
  account_id: string;
  can_login?: boolean | null;
  has_risk_control?: boolean | null;
  target_model_available?: boolean | null;
  need_fixed_proxy?: boolean | null;
  request_success_rate?: string | number | null;
  avg_response_quality?: string | number | null;
  available_days?: number | null;
  is_banned: boolean;
  is_refunded: boolean;
  manual_score?: string | number | null;
  conclusion?: string | null;
  remark?: string | null;
  created_at: string;
  updated_at: string;
};

export type Revenue = {
  id: string;
  revenue_no: string;
  source: string;
  customer?: string | null;
  amount: string | number;
  currency: string;
  payment_method?: string | null;
  revenue_date: string;
  received: boolean;
  remark?: string | null;
  created_at: string;
  updated_at: string;
};

export type Sub2APIRevenueSyncResult = {
  instance_id?: string | null;
  instance_name?: string | null;
  created_count: number;
  updated_count: number;
  skipped_count: number;
  failed_count: number;
  status: string;
  message?: string | null;
};

export type CostItem = {
  id: string;
  cost_no: string;
  cost_type: string;
  source_type: string;
  supplier_id?: string | null;
  product_name?: string | null;
  amount: string | number;
  currency: string;
  cost_date: string;
  include_all_cost: boolean;
  include_real_cost: boolean;
  one_time: boolean;
  recurring: boolean;
  remark?: string | null;
  created_at: string;
  updated_at: string;
};

export type AuditLog = {
  id: string;
  user_id?: string | null;
  action: string;
  resource_type: string;
  resource_id?: string | null;
  ip_address?: string | null;
  user_agent?: string | null;
  detail?: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};

export type SystemMaintenanceStatus = {
  app_name: string;
  app_env: string;
  alembic_head?: string | null;
  backup_dir: string;
  upgrade_commands: {
    docker: string;
    native: string;
  };
};

export type BackupCreateResult = {
  filename: string;
  size_bytes: number;
  created_at: string;
};

export type BackupImportResult = {
  status: string;
};
