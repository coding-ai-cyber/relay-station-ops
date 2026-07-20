import { EditOutlined, PlusOutlined } from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, DatePicker, Form, Input, InputNumber, Modal, Select, Switch, message } from "antd";
import dayjs from "dayjs";
import { useState } from "react";

import { createCostItem, deleteCostItem, listCostItems, updateCostItem } from "../api/endpoints";
import type { CostItem } from "../api/types";
import { DeleteButton } from "../components/DeleteButton";
import { EntityTable } from "../components/EntityTable";
import { PageHeader } from "../components/PageHeader";
import { dateOnly, money, yesNo } from "../utils/format";
import { costSourceTypeLabel, costTypeLabel, costTypeOptions, currencyOptions } from "../utils/labels";

export function CostsPage() {
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<CostItem | null>(null);
  const [form] = Form.useForm();
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["cost-items"], queryFn: listCostItems });
  const mutation = useMutation({
    mutationFn: (values: Record<string, unknown>) => {
      const payload = {
        ...values,
        cost_date: dayjs(values.cost_date as string).format("YYYY-MM-DD")
      };
      return editing ? updateCostItem(editing.id, payload) : createCostItem(payload);
    },
    onSuccess: async () => {
      message.success(editing ? "成本已更新" : "成本已创建");
      setOpen(false);
      setEditing(null);
      form.resetFields();
      await queryClient.invalidateQueries({ queryKey: ["cost-items"] });
    },
    onError: (error) => message.error(error.message)
  });
  const deleteMutation = useMutation({
    mutationFn: deleteCostItem,
    onSuccess: async () => {
      message.success("成本已删除");
      await queryClient.invalidateQueries({ queryKey: ["cost-items"] });
    },
    onError: (error) => message.error(error.message)
  });

  return (
    <>
      <PageHeader title="成本管理" subtitle="统一归集采购成本、IP地址、邮箱和其他经营成本。" />
      <EntityTable<CostItem>
        title="成本记录"
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
          { title: "成本编号", dataIndex: "cost_no", fixed: "left" },
          { title: "类型", dataIndex: "cost_type", render: costTypeLabel },
          { title: "商品/用途", dataIndex: "product_name", render: (value?: string | null) => value || "-" },
          { title: "来源", dataIndex: "source_type", render: costSourceTypeLabel },
          { title: "金额", dataIndex: "amount", render: money },
          { title: "日期", dataIndex: "cost_date", render: dateOnly },
          { title: "所有成本", dataIndex: "include_all_cost", render: yesNo },
          { title: "真实成本", dataIndex: "include_real_cost", render: yesNo },
          {
            title: "操作",
            fixed: "right",
            render: (_, record) => (
              <div className="table-actions">
                <Button
                  size="small"
                  icon={<EditOutlined />}
                  disabled={record.source_type === "purchase"}
                  onClick={() => {
                    setEditing(record);
                    form.setFieldsValue({
                      ...record,
                      cost_date: dayjs(record.cost_date)
                    });
                    setOpen(true);
                  }}
                >
                  编辑
                </Button>
                <DeleteButton
                  disabled={record.source_type === "purchase"}
                  loading={deleteMutation.isPending}
                  onConfirm={() => deleteMutation.mutate(record.id)}
                />
              </div>
            )
          }
        ]}
      />
      <Modal
        title={editing ? "编辑成本" : "新增成本"}
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
          <Form.Item name="cost_no" label="成本编号" tooltip="新增时可留空，系统会自动生成成本编号。">
            <Input placeholder="留空自动生成" />
          </Form.Item>
          <Form.Item name="cost_type" label="成本类型" initialValue="other">
            <Select options={costTypeOptions} />
          </Form.Item>
          <Form.Item
            name="product_name"
            label="商品/用途"
            tooltip="用于补录早期只知道金额、但能大概说明购买内容的成本。"
          >
            <Input placeholder="例如：早期账号批次、服务器、IP地址额度" />
          </Form.Item>
          <Form.Item name="amount" label="金额" initialValue={0}>
            <InputNumber min={0} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="currency" label="币种" initialValue="USD">
            <Select options={currencyOptions} />
          </Form.Item>
          <Form.Item name="cost_date" label="成本日期" initialValue={dayjs()}>
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="include_all_cost" label="计入所有成本" initialValue valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="include_real_cost" label="计入真实成本" initialValue={false} valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
