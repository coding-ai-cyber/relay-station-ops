import { EditOutlined, EyeOutlined, PlusOutlined } from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, Form, Input, Modal, Select, Space, Switch, Tag, message } from "antd";
import { useMemo, useState } from "react";

import {
  createSupplier,
  deleteSupplier,
  listSuppliers,
  revealSupplierSecret,
  updateSupplier
} from "../api/endpoints";
import type { Supplier, SupplierSecret } from "../api/types";
import { DeleteButton } from "../components/DeleteButton";
import { EntityTable } from "../components/EntityTable";
import { PageHeader } from "../components/PageHeader";
import { yesNo } from "../utils/format";
import {
  preferredProductTagOptions,
  supplierStatusLabel,
  supplierStatusOptions,
  supplierTypeLabel,
  supplierTypeOptions
} from "../utils/labels";

export function SuppliersPage() {
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Supplier | null>(null);
  const [secret, setSecret] = useState<SupplierSecret | null>(null);
  const [keyword, setKeyword] = useState("");
  const [typeFilter, setTypeFilter] = useState<string | undefined>();
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [cooperationFilter, setCooperationFilter] = useState<string | undefined>();
  const [form] = Form.useForm();
  const selectedSupplierType = Form.useWatch("type", form) ?? editing?.type ?? "account";
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["suppliers"], queryFn: listSuppliers });
  const filteredSuppliers = useMemo(() => {
    const normalizedKeyword = keyword.trim().toLowerCase();
    return (query.data ?? []).filter((supplier) => {
      const matchesKeyword = normalizedKeyword
        ? [
            supplier.name,
            supplier.contact_name,
            supplier.login_url,
            supplier.country_region,
            supplier.remark,
            supplierTypeLabel(supplier.type),
            supplierStatusLabel(supplier.status)
          ]
            .filter(Boolean)
            .some((value) => String(value).toLowerCase().includes(normalizedKeyword))
        : true;
      const matchesType = typeFilter ? supplier.type === typeFilter : true;
      const matchesStatus = statusFilter ? supplier.status === statusFilter : true;
      const matchesCooperation =
        cooperationFilter === undefined
          ? true
          : supplier.continue_cooperation === (cooperationFilter === "true");
      return matchesKeyword && matchesType && matchesStatus && matchesCooperation;
    });
  }, [cooperationFilter, keyword, query.data, statusFilter, typeFilter]);
  const resetFilters = () => {
    setKeyword("");
    setTypeFilter(undefined);
    setStatusFilter(undefined);
    setCooperationFilter(undefined);
  };
  const mutation = useMutation({
    mutationFn: (values: Record<string, unknown>) =>
      editing ? updateSupplier(editing.id, values) : createSupplier(values),
    onSuccess: async () => {
      message.success(editing ? "供应商已更新" : "供应商已创建");
      setOpen(false);
      setEditing(null);
      form.resetFields();
      await queryClient.invalidateQueries({ queryKey: ["suppliers"] });
    },
    onError: (error) => message.error(error.message)
  });
  const revealMutation = useMutation({
    mutationFn: revealSupplierSecret,
    onSuccess: (payload) => setSecret(payload),
    onError: (error) => message.error(error.message)
  });
  const deleteMutation = useMutation({
    mutationFn: deleteSupplier,
    onSuccess: async () => {
      message.success("供应商已删除");
      await queryClient.invalidateQueries({ queryKey: ["suppliers"] });
    },
    onError: (error) => message.error(error.message)
  });

  return (
    <>
      <PageHeader title="供应商管理" subtitle="维护号商、服务器厂商、IP地址池厂商和其他成本供应商。" />
      <EntityTable<Supplier>
        title="供应商列表"
        data={filteredSuppliers}
        loading={query.isLoading}
        onRefresh={() => query.refetch()}
        extra={
          <Space wrap size={8}>
            <Input.Search
              allowClear
              placeholder="搜索名称、店铺地址、备注"
              style={{ width: 220 }}
              value={keyword}
              onChange={(event) => setKeyword(event.target.value)}
            />
            <Select
              allowClear
              placeholder="类型"
              style={{ width: 150 }}
              value={typeFilter}
              options={supplierTypeOptions}
              onChange={setTypeFilter}
            />
            <Select
              allowClear
              placeholder="状态"
              style={{ width: 120 }}
              value={statusFilter}
              options={supplierStatusOptions}
              onChange={setStatusFilter}
            />
            <Select
              allowClear
              placeholder="合作状态"
              style={{ width: 120 }}
              value={cooperationFilter}
              options={[
                { value: "true", label: "继续合作" },
                { value: "false", label: "停止合作" }
              ]}
              onChange={setCooperationFilter}
            />
            <Button onClick={resetFilters}>重置</Button>
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
          { title: "名称", dataIndex: "name", fixed: "left" },
          { title: "类型", dataIndex: "type", render: supplierTypeLabel },
          {
            title: "登录/店铺地址",
            dataIndex: "login_url",
            render: (value?: string | null) =>
              value ? (
                <a href={value} target="_blank" rel="noreferrer">
                  {value}
                </a>
              ) : (
                "-"
              )
          },
          {
            title: "优质商品",
            dataIndex: "preferred_product_tags",
            render: (value: string[] | undefined, record) =>
              record.type === "account" && value?.length ? (
                <Space size={[4, 4]} wrap>
                  {value.map((tag) => (
                    <Tag color="blue" key={tag}>{tag}</Tag>
                  ))}
                </Space>
              ) : (
                "-"
              )
          },
          { title: "状态", dataIndex: "status", render: supplierStatusLabel },
          { title: "继续合作", dataIndex: "continue_cooperation", render: yesNo },
          {
            title: "店铺监测",
            dataIndex: "monitor_shop",
            render: (value: boolean, record) => (record.type === "account" ? yesNo(value) : "-")
          },
          { title: "有密钥", dataIndex: "has_login_secret", render: yesNo },
          {
            title: "操作",
            fixed: "right",
            render: (_, record) => (
              <div className="table-actions">
                <Button
                  size="small"
                  disabled={!record.login_url}
                  onClick={() => record.login_url && window.open(record.login_url, "_blank", "noopener,noreferrer")}
                >
                  跳转
                </Button>
                <Button
                  size="small"
                  icon={<EyeOutlined />}
                  disabled={!record.has_login_account && !record.has_login_secret}
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
      <Modal
        title={editing ? "编辑供应商" : "新增供应商"}
        open={open}
        onCancel={() => {
          setOpen(false);
          setEditing(null);
          form.resetFields();
        }}
        onOk={() => form.submit()}
        confirmLoading={mutation.isPending}
        destroyOnHidden
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={(values) =>
            mutation.mutate({
              ...values,
              monitor_shop: values.type === "account" ? Boolean(values.monitor_shop) : false,
              preferred_product_tags: values.type === "account" ? values.preferred_product_tags ?? [] : []
            })
          }
        >
          <Form.Item name="name" label="供应商名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="type" label="类型" initialValue="account" rules={[{ required: true }]}>
            <Select options={supplierTypeOptions} />
          </Form.Item>
          <Form.Item name="status" label="状态" initialValue="normal">
            <Select options={supplierStatusOptions} />
          </Form.Item>
          <Form.Item name="continue_cooperation" label="继续合作" initialValue valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="login_url" label="登录/店铺地址">
            <Input placeholder="https://pay.ldxp.cn/shop/DD6LGP2Z 或 https://catfk.com/shop/666666" />
          </Form.Item>
          {selectedSupplierType === "account" ? (
            <>
              <Form.Item name="preferred_product_tags" label="优质商品标签" initialValue={[]}>
                <Select mode="multiple" allowClear options={preferredProductTagOptions} />
              </Form.Item>
              <Form.Item name="monitor_shop" label="店铺监测" initialValue={false} valuePropName="checked">
                <Switch />
              </Form.Item>
            </>
          ) : null}
          <Form.Item name="login_account" label="登录账号">
            <Input />
          </Form.Item>
          <Form.Item name="login_secret" label="登录密码/密钥">
            <Input.Password />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        title="供应商敏感字段"
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
