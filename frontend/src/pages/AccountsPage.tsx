import {
  CloudUploadOutlined,
  ClockCircleOutlined,
  EditOutlined,
  EyeOutlined,
  HistoryOutlined,
  PlusOutlined,
  RedoOutlined,
  DeleteOutlined,
  ThunderboltOutlined,
  UnorderedListOutlined,
  UploadOutlined
} from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  App,
  Button,
  Form,
  Input,
  InputNumber,
  Modal,
  Segmented,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Upload
} from "antd";
import type { UploadProps } from "antd";
import { useState } from "react";

import {
  bulkDeleteAccounts,
  bulkImportAccounts,
  createSub2ApiImport,
  createAccount,
  deleteAccount,
  listAccountCheckRecords,
  listAccountItems,
  listAccounts,
  listSub2ApiGroups,
  listSub2ApiImportItems,
  listSub2ApiImports,
  listSub2ApiInstances,
  listSub2ApiProxies,
  listSub2ApiAccountChecks,
  markAccountStatus,
  revealAccountSecret,
  retrySub2ApiImport,
  runAutoSub2ApiAccountCheck,
  updateAccount,
  uploadFile
} from "../api/endpoints";
import type {
  Account,
  AccountCheckRecord,
  AccountItem,
  AccountSecret,
  Sub2APIImportBatch,
  Sub2APIImportItem
} from "../api/types";
import { DeleteButton } from "../components/DeleteButton";
import { EntityTable } from "../components/EntityTable";
import { PageHeader } from "../components/PageHeader";
import { dateTime, duration, money, yesNo } from "../utils/format";

const statusOptions = [
  { value: "pending_test", label: "待测试" },
  { value: "available", label: "可用" },
  { value: "unavailable", label: "不可用" },
  { value: "risk_control", label: "风控" },
  { value: "banned", label: "封禁" },
  { value: "refunded", label: "已退款" },
  { value: "abandoned", label: "已废弃" },
  { value: "api_401", label: "Sub2API 401" },
  { value: "api_403", label: "Sub2API 403" },
  { value: "api_429", label: "Sub2API 429" },
  { value: "rate_limited", label: "限流中" },
  { value: "error", label: "错误" },
  { value: "check_failed", label: "检测失败" }
];

function statusTag(status: string) {
  const color =
    status === "available"
      ? "green"
      : ["api_401", "api_403", "api_429", "risk_control", "banned", "error"].includes(status)
        ? "red"
        : status === "rate_limited"
          ? "gold"
          : status === "pending_test"
            ? "blue"
            : "orange";
  const label = statusOptions.find((item) => item.value === status)?.label ?? status;
  return <Tag color={color}>{label}</Tag>;
}

function importStatusTag(status: Sub2APIImportBatch["status"] | Sub2APIImportItem["status"]) {
  const config = {
    running: { color: "blue", label: "执行中" },
    completed: { color: "green", label: "已完成" },
    partial: { color: "gold", label: "部分成功" },
    failed: { color: "red", label: "失败" },
    pending: { color: "default", label: "等待中" },
    success: { color: "green", label: "成功" },
    skipped: { color: "default", label: "已跳过" }
  }[status] ?? { color: "default", label: status };
  return <Tag color={config.color}>{config.label}</Tag>;
}

function isStaleRunningImport(batch: Sub2APIImportBatch) {
  if (batch.status !== "running" || !batch.started_at) {
    return false;
  }
  return Date.now() - new Date(batch.started_at).getTime() >= 15 * 60 * 1000;
}

function canRetryImport(batch: Sub2APIImportBatch) {
  return batch.failed_count > 0 || isStaleRunningImport(batch);
}

function hasImportableCredentials(account: Account) {
  return account.has_sub2api_key || account.has_raw_credentials;
}

function parseBool(value: unknown, defaultValue = false) {
  if (value === undefined || value === null || value === "") {
    return defaultValue;
  }
  if (typeof value === "boolean") {
    return value;
  }
  return ["1", "true", "yes", "y", "是"].includes(String(value).toLowerCase());
}

function normalizeImportedRow(
  row: Record<string, unknown>,
  importFileId?: string,
  importBatchNo?: string
) {
  const accountNo =
    row.account_no ??
    row.accountNo ??
    row.no ??
    row.email ??
    row.login_account ??
    row.username ??
    row.account;
  return {
    account_no: String(accountNo || `ACC-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`),
    name: row.name,
    account_type: row.account_type ?? row.type ?? "OpenAI",
    plan_type: row.plan_type ?? row.plan ?? "Free",
    login_url: row.login_url,
    login_account: row.login_account ?? row.username ?? row.account ?? row.email,
    login_password: row.login_password ?? row.password,
    authorized_email: row.authorized_email ?? row.auth_email ?? row.email,
    bind_email: row.bind_email,
    recovery_email: row.recovery_email,
    sub2api_instance_id: row.sub2api_instance_id,
    sub2api_account_id: row.sub2api_account_id ?? row.sub2api_id ?? row.sub_id,
    sub2api_key: row.sub2api_key ?? row.api_key ?? row.key,
    country_region: row.country_region,
    proxy_requirement: row.proxy_requirement,
    status: row.status ?? "pending_test",
    participate_operation: parseBool(row.participate_operation),
    include_real_cost: parseBool(row.include_real_cost),
    cost_unit_price: row.cost_unit_price,
    import_file_id: importFileId,
    import_batch_no: importBatchNo,
    raw_payload: row,
    remark: row.remark
  };
}

