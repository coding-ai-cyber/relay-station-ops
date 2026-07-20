import { apiRequest, getToken, toQuery } from "./client";
import type {
  Account,
  AccountBulkDeleteResult,
  AccountCheckBatch,
  AccountCheckRecord,
  AccountEvaluation,
  AccountItem,
  AccountSecret,
  AccountTypeProfitRow,
  AIPricingRecommendationRow,
  AuditLog,
  CostItem,
  DashboardOverview,
  EvaluationBatch,
  ExpiringAssetRow,
  FileRecord,
  MonthlyProfitRow,
  OperationsPlatform,
  OperationsPlatformSecret,
  Purchase,
  PurchaseAccountJsonBindRequest,
  PurchaseAccountJsonBindResult,
  PurchaseAssetGenerationResult,
  PurchaseBatchProfitRow,
  ProxyPool,
  Revenue,
  ServerAsset,
  ServerSecret,
  ShopMonitor,
  ShopMonitorImportResult,
  ShopMonitorSyncResult,
  Sub2APIRevenueSyncResult,
  BackupCreateResult,
  Supplier,
  SupplierMultiplierRow,
  SupplierSecret,
  Sub2APIInstance,
  Sub2APIGroup,
  Sub2APIProxy,
  Sub2APIImportBatch,
  Sub2APIImportCreateRequest,
  Sub2APIImportItem,
  Sub2APIProbeResult,
  SupplierRankingRow,
  BackupImportResult,
  SystemMaintenanceStatus,
  User
} from "./types";

export async function login(username: string, password: string) {
  return apiRequest<{ access_token: string; token_type: string }>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password })
  });
}

export async function getMe() {
  return apiRequest<User>("/api/auth/me");
}

export async function getDashboardOverview(params: {
  year?: number;
  month?: number;
  start_date?: string;
  end_date?: string;
}) {
  return apiRequest<DashboardOverview>(
    `/api/dashboard/overview${toQuery(params)}`
  );
}

export async function getMonthlyProfitReport(params: {
  start_year: number;
  start_month: number;
  end_year: number;
  end_month: number;
}) {
  return apiRequest<MonthlyProfitRow[]>(
    `/api/reports/monthly-profit${toQuery(params)}`
  );
}

export async function getSupplierRanking() {
  return apiRequest<SupplierRankingRow[]>("/api/reports/supplier-ranking");
}

export async function getSupplierMultiplierReport(targetMargin = 35) {
  return apiRequest<SupplierMultiplierRow[]>(
    `/api/reports/supplier-multiplier${toQuery({ target_margin: targetMargin })}`
  );
}

export async function getAIPricingRecommendations(targetMargin = 35) {
  return apiRequest<AIPricingRecommendationRow[]>(
    `/api/reports/ai-pricing-recommendations${toQuery({ target_margin: targetMargin })}`
  );
}

export async function getAccountTypeProfitReport() {
  return apiRequest<AccountTypeProfitRow[]>("/api/reports/account-type-profit");
}

export async function getPurchaseBatchProfitReport() {
  return apiRequest<PurchaseBatchProfitRow[]>("/api/reports/purchase-batch-profit");
}

export async function getRecentPurchases() {
  return apiRequest<Purchase[]>("/api/dashboard/recent-purchases");
}

export async function getAbnormalAccounts() {
  return apiRequest<Account[]>("/api/dashboard/abnormal-accounts");
}

export async function getExpiringAssets(days = 30) {
  return apiRequest<ExpiringAssetRow[]>(
    `/api/dashboard/expiring-assets${toQuery({ days })}`
  );
}

export async function listSuppliers() {
  return apiRequest<Supplier[]>("/api/suppliers");
}

