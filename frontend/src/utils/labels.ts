export const supplierTypeOptions = [
  { value: "account", label: "号商" },
  { value: "server", label: "服务器厂商" },
  { value: "proxy", label: "IP地址池厂商" },
  { value: "phone_code", label: "手机接码" },
  { value: "email", label: "邮箱" },
  { value: "shield", label: "过盾" },
  { value: "domain", label: "域名厂商" },
  { value: "other", label: "其他成本供应商" }
];

export const preferredProductTagOptions = [
  { value: "free", label: "free" },
  { value: "K12", label: "K12" },
  { value: "bugteam", label: "bugteam" },
  { value: "plus", label: "plus" },
  { value: "pro", label: "pro" }
];

export const supplierStatusOptions = [
  { value: "normal", label: "正常" },
  { value: "observing", label: "观察中" },
  { value: "paused", label: "暂停" },
  { value: "blocked", label: "拉黑" }
];

export const currencyOptions = [
  { value: "USDT", label: "USDT" },
  { value: "CNY", label: "人民币 CNY" },
  { value: "USD", label: "美元 USD" }
];

export const paymentMethodOptions = [
  { value: "USDT", label: "USDT" },
  { value: "alipay", label: "支付宝" },
  { value: "wechat_pay", label: "微信支付" },
  { value: "bank_card", label: "银行卡" },
  { value: "paypal", label: "PayPal" },
  { value: "wise", label: "Wise" },
  { value: "stripe", label: "Stripe" },
  { value: "cash", label: "现金" },
  { value: "other", label: "其他" }
];

export const costStatusOptions = [
  { value: "testing", label: "测试中" },
  { value: "valid", label: "有效" },
  { value: "partial_valid", label: "部分有效" },
  { value: "invalid", label: "无效" },
  { value: "refunded", label: "退款" },
  { value: "scrapped", label: "报废" }
];

export const costTypeOptions = [
  { value: "account", label: "账号" },
  { value: "server", label: "服务器" },
  { value: "proxy", label: "IP地址代理" },
  { value: "domain", label: "域名" },
  { value: "email", label: "邮箱" },
  { value: "phone", label: "手机号" },
  { value: "software", label: "软件" },
  { value: "labor", label: "人工" },
  { value: "historical_purchase", label: "历史采购" },
  { value: "other", label: "其他" }
];

const nonPurchaseCostTypes = new Set(["historical_purchase", "labor"]);

export const purchaseTypeOptions = costTypeOptions.filter(
  (option) => !nonPurchaseCostTypes.has(option.value)
);

export const costSourceTypeOptions = [
  { value: "manual", label: "手动录入" },
  { value: "purchase", label: "采购生成" },
  { value: "system", label: "系统生成" }
];

export const auditActionOptions = [
  { value: "reveal_supplier_secret", label: "查看供应商密钥" },
  { value: "reveal_account_secret", label: "查看账号密钥" },
  { value: "reveal_server_secret", label: "查看服务器密钥" },
  { value: "create", label: "创建" },
  { value: "update", label: "更新" },
  { value: "delete", label: "删除" }
];

export const auditResourceTypeOptions = [
  { value: "supplier", label: "供应商" },
  { value: "account", label: "账号" },
  { value: "server", label: "服务器" },
  { value: "proxy_pool", label: "IP地址池" },
  { value: "purchase", label: "采购" },
  { value: "cost_item", label: "成本记录" }
];

export const auditDetailOptions = [
  { value: "supplier_name", label: "供应商名称" },
  { value: "account_no", label: "账号编号" },
  { value: "server_name", label: "服务器名称" }
];

export const serverUsageOptions = [
  { value: "sub2api_main", label: "中转站主服务" },
  { value: "database", label: "数据库" },
  { value: "proxy_access", label: "代理访问" },
  { value: "registrar", label: "注册机" },
  { value: "other", label: "其他" }
];

export const serverStatusOptions = [
  { value: "running", label: "运行中" },
  { value: "stopped", label: "停用" },
  { value: "expired", label: "到期" },
  { value: "migrating", label: "迁移中" }
];

export function optionLabel(options: Array<{ value: string; label: string }>, value?: string | null) {
  return options.find((item) => item.value === value)?.label ?? value ?? "-";
}

export function supplierTypeLabel(value?: string | null) {
  return optionLabel(supplierTypeOptions, value);
}

export function supplierStatusLabel(value?: string | null) {
  return optionLabel(supplierStatusOptions, value);
}

export function purchaseTypeLabel(value?: string | null) {
  return optionLabel(purchaseTypeOptions, value);
}

export function costStatusLabel(value?: string | null) {
  return optionLabel(costStatusOptions, value);
}

export function costTypeLabel(value?: string | null) {
  return optionLabel(costTypeOptions, value);
}

export function costSourceTypeLabel(value?: string | null) {
  return optionLabel(costSourceTypeOptions, value);
}

export function auditActionLabel(value?: string | null) {
  return optionLabel(auditActionOptions, value);
}

export function auditResourceTypeLabel(value?: string | null) {
  return optionLabel(auditResourceTypeOptions, value);
}

export function auditDetailLabel(value?: string | null) {
  return optionLabel(auditDetailOptions, value);
}

export function serverUsageLabel(value?: string | null) {
  return optionLabel(serverUsageOptions, value);
}

export function serverStatusLabel(value?: string | null) {
  return optionLabel(serverStatusOptions, value);
}