export function AccountsPage() {
  const { message, modal } = App.useApp();
  const [open, setOpen] = useState(false);
  const [checkOpen, setCheckOpen] = useState(false);
  const [editing, setEditing] = useState<Account | null>(null);
  const [secret, setSecret] = useState<AccountSecret | null>(null);
  const [statusAccount, setStatusAccount] = useState<Account | null>(null);
  const [historyAccount, setHistoryAccount] = useState<Account | null>(null);
  const [detailAccount, setDetailAccount] = useState<Account | null>(null);
  const [sub2apiImportOpen, setSub2apiImportOpen] = useState(false);
  const [importDetailBatch, setImportDetailBatch] = useState<Sub2APIImportBatch | null>(null);
  const [selectedAccountIds, setSelectedAccountIds] = useState<string[]>([]);
  const [form] = Form.useForm();
  const [statusForm] = Form.useForm();
  const [checkForm] = Form.useForm();
  const [sub2apiImportForm] = Form.useForm();
  const selectedImportInstanceId = Form.useWatch("instance_id", sub2apiImportForm) as string | undefined;
  const selectedImportScope = Form.useWatch("scope", sub2apiImportForm) as "selected" | "all" | undefined;
  const queryClient = useQueryClient();

  const query = useQuery({ queryKey: ["accounts"], queryFn: listAccounts });
  const instancesQuery = useQuery({
    queryKey: ["sub2api-instances"],
    queryFn: listSub2ApiInstances
  });
  const instancesById = new Map((instancesQuery.data ?? []).map((item) => [item.id, item]));
  const checkBatchesQuery = useQuery({
    queryKey: ["account-check-batches"],
    queryFn: listSub2ApiAccountChecks
  });
  const importBatchesQuery = useQuery({
    queryKey: ["sub2api-imports"],
    queryFn: listSub2ApiImports
  });
  const groupsQuery = useQuery({
    queryKey: ["sub2api-groups", selectedImportInstanceId],
    queryFn: () => listSub2ApiGroups(selectedImportInstanceId!),
    enabled: !!selectedImportInstanceId && sub2apiImportOpen
  });
  const proxiesQuery = useQuery({
    queryKey: ["sub2api-proxies", selectedImportInstanceId],
    queryFn: () => listSub2ApiProxies(selectedImportInstanceId!),
    enabled: !!selectedImportInstanceId && sub2apiImportOpen
  });
  const importItemsQuery = useQuery({
    queryKey: ["sub2api-import-items", importDetailBatch?.id],
    queryFn: () => listSub2ApiImportItems(importDetailBatch!.id),
    enabled: !!importDetailBatch
  });
  const historyQuery = useQuery({
    queryKey: ["account-check-records", historyAccount?.id],
    queryFn: () => listAccountCheckRecords(historyAccount!.id),
    enabled: !!historyAccount
  });
  const detailQuery = useQuery({
    queryKey: ["account-items", detailAccount?.id],
    queryFn: () => listAccountItems(detailAccount!.id),
    enabled: !!detailAccount
  });
  const detailItems = detailQuery.data ?? [];
  const detailStatusSummary = {
    total: detailItems.length,
    available: detailItems.filter((item) => item.status === "available").length,
    rateLimited: detailItems.filter((item) => item.status === "rate_limited").length,
    error: detailItems.filter((item) =>
      ["error", "unavailable", "api_401", "api_403", "api_429", "check_failed", "risk_control", "banned"].includes(
        item.status
      )
    ).length,
    unchecked: detailItems.filter((item) => !item.last_checked_at).length
  };
  const selectedAccountIdSet = new Set(selectedAccountIds);
  const importTargetAccounts = (query.data ?? []).filter((account) => selectedAccountIdSet.has(account.id));
  const importReadyCount = importTargetAccounts.filter(hasImportableCredentials).length;

  const mutation = useMutation({
    mutationFn: (values: Record<string, unknown>) =>
      editing ? updateAccount(editing.id, values) : createAccount(values),
    onSuccess: async () => {
      message.success(editing ? "账号已更新" : "账号已创建");
      setOpen(false);
      setEditing(null);
      form.resetFields();
      await queryClient.invalidateQueries({ queryKey: ["accounts"] });
    },
    onError: (error) => message.error(error.message)
  });

  const revealMutation = useMutation({
    mutationFn: revealAccountSecret,
    onSuccess: (payload) => setSecret(payload),
    onError: (error) => message.error(error.message)
  });

  const statusMutation = useMutation({
    mutationFn: (values: Record<string, unknown>) => markAccountStatus(statusAccount!.id, values),
    onSuccess: async () => {
      message.success("账号状态已更新");
      setStatusAccount(null);
      await queryClient.invalidateQueries({ queryKey: ["accounts"] });
    },
    onError: (error) => message.error(error.message)
  });
  const deleteMutation = useMutation({
    mutationFn: deleteAccount,
    onSuccess: async () => {
      message.success("账号已删除");
      setSelectedAccountIds([]);
      await queryClient.invalidateQueries({ queryKey: ["accounts"] });
    },
    onError: (error) => message.error(error.message)
  });
  const bulkDeleteMutation = useMutation({
    mutationFn: bulkDeleteAccounts,
    onSuccess: async (result) => {
      message.success(`已删除 ${result.deleted_count} 个账号`);
      setSelectedAccountIds([]);
      await queryClient.invalidateQueries({ queryKey: ["accounts"] });
    },
    onError: (error) => message.error(error.message)
  });

  const importMutation = useMutation({
    mutationFn: bulkImportAccounts,
    onSuccess: async (rows) => {
      message.success(`已导入 ${rows.length} 个账号`);
      await queryClient.invalidateQueries({ queryKey: ["accounts"] });
    },
    onError: (error) => message.error(error.message)
  });

  const sub2apiImportMutation = useMutation({
    mutationFn: (values: Record<string, unknown>) => {
      const selectAll = values.scope === "all";
      const accountIds = selectAll ? [] : selectedAccountIds;
      if (!selectAll && !accountIds.length) {
        throw new Error("没有可导入的账号");
      }
      return createSub2ApiImport({
        instance_id: String(values.instance_id),
        select_all: selectAll,
        account_ids: accountIds,
        group_ids: values.group_ids as number[],
        proxy_id: values.proxy_id ? Number(values.proxy_id) : undefined,
        duplicate_policy: values.duplicate_policy as "skip" | "update",
        remark: values.remark ? String(values.remark) : undefined
      });
    },
    onSuccess: async (batch) => {
      message.success(
        `导入完成：成功 ${batch.success_count}，失败 ${batch.failed_count}，跳过 ${batch.skipped_count}`
      );
      setSub2apiImportOpen(false);
      setSelectedAccountIds([]);
      sub2apiImportForm.resetFields();
      setImportDetailBatch(batch);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["accounts"] }),
        queryClient.invalidateQueries({ queryKey: ["sub2api-imports"] })
      ]);
    },
    onError: (error) => message.error(error.message)
  });

  const retryImportMutation = useMutation({
    mutationFn: retrySub2ApiImport,
    onSuccess: async (batch) => {
      message.success(
        `重试完成：成功 ${batch.success_count}，失败 ${batch.failed_count}，跳过 ${batch.skipped_count}`
      );
      setImportDetailBatch(batch);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["accounts"] }),
        queryClient.invalidateQueries({ queryKey: ["sub2api-imports"] })
      ]);
    },
    onError: (error) => message.error(error.message)
  });

  const autoCheckMutation = useMutation({
    mutationFn: runAutoSub2ApiAccountCheck,
    onSuccess: async (batch) => {
      message.success(
        `自动检测完成：共 ${batch.total_count} 个，可用 ${batch.alive_count} 个，异常 ${batch.abnormal_count} 个`
      );
      setCheckOpen(false);
      checkForm.resetFields();
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["accounts"] }),
        queryClient.invalidateQueries({ queryKey: ["account-check-batches"] }),
        queryClient.invalidateQueries({ queryKey: ["sub2api-instances"] })
      ]);
    },
    onError: (error) => message.error(error.message)
  });

  const handleCsvImport: UploadProps["customRequest"] = (options) => {
    const file = options.file as File;
    const importBatchNo = `IMPORT-${new Date().toISOString().replace(/\D/g, "").slice(0, 14)}`;
    const reader = new FileReader();
    reader.onload = async () => {
      try {
        const text = String(reader.result ?? "");
        const [headerLine, ...lines] = text.split(/\r?\n/).filter((line) => line.trim());
        const headers = headerLine.split(",").map((item) => item.trim());
        const rows = lines.map((line) => {
          const cells = line.split(",").map((item) => item.trim());
          return Object.fromEntries(headers.map((header, index) => [header, cells[index] || undefined]));
        });
        await importMutation.mutateAsync(
          rows.map((row) => normalizeImportedRow(row, undefined, importBatchNo))
        );
        options.onSuccess?.(rows);
      } catch (error) {
        options.onError?.(error as Error);
      }
    };
    reader.onerror = () => options.onError?.(new Error("CSV 读取失败"));
    reader.readAsText(file, "utf-8");
  };

  const handleJsonImport: UploadProps["customRequest"] = async (options) => {
    const file = options.file as File;
    const importBatchNo = `JSON-${new Date().toISOString().replace(/\D/g, "").slice(0, 14)}`;
    try {
      const [uploaded, text] = await Promise.all([uploadFile(file), file.text()]);
      const parsed = JSON.parse(text) as unknown;
      const rows = Array.isArray(parsed)
        ? parsed
        : Array.isArray((parsed as { accounts?: unknown[] }).accounts)
          ? (parsed as { accounts: unknown[] }).accounts
          : [parsed];
      const normalized = rows.map((row) =>
        normalizeImportedRow(row as Record<string, unknown>, uploaded.id, importBatchNo)
      );
      await importMutation.mutateAsync(normalized);
      options.onSuccess?.(normalized);
    } catch (error) {
      options.onError?.(error as Error);
      message.error(error instanceof Error ? error.message : "JSON 导入失败");
    }
  };

  const openSub2apiImport = () => {
    sub2apiImportForm.setFieldsValue({
      scope: selectedAccountIds.length ? "selected" : "all",
      duplicate_policy: "skip",
      group_ids: []
    });
    setSub2apiImportOpen(true);
  };

  const submitSub2apiImport = (values: Record<string, unknown>) => {
    sub2apiImportMutation.mutate(values);
  };
  const confirmBulkDelete = () => {
    if (!selectedAccountIds.length) {
      return;
    }
    modal.confirm({
      title: "批量删除账号",
      content: `将删除选中的 ${selectedAccountIds.length} 个账号，并同步清理关联的检测记录和测评记录。`,
      okText: "确认删除",
      okButtonProps: { danger: true },
      cancelText: "取消",
      onOk: () => bulkDeleteMutation.mutateAsync(selectedAccountIds)
    });
  };

  const historyColumns = [
    { title: "检测时间", dataIndex: "checked_at", render: dateTime },
    {
      title: "结果",
      dataIndex: "is_alive",
      render: (value: boolean) => (
        <Tag color={value ? "green" : "red"}>{value ? "可用" : "异常"}</Tag>
      )
    },
    { title: "HTTP", dataIndex: "http_status", render: (value?: number) => value ?? "-" },
    { title: "状态", dataIndex: "sub2api_status" },
    { title: "错误码", dataIndex: "error_code", render: (value?: string) => value ?? "-" },
    { title: "响应耗时", dataIndex: "response_ms", render: (value?: number) => (value ? `${value} ms` : "-") },
    { title: "存活时长", dataIndex: "survived_seconds", render: duration },
    { title: "错误信息", dataIndex: "error_message", render: (value?: string) => value ?? "-" }
  ];

  const detailColumns = [
    { title: "明细编号", dataIndex: "item_no", fixed: "left" as const },
    { title: "邮箱", dataIndex: "email", render: (value?: string) => value ?? "-" },
    { title: "平台", dataIndex: "platform", render: (value?: string) => value ?? "-" },
    { title: "套餐", dataIndex: "plan_type", render: (value?: string) => value ?? "-" },
    { title: "远端账号 ID", dataIndex: "remote_account_id", render: (value?: string) => value ?? "-" },
    { title: "状态", dataIndex: "status", render: statusTag },
    { title: "最近检测", dataIndex: "last_checked_at", render: dateTime },
    {
      title: "HTTP",
      dataIndex: "last_sub2api_status_code",
      render: (value?: number) => (value ? <Tag color={value < 300 ? "green" : "red"}>{value}</Tag> : "-")
    },
    { title: "错误码", dataIndex: "last_sub2api_error_code", render: (value?: string) => value ?? "-" },
    { title: "错误信息", dataIndex: "last_sub2api_message", render: (value?: string) => value ?? "-" },
    { title: "存活时长", dataIndex: "survival_seconds", render: duration },
    { title: "导入批次", dataIndex: "import_batch_no", render: (value?: string) => value ?? "-" },
    { title: "备注", dataIndex: "remark", render: (value?: string) => value ?? "-" }
  ];

  return (
    <>
      <PageHeader
        title="账号资产"
        subtitle="统一管理账号凭证、检测状态，并按远端分组批量导入 Sub2API。"
      />
      <EntityTable<Account>
        title="账号列表"
        data={query.data}
        loading={query.isLoading}
        onRefresh={() => query.refetch()}
        rowSelection={{
          selectedRowKeys: selectedAccountIds,
          preserveSelectedRowKeys: true,
          onChange: (keys) => setSelectedAccountIds(keys.map(String))
        }}
        extra={
          <Space wrap>
            <Upload accept=".csv" customRequest={handleCsvImport} showUploadList={false}>
              <Button icon={<UploadOutlined />} loading={importMutation.isPending}>
                CSV 导入
              </Button>
            </Upload>
            <Upload accept=".json,application/json" customRequest={handleJsonImport} showUploadList={false}>
              <Button icon={<UploadOutlined />} loading={importMutation.isPending}>
                JSON 导入
              </Button>
            </Upload>
            <Button
              icon={<CloudUploadOutlined />}
              disabled={!query.data?.length}
              onClick={openSub2apiImport}
            >
              {selectedAccountIds.length
                ? `导入选中 (${selectedAccountIds.length})`
                : "一键导入全部"}
            </Button>
            <Button icon={<ThunderboltOutlined />} onClick={() => setCheckOpen(true)}>
              一键检测
            </Button>
            <Button
              danger
              icon={<DeleteOutlined />}
              disabled={!selectedAccountIds.length}
              loading={bulkDeleteMutation.isPending}
              onClick={confirmBulkDelete}
            >
              批量删除{selectedAccountIds.length ? ` (${selectedAccountIds.length})` : ""}
            </Button>
            <Button
              icon={<PlusOutlined />}
              type="primary"
              onClick={() => {
                setEditing(null);
                form.resetFields();
                setOpen(true);
              }}
            >
              新增
            </Button>
          </Space>
        }
        columns={[
          { title: "账号编号", dataIndex: "account_no", fixed: "left" },
          { title: "类型", dataIndex: "account_type" },
          { title: "套餐", dataIndex: "plan_type" },
          { title: "登录账号", dataIndex: "login_account" },
          { title: "授权邮箱", dataIndex: "authorized_email", render: (value?: string) => value ?? "-" },
          {
            title: "所属中转站",
            dataIndex: "sub2api_instance_id",
            render: (value?: string | null) => (value ? instancesById.get(value)?.name ?? value : "-")
          },
          { title: "Sub2API ID", dataIndex: "sub2api_account_id", render: (value?: string) => value ?? "-" },
          { title: "状态", dataIndex: "status", render: statusTag },
          {
            title: "最近HTTP",
            dataIndex: "last_sub2api_status_code",
            render: (value?: number) => (value ? <Tag color={value < 300 ? "green" : "red"}>{value}</Tag> : "-")
          },
          { title: "最近检测", dataIndex: "last_checked_at", render: dateTime },
          { title: "存活时长", dataIndex: "survival_seconds", render: duration },
          { title: "导入批次", dataIndex: "import_batch_no", render: (value?: string) => value ?? "-" },
          { title: "参与运营", dataIndex: "participate_operation", render: yesNo },
          { title: "真实成本", dataIndex: "include_real_cost", render: yesNo },
          { title: "成本单价", dataIndex: "cost_unit_price", render: money },
          { title: "有密码", dataIndex: "has_login_password", render: yesNo },
          { title: "有API Key", dataIndex: "has_sub2api_key", render: yesNo },
          {
            title: "操作",
            fixed: "right",
            render: (_, record) => (
              <div className="table-actions">
                <Button
                  size="small"
                  icon={<EyeOutlined />}
                  disabled={!record.has_login_password && !record.has_sub2api_key}
                  loading={revealMutation.isPending}
                  onClick={() => revealMutation.mutate(record.id)}
                >
                  查看密钥
                </Button>
                <Button
                  size="small"
                  icon={<HistoryOutlined />}
                  onClick={() => setHistoryAccount(record)}
                >
                  检测历史
                </Button>
                <Button
                  size="small"
                  icon={<UnorderedListOutlined />}
                  onClick={() => setDetailAccount(record)}
                >
                  查看明细
                </Button>
                <Button
                  size="small"
                  icon={<EditOutlined />}
                  onClick={() => {
                    setEditing(record);
                    form.setFieldsValue(record);
                    setOpen(true);
                  }}
                >
                  编辑
                </Button>
                <Button
                  size="small"
                  icon={<EditOutlined />}
                  onClick={() => {
                    setStatusAccount(record);
                    statusForm.setFieldsValue({
                      status: record.status,
                      participate_operation: record.participate_operation,
                      include_real_cost: record.include_real_cost,
                      available_days: record.available_days
                    });
                  }}
                >
                  状态
                </Button>
                <DeleteButton
                  loading={deleteMutation.isPending}
                  onConfirm={() => deleteMutation.mutate(record.id)}
                />
              </div>
            )
          }
        ]}
      />

      <div className="content-section">
        <div className="toolbar">
          <div>
            <strong className="section-title">Sub2API 导入批次</strong>
            <div className="section-subtitle">逐账号记录创建、更新、跳过和失败结果</div>
          </div>
        </div>
        <Table<Sub2APIImportBatch>
          rowKey="id"
          size="middle"
          loading={importBatchesQuery.isLoading}
          dataSource={importBatchesQuery.data ?? []}
          pagination={{ pageSize: 5, showSizeChanger: false }}
          scroll={{ x: "max-content" }}
          columns={[
            { title: "批次编号", dataIndex: "batch_no", fixed: "left" },
            { title: "Sub2API 实例", dataIndex: "instance_name", render: (value?: string) => value ?? "-" },
            { title: "目标分组", dataIndex: "group_ids", render: (value: number[]) => `${value.length} 个` },
            { title: "重复策略", dataIndex: "duplicate_policy", render: (value: string) => value === "update" ? "更新已有" : "跳过已有" },
            { title: "状态", dataIndex: "status", render: importStatusTag },
            { title: "总数", dataIndex: "total_count" },
            { title: "成功", dataIndex: "success_count", render: (value: number) => <Tag color="green">{value}</Tag> },
            { title: "失败", dataIndex: "failed_count", render: (value: number) => <Tag color={value ? "red" : "default"}>{value}</Tag> },
            { title: "跳过", dataIndex: "skipped_count" },
            { title: "完成时间", dataIndex: "finished_at", render: dateTime },
            {
              title: "操作",
              fixed: "right",
              render: (_, record) => (
                <div className="table-actions">
                  <Button
                    size="small"
                    icon={<UnorderedListOutlined />}
                    onClick={() => setImportDetailBatch(record)}
                  >
                    明细
                  </Button>
                  {canRetryImport(record) ? (
                    <Button
                      size="small"
                      icon={<RedoOutlined />}
                      loading={retryImportMutation.isPending}
                      onClick={() => retryImportMutation.mutate(record.id)}
                    >
                      {isStaleRunningImport(record) ? "恢复并重试" : "重试失败项"}
                    </Button>
                  ) : null}
                </div>
              )
            }
          ]}
        />
      </div>


      <div className="content-section">
        <div className="toolbar">
          <div>
            <strong className="section-title">最近检测批次</strong>
            <div className="section-subtitle">展示每次连接 Sub2API 后的批量检测统计</div>
          </div>
        </div>
        <Table
          rowKey="id"
          size="middle"
          loading={checkBatchesQuery.isLoading}
          dataSource={checkBatchesQuery.data ?? []}
          pagination={{ pageSize: 5, showSizeChanger: false }}
          scroll={{ x: "max-content" }}
          columns={[
            { title: "批次编号", dataIndex: "batch_no", fixed: "left" },
            { title: "总数", dataIndex: "total_count" },
            { title: "可用", dataIndex: "alive_count", render: (value) => <Tag color="green">{value}</Tag> },
            { title: "异常", dataIndex: "abnormal_count", render: (value) => <Tag color="red">{value}</Tag> },
            { title: "401", dataIndex: "status_401_count" },
            { title: "403", dataIndex: "status_403_count" },
            { title: "429", dataIndex: "status_429_count" },
            { title: "开始时间", dataIndex: "started_at", render: dateTime },
            { title: "完成时间", dataIndex: "finished_at", render: dateTime }
          ]}
        />
      </div>

      <Modal
        title={editing ? "编辑账号" : "新增账号"}
        open={open}
        onCancel={() => {
          setOpen(false);
          setEditing(null);
          form.resetFields();
        }}
        onOk={() => form.submit()}
        confirmLoading={mutation.isPending}
        width={760}
        destroyOnHidden
      >
        <Form form={form} layout="vertical" onFinish={(values) => mutation.mutate(values)}>
          <Form.Item name="account_no" label="账号编号" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="account_type" label="账号类型" initialValue="OpenAI">
            <Select
              options={["OpenAI", "Claude", "Gemini", "Grok", "Codex", "other"].map((value) => ({
                value,
                label: value
              }))}
            />
          </Form.Item>
          <Form.Item name="plan_type" label="套餐类型" initialValue="Free">
            <Select
              options={["Free", "Plus", "Team", "API", "normal"].map((value) => ({
                value,
                label: value
              }))}
            />
          </Form.Item>
          <Form.Item
            name="sub2api_instance_id"
            label="所属中转站"
            tooltip="先到「中转站配置」维护多个 Sub2API 中转站，然后在这里选择该账号属于哪个中转。"
          >
            <Select
              allowClear
              loading={instancesQuery.isLoading}
              placeholder="选择对应中转站"
              options={(instancesQuery.data ?? []).map((instance) => ({
                value: instance.id,
                label: `${instance.name} / ${instance.base_url}`,
                disabled: !instance.is_active
              }))}
            />
          </Form.Item>
          <Form.Item name="login_account" label="登录账号">
            <Input />
          </Form.Item>
          <Form.Item name="login_password" label="登录密码">
            <Input.Password placeholder={editing ? "不填写则不修改" : undefined} />
          </Form.Item>
          <Form.Item name="authorized_email" label="授权邮箱">
            <Input />
          </Form.Item>
          <Form.Item name="sub2api_account_id" label="Sub2API 账号ID / Key ID">
            <Input placeholder="用于检测接口中的 {sub2api_account_id}" />
          </Form.Item>
          <Form.Item name="sub2api_key" label="Sub2API Key / Token">
            <Input.Password placeholder={editing ? "不填写则不修改" : "用于检测接口中的 {sub2api_key}"} />
          </Form.Item>
          <Form.Item name="status" label="状态" initialValue="pending_test">
            <Select options={statusOptions} />
          </Form.Item>
          <Form.Item name="cost_unit_price" label="成本单价">
            <InputNumber min={0} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="participate_operation" label="参与运营" initialValue={false} valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="include_real_cost" label="计入真实成本" initialValue={false} valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="导入账号到 Sub2API"
        open={sub2apiImportOpen}
        onCancel={() => {
          setSub2apiImportOpen(false);
          sub2apiImportForm.resetFields();
        }}
        onOk={() => sub2apiImportForm.submit()}
        okText="开始导入"
        confirmLoading={sub2apiImportMutation.isPending}
        width={720}
        forceRender
      >
        <Form
          form={sub2apiImportForm}
          layout="vertical"
          onFinish={submitSub2apiImport}
        >
          <Form.Item name="scope" label="导入范围" rules={[{ required: true }]}>
            <Segmented
              block
              options={[
                {
                  value: "selected",
                  label: `已选择 ${selectedAccountIds.length} 个`,
                  disabled: selectedAccountIds.length === 0
                },
                { value: "all", label: "系统全部账号" }
              ]}
            />
          </Form.Item>

          <div className="import-readiness" aria-live="polite">
            {selectedImportScope === "all" ? (
              <>
                <div>
                  <span>目标账号</span>
                  <strong className="import-server-check">系统全部</strong>
                </div>
                <div>
                  <span>凭证状态</span>
                  <strong className="import-server-check import-ready-count">逐条校验</strong>
                </div>
                <div>
                  <span>异常账号</span>
                  <strong className="import-server-check">结果中展示</strong>
                </div>
              </>
            ) : (
              <>
                <div>
                  <span>目标账号</span>
                  <strong>{importTargetAccounts.length}</strong>
                </div>
                <div>
                  <span>可识别凭证</span>
                  <strong className="import-ready-count">{importReadyCount}</strong>
                </div>
                <div>
                  <span>缺少凭证</span>
                  <strong className={importTargetAccounts.length - importReadyCount ? "import-missing-count" : ""}>
                    {importTargetAccounts.length - importReadyCount}
                  </strong>
                </div>
              </>
            )}
          </div>

          <Alert
            type={selectedImportScope !== "all" && importTargetAccounts.length - importReadyCount > 0 ? "warning" : "info"}
            showIcon
            title="凭证由后端安全发送"
            description={selectedImportScope === "all"
              ? "服务端将读取系统中的全部账号并逐条校验凭证；失败账号会保留在批次明细中。"
              : "优先使用原始 JSON 中的 credentials，其次使用已保存的 API Key；只有登录密码的账号会记录为失败。"}
          />

          <Form.Item
            name="instance_id"
            label="Sub2API 实例"
            rules={[{ required: true, message: "请选择 Sub2API 实例" }]}
            style={{ marginTop: 18 }}
          >
            <Select
              loading={instancesQuery.isLoading}
              placeholder="请选择实例"
              onChange={() => {
                sub2apiImportForm.setFieldValue("group_ids", []);
                sub2apiImportForm.setFieldValue("proxy_id", undefined);
              }}
              options={(instancesQuery.data ?? []).map((instance) => ({
                value: instance.id,
                label: `${instance.name} / ${instance.base_url}`,
                disabled: !instance.is_active
              }))}
            />
          </Form.Item>

          {groupsQuery.isError ? (
            <Alert
              type="error"
              showIcon
              title="分组加载失败"
              description={groupsQuery.error.message}
              style={{ marginBottom: 18 }}
            />
          ) : null}

          <Form.Item
            name="group_ids"
            label="目标分租/分组"
            tooltip="可以只选择某一个分租，也可以同时选择多个分组。后端会按账号平台只绑定匹配的分组。"
            rules={[{ required: true, message: "请选择至少一个目标分组" }]}
          >
            <Select
              mode="multiple"
              allowClear
              loading={groupsQuery.isLoading}
              disabled={!selectedImportInstanceId}
              placeholder={selectedImportInstanceId ? "选择一个或多个分租/分组" : "请先选择实例"}
              options={(groupsQuery.data ?? []).map((group) => ({
                value: group.id,
                label: `${group.name} · ${group.platform || "未标注平台"}`,
                disabled: !!group.status && !["active", "enabled"].includes(group.status.toLowerCase())
              }))}
            />
          </Form.Item>

          <Form.Item name="proxy_id" label="代理地址">
            <Select
              allowClear
              loading={proxiesQuery.isLoading}
              disabled={!selectedImportInstanceId}
              placeholder={selectedImportInstanceId ? "不选择则不指定代理" : "请先选择实例"}
              options={(proxiesQuery.data ?? []).map((proxy) => ({
                value: proxy.id,
                label: `${proxy.name} / ${proxy.protocol || "-"}://${proxy.host || "-"}:${proxy.port ?? "-"}${proxy.latency_ms ? ` / ${proxy.latency_ms}ms` : ""}`,
                disabled: !!proxy.status && !["active", "enabled"].includes(proxy.status.toLowerCase())
              }))}
            />
          </Form.Item>

          <Form.Item
            name="duplicate_policy"
            label="远端重复账号"
            rules={[{ required: true }]}
          >
            <Segmented
              block
              options={[
                { value: "skip", label: "跳过已有账号" },
                { value: "update", label: "更新凭证与分组" }
              ]}
            />
          </Form.Item>

          <Form.Item name="remark" label="批次备注">
            <Input.TextArea rows={2} maxLength={500} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="一键检测 Sub2API 账号"
        open={checkOpen}
        onCancel={() => setCheckOpen(false)}
        onOk={() => checkForm.submit()}
        confirmLoading={autoCheckMutation.isPending}
        width={720}
        destroyOnHidden
      >
        <Form
          form={checkForm}
          layout="vertical"
          initialValues={{
            include_only_operation: true,
            timeout_seconds: 15
          }}
          onFinish={(values) => autoCheckMutation.mutate(values)}
        >
          <Form.Item
            name="instance_id"
            label="Sub2API 实例"
            tooltip="只需要先在配置里保存访问地址和管理员Key，这里选择实例即可自动调用管理接口检测账号。"
            rules={[{ required: true }]}
          >
            <Select
              loading={instancesQuery.isLoading}
              placeholder="请选择 Sub2API 实例"
              options={(instancesQuery.data ?? []).map((item) => ({
                value: item.id,
                label: `${item.name} / ${item.base_url}`
              }))}
            />
          </Form.Item>
          <Form.Item name="account_type" label="只检测账号类型">
            <Select
              allowClear
              options={["OpenAI", "Claude", "Gemini", "Grok", "Codex", "other"].map((value) => ({
                value,
                label: value
              }))}
            />
          </Form.Item>
          <Form.Item name="import_batch_no" label="只检测导入批次">
            <Input placeholder="例如 JSON-20260713010101，可留空" />
          </Form.Item>
          <Form.Item name="include_only_operation" label="只检测参与运营账号" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="timeout_seconds" label="接口超时时间">
            <InputNumber min={1} max={120} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="remark" label="备注">
            <Input />
          </Form.Item>
        </Form>
      </Modal>


      <Modal
        title="账号敏感字段"
        open={!!secret}
        onCancel={() => setSecret(null)}
        footer={<Button onClick={() => setSecret(null)}>关闭</Button>}
        destroyOnHidden
      >
        <Form layout="vertical">
          <Form.Item label="登录账号">
            <Input value={secret?.login_account ?? ""} readOnly />
          </Form.Item>
          <Form.Item label="登录密码">
            <Input.Password value={secret?.login_password ?? ""} readOnly />
          </Form.Item>
          <Form.Item label="授权邮箱">
            <Input value={secret?.authorized_email ?? ""} readOnly />
          </Form.Item>
          <Form.Item label="Sub2API 账号ID">
            <Input value={secret?.sub2api_account_id ?? ""} readOnly />
          </Form.Item>
          <Form.Item label="Sub2API Key">
            <Input.Password value={secret?.sub2api_key ?? ""} readOnly />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="更新账号状态"
        open={!!statusAccount}
        onCancel={() => setStatusAccount(null)}
        onOk={() => statusForm.submit()}
        confirmLoading={statusMutation.isPending}
        destroyOnHidden
      >
        <Form form={statusForm} layout="vertical" onFinish={(values) => statusMutation.mutate(values)}>
          <Form.Item name="status" label="状态" rules={[{ required: true }]}>
            <Select options={statusOptions} />
          </Form.Item>
          <Form.Item name="participate_operation" label="参与运营" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="include_real_cost" label="计入真实成本" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="available_days" label="可用天数">
            <InputNumber min={0} style={{ width: "100%" }} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`检测历史：${historyAccount?.account_no ?? ""}`}
        open={!!historyAccount}
        onCancel={() => setHistoryAccount(null)}
        footer={<Button onClick={() => setHistoryAccount(null)}>关闭</Button>}
        width={1000}
        destroyOnHidden
      >
        <Table<AccountCheckRecord>
          rowKey="id"
          size="middle"
          loading={historyQuery.isLoading}
          dataSource={historyQuery.data ?? []}
          columns={historyColumns}
          pagination={{ pageSize: 8, showSizeChanger: false }}
          scroll={{ x: "max-content" }}
        />
      </Modal>

      <Modal
        title={`账号明细：${detailAccount?.account_no ?? ""}`}
        open={!!detailAccount}
        onCancel={() => setDetailAccount(null)}
        footer={<Button onClick={() => setDetailAccount(null)}>关闭</Button>}
        width={1100}
        destroyOnHidden
      >
        <div className="import-result-summary">
          <div><span>总数</span><strong>{detailStatusSummary.total}</strong></div>
          <div><span>正常</span><strong className="import-ready-count">{detailStatusSummary.available}</strong></div>
          <div><span>限流中</span><strong className="detail-rate-limited-count">{detailStatusSummary.rateLimited}</strong></div>
          <div><span>错误</span><strong className={detailStatusSummary.error ? "import-missing-count" : ""}>{detailStatusSummary.error}</strong></div>
          <div><span>未检测</span><strong>{detailStatusSummary.unchecked}</strong></div>
        </div>
        <Table<AccountItem>
          rowKey="id"
          size="middle"
          loading={detailQuery.isLoading}
          dataSource={detailQuery.data ?? []}
          columns={detailColumns}
          pagination={{ pageSize: 10, showSizeChanger: false }}
          scroll={{ x: "max-content" }}
        />
      </Modal>

      <Modal
        title={`Sub2API 导入明细：${importDetailBatch?.batch_no ?? ""}`}
        open={!!importDetailBatch}
        onCancel={() => setImportDetailBatch(null)}
        width={980}
        destroyOnHidden
        footer={[
          importDetailBatch && canRetryImport(importDetailBatch) ? (
            <Button
              key="retry"
              icon={<RedoOutlined />}
              loading={retryImportMutation.isPending}
              onClick={() => retryImportMutation.mutate(importDetailBatch.id)}
            >
              {isStaleRunningImport(importDetailBatch) ? "恢复并重试" : "重试失败项"}
            </Button>
          ) : null,
          <Button key="close" type="primary" onClick={() => setImportDetailBatch(null)}>
            关闭
          </Button>
        ]}
      >
        <div className="import-result-summary">
          <div><span>总数</span><strong>{importDetailBatch?.total_count ?? 0}</strong></div>
          <div><span>成功</span><strong className="import-ready-count">{importDetailBatch?.success_count ?? 0}</strong></div>
          <div><span>失败</span><strong className="import-missing-count">{importDetailBatch?.failed_count ?? 0}</strong></div>
          <div><span>跳过</span><strong>{importDetailBatch?.skipped_count ?? 0}</strong></div>
        </div>
        <Table<Sub2APIImportItem>
          rowKey="id"
          size="small"
          loading={importItemsQuery.isLoading}
          dataSource={importItemsQuery.data ?? []}
          pagination={{ pageSize: 10, showSizeChanger: false }}
          scroll={{ x: "max-content" }}
          columns={[
            { title: "账号编号", dataIndex: "account_no", fixed: "left" },
            { title: "账号类型", dataIndex: "account_type" },
            {
              title: "动作",
              dataIndex: "action",
              render: (value: string) => ({ create: "创建", update: "更新", skip: "跳过" })[value] ?? value
            },
            { title: "结果", dataIndex: "status", render: importStatusTag },
            { title: "远端账号 ID", dataIndex: "remote_account_id", render: (value?: string) => value ?? "-" },
            { title: "失败原因", dataIndex: "error_message", render: (value?: string) => value ?? "-" },
            { title: "执行时间", dataIndex: "attempted_at", render: dateTime }
          ]}
        />
      </Modal>
    </>
  );
}