export async function createSupplier(payload: Record<string, unknown>) {
  return apiRequest<Supplier>("/api/suppliers", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function updateSupplier(id: string, payload: Record<string, unknown>) {
  return apiRequest<Supplier>(`/api/suppliers/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export async function listShopMonitors() {
  return apiRequest<ShopMonitor[]>("/api/shop-monitors");
}

export async function createShopMonitor(payload: Record<string, unknown>) {
  return apiRequest<ShopMonitor>("/api/shop-monitors", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function importSupplierShopMonitors() {
  return apiRequest<ShopMonitorImportResult>("/api/shop-monitors/import-suppliers", {
    method: "POST"
  });
}

export async function syncShopMonitor(id: string) {
  return apiRequest<ShopMonitorSyncResult>(`/api/shop-monitors/${id}/sync`, {
    method: "POST"
  });
}

export async function syncAllShopMonitors() {
  return apiRequest<ShopMonitorSyncResult[]>("/api/shop-monitors/sync-all", {
    method: "POST"
  });
}

export async function deleteSupplier(id: string) {
  return apiRequest<void>(`/api/suppliers/${id}`, {
    method: "DELETE"
  });
}

export async function revealSupplierSecret(id: string) {
  return apiRequest<SupplierSecret>(`/api/suppliers/${id}/reveal-secret`, {
    method: "POST"
  });
}

export async function listOperationsPlatforms(params: Record<string, unknown> = {}) {
  return apiRequest<OperationsPlatform[]>(`/api/operations-platforms${toQuery(params)}`);
}

export async function createOperationsPlatform(payload: Record<string, unknown>) {
  return apiRequest<OperationsPlatform>("/api/operations-platforms", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function updateOperationsPlatform(id: string, payload: Record<string, unknown>) {
  return apiRequest<OperationsPlatform>(`/api/operations-platforms/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export async function deleteOperationsPlatform(id: string) {
  return apiRequest<void>(`/api/operations-platforms/${id}`, {
    method: "DELETE"
  });
}

export async function revealOperationsPlatformSecret(id: string) {
  return apiRequest<OperationsPlatformSecret>(`/api/operations-platforms/${id}/reveal-secret`, {
    method: "POST"
  });
}

export async function listPurchases() {
  return apiRequest<Purchase[]>("/api/purchases");
}

export async function createPurchase(payload: Record<string, unknown>) {
  return apiRequest<Purchase>("/api/purchases", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function updatePurchase(id: string, payload: Record<string, unknown>) {
  return apiRequest<Purchase>(`/api/purchases/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export async function deletePurchase(id: string) {
  return apiRequest<void>(`/api/purchases/${id}`, {
    method: "DELETE"
  });
}

export async function createPurchaseAssets(id: string, payload: Record<string, unknown> = {}) {
  return apiRequest<PurchaseAssetGenerationResult>(`/api/purchases/${id}/create-assets`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function bindPurchaseAccountJson(
  purchaseId: string,
  payload: PurchaseAccountJsonBindRequest
) {
  return apiRequest<PurchaseAccountJsonBindResult>(
    `/api/purchases/${purchaseId}/accounts/bind-json`,
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function uploadFile(file: File) {
  const body = new FormData();
  body.append("upload", file);
  return apiRequest<FileRecord>("/api/files/upload", {
    method: "POST",
    body
  });
}

export async function downloadFile(fileId: string) {
  const headers = new Headers();
  const token = getToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`/api/files/${fileId}/download`, { headers });
  if (!response.ok) {
    throw new Error(`下载失败：${response.status}`);
  }
  return response.blob();
}

export async function listAccounts() {
  return apiRequest<Account[]>("/api/accounts");
}

export async function bulkImportAccounts(payload: Record<string, unknown>[]) {
  return apiRequest<Account[]>("/api/accounts/bulk-import", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function listUsers() {
  return apiRequest<User[]>("/api/users");
}

export async function createUser(payload: Record<string, unknown>) {
  return apiRequest<User>("/api/users", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function updateUser(id: string, payload: Record<string, unknown>) {
  return apiRequest<User>(`/api/users/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export async function deleteUser(id: string) {
  return apiRequest<void>(`/api/users/${id}`, {
    method: "DELETE"
  });
}

export async function createAccount(payload: Record<string, unknown>) {
  return apiRequest<Account>("/api/accounts", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function updateAccount(id: string, payload: Record<string, unknown>) {
  return apiRequest<Account>(`/api/accounts/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export async function deleteAccount(id: string) {
  return apiRequest<void>(`/api/accounts/${id}`, {
    method: "DELETE"
  });
}

export async function bulkDeleteAccounts(accountIds: string[]) {
  return apiRequest<AccountBulkDeleteResult>("/api/accounts/bulk-delete", {
    method: "POST",
    body: JSON.stringify({ account_ids: accountIds })
  });
}

export async function markAccountStatus(id: string, payload: Record<string, unknown>) {
  return apiRequest<Account>(`/api/accounts/${id}/mark-status`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function revealAccountSecret(id: string) {
  return apiRequest<AccountSecret>(`/api/accounts/${id}/reveal-secret`, {
    method: "POST"
  });
}

export async function runSub2ApiAccountCheck(payload: Record<string, unknown>) {
  return apiRequest<AccountCheckBatch>("/api/accounts/sub2api-checks", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function runAutoSub2ApiAccountCheck(payload: Record<string, unknown>) {
  return apiRequest<AccountCheckBatch>("/api/accounts/sub2api-checks/auto", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function listSub2ApiAccountChecks() {
  return apiRequest<AccountCheckBatch[]>("/api/accounts/sub2api-checks");
}

export async function listSub2ApiCheckRecords(batchId: string) {
  return apiRequest<AccountCheckRecord[]>(
    `/api/accounts/sub2api-checks/${batchId}/records`
  );
}

export async function listAccountCheckRecords(accountId: string) {
  return apiRequest<AccountCheckRecord[]>(`/api/accounts/${accountId}/check-records`);
}

export async function listAccountItems(accountId: string) {
  return apiRequest<AccountItem[]>(`/api/accounts/${accountId}/items`);
}

export async function listSub2ApiInstances() {
  return apiRequest<Sub2APIInstance[]>("/api/sub2api-instances");
}

export async function createSub2ApiInstance(payload: Record<string, unknown>) {
  return apiRequest<Sub2APIInstance>("/api/sub2api-instances", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function updateSub2ApiInstance(id: string, payload: Record<string, unknown>) {
  return apiRequest<Sub2APIInstance>(`/api/sub2api-instances/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export async function deleteSub2ApiInstance(id: string) {
  return apiRequest<void>(`/api/sub2api-instances/${id}`, {
    method: "DELETE"
  });
}

export async function probeSub2ApiInstance(id: string) {
  return apiRequest<Sub2APIProbeResult>(`/api/sub2api-instances/${id}/probe`, {
    method: "POST"
  });
}

export async function listSub2ApiGroups(instanceId: string) {
  return apiRequest<Sub2APIGroup[]>(`/api/sub2api-instances/${instanceId}/groups`);
}

export async function listSub2ApiProxies(instanceId: string) {
  return apiRequest<Sub2APIProxy[]>(`/api/sub2api-instances/${instanceId}/proxies`);
}

export async function createSub2ApiImport(payload: Sub2APIImportCreateRequest) {
  return apiRequest<Sub2APIImportBatch>("/api/sub2api-imports", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function listSub2ApiImports() {
  return apiRequest<Sub2APIImportBatch[]>("/api/sub2api-imports");
}

export async function listSub2ApiImportItems(batchId: string) {
  return apiRequest<Sub2APIImportItem[]>(`/api/sub2api-imports/${batchId}/items`);
}

export async function retrySub2ApiImport(batchId: string) {
  return apiRequest<Sub2APIImportBatch>(`/api/sub2api-imports/${batchId}/retry`, {
    method: "POST"
  });
}

export async function listServers() {
  return apiRequest<ServerAsset[]>("/api/servers");
}

export async function createServer(payload: Record<string, unknown>) {
  return apiRequest<ServerAsset>("/api/servers", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function updateServer(id: string, payload: Record<string, unknown>) {
  return apiRequest<ServerAsset>(`/api/servers/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export async function deleteServer(id: string) {
  return apiRequest<void>(`/api/servers/${id}`, {
    method: "DELETE"
  });
}

export async function renewServer(id: string, payload: Record<string, unknown>) {
  return apiRequest<Purchase>(`/api/servers/${id}/renew`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function revealServerSecret(id: string) {
  return apiRequest<ServerSecret>(`/api/servers/${id}/reveal-secret`, {
    method: "POST"
  });
}

export async function listProxyPools() {
  return apiRequest<ProxyPool[]>("/api/proxy-pools");
}

export async function createProxyPool(payload: Record<string, unknown>) {
  return apiRequest<ProxyPool>("/api/proxy-pools", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function updateProxyPool(id: string, payload: Record<string, unknown>) {
  return apiRequest<ProxyPool>(`/api/proxy-pools/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export async function deleteProxyPool(id: string) {
  return apiRequest<void>(`/api/proxy-pools/${id}`, {
    method: "DELETE"
  });
}

export async function listEvaluationBatches() {
  return apiRequest<EvaluationBatch[]>("/api/evaluation-batches");
}

export async function createEvaluationBatch(payload: Record<string, unknown>) {
  return apiRequest<EvaluationBatch>("/api/evaluation-batches", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function updateEvaluationBatch(id: string, payload: Record<string, unknown>) {
  return apiRequest<EvaluationBatch>(`/api/evaluation-batches/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export async function deleteEvaluationBatch(id: string) {
  return apiRequest<void>(`/api/evaluation-batches/${id}`, {
    method: "DELETE"
  });
}

export async function finalizeEvaluationBatch(id: string) {
  return apiRequest<EvaluationBatch>(`/api/evaluation-batches/${id}/finalize`, {
    method: "POST"
  });
}

export async function listAccountEvaluations(batchId: string) {
  return apiRequest<AccountEvaluation[]>(
    `/api/evaluation-batches/${batchId}/account-evaluations`
  );
}

export async function createAccountEvaluation(
  batchId: string,
  payload: Record<string, unknown>
) {
  return apiRequest<AccountEvaluation>(
    `/api/evaluation-batches/${batchId}/account-evaluations`,
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function listRevenues() {
  return apiRequest<Revenue[]>("/api/revenues");
}

export async function createRevenue(payload: Record<string, unknown>) {
  return apiRequest<Revenue>("/api/revenues", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function updateRevenue(id: string, payload: Record<string, unknown>) {
  return apiRequest<Revenue>(`/api/revenues/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export async function deleteRevenue(id: string) {
  return apiRequest<void>(`/api/revenues/${id}`, {
    method: "DELETE"
  });
}

export async function syncSub2ApiRevenues() {
  return apiRequest<Sub2APIRevenueSyncResult[]>("/api/revenues/sync-sub2api", {
    method: "POST"
  });
}

export async function listCostItems() {
  return apiRequest<CostItem[]>("/api/cost-items");
}

export async function createCostItem(payload: Record<string, unknown>) {
  return apiRequest<CostItem>("/api/cost-items", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function updateCostItem(id: string, payload: Record<string, unknown>) {
  return apiRequest<CostItem>(`/api/cost-items/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export async function deleteCostItem(id: string) {
  return apiRequest<void>(`/api/cost-items/${id}`, {
    method: "DELETE"
  });
}

export async function listAuditLogs() {
  return apiRequest<AuditLog[]>("/api/audit-logs");
}

export async function getSystemMaintenanceStatus() {
  return apiRequest<SystemMaintenanceStatus>("/api/system-maintenance/status");
}

export async function createSystemBackup() {
  return apiRequest<BackupCreateResult>("/api/system-maintenance/backups", {
    method: "POST",
    timeoutMs: 120_000
  });
}

export async function importSystemBackup(file: File, force = false) {
  const body = new FormData();
  body.append("upload", file);
  return apiRequest<BackupImportResult>(`/api/system-maintenance/import${toQuery({ force })}`, {
    method: "POST",
    body,
    timeoutMs: 120_000
  });
}

export async function downloadSystemBackup(filename: string) {
  const headers = new Headers();
  const token = getToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const response = await fetch(
    `/api/system-maintenance/backups/${encodeURIComponent(filename)}/download`,
    { headers }
  );
  if (!response.ok) {
    throw new Error(`备份下载失败：${response.status}`);
  }
  return response.blob();
}
