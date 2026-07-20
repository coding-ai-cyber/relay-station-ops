import {
  BuildOutlined,
  CloudUploadOutlined,
  EditOutlined,
  FileSearchOutlined,
  PlusOutlined,
  ThunderboltOutlined,
  UploadOutlined
} from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  DatePicker,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Space,
  Switch,
  Tag,
  Upload,
  message
} from "antd";
import type { UploadProps } from "antd";
import dayjs, { Dayjs } from "dayjs";
import { useEffect, useMemo, useState } from "react";

import {
  bindPurchaseAccountJson,
  createPurchase,
  createPurchaseAssets,
  createSub2ApiImport,
  deletePurchase,
  downloadFile,
  listPurchases,
  listSub2ApiGroups,
  listSub2ApiInstances,
  listSub2ApiProxies,
  listSuppliers,
  runAutoSub2ApiAccountCheck,
  updatePurchase,
  uploadFile
} from "../api/endpoints";
import type { Purchase } from "../api/types";
import { DeleteButton } from "../components/DeleteButton";
import { EntityTable } from "../components/EntityTable";
import { PageHeader } from "../components/PageHeader";
import { dateOnly, money, yesNo } from "../utils/format";
import {
  costStatusLabel,
  costStatusOptions,
  currencyOptions,
  paymentMethodOptions,
  purchaseTypeLabel,
  purchaseTypeOptions,
  supplierStatusLabel,
  supplierTypeLabel
} from "../utils/labels";
import { calculatePurchaseTotal } from "../utils/purchaseMath";

const assetGeneratingPurchaseTypes = ["account", "server", "proxy"];
const accountTypeOptions = ["OpenAI", "Claude", "Gemini", "Grok", "Codex", "other"].map((value) => ({
  value,
  label: value
}));
const accountPlanOptions = ["free", "K12", "bugteam", "plus", "pro", "team", "other"].map((value) => ({
  value,
  label: value
}));

function isAssetGeneratingPurchaseType(purchaseType: string) {
  return assetGeneratingPurchaseTypes.includes(purchaseType);
}

function renderAssetStatus(record: Purchase) {
  if (!isAssetGeneratingPurchaseType(record.purchase_type)) {
    return <Tag>不适用</Tag>;
  }
  if (!record.asset_generated) {
    return <Tag color="warning">未生成资产</Tag>;
  }
  return <Tag color="success">已生成 {record.generated_asset_count}</Tag>;
}

function renderAccountBatchCounts(record: Purchase) {
  if (record.purchase_type !== "account") {
    return "-";
  }
  return (
    <Space size={[4, 4]} wrap>
      <Tag color="success">生成 {record.generated_asset_count}</Tag>
      <Tag color={record.bound_account_count ? "processing" : "default"}>
        绑定 {record.bound_account_count}
      </Tag>
      <Tag color={record.imported_account_count ? "blue" : "default"}>
        导入 {record.imported_account_count}
      </Tag>
      <Tag color={record.abnormal_account_count ? "error" : "default"}>
        异常 {record.abnormal_account_count}
      </Tag>
    </Space>
  );
}

type UploadValue = {
  originFileObj?: unknown;
  file?: unknown;
  fileList?: unknown;
};

function getFileFromUploadValue(value: unknown): File | undefined {
  if (value instanceof File) {
    return value;
  }
  if (!value || typeof value !== "object") {
    return undefined;
  }

  const uploadValue = value as UploadValue;
  if (uploadValue.originFileObj instanceof File) {
    return uploadValue.originFileObj;
  }
  if (uploadValue.file instanceof File) {
    return uploadValue.file;
  }
  if (uploadValue.file && typeof uploadValue.file === "object") {
    const nestedFile = getFileFromUploadValue(uploadValue.file);
    if (nestedFile) {
      return nestedFile;
    }
  }
  if (Array.isArray(uploadValue.fileList)) {
    return getFileFromUploadValue(uploadValue.fileList[0]);
  }

  return undefined;
}

