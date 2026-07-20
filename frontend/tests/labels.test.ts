import {
  auditActionLabel,
  auditDetailLabel,
  auditResourceTypeLabel,
  costTypeOptions,
  costSourceTypeLabel,
  costTypeLabel,
  purchaseTypeOptions,
  purchaseTypeLabel,
  serverUsageOptions,
  supplierTypeLabel,
  serverStatusLabel,
  serverUsageLabel
} from "../src/utils/labels";

function assertEqual(actual: string, expected: string, label: string) {
  if (actual !== expected) {
    throw new Error(`${label}: expected ${expected}, got ${actual}`);
  }
}

assertEqual(costTypeLabel("historical_purchase"), "历史采购", "translates historical purchase cost type");
assertEqual(costTypeLabel("proxy"), "IP地址代理", "translates proxy cost type");
assertEqual(costTypeLabel("email"), "邮箱", "translates email cost type");
assertEqual(costTypeLabel("phone"), "手机号", "translates phone cost type");
assertEqual(costSourceTypeLabel("manual"), "手动录入", "translates manual cost source");
assertEqual(costSourceTypeLabel("purchase"), "采购生成", "translates purchase cost source");
assertEqual(auditActionLabel("reveal_supplier_secret"), "查看供应商密钥", "translates audit action");
assertEqual(auditResourceTypeLabel("supplier"), "供应商", "translates audit resource type");
assertEqual(auditResourceTypeLabel("proxy_pool"), "IP地址池", "translates audit proxy pool resource type");
assertEqual(auditDetailLabel("supplier_name"), "供应商名称", "translates audit detail key");
assertEqual(purchaseTypeLabel("proxy"), "IP地址代理", "translates proxy purchase type");
assertEqual(supplierTypeLabel("proxy"), "IP地址池厂商", "translates proxy supplier type");
assertEqual(serverUsageLabel("proxy_access"), "代理访问", "translates proxy access server usage");
assertEqual(serverUsageLabel("registrar"), "注册机", "translates registrar server usage");
assertEqual(serverStatusLabel("running"), "运行中", "translates server status");

const costTypeValues = costTypeOptions.map((option) => option.value);
const purchaseTypeValues = purchaseTypeOptions.map((option) => option.value);
const expectedPurchaseTypeValues = costTypeValues.filter(
  (value) => !["historical_purchase", "labor"].includes(value)
);
if (purchaseTypeValues.join(",") !== expectedPurchaseTypeValues.join(",")) {
  throw new Error(
    `purchase type options should sync with cost type options except historical_purchase and labor: expected ${expectedPurchaseTypeValues.join(",")}, got ${purchaseTypeValues.join(",")}`
  );
}
for (const excludedPurchaseType of ["historical_purchase", "labor"]) {
  if (purchaseTypeValues.includes(excludedPurchaseType)) {
    throw new Error(`purchase type options should not include ${excludedPurchaseType}`);
  }
}
for (const removedType of ["fee", "test_loss", "refund_loss"]) {
  if (costTypeValues.includes(removedType)) {
    throw new Error(`cost type options should not include ${removedType}`);
  }
}

const serverUsageValues = serverUsageOptions.map((option) => option.value);
const expectedServerUsageValues = ["sub2api_main", "database", "proxy_access", "registrar", "other"];
if (serverUsageValues.join(",") !== expectedServerUsageValues.join(",")) {
  throw new Error(
    `server usage options should be ${expectedServerUsageValues.join(",")}, got ${serverUsageValues.join(",")}`
  );
}
for (const removedUsage of ["proxy", "testing"]) {
  if (serverUsageValues.includes(removedUsage)) {
    throw new Error(`server usage options should not include ${removedUsage}`);
  }
}
