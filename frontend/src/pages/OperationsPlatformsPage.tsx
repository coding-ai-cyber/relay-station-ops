import { EditOutlined, EyeOutlined, LinkOutlined, PlusOutlined } from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, Form, Input, Modal, Select, Space, Switch, Tag, Typography, message } from "antd";
import { useMemo, useState } from "react";

import {
  createOperationsPlatform,
  deleteOperationsPlatform,
  listOperationsPlatforms,
  revealOperationsPlatformSecret,
  updateOperationsPlatform
} from "../api/endpoints";
import type { OperationsPlatform, OperationsPlatformSecret } from "../api/types";
import { DeleteButton } from "../components/DeleteButton";
import { EntityTable } from "../components/EntityTable";
import { PageHeader } from "../components/PageHeader";
import { yesNo } from "../utils/format";

const platformTypeOptions = [
  { value: "dns", label: "DNS" },
  { value: "domain", label: "域名" },
  { value: "fingerprint_browser", label: "指纹浏览器" },
  { value: "email", label: "邮箱" },
  { value: "monitoring", label: "监控" },
  { value: "storage", label: "云存储" },
  { value: "payment", label: "支付" },
  { value: "notification", label: "通知" },
  { value: "other", label: "其他" }
];

const platformStatusOptions = [
  { value: "active", label: "正常" },
  { value: "inactive", label: "停用" },
  { value: "expired", label: "已到期" },
  { value: "abandoned", label: "已废弃" }
];

function optionLabel(options: { value: string; label: string }[], value?: string | null) {
  return options.find((item) => item.value === value)?.label ?? value ?? "-";
}

function statusColor(status?: string | null) {
  if (status === "active") {
    return "green";
  }
  if (status === "expired") {
    return "red";
  }
  if (status === "inactive") {
    return "gold";
  }
  return "default";
}

function normalizePayload(values: Record<string, unknown>, editing: OperationsPlatform | null) {
  const payload: Record<string, unknown> = {
    ...values,
    bound_email: null,
    bound_phone: null,
    has_expiry: false,
    expired_at: null,
    include_cost: false
  };

  for (const key of ["login_url", "remark"]) {
    if (typeof payload[key] === "string" && !payload[key].trim()) {
      payload[key] = null;
    }
  }

  if (editing) {
    if (typeof payload.login_account === "string" && !payload.login_account.trim()) {
      delete payload.login_account;
    }
    if (typeof payload.login_secret === "string" && !payload.login_secret.trim()) {
      delete payload.login_secret;
    }
  }

  return payload;
}

