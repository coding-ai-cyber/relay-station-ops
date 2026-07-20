import { EditOutlined, EyeOutlined, PlusOutlined, RedoOutlined } from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, DatePicker, Form, Input, InputNumber, Modal, Select, Switch, message } from "antd";
import dayjs from "dayjs";
import { useState } from "react";

import { createServer, deleteServer, listServers, renewServer, revealServerSecret, updateServer } from "../api/endpoints";
import type { ServerAsset, ServerSecret } from "../api/types";
import { DeleteButton } from "../components/DeleteButton";
import { EntityTable } from "../components/EntityTable";
import { PageHeader } from "../components/PageHeader";
import { dateOnly, money, yesNo } from "../utils/format";
import {
  costStatusOptions,
  currencyOptions,
  paymentMethodOptions,
  serverStatusLabel,
  serverStatusOptions,
  serverUsageLabel,
  serverUsageOptions
} from "../utils/labels";

function cleanPayload(values: Record<string, unknown>) {
  const payload = Object.fromEntries(
    Object.entries(values).map(([key, value]) => [key, value === "" ? null : value])
  );

  if (payload.expired_at) {
    payload.expired_at = dayjs(payload.expired_at as string).startOf("day").toISOString();
  }

  return payload;
}

export function ServersPage() {
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<ServerAsset | null>(null);
  const [renewing, setRenewing] = useState<ServerAsset | null>(null);
  const [secret, setSecret] = useState<ServerSecret | null>(null);
  const [form] = Form.useForm();
  const [renewForm] = Form.useForm();
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["servers"], queryFn: listServers });
  const mutation = useMutation({
    mutationFn: (values: Record<string, unknown>) => {
      const payload = cleanPayload(values);
      return editing ? updateServer(editing.id, payload) : createServer(payload);
    },
    onSuccess: async () => {
      message.success(editing ? "服务器已更新" : "服务器已创建");
      setOpen(false);
      setEditing(null);
      form.resetFields();
      await queryClient.invalidateQueries({ queryKey: ["servers"] });
    },
    onError: (error) => message.error(error.message)
  });
  const revealMutation = useMutation({
    mutationFn: revealServerSecret,
    onSuccess: (payload) => setSecret(payload),
    onError: (error) => message.error(error.message)
  });
  const deleteMutation = useMutation({
    mutationFn: deleteServer,
    onSuccess: async () => {
      message.success("服务器已删除");
      await queryClient.invalidateQueries({ queryKey: ["servers"] });
    },
    onError: (error) => message.error(error.message)
  });
  const renewMutation = useMutation({
    mutationFn: (values: Record<string, unknown>) => {
      if (!renewing) {
        throw new Error("请选择要续费的服务器");
      }
      return renewServer(renewing.id, {
        ...values,
        purchased_at: dayjs(values.purchased_at as string).format("YYYY-MM-DD"),
        new_expired_at: dayjs(values.new_expired_at as string).endOf("day").toISOString()
      });
    },
    onSuccess: async () => {
      message.success("服务器续费已记录");
      setRenewing(null);
      renewForm.resetFields();
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["servers"] }),
        queryClient.invalidateQueries({ queryKey: ["purchases"] }),
        queryClient.invalidateQueries({ queryKey: ["cost-items"] }),
        queryClient.invalidateQueries({ queryKey: ["dashboard", "expiring-assets"] })
      ]);
    },
    onError: (error) => message.error(error.message)
  });

  return (
    <>
      <PageHeader title="服务器资产" subtitle="维护主服务、数据库、IP地址、测试等服务器资产和真实成本口径。" />
      <EntityTable<ServerAsset>
        title="服务器列表"
        data={query.data}
        loading={query.isLoading}
        onRefresh={() => query.refetch()}
        extra={
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
        }
        columns={[
          { title: "服务器名称", dataIndex: "name", fixed: "left" },
          { title: "登录地址/IP", dataIndex: "login_host" },
          { title: "用途", dataIndex: "usage", render: serverUsageLabel },
          { title: "地区", dataIndex: "region" },
          { title: "配置", render: (_, record) => [record.cpu, record.memory, record.disk].filter(Boolean).join(" / ") },
          { title: "月成本", dataIndex: "monthly_cost", render: money },
          { title: "到期时间", dataIndex: "expired_at", render: dateOnly },
          { title: "状态", dataIndex: "status", render: serverStatusLabel },
          { title: "真实成本", dataIndex: "include_real_cost", render: yesNo },
          { title: "有 SSH 密钥", dataIndex: "has_ssh_secret", render: yesNo },
          {
            title: "操作",
            fixed: "right",
            render: (_, record) => (
              <div className="table-actions">
                <Button
                  size="small"
                  icon={<EyeOutlined />}
                  disabled={!record.has_ssh_secret}
                  loading={revealMutation.isPending}
                  onClick={() => revealMutation.mutate(record.id)}
                >
                  查看密钥
                </Button>
                <Button
                  size="small"
                  icon={<EditOutlined />}
                  onClick={() => {
                    setEditing(record);
                    form.setFieldsValue({
                      ...record,
                      expired_at: record.expired_at ? dayjs(record.expired_at) : undefined
                    });
                    setOpen(true);
                  }}
                >
                  编辑
                </Button>
                <Button
                  size="small"
                  icon={<RedoOutlined />}
                  onClick={() => {
                    setRenewing(record);
                    renewForm.setFieldsValue({
                      amount: record.monthly_cost ?? 0,
                      currency: "CNY",
                      purchased_at: dayjs(),
                      new_expired_at: record.expired_at ? dayjs(record.expired_at).add(1, "month") : dayjs().add(1, "month"),
                      include_real_cost: record.include_real_cost,
                      cost_status: "valid"
                    });
                  }}
                >
                  续费
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
        title={`服务器续费：${renewing?.name ?? ""}`}
        open={!!renewing}
        onCancel={() => {
          setRenewing(null);
          renewForm.resetFields();
        }}
        onOk={() => renewForm.submit()}
        confirmLoading={renewMutation.isPending}
        destroyOnHidden
      >
        <Form form={renewForm} layout="vertical" onFinish={(values) => renewMutation.mutate(values)}>
          <Form.Item name="amount" label="续费金额" rules={[{ required: true }]}>
            <InputNumber min={0} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="currency" label="币种" initialValue="CNY">
            <Select options={currencyOptions} />
          </Form.Item>
          <Form.Item name="payment_method" label="支付方式">
            <Select allowClear showSearch options={paymentMethodOptions} />
          </Form.Item>
          <Form.Item name="purchased_at" label="续费日期" rules={[{ required: true }]}>
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="new_expired_at" label="新的到期时间" rules={[{ required: true }]}>
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="cost_status" label="成本状态" initialValue="valid">
            <Select options={costStatusOptions} />
          </Form.Item>
          <Form.Item name="include_real_cost" label="计入真实成本" valuePropName="checked" initialValue>
            <Switch />
          </Form.Item>
          <Form.Item name="remark" label="备注">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={editing ? "编辑服务器" : "新增服务器"}
        open={open}
        onCancel={() => {
          setOpen(false);
          setEditing(null);
          form.resetFields();
        }}
        onOk={() => form.submit()}
        confirmLoading={mutation.isPending}
        width={760}
      >
        <Form form={form} layout="vertical" onFinish={(values) => mutation.mutate(values)}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0 16px" }}>
            <Form.Item name="name" label="服务器名称" rules={[{ required: true }]}>
              <Input placeholder="sub2api-main-01" />
            </Form.Item>
            <Form.Item name="status" label="状态" initialValue="running">
              <Select options={serverStatusOptions} />
            </Form.Item>
            <Form.Item name="login_host" label="登录地址/IP">
              <Input />
            </Form.Item>
            <Form.Item name="ssh_username" label="SSH 用户名">
              <Input />
            </Form.Item>
            <Form.Item name="ssh_secret" label="SSH 密码/密钥">
              <Input.Password placeholder={editing ? "留空则不修改" : undefined} />
            </Form.Item>
            <Form.Item name="console_url" label="控制台地址">
              <Input />
            </Form.Item>
            <Form.Item name="cpu" label="CPU">
              <Input placeholder="4C" />
            </Form.Item>
            <Form.Item name="memory" label="内存">
              <Input placeholder="8GB" />
            </Form.Item>
            <Form.Item name="disk" label="硬盘">
              <Input placeholder="100GB SSD" />
            </Form.Item>
            <Form.Item name="bandwidth" label="带宽">
              <Input placeholder="100Mbps" />
            </Form.Item>
            <Form.Item name="region" label="地区">
              <Input placeholder="US-West" />
            </Form.Item>
            <Form.Item name="usage" label="用途">
              <Select options={serverUsageOptions} />
            </Form.Item>
            <Form.Item name="monthly_cost" label="月成本">
              <InputNumber min={0} style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item name="expired_at" label="到期时间">
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
          </div>
          <Form.Item name="include_real_cost" label="计入真实成本" initialValue={false} valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="remark" label="备注">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="服务器敏感字段"
        open={!!secret}
        onCancel={() => setSecret(null)}
        footer={<Button onClick={() => setSecret(null)}>关闭</Button>}
        destroyOnHidden
      >
        <Form layout="vertical">
          <Form.Item label="登录地址/IP">
            <Input value={secret?.login_host ?? ""} readOnly />
          </Form.Item>
          <Form.Item label="SSH 用户名">
            <Input value={secret?.ssh_username ?? ""} readOnly />
          </Form.Item>
          <Form.Item label="SSH 密码/密钥">
            <Input.Password value={secret?.ssh_secret ?? ""} readOnly />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
