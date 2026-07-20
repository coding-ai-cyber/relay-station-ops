import { CheckCircleOutlined, EditOutlined, PlusOutlined } from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, Form, Input, Modal, Select, Switch, Table, Tag, message } from "antd";
import { useState } from "react";

import {
  createSub2ApiInstance,
  deleteSub2ApiInstance,
  listSub2ApiInstances,
  probeSub2ApiInstance,
  updateSub2ApiInstance
} from "../api/endpoints";
import type { Sub2APIInstance } from "../api/types";
import { DeleteButton } from "../components/DeleteButton";
import { PageHeader } from "../components/PageHeader";
import { dateTime, yesNo } from "../utils/format";

export function Sub2APIInstancesPage() {
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Sub2APIInstance | null>(null);
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["sub2api-instances"],
    queryFn: listSub2ApiInstances
  });

  const mutation = useMutation({
    mutationFn: (values: Record<string, unknown>) =>
      editing ? updateSub2ApiInstance(editing.id, values) : createSub2ApiInstance(values),
    onSuccess: async () => {
      message.success(editing ? "中转站配置已更新" : "中转站配置已创建");
      setOpen(false);
      setEditing(null);
      form.resetFields();
      await queryClient.invalidateQueries({ queryKey: ["sub2api-instances"] });
    },
    onError: (error) => message.error(error.message)
  });

  const probeMutation = useMutation({
    mutationFn: probeSub2ApiInstance,
    onSuccess: async (result) => {
      if (result.ok) {
        message.success(`连接成功，发现 ${result.sample_count} 个远端账号`);
      } else {
        message.error(`${result.status}：${result.message}`);
      }
      await queryClient.invalidateQueries({ queryKey: ["sub2api-instances"] });
    },
    onError: (error) => message.error(error.message)
  });
  const deleteMutation = useMutation({
    mutationFn: deleteSub2ApiInstance,
    onSuccess: async () => {
      message.success("中转站配置已删除");
      await queryClient.invalidateQueries({ queryKey: ["sub2api-instances"] });
    },
    onError: (error) => message.error(error.message)
  });

  return (
    <>
      <PageHeader
        title="中转站配置"
        subtitle="统一维护多个 Sub2API 中转站。账号资产只选择所属中转站，不在账号页维护访问地址和管理员 Key。"
      />

      <div className="content-section">
        <div className="toolbar">
          <div>
            <strong className="section-title">Sub2API 中转站列表</strong>
            <div className="section-subtitle">每个中转站可单独命名、保存访问地址和管理员 Key</div>
          </div>
          <Button
            icon={<PlusOutlined />}
            type="primary"
            onClick={() => {
              setEditing(null);
              form.resetFields();
              setOpen(true);
            }}
          >
            新增中转站
          </Button>
        </div>

        <Table<Sub2APIInstance>
          rowKey="id"
          size="middle"
          loading={query.isLoading}
          dataSource={query.data ?? []}
          pagination={{ pageSize: 10, showSizeChanger: false }}
          scroll={{ x: "max-content" }}
          columns={[
            { title: "名称", dataIndex: "name", fixed: "left" },
            { title: "访问地址", dataIndex: "base_url" },
            {
              title: "启用",
              dataIndex: "is_active",
              render: (value: boolean) => <Tag color={value ? "green" : "default"}>{yesNo(value)}</Tag>
            },
            { title: "管理员Key", dataIndex: "has_admin_key", render: yesNo },
            {
              title: "连接状态",
              dataIndex: "last_probe_status",
              render: (value?: string) =>
                value ? <Tag color={value === "ok" ? "green" : "red"}>{value}</Tag> : "-"
            },
            { title: "最近测试", dataIndex: "last_probe_at", render: dateTime },
            { title: "测试信息", dataIndex: "last_probe_message", render: (value?: string) => value ?? "-" },
            {
              title: "操作",
              fixed: "right",
              render: (_, record) => (
                <div className="table-actions">
                  <Button
                    size="small"
                    icon={<CheckCircleOutlined />}
                    loading={probeMutation.isPending}
                    onClick={() => probeMutation.mutate(record.id)}
                  >
                    测试连接
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
                  <DeleteButton
                    loading={deleteMutation.isPending}
                    onConfirm={() => deleteMutation.mutate(record.id)}
                  />
                </div>
              )
            }
          ]}
        />
      </div>

      <Modal
        title={editing ? "编辑中转站" : "新增中转站"}
        open={open}
        onCancel={() => {
          setOpen(false);
          setEditing(null);
          form.resetFields();
        }}
        onOk={() => form.submit()}
        confirmLoading={mutation.isPending}
        width={640}
        destroyOnHidden
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{ is_active: true, adapter: "sub2api" }}
          onFinish={(values) => mutation.mutate(values)}
        >
          <Form.Item name="name" label="中转站名称" rules={[{ required: true }]}>
            <Input placeholder="例如：主站 / 香港中转 / 客户A中转" />
          </Form.Item>
          <Form.Item
            name="base_url"
            label="访问地址"
            rules={[{ required: true }]}
            tooltip="填写域名即可，例如 https://api.example.com，不需要填写具体接口路径。"
          >
            <Input placeholder="https://your-sub2api-domain.com" />
          </Form.Item>
          <Form.Item
            name="admin_key"
            label="管理员 Key"
            rules={editing ? [] : [{ required: true }]}
            tooltip="系统会使用 x-api-key 自动访问 Sub2API 管理接口。"
          >
            <Input.Password placeholder={editing ? "不填写则不修改" : "请输入管理员 Key"} />
          </Form.Item>
          <Form.Item name="is_active" label="启用" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="adapter" label="适配器" initialValue="sub2api">
            <Select options={[{ value: "sub2api", label: "Sub2API" }]} />
          </Form.Item>
          <Form.Item name="remark" label="备注">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
