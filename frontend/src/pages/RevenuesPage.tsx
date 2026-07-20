import { EditOutlined, PlusOutlined, SyncOutlined } from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, DatePicker, Form, Input, InputNumber, Modal, Select, Space, Switch, message } from "antd";
import dayjs from "dayjs";
import { useState } from "react";

import {
  createRevenue,
  deleteRevenue,
  listRevenues,
  syncSub2ApiRevenues,
  updateRevenue
} from "../api/endpoints";
import type { Revenue } from "../api/types";
import { DeleteButton } from "../components/DeleteButton";
import { EntityTable } from "../components/EntityTable";
import { PageHeader } from "../components/PageHeader";
import { dateOnly, money, yesNo } from "../utils/format";
import { currencyOptions } from "../utils/labels";

export function RevenuesPage() {
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Revenue | null>(null);
  const [form] = Form.useForm();
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["revenues"], queryFn: listRevenues });
  const mutation = useMutation({
    mutationFn: (values: Record<string, unknown>) => {
      const payload = {
        ...values,
        revenue_date: dayjs(values.revenue_date as string).format("YYYY-MM-DD")
      };
      return editing ? updateRevenue(editing.id, payload) : createRevenue(payload);
    },
    onSuccess: async () => {
      message.success(editing ? "收入已更新" : "收入已创建");
      setOpen(false);
      setEditing(null);
      form.resetFields();
      await queryClient.invalidateQueries({ queryKey: ["revenues"] });
    },
    onError: (error) => message.error(error.message)
  });
  const deleteMutation = useMutation({
    mutationFn: deleteRevenue,
    onSuccess: async () => {
      message.success("收入已删除");
      await queryClient.invalidateQueries({ queryKey: ["revenues"] });
    },
    onError: (error) => message.error(error.message)
  });
  const syncMutation = useMutation({
    mutationFn: syncSub2ApiRevenues,
    onSuccess: async (results) => {
      const created = results.reduce((sum, item) => sum + item.created_count, 0);
      const updated = results.reduce((sum, item) => sum + item.updated_count, 0);
      const failed = results.reduce((sum, item) => sum + item.failed_count, 0);
      if (failed > 0) {
        message.warning(`同步完成：新增 ${created}，更新 ${updated}，失败实例 ${failed}`);
      } else {
        message.success(`同步完成：新增 ${created}，更新 ${updated}`);
      }
      await queryClient.invalidateQueries({ queryKey: ["revenues"] });
    },
    onError: (error) => message.error(error.message)
  });

  return (
    <>
      <PageHeader title="收入管理" subtitle="第一阶段手动录入收入，后续可对接 sub2api。" />
      <EntityTable<Revenue>
        title="收入记录"
        data={query.data}
        loading={query.isLoading}
        onRefresh={() => query.refetch()}
        extra={
          <Space wrap size={8}>
            <Button
              icon={<SyncOutlined />}
              loading={syncMutation.isPending}
              onClick={() => syncMutation.mutate()}
            >
              同步 Sub2API
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
          { title: "收入编号", dataIndex: "revenue_no", fixed: "left" },
          { title: "来源", dataIndex: "source" },
          { title: "客户", dataIndex: "customer" },
          { title: "金额", dataIndex: "amount", render: money },
          { title: "币种", dataIndex: "currency" },
          { title: "日期", dataIndex: "revenue_date", render: dateOnly },
          { title: "到账", dataIndex: "received", render: yesNo },
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
                      revenue_date: dayjs(record.revenue_date)
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
        title={editing ? "编辑收入" : "新增收入"}
        open={open}
        onCancel={() => {
          setOpen(false);
          setEditing(null);
          form.resetFields();
        }}
        onOk={() => form.submit()}
        confirmLoading={mutation.isPending}
      >
        <Form form={form} layout="vertical" onFinish={(values) => mutation.mutate(values)}>
          <Form.Item
            name="revenue_no"
            label="收入编号"
            tooltip={editing ? undefined : "新增时可留空，系统会自动生成收入编号。"}
          >
            <Input placeholder={editing ? "REV-20260716-ABC123" : "留空自动生成"} />
          </Form.Item>
          <Form.Item name="source" label="收入来源" initialValue="manual_payment">
            <Select
              options={[
                { value: "recharge", label: "用户充值" },
                { value: "subscription", label: "订阅" },
                { value: "manual_payment", label: "手动收款" },
                { value: "other", label: "其他" }
              ]}
            />
          </Form.Item>
          <Form.Item name="customer" label="用户/客户">
            <Input />
          </Form.Item>
          <Form.Item name="amount" label="金额" initialValue={0}>
            <InputNumber min={0} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="currency" label="币种" initialValue="USD">
            <Select options={currencyOptions} />
          </Form.Item>
          <Form.Item name="revenue_date" label="收入日期" initialValue={dayjs()}>
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="received" label="已到账" initialValue valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
