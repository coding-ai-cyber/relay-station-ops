import { EditOutlined, PlusOutlined } from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, Form, Input, Modal, Select, Switch, message } from "antd";
import { useState } from "react";

import { createUser, deleteUser, listUsers, updateUser } from "../api/endpoints";
import type { User } from "../api/types";
import { DeleteButton } from "../components/DeleteButton";
import { EntityTable } from "../components/EntityTable";
import { PageHeader } from "../components/PageHeader";
import { yesNo } from "../utils/format";

const roleOptions = [
  { value: "admin", label: "管理员" },
  { value: "finance", label: "财务" },
  { value: "purchaser", label: "采购" },
  { value: "tester", label: "测评" },
  { value: "viewer", label: "只读" }
];

export function UsersPage() {
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<User | null>(null);
  const [form] = Form.useForm();
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["users"], queryFn: listUsers });
  const mutation = useMutation({
    mutationFn: (values: Record<string, unknown>) => {
      const payload = { ...values };
      if (payload.password === "") {
        delete payload.password;
      }
      return editing ? updateUser(editing.id, payload) : createUser(payload);
    },
    onSuccess: async () => {
      message.success(editing ? "用户已更新" : "用户已创建");
      setOpen(false);
      setEditing(null);
      form.resetFields();
      await queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (error) => message.error(error.message)
  });
  const deleteMutation = useMutation({
    mutationFn: deleteUser,
    onSuccess: async () => {
      message.success("用户已删除");
      await queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (error) => message.error(error.message)
  });

  return (
    <>
      <PageHeader title="用户管理" subtitle="维护后台用户、角色和启用状态。" />
      <EntityTable<User>
        title="用户列表"
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
          { title: "用户名", dataIndex: "username", fixed: "left" },
          { title: "角色", dataIndex: "role" },
          { title: "启用", dataIndex: "is_active", render: yesNo },
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
                    form.setFieldsValue({ ...record, password: "" });
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
        title={editing ? "编辑用户" : "新增用户"}
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
          <Form.Item name="username" label="用户名" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item
            name="password"
            label={editing ? "新密码" : "密码"}
            rules={editing ? [] : [{ required: true, min: 6 }]}
          >
            <Input.Password placeholder={editing ? "留空则不修改" : undefined} />
          </Form.Item>
          <Form.Item name="role" label="角色" initialValue="viewer">
            <Select options={roleOptions} />
          </Form.Item>
          <Form.Item name="is_active" label="启用" initialValue valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