export function PurchasesPage() {
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Purchase | null>(null);
  const [jsonBindPurchase, setJsonBindPurchase] = useState<Purchase | null>(null);
  const [sub2apiPurchase, setSub2apiPurchase] = useState<Purchase | null>(null);
  const [checkPurchase, setCheckPurchase] = useState<Purchase | null>(null);
  const [assetPurchase, setAssetPurchase] = useState<Purchase | null>(null);
  const [keyword, setKeyword] = useState("");
  const [purchaseTypeFilter, setPurchaseTypeFilter] = useState<string | undefined>();
  const [supplierFilter, setSupplierFilter] = useState<string | undefined>();
  const [costStatusFilter, setCostStatusFilter] = useState<string | undefined>();
  const [assetStatusFilter, setAssetStatusFilter] = useState<string | undefined>();
  const [purchaseDateRange, setPurchaseDateRange] = useState<[Dayjs, Dayjs] | null>(null);
  const [form] = Form.useForm();
  const [jsonBindForm] = Form.useForm();
  const [sub2apiForm] = Form.useForm();
  const [checkForm] = Form.useForm();
  const [assetForm] = Form.useForm();
  const selectedPurchaseType = Form.useWatch("purchase_type", form);
  const watchedQuantity = Form.useWatch("quantity", form);
  const watchedUnitPrice = Form.useWatch("unit_price", form);
  const selectedInstanceId = Form.useWatch("instance_id", sub2apiForm) as string | undefined;
  const queryClient = useQueryClient();

  const query = useQuery({ queryKey: ["purchases"], queryFn: listPurchases });
  const suppliersQuery = useQuery({ queryKey: ["suppliers"], queryFn: listSuppliers });
  const instancesQuery = useQuery({
    queryKey: ["sub2api-instances"],
    queryFn: listSub2ApiInstances
  });
  const groupsQuery = useQuery({
    queryKey: ["sub2api-groups", selectedInstanceId],
    queryFn: () => listSub2ApiGroups(selectedInstanceId!),
    enabled: !!selectedInstanceId && !!sub2apiPurchase
  });
  const proxiesQuery = useQuery({
    queryKey: ["sub2api-proxies", selectedInstanceId],
    queryFn: () => listSub2ApiProxies(selectedInstanceId!),
    enabled: !!selectedInstanceId && !!sub2apiPurchase
  });

  const suppliersById = new Map((suppliersQuery.data ?? []).map((supplier) => [supplier.id, supplier]));
  const supplierOptions = (suppliersQuery.data ?? [])
    .filter((supplier) => {
      if (!selectedPurchaseType) {
        return true;
      }
      if (selectedPurchaseType === "software") {
        return supplier.type === "other";
      }
      return supplier.type === selectedPurchaseType || supplier.type === "other";
    })
    .map((supplier) => ({
      value: supplier.id,
      label: `${supplier.name} / ${supplierTypeLabel(supplier.type)} / ${supplierStatusLabel(supplier.status)}`
    }));
  const purchaseFilterSupplierOptions = (suppliersQuery.data ?? []).map((supplier) => ({
    value: supplier.id,
    label: `${supplier.name} / ${supplierTypeLabel(supplier.type)}`
  }));
  const filteredPurchases = useMemo(() => {
    const normalizedKeyword = keyword.trim().toLowerCase();
    return (query.data ?? []).filter((purchase) => {
      const supplierName = purchase.supplier_id ? suppliersById.get(purchase.supplier_id)?.name ?? "" : "";
      const matchesKeyword = normalizedKeyword
        ? [
            purchase.purchase_no,
            purchase.product_name,
            purchase.product_type,
            purchase.remark,
            supplierName,
            purchaseTypeLabel(purchase.purchase_type),
            costStatusLabel(purchase.cost_status)
          ]
            .filter(Boolean)
            .some((value) => String(value).toLowerCase().includes(normalizedKeyword))
        : true;
      const matchesType = purchaseTypeFilter ? purchase.purchase_type === purchaseTypeFilter : true;
      const matchesSupplier = supplierFilter ? purchase.supplier_id === supplierFilter : true;
      const matchesStatus = costStatusFilter ? purchase.cost_status === costStatusFilter : true;
      const matchesAsset =
        assetStatusFilter === "generated"
          ? purchase.asset_generated
          : assetStatusFilter === "not_generated"
            ? isAssetGeneratingPurchaseType(purchase.purchase_type) && !purchase.asset_generated
            : true;
      const purchasedAt = dayjs(purchase.purchased_at);
      const matchesDate = purchaseDateRange
        ? !purchasedAt.isBefore(purchaseDateRange[0], "day") && !purchasedAt.isAfter(purchaseDateRange[1], "day")
        : true;
      return matchesKeyword && matchesType && matchesSupplier && matchesStatus && matchesAsset && matchesDate;
    });
  }, [
    assetStatusFilter,
    costStatusFilter,
    keyword,
    purchaseDateRange,
    purchaseTypeFilter,
    query.data,
    supplierFilter,
    suppliersById
  ]);
  const resetFilters = () => {
    setKeyword("");
    setPurchaseTypeFilter(undefined);
    setSupplierFilter(undefined);
    setCostStatusFilter(undefined);
    setAssetStatusFilter(undefined);
    setPurchaseDateRange(null);
  };

  useEffect(() => {
    if (!open) {
      return;
    }
    form.setFieldValue(
      "total_price",
      calculatePurchaseTotal(watchedQuantity, watchedUnitPrice)
    );
  }, [form, open, watchedQuantity, watchedUnitPrice]);

  useEffect(() => {
    if (!jsonBindPurchase) {
      return;
    }
    jsonBindForm.setFieldsValue({
      account_type: jsonBindPurchase.product_type || "OpenAI",
      plan_type: undefined,
      overwrite_existing: false,
      remark: undefined,
      file: undefined
    });
  }, [jsonBindForm, jsonBindPurchase]);

  const uploadMutation = useMutation({
    mutationFn: uploadFile,
    onError: (error) => message.error(error.message)
  });

  const downloadMutation = useMutation({
    mutationFn: downloadFile,
    onSuccess: (blob) => {
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank", "noopener,noreferrer");
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
    },
    onError: (error) => message.error(error.message)
  });

  const mutation = useMutation({
    mutationFn: (values: Record<string, unknown>) => {
      const payload = {
        ...values,
        total_price:
          values.total_price ??
          calculatePurchaseTotal(
            values.quantity as number | string | null | undefined,
            values.unit_price as number | string | null | undefined
          ),
        purchased_at: dayjs(values.purchased_at as dayjs.ConfigType).format("YYYY-MM-DD")
      };
      return editing ? updatePurchase(editing.id, payload) : createPurchase(payload);
    },
    onSuccess: async () => {
      message.success(editing ? "采购单已更新" : "采购单已创建");
      setOpen(false);
      setEditing(null);
      form.resetFields();
      await queryClient.invalidateQueries({ queryKey: ["purchases"] });
    },
    onError: (error) => message.error(error.message)
  });

  const assetMutation = useMutation({
    mutationFn: ({ id, values }: { id: string; values: Record<string, unknown> }) => {
      const payload = {
        ...values,
        expired_at: values.expired_at
          ? dayjs(values.expired_at as string).endOf("day").toISOString()
          : null
      };
      return createPurchaseAssets(id, payload);
    },
    onSuccess: async (result) => {
      if (result.skipped_reason) {
        message.warning(result.skipped_reason);
      } else {
        message.success(
          `已生成资产：账号 ${result.created_accounts}，服务器 ${result.created_servers}，IP地址池 ${result.created_proxy_pools}`
        );
      }
      setAssetPurchase(null);
      assetForm.resetFields();
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["purchases"] }),
        queryClient.invalidateQueries({ queryKey: ["accounts"] }),
        queryClient.invalidateQueries({ queryKey: ["servers"] }),
        queryClient.invalidateQueries({ queryKey: ["proxy-pools"] }),
        queryClient.invalidateQueries({ queryKey: ["dashboard", "expiring-assets"] })
      ]);
    },
    onError: (error) => message.error(error.message)
  });

  const bindJsonMutation = useMutation({
    mutationFn: async (values: Record<string, unknown>) => {
      const file = getFileFromUploadValue(values.file);
      if (!jsonBindPurchase || !file) {
        throw new Error("请选择要绑定的 JSON 文件");
      }
      let payload: Record<string, unknown> | Record<string, unknown>[];
      try {
        payload = JSON.parse(await file.text()) as Record<string, unknown> | Record<string, unknown>[];
      } catch {
        throw new Error("JSON 文件格式无效");
      }
      return bindPurchaseAccountJson(jsonBindPurchase.id, {
        file_id: null,
        payload,
        overwrite_existing: Boolean(values.overwrite_existing),
        account_type: values.account_type ? String(values.account_type) : undefined,
        plan_type: values.plan_type ? String(values.plan_type) : undefined,
        remark: values.remark ? String(values.remark) : undefined
      });
    },
    onSuccess: async (result) => {
      message.success(`已绑定 ${result.bound_count} 个账号，跳过 ${result.skipped_count} 个`);
      setJsonBindPurchase(null);
      jsonBindForm.resetFields();
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["purchases"] }),
        queryClient.invalidateQueries({ queryKey: ["accounts"] })
      ]);
    },
    onError: (error) => message.error(error.message)
  });

  const purchaseImportMutation = useMutation({
    mutationFn: (values: Record<string, unknown>) => {
      if (!sub2apiPurchase) {
        throw new Error("请选择采购批次");
      }
      return createSub2ApiImport({
        instance_id: String(values.instance_id),
        purchase_id: sub2apiPurchase.id,
        select_all: false,
        account_ids: [],
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
      setSub2apiPurchase(null);
      sub2apiForm.resetFields();
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["purchases"] }),
        queryClient.invalidateQueries({ queryKey: ["accounts"] }),
        queryClient.invalidateQueries({ queryKey: ["sub2api-imports"] })
      ]);
    },
    onError: (error) => message.error(error.message)
  });

  const purchaseCheckMutation = useMutation({
    mutationFn: (values: Record<string, unknown>) => {
      if (!checkPurchase) {
        throw new Error("请选择采购批次");
      }
      return runAutoSub2ApiAccountCheck({
        instance_id: String(values.instance_id),
        purchase_id: checkPurchase.id,
        include_only_operation: Boolean(values.include_only_operation),
        timeout_seconds: Number(values.timeout_seconds ?? 15),
        remark: values.remark ? String(values.remark) : undefined
      });
    },
    onSuccess: async (batch) => {
      message.success(`检测完成：可用 ${batch.alive_count}，异常 ${batch.abnormal_count}`);
      setCheckPurchase(null);
      checkForm.resetFields();
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["purchases"] }),
        queryClient.invalidateQueries({ queryKey: ["accounts"] }),
        queryClient.invalidateQueries({ queryKey: ["account-check-batches"] })
      ]);
    },
    onError: (error) => message.error(error.message)
  });

  const deleteMutation = useMutation({
    mutationFn: deletePurchase,
    onSuccess: async () => {
      message.success("采购单已删除");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["purchases"] }),
        queryClient.invalidateQueries({ queryKey: ["cost-items"] })
      ]);
    },
    onError: (error) => message.error(error.message)
  });

  const handleVoucherUpload: UploadProps["customRequest"] = async (options) => {
    try {
      const uploaded = await uploadMutation.mutateAsync(options.file as File);
      form.setFieldValue("voucher_file_id", uploaded.id);
      message.success("凭证已上传");
      options.onSuccess?.(uploaded);
    } catch (error) {
      options.onError?.(error as Error);
    }
  };

  const openEditor = (record?: Purchase) => {
    setEditing(record ?? null);
    form.resetFields();
    if (record) {
      form.setFieldsValue({
        ...record,
        purchased_at: dayjs(record.purchased_at)
      });
    }
    setOpen(true);
  };

  return (
    <>
      <PageHeader title="采购记录" subtitle="从采购批次生成账号资产，绑定 JSON 后导入和检测 Sub2API 状态。" />
      <EntityTable<Purchase>
        title="采购单"
        data={filteredPurchases}
        loading={query.isLoading}
        onRefresh={() => query.refetch()}
        extra={
          <Space wrap size={8}>
            <Input.Search
              allowClear
              placeholder="搜索编号、产品、供应商"
              style={{ width: 220 }}
              value={keyword}
              onChange={(event) => setKeyword(event.target.value)}
            />
            <Select
              allowClear
              placeholder="采购类型"
              style={{ width: 140 }}
              value={purchaseTypeFilter}
              options={purchaseTypeOptions}
              onChange={setPurchaseTypeFilter}
            />
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              placeholder="供应商"
              style={{ width: 180 }}
              value={supplierFilter}
              options={purchaseFilterSupplierOptions}
              onChange={setSupplierFilter}
            />
            <Select
              allowClear
              placeholder="成本状态"
              style={{ width: 130 }}
              value={costStatusFilter}
              options={costStatusOptions}
              onChange={setCostStatusFilter}
            />
            <Select
              allowClear
              placeholder="资产状态"
              style={{ width: 130 }}
              value={assetStatusFilter}
              options={[
                { value: "generated", label: "已生成资产" },
                { value: "not_generated", label: "未生成资产" }
              ]}
              onChange={setAssetStatusFilter}
            />
            <DatePicker.RangePicker
              value={purchaseDateRange}
              onChange={(value) =>
                setPurchaseDateRange(value?.[0] && value?.[1] ? [value[0], value[1]] : null)
              }
            />
            <Button onClick={resetFilters}>重置</Button>
            <Button icon={<PlusOutlined />} type="primary" onClick={() => openEditor()}>
              新增
            </Button>
          </Space>
        }
        columns={[
          { title: "采购编号", dataIndex: "purchase_no", fixed: "left" },
          { title: "类型", dataIndex: "purchase_type", render: purchaseTypeLabel },
          {
            title: "供应商",
            dataIndex: "supplier_id",
            render: (value?: string | null) => (value ? suppliersById.get(value)?.name ?? value : "-")
          },
          { title: "产品", dataIndex: "product_name" },
          { title: "总价", dataIndex: "total_price", render: money },
          { title: "币种", dataIndex: "currency" },
          {
            title: "支付方式",
            dataIndex: "payment_method",
            render: (value?: string | null) =>
              value ? paymentMethodOptions.find((item) => item.value === value)?.label ?? value : "-"
          },
          { title: "采购日期", dataIndex: "purchased_at", render: dateOnly },
          {
            title: "凭证",
            dataIndex: "voucher_file_id",
            render: (value: string | null | undefined) =>
              value ? (
                <Button
                  size="small"
                  icon={<FileSearchOutlined />}
                  loading={downloadMutation.isPending}
                  onClick={() => downloadMutation.mutate(value)}
                >
                  查看
                </Button>
              ) : (
                "无"
              )
          },
          { title: "所有成本", dataIndex: "include_all_cost", render: yesNo },
          { title: "真实成本", dataIndex: "include_real_cost", render: yesNo },
          { title: "状态", dataIndex: "cost_status", render: costStatusLabel },
          { title: "资产状态", render: (_, record) => renderAssetStatus(record) },
          { title: "账号批次", render: (_, record) => renderAccountBatchCounts(record) },
          {
            title: "操作",
            fixed: "right",
            render: (_, record) => (
              <Space size={[6, 6]} wrap>
                <Button
                  size="small"
                  icon={<BuildOutlined />}
                  loading={assetMutation.isPending}
                  disabled={!isAssetGeneratingPurchaseType(record.purchase_type) || record.asset_generated}
                  onClick={() => {
                    setAssetPurchase(record);
                    assetForm.resetFields();
                  }}
                >
                  生成资产
                </Button>
                {record.purchase_type === "account" ? (
                  <>
                    <Button size="small" icon={<UploadOutlined />} onClick={() => setJsonBindPurchase(record)}>
                      绑定 JSON
                    </Button>
                    <Button size="small" icon={<CloudUploadOutlined />} onClick={() => setSub2apiPurchase(record)}>
                      导入 Sub2API
                    </Button>
                    <Button size="small" icon={<ThunderboltOutlined />} onClick={() => setCheckPurchase(record)}>
                      检测
                    </Button>
                  </>
                ) : null}
                <Button size="small" icon={<EditOutlined />} onClick={() => openEditor(record)}>
                  编辑
                </Button>
                <DeleteButton
                  loading={deleteMutation.isPending}
                  onConfirm={() => deleteMutation.mutate(record.id)}
                />
              </Space>
            )
          }
        ]}
      />

      <Modal
        title={`生成资产：${assetPurchase?.purchase_no ?? ""}`}
        open={!!assetPurchase}
        onCancel={() => {
          setAssetPurchase(null);
          assetForm.resetFields();
        }}
        onOk={() => assetForm.submit()}
        confirmLoading={assetMutation.isPending}
        destroyOnHidden
      >
        <Form
          form={assetForm}
          layout="vertical"
          onFinish={(values) => {
            if (!assetPurchase) {
              return;
            }
            assetMutation.mutate({ id: assetPurchase.id, values });
          }}
        >
          <Form.Item
            name="expired_at"
            label="资产到期时间"
            tooltip="留空则生成无固定到期时间的资产，不参与到期提醒。"
          >
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        title={editing ? "编辑采购单" : "新增采购单"}
        open={open}
        onCancel={() => {
          setOpen(false);
          setEditing(null);
          form.resetFields();
        }}
        onOk={() => form.submit()}
        confirmLoading={mutation.isPending}
        width={720}
      >
        <Form form={form} layout="vertical" onFinish={(values) => mutation.mutate(values)}>
          <Form.Item
            name="purchase_no"
            label="采购编号"
            tooltip={editing ? "编辑时可手动调整采购编号。" : "新增时可留空，系统会自动生成采购编号。"}
          >
            <Input placeholder={editing ? "PO-20260710-001" : "留空自动生成"} />
          </Form.Item>
          <Form.Item name="purchase_type" label="采购类型" initialValue="account">
            <Select
              onChange={() => form.setFieldValue("supplier_id", undefined)}
              options={purchaseTypeOptions}
            />
          </Form.Item>
          <Form.Item name="supplier_id" label="供应商">
            <Select
              allowClear
              showSearch
              loading={suppliersQuery.isLoading}
              optionFilterProp="label"
              placeholder="选择供应商"
              options={supplierOptions}
            />
          </Form.Item>
          <Form.Item name="product_name" label="产品名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="quantity" label="数量" initialValue={1}>
            <InputNumber min={0} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="unit_price" label="单价" initialValue={0}>
            <InputNumber min={0} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="total_price" label="总价" initialValue={0}>
            <InputNumber min={0} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="currency" label="币种" initialValue="USDT">
            <Select options={currencyOptions} />
          </Form.Item>
          <Form.Item name="payment_method" label="支付方式">
            <Select allowClear showSearch placeholder="选择支付方式" options={paymentMethodOptions} />
          </Form.Item>
          <Form.Item name="order_url" label="订单链接">
            <Input />
          </Form.Item>
          <Form.Item name="purchased_at" label="采购日期" initialValue={dayjs()} rules={[{ required: true }]}>
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="voucher_file_id" hidden>
            <Input />
          </Form.Item>
          <Form.Item label="凭证截图/PDF">
            <Space size={8} wrap>
              <Upload
                accept="image/*,.pdf"
                customRequest={handleVoucherUpload}
                maxCount={1}
                showUploadList={false}
              >
                <Button icon={<UploadOutlined />} loading={uploadMutation.isPending}>
                  上传凭证
                </Button>
              </Upload>
              <Form.Item noStyle shouldUpdate={(prev, curr) => prev.voucher_file_id !== curr.voucher_file_id}>
                {({ getFieldValue }) => {
                  const fileId = getFieldValue("voucher_file_id") as string | undefined;
                  return fileId ? (
                    <>
                      <span style={{ color: "#617086" }}>已绑定凭证</span>
                      <Button
                        size="small"
                        icon={<FileSearchOutlined />}
                        loading={downloadMutation.isPending}
                        onClick={() => downloadMutation.mutate(fileId)}
                      >
                        查看
                      </Button>
                    </>
                  ) : (
                    <span style={{ color: "#8a96a8" }}>支持图片或 PDF，单文件不超过 20MB</span>
                  );
                }}
              </Form.Item>
            </Space>
          </Form.Item>
          <Form.Item name="include_real_cost" label="计入真实成本" initialValue={false} valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="include_all_cost" label="计入所有成本" initialValue valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="cost_status" label="成本状态" initialValue="testing">
            <Select options={costStatusOptions} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`绑定账号 JSON：${jsonBindPurchase?.purchase_no ?? ""}`}
        open={!!jsonBindPurchase}
        onCancel={() => {
          setJsonBindPurchase(null);
          jsonBindForm.resetFields();
        }}
        onOk={() => jsonBindForm.submit()}
        okText="开始绑定"
        confirmLoading={bindJsonMutation.isPending}
        destroyOnHidden
      >
        <Form form={jsonBindForm} layout="vertical" onFinish={(values) => bindJsonMutation.mutate(values)}>
          <Form.Item
            name="file"
            label="JSON 文件"
            getValueFromEvent={getFileFromUploadValue}
            rules={[{ required: true, message: "请选择 JSON 文件" }]}
          >
            <Upload
              accept="application/json,.json"
              maxCount={1}
              beforeUpload={(file) => {
                jsonBindForm.setFieldValue("file", file);
                return false;
              }}
              onRemove={() => jsonBindForm.setFieldValue("file", undefined)}
            >
              <Button icon={<UploadOutlined />}>选择 JSON</Button>
            </Upload>
          </Form.Item>
          <Form.Item name="account_type" label="账号类型" rules={[{ required: true, message: "请选择账号类型" }]}>
            <Select options={accountTypeOptions} />
          </Form.Item>
          <Form.Item name="plan_type" label="套餐类型">
            <Select allowClear options={accountPlanOptions} placeholder="不选择则按 JSON 或留空" />
          </Form.Item>
          <Form.Item name="overwrite_existing" label="覆盖已有凭证" valuePropName="checked" initialValue={false}>
            <Switch />
          </Form.Item>
          <Form.Item name="remark" label="备注">
            <Input.TextArea rows={2} maxLength={500} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`导入 Sub2API：${sub2apiPurchase?.purchase_no ?? ""}`}
        open={!!sub2apiPurchase}
        onCancel={() => {
          setSub2apiPurchase(null);
          sub2apiForm.resetFields();
        }}
        onOk={() => sub2apiForm.submit()}
        okText="开始导入"
        confirmLoading={purchaseImportMutation.isPending}
        destroyOnHidden
      >
        <Form
          form={sub2apiForm}
          layout="vertical"
          initialValues={{ duplicate_policy: "skip" }}
          onFinish={(values) => purchaseImportMutation.mutate(values)}
        >
          <Form.Item name="instance_id" label="Sub2API 实例" rules={[{ required: true, message: "请选择 Sub2API 实例" }]}>
            <Select
              loading={instancesQuery.isLoading}
              placeholder="请选择实例"
              onChange={() => {
                sub2apiForm.setFieldValue("group_ids", []);
                sub2apiForm.setFieldValue("proxy_id", undefined);
              }}
              options={(instancesQuery.data ?? []).map((instance) => ({
                value: instance.id,
                label: `${instance.name} / ${instance.base_url}`,
                disabled: !instance.is_active
              }))}
            />
          </Form.Item>
          <Form.Item name="group_ids" label="目标分组" rules={[{ required: true, message: "请选择至少一个目标分组" }]}>
            <Select
              mode="multiple"
              allowClear
              loading={groupsQuery.isLoading}
              disabled={!selectedInstanceId}
              placeholder={selectedInstanceId ? "选择一个或多个分组" : "请先选择实例"}
              options={(groupsQuery.data ?? []).map((group) => ({
                value: group.id,
                label: `${group.name} / ${group.platform || "未标注平台"}`,
                disabled: !!group.status && !["active", "enabled"].includes(group.status.toLowerCase())
              }))}
            />
          </Form.Item>
          <Form.Item name="proxy_id" label="代理地址">
            <Select
              allowClear
              loading={proxiesQuery.isLoading}
              disabled={!selectedInstanceId}
              placeholder={selectedInstanceId ? "不选择则不指定代理" : "请先选择实例"}
              options={(proxiesQuery.data ?? []).map((proxy) => ({
                value: proxy.id,
                label: `${proxy.name} / ${proxy.protocol || "-"}://${proxy.host || "-"}:${proxy.port ?? "-"}${proxy.latency_ms ? ` / ${proxy.latency_ms}ms` : ""}`,
                disabled: !!proxy.status && !["active", "enabled"].includes(proxy.status.toLowerCase())
              }))}
            />
          </Form.Item>
          <Form.Item name="duplicate_policy" label="远端重复账号" rules={[{ required: true }]}>
            <Select
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
        title={`检测 Sub2API 账号：${checkPurchase?.purchase_no ?? ""}`}
        open={!!checkPurchase}
        onCancel={() => {
          setCheckPurchase(null);
          checkForm.resetFields();
        }}
        onOk={() => checkForm.submit()}
        okText="开始检测"
        confirmLoading={purchaseCheckMutation.isPending}
        destroyOnHidden
      >
        <Form
          form={checkForm}
          layout="vertical"
          initialValues={{ include_only_operation: false, timeout_seconds: 15 }}
          onFinish={(values) => purchaseCheckMutation.mutate(values)}
        >
          <Form.Item name="instance_id" label="Sub2API 实例" rules={[{ required: true, message: "请选择 Sub2API 实例" }]}>
            <Select
              loading={instancesQuery.isLoading}
              placeholder="请选择实例"
              options={(instancesQuery.data ?? []).map((instance) => ({
                value: instance.id,
                label: `${instance.name} / ${instance.base_url}`,
                disabled: !instance.is_active
              }))}
            />
          </Form.Item>
          <Form.Item name="include_only_operation" label="只检测参与运营账号" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="timeout_seconds" label="超时秒数">
            <InputNumber min={1} max={120} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="remark" label="备注">
            <Input.TextArea rows={2} maxLength={500} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