export function OperationsPlatformsPage() {
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<OperationsPlatform | null>(null);
  const [secret, setSecret] = useState<OperationsPlatformSecret | null>(null);
  const [keyword, setKeyword] = useState("");
  const [typeFilter, setTypeFilter] = useState<string | undefined>();
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [coreFilter, setCoreFilter] = useState<string | undefined>();
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  const queryParams = useMemo(
    () => ({
      q: keyword.trim() || undefined,
      type: typeFilter,
      status: statusFilter,
      is_core: coreFilter === undefined ? undefined : coreFilter === "true"
    }),
    [coreFilter, keyword, statusFilter, typeFilter]
  );

  const query = useQuery({
    queryKey: ["operations-platforms", queryParams],
    queryFn: () => listOperationsPlatforms(queryParams)
  });

  const mutation = useMutation({
    mutationFn: (values: Record<string, unknown>) =>
      editing ? updateOperationsPlatform(editing.id, values) : createOperationsPlatform(values),
    onSuccess: async () => {
      message.success(editing ? "平台配置已更新" : "平台配置已创建");
      setOpen(false);
      setEditing(null);
      form.resetFields();
      await queryClient.invalidateQueries({ queryKey: ["operations-platforms"] });
    },
    onError: (error) => message.error(error.message)
  });

  const revealMutation = useMutation({
    mutationFn: revealOperationsPlatformSecret,
    onSuccess: (payload) => setSecret(payload),
    onError: (error) => message.error(error.message)
  });

  const deleteMutation = useMutation({
    mutationFn: deleteOperationsPlatform,
    onSuccess: async () => {
      message.success("平台配置已删除");
      await queryClient.invalidateQueries({ queryKey: ["operations-platforms"] });
    },
    onError: (error) => message.error(error.message)
  });

  const resetFilters = () => {
    setKeyword("");
    setTypeFilter(undefined);
    setStatusFilter(undefined);
    setCoreFilter(undefined);
  };

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({
      type: "dns",
      status: "active",
      is_core: false
    });
    setOpen(true);
  };

  const openEdit = (record: OperationsPlatform) => {
    setEditing(record);
    form.setFieldsValue({
      ...record,
      login_account: undefined,
      login_secret: undefined
    });
    setOpen(true);
  };

  return (
    <>
      <PageHeader
        title="平台配置"
        subtitle="记录 DNS、域名、指纹浏览器、邮箱、监控等不一定走采购流程的运维平台信息。"
      />

      <EntityTable<OperationsPlatform>
        title="平台配置列表"
        data={query.data ?? []}
        loading={query.isLoading}
        onRefresh={() => query.refetch()}
        extra={
          <Space wrap size={8}>
            <Input.Search
              allowClear
              placeholder="搜索平台名称"
              style={{ width: 200 }}
              value={keyword}
              onChange={(event) => setKeyword(event.target.value)}
            />
            <Select
              allowClear
              placeholder="类型"
              style={{ width: 140 }}
              value={typeFilter}
              options={platformTypeOptions}
              onChange={setTypeFilter}
            />
            <Select
              allowClear
              placeholder="状态"
              style={{ width: 120 }}
              value={statusFilter}
              options={platformStatusOptions}
              onChange={setStatusFilter}
            />
            <Select
              allowClear
              placeholder="核心"
              style={{ width: 120 }}
              value={coreFilter}
              options={[
                { value: "true", label: "核心" },
                { value: "false", label: "非核心" }
              ]}
              onChange={setCoreFilter}
            />
            <Button onClick={resetFilters}>重置</Button>
            <Button icon={<PlusOutlined />} type="primary" onClick={openCreate}>
              新增
            </Button>
          </Space>
        }
        columns={[
          { title: "名称", dataIndex: "name", fixed: "left", width: 180 },
          {
            title: "类型",
            dataIndex: "type",
            width: 120,
            render: (value?: string) => optionLabel(platformTypeOptions, value)
          },
          {
            title: "登录地址",
            dataIndex: "login_url",
            width: 220,
            render: (value?: string | null) =>
              value ? (
                <Typography.Link href={value} target="_blank" rel="noreferrer" ellipsis>
                  {value}
                </Typography.Link>
              ) : (
                "-"
              )
          },
          { title: "核心", dataIndex: "is_core", width: 90, render: yesNo },
          {
            title: "状态",
            dataIndex: "status",
            width: 100,
            render: (value?: string) => <Tag color={statusColor(value)}>{optionLabel(platformStatusOptions, value)}</Tag>
          },
          {
            title: "凭证",
            width: 120,
            render: (_, record) =>
              record.has_login_account || record.has_login_secret ? <Tag color="blue">已录入</Tag> : <Tag>未录入</Tag>
          },
          {
            title: "操作",
            fixed: "right",
            width: 280,
            render: (_, record) => (
              <div className="table-actions">
                <Button
                  size="small"
                  icon={<LinkOutlined />}
                  disabled={!record.login_url}
                  onClick={() => record.login_url && window.open(record.login_url, "_blank", "noopener,noreferrer")}
                >
                  打开
                </Button>
                <Button
                  size="small"
                  icon={<EyeOutlined />}
                  disabled={!record.has_login_account && !record.has_login_secret}
                  loading={revealMutation.isPending}
                  onClick={() => revealMutation.mutate(record.id)}
                >
                  查看凭证
                </Button>
                <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>
                  编辑
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

      <Modal
        title={editing ? "编辑平台配置" : "新增平台配置"}
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
        <Form
          form={form}
          layout="vertical"
          onFinish={(values) => mutation.mutate(normalizePayload(values, editing))}
        >
          <Form.Item name="name" label="平台名称" rules={[{ required: true }]}>
            <Input placeholder="例如：Cloudflare / 指纹浏览器后台 / 域名注册商" />
          </Form.Item>
          <Space align="start" size={12} wrap>
            <Form.Item name="type" label="类型" initialValue="dns" rules={[{ required: true }]} style={{ width: 180 }}>
              <Select options={platformTypeOptions} />
            </Form.Item>
            <Form.Item name="status" label="状态" initialValue="active" style={{ width: 160 }}>
              <Select options={platformStatusOptions} />
            </Form.Item>
            <Form.Item name="is_core" label="核心平台" initialValue={false} valuePropName="checked" style={{ width: 120 }}>
              <Switch />
            </Form.Item>
          </Space>
          <Form.Item name="login_url" label="登录地址">
            <Input placeholder="https://example.com" />
          </Form.Item>
          <Space align="start" size={12} wrap>
            <Form.Item name="login_account" label="登录账号" style={{ width: 260 }}>
              <Input placeholder={editing ? "留空则不修改" : undefined} />
            </Form.Item>
            <Form.Item name="login_secret" label="登录密码/密钥" style={{ width: 260 }}>
              <Input.Password placeholder={editing ? "留空则不修改" : undefined} />
            </Form.Item>
          </Space>
          <Form.Item name="remark" label="备注">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="平台凭证"
        open={!!secret}
        onCancel={() => setSecret(null)}
        footer={<Button onClick={() => setSecret(null)}>关闭</Button>}
        destroyOnHidden
      >
        <Form layout="vertical">
          <Form.Item label="登录账号">
            <Input value={secret?.login_account ?? ""} readOnly />
          </Form.Item>
          <Form.Item label="登录密码/密钥">
            <Input.Password value={secret?.login_secret ?? ""} readOnly />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
