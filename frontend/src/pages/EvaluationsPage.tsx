import { CheckOutlined, EditOutlined, FormOutlined, PlusOutlined } from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, Checkbox, Form, Input, InputNumber, Modal, Select, message } from "antd";
import { useState } from "react";

import {
  createAccountEvaluation,
  createEvaluationBatch,
  deleteEvaluationBatch,
  finalizeEvaluationBatch,
  listAccounts,
  listEvaluationBatches,
  updateEvaluationBatch
} from "../api/endpoints";
import type { EvaluationBatch } from "../api/types";
import { DeleteButton } from "../components/DeleteButton";
import { EntityTable } from "../components/EntityTable";
import { PageHeader } from "../components/PageHeader";
import { money } from "../utils/format";

export function EvaluationsPage() {
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<EvaluationBatch | null>(null);
  const [evaluationBatch, setEvaluationBatch] = useState<EvaluationBatch | null>(null);
  const [form] = Form.useForm();
  const [evaluationForm] = Form.useForm();
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["evaluation-batches"], queryFn: listEvaluationBatches });
  const accountsQuery = useQuery({ queryKey: ["accounts"], queryFn: listAccounts });
  const createMutation = useMutation({
    mutationFn: (values: Record<string, unknown>) =>
      editing ? updateEvaluationBatch(editing.id, values) : createEvaluationBatch(values),
    onSuccess: async () => {
      message.success(editing ? "测评批次已更新" : "测评批次已创建");
      setOpen(false);
      setEditing(null);
      form.resetFields();
      await queryClient.invalidateQueries({ queryKey: ["evaluation-batches"] });
    },
    onError: (error) => message.error(error.message)
  });
  const finalizeMutation = useMutation({
    mutationFn: finalizeEvaluationBatch,
    onSuccess: async () => {
      message.success("批次已 finalize，并已回写采购和账号状态");
      await queryClient.invalidateQueries({ queryKey: ["evaluation-batches"] });
    },
    onError: (error) => message.error(error.message)
  });
  const evaluationMutation = useMutation({
    mutationFn: (values: Record<string, unknown>) =>
      createAccountEvaluation(evaluationBatch!.id, values),
    onSuccess: async () => {
      message.success("单账号测评已录入");
      setEvaluationBatch(null);
      evaluationForm.resetFields();
      await queryClient.invalidateQueries({ queryKey: ["evaluation-batches"] });
    },
    onError: (error) => message.error(error.message)
  });
  const deleteMutation = useMutation({
    mutationFn: deleteEvaluationBatch,
    onSuccess: async () => {
      message.success("测评批次已删除");
      await queryClient.invalidateQueries({ queryKey: ["evaluation-batches"] });
    },
    onError: (error) => message.error(error.message)
  });

  return (
    <>
      <PageHeader title="账号测评" subtitle="跟踪批次有效率、真实有效单价和采购结论。" />
      <EntityTable<EvaluationBatch>
        title="测评批次"
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
          { title: "批次编号", dataIndex: "batch_no", fixed: "left" },
          { title: "账号类型", dataIndex: "account_type" },
          { title: "采购数量", dataIndex: "purchase_quantity" },
          { title: "采购总价", dataIndex: "purchase_total_price", render: money },
          { title: "有效账号", dataIndex: "effective_account_count" },
          { title: "表面单价", dataIndex: "nominal_unit_price", render: money },
          { title: "真实有效单价", dataIndex: "real_effective_unit_price", render: money },
          { title: "评分", dataIndex: "overall_score" },
          { title: "结论", dataIndex: "conclusion" },
          {
            title: "操作",
            render: (_, record) => (
              <div className="table-actions">
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
                  icon={<FormOutlined />}
                  onClick={() => {
                    setEvaluationBatch(record);
                    evaluationForm.resetFields();
                  }}
                >
                  录入结果
                </Button>
                <Button
                  size="small"
                  icon={<CheckOutlined />}
                  onClick={() => finalizeMutation.mutate(record.id)}
                >
                  Finalize
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
        title={editing ? "编辑测评批次" : "新增测评批次"}
        open={open}
        onCancel={() => {
          setOpen(false);
          setEditing(null);
          form.resetFields();
        }}
        onOk={() => form.submit()}
        confirmLoading={createMutation.isPending}
      >
        <Form form={form} layout="vertical" onFinish={(values) => createMutation.mutate(values)}>
          <Form.Item name="batch_no" label="批次编号" rules={[{ required: true }]}>
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
          <Form.Item name="purchase_quantity" label="采购数量" initialValue={0}>
            <InputNumber min={0} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="purchase_total_price" label="采购总价" initialValue={0}>
            <InputNumber min={0} style={{ width: "100%" }} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        title="录入单账号测评"
        open={!!evaluationBatch}
        onCancel={() => setEvaluationBatch(null)}
        onOk={() => evaluationForm.submit()}
        confirmLoading={evaluationMutation.isPending}
        destroyOnHidden
      >
        <Form
          form={evaluationForm}
          layout="vertical"
          initialValues={{
            can_login: true,
            has_risk_control: false,
            target_model_available: true,
            need_fixed_proxy: false,
            is_banned: false,
            is_refunded: false,
            request_success_rate: 100,
            avg_response_quality: 80,
            manual_score: 80
          }}
          onFinish={(values) => evaluationMutation.mutate(values)}
        >
          <Form.Item name="account_id" label="账号" rules={[{ required: true }]}>
            <Select
              loading={accountsQuery.isLoading}
              showSearch
              optionFilterProp="label"
              options={(accountsQuery.data ?? []).map((account) => ({
                value: account.id,
                label: `${account.account_no} / ${account.account_type} / ${account.status}`
              }))}
            />
          </Form.Item>
          <Form.Item name="can_login" valuePropName="checked">
            <Checkbox>可登录</Checkbox>
          </Form.Item>
          <Form.Item name="has_risk_control" valuePropName="checked">
            <Checkbox>有风控</Checkbox>
          </Form.Item>
          <Form.Item name="target_model_available" valuePropName="checked">
            <Checkbox>目标模型可用</Checkbox>
          </Form.Item>
          <Form.Item name="need_fixed_proxy" valuePropName="checked">
            <Checkbox>需要固定IP地址</Checkbox>
          </Form.Item>
          <Form.Item name="request_success_rate" label="请求成功率">
            <InputNumber min={0} max={100} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="avg_response_quality" label="平均响应质量">
            <InputNumber min={0} max={100} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="available_days" label="可用天数">
            <InputNumber min={0} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="manual_score" label="人工评分">
            <InputNumber min={0} max={100} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="is_banned" valuePropName="checked">
            <Checkbox>已封禁</Checkbox>
          </Form.Item>
          <Form.Item name="is_refunded" valuePropName="checked">
            <Checkbox>已退款</Checkbox>
          </Form.Item>
          <Form.Item name="conclusion" label="测试结论">
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
