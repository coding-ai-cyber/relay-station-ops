import { EditOutlined, PlusOutlined } from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, DatePicker, Form, Input, InputNumber, Modal, Select, Switch, message } from "antd";
import dayjs from "dayjs";
import { useState } from "react";

import { createProxyPool, deleteProxyPool, listProxyPools, updateProxyPool } from "../api/endpoints";
import type { ProxyPool } from "../api/types";
import { DeleteButton } from "../components/DeleteButton";
import { EntityTable } from "../components/EntityTable";
import { PageHeader } from "../components/PageHeader";
import { dateOnly, money, yesNo } from "../utils/format";

function cleanPayload(values: Record<string, unknown>) {
  const payload = Object.fromEntries(
    Object.entries(values).map(([key, value]) => [key, value === "" ? null : value])
  );

  if (payload.expired_at) {
    payload.expired_at = dayjs(payload.expired_at as string).startOf("day").toISOString();
  }

  return payload;
}

export function ProxyPoolsPage() {
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<ProxyPool | null>(null);
  const [form] = Form.useForm();
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["proxy-pools"], queryFn: listProxyPools });
  const mutation = useMutation({
    mutationFn: (values: Record<string, unknown>) => {
      const payload = cleanPayload(values);
      return editing ? updateProxyPool(editing.id, payload) : createProxyPool(payload);
    },
    onSuccess: async () => {
      message.success(editing ? "IP地址池已更新" : "IP地址池已创建");
      setOpen(false);
      setEditing(null);
      form.resetFields();
      await queryClient.invalidateQueries({ queryKey: ["proxy-pools"] });
    },
    onError: (error) => message.error(error.message)
  });
  const deleteMutation = useMutation({
    mutationFn: deleteProxyPool,
    onSuccess: async () => {
      message.success("IP地址池已删除");
      await queryClient.invalidateQueries({ queryKey: ["proxy-pools"] });
    },
    onError: (error) => message.error(error.message)
  });

  return (
    <>
      <PageHeader title="IP地址池资产" subtitle="维护住宅、机房、移动、动态、静态IP地址的质量、适用场景和采购决策。" />
      <EntityTable<ProxyPool>
        title="IP地址池列表"
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
          { title: "IP地址类型", dataIndex: "proxy_type", fixed: "left" },
          { title: "地区", dataIndex: "region" },
          { title: "数量/流量", dataIndex: "quantity_or_traffic" },
          { title: "单价", dataIndex: "unit_price", render: money },
          { title: "总价", dataIndex: "total_price", render: money },
          { title: "到期时间", dataIndex: "expired_at", render: dateOnly },
          {
            title: "成功率",
            dataIndex: "success_rate",
            render: (value) => (value == null ? "-" : `${Number(value).toFixed(2)}%`)
          },
          {
            title: "延迟",
            dataIndex: "latency_ms",
            render: (value) => (value == null ? "-" : `${value} ms`)
          },
          { title: "适合登录", dataIndex: "suitable_for_login", render: yesNo },
          { title: "适合 API", dataIndex: "suitable_for_api", render: yesNo },
          { title: "继续采购", dataIndex: "continue_purchase", render: yesNo },
          { title: "真实成本", dataIndex: "include_real_cost", render: yesNo },
          { title: "状态", dataIndex: "status" },
          {
            title: "操作",
            fixed: "right",
            render: (_, record) => (
              <div className="table-actions">
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
        title={editing ? "编辑IP地址池" : "新增IP地址池"}
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
            <Form.Item name="proxy_type" label="IP地址类型" initialValue="residential" rules={[{ required: true }]}>
              <Select
                options={[
                  { value: "residential", label: "住宅" },
                  { value: "datacenter", label: "机房" },
                  { value: "mobile", label: "移动" },
                  { value: "dynamic", label: "动态" },
                  { value: "static", label: "静态" }
                ]}
              />
            </Form.Item>
            <Form.Item name="status" label="状态" initialValue="active">
              <Select
                options={[
                  { value: "active", label: "可用" },
                  { value: "testing", label: "测试中" },
                  { value: "unstable", label: "不稳定" },
                  { value: "expired", label: "到期" },
                  { value: "stopped", label: "停用" }
                ]}
              />
            </Form.Item>
            <Form.Item name="region" label="地区">
              <Input placeholder="US / HK / JP" />
            </Form.Item>
            <Form.Item name="quantity_or_traffic" label="数量/流量">
              <Input placeholder="100 IP / 50GB" />
            </Form.Item>
            <Form.Item name="unit_price" label="单价">
              <InputNumber min={0} style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item name="total_price" label="总价">
              <InputNumber min={0} style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item name="expired_at" label="到期时间">
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item name="success_rate" label="成功率">
              <InputNumber min={0} max={100} addonAfter="%" style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item name="latency_ms" label="延迟">
              <InputNumber min={0} addonAfter="ms" style={{ width: "100%" }} />
            </Form.Item>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "0 16px" }}>
            <Form.Item name="suitable_for_login" label="适合账号登录" initialValue={false} valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item name="suitable_for_api" label="适合 API 调用" initialValue={false} valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item name="continue_purchase" label="继续采购" initialValue valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item name="include_real_cost" label="计入真实成本" initialValue={false} valuePropName="checked">
              <Switch />
            </Form.Item>
          </div>
          <Form.Item name="remark" label="备注">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
