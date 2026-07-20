import {
  ClearOutlined,
  CloudSyncOutlined,
  ExportOutlined,
  ImportOutlined,
  PlusOutlined,
  SyncOutlined
} from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, Form, Input, Modal, Select, Space, Tag, Tooltip, message } from "antd";
import { useMemo, useState } from "react";

import {
  createShopMonitor,
  importSupplierShopMonitors,
  listShopMonitors,
  listSuppliers,
  syncAllShopMonitors,
  syncShopMonitor
} from "../api/endpoints";
import type { ShopMonitor, ShopProduct } from "../api/types";
import { EntityTable } from "../components/EntityTable";
import { PageHeader } from "../components/PageHeader";
import { dateTime, money } from "../utils/format";

type ProductRow = ShopProduct & {
  monitor_id: string;
  monitor_name: string;
  shop_url: string;
  platform: string;
  last_synced_at?: string | null;
};

const goodsTypeLabels: Record<string, string> = {
  card: "卡密",
  article: "文章",
  resource: "资源",
  equity: "权益"
};

const platformItemHosts: Record<string, string> = {
  link_shop: "https://pay.ldxp.cn",
  catfk: "https://catfk.com"
};

function shopItemUrl(platform: string, externalProductId: string) {
  const host = platformItemHosts[platform] ?? platformItemHosts.link_shop;
  return `${host}/item/${encodeURIComponent(externalProductId)}`;
}

function syncStatusTag(status: string) {
  if (status === "success") {
    return <Tag color="green">同步成功</Tag>;
  }
  if (status === "failed") {
    return <Tag color="red">同步失败</Tag>;
  }
  return <Tag>待同步</Tag>;
}

export function ShopMonitorsPage() {
  const [open, setOpen] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState<string>();
  const [monitorFilter, setMonitorFilter] = useState<string>();
  const [stockFilter, setStockFilter] = useState<string>();
  const [productKeyword, setProductKeyword] = useState("");
  const [form] = Form.useForm();
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["shop-monitors"], queryFn: listShopMonitors });
  const suppliersQuery = useQuery({ queryKey: ["suppliers"], queryFn: listSuppliers });
  const supplierOptions = (suppliersQuery.data ?? []).map((supplier) => ({
    value: supplier.id,
    label: supplier.name
  }));
  const productRows = useMemo<ProductRow[]>(
    () =>
      (query.data ?? []).flatMap((monitor) =>
        monitor.products.map((product) => ({
          ...product,
          monitor_id: monitor.id,
          monitor_name: monitor.name,
          shop_url: monitor.shop_url,
          platform: monitor.platform,
          last_synced_at: monitor.last_synced_at
        }))
      ),
    [query.data]
  );
  const categoryOptions = useMemo(() => {
    const options = new Map<string, string>();
    productRows.forEach((product) => {
      const key = product.standard_category_key || product.category_name || product.category_id || "__uncategorized__";
      const label = product.standard_category_name || product.category_name || product.category_id || "未分类";
      if (!options.has(key)) {
        options.set(key, label);
      }
    });
    return Array.from(options, ([value, label]) => ({ value, label }));
  }, [productRows]);
  const monitorOptions = useMemo(
    () => (query.data ?? []).map((monitor) => ({ value: monitor.id, label: monitor.name })),
    [query.data]
  );
  const filteredProductRows = useMemo(() => {
    const keyword = productKeyword.trim().toLowerCase();
    return productRows.filter((product) => {
      const productCategory =
        product.standard_category_key || product.category_name || product.category_id || "__uncategorized__";
      if (categoryFilter && productCategory !== categoryFilter) {
        return false;
      }
      if (monitorFilter && product.monitor_id !== monitorFilter) {
        return false;
      }
      if (stockFilter === "out_of_stock" && !product.is_out_of_stock) {
        return false;
      }
      if (stockFilter === "in_stock" && product.is_out_of_stock) {
        return false;
      }
      if (!keyword) {
        return true;
      }
      return [product.name, product.monitor_name, product.category_name, product.external_product_id]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(keyword));
    });
  }, [categoryFilter, monitorFilter, productKeyword, productRows, stockFilter]);
  const resetProductFilters = () => {
    setCategoryFilter(undefined);
    setMonitorFilter(undefined);
    setStockFilter(undefined);
    setProductKeyword("");
  };
  const monitorCount = query.data?.length ?? 0;
  const outOfStockCount = productRows.filter((item) => item.is_out_of_stock).length;

  const createMutation = useMutation({
    mutationFn: createShopMonitor,
    onSuccess: async () => {
      message.success("店铺监控已创建");
      setOpen(false);
      form.resetFields();
      await queryClient.invalidateQueries({ queryKey: ["shop-monitors"] });
    },
    onError: (error) => message.error(error.message)
  });
  const importMutation = useMutation({
    mutationFn: importSupplierShopMonitors,
    onSuccess: async (result) => {
      message.success(`导入完成：新增 ${result.created_count}，跳过 ${result.skipped_count}`);
      await queryClient.invalidateQueries({ queryKey: ["shop-monitors"] });
    },
    onError: (error) => message.error(error.message)
  });
  const syncOneMutation = useMutation({
    mutationFn: syncShopMonitor,
    onSuccess: async (result) => {
      if (result.status === "success") {
        message.success(`同步完成：商品 ${result.product_count}，缺货 ${result.out_of_stock_count}`);
      } else {
        message.error(result.message ?? "同步失败");
      }
      await queryClient.invalidateQueries({ queryKey: ["shop-monitors"] });
    },
    onError: (error) => message.error(error.message)
  });
  const syncAllMutation = useMutation({
    mutationFn: syncAllShopMonitors,
    onSuccess: async (results) => {
      const failed = results.filter((item) => item.status !== "success");
      if (failed.length > 0) {
        message.warning(`同步完成，${failed.length} 个店铺失败`);
      } else {
        message.success("全部店铺同步完成");
      }
      await queryClient.invalidateQueries({ queryKey: ["shop-monitors"] });
    },
    onError: (error) => message.error(error.message)
  });

  return (
    <>
      <PageHeader
        title="店铺监控"
        subtitle="监测链动小铺和云猫店铺的商品价格、库存和缺货状态；为避免访问过频，页面仅在手动点击时同步。"
      />
      <div className="content-section">
        <div className="toolbar">
          <div>
            <strong className="section-title">监控概览</strong>
            <div className="section-subtitle">
              店铺 {monitorCount} 个，商品 {productRows.length} 个，缺货 {outOfStockCount} 个
            </div>
          </div>
          <Space wrap size={8}>
            <Button
              icon={<ImportOutlined />}
              loading={importMutation.isPending}
              onClick={() => importMutation.mutate()}
            >
              从供应商导入
            </Button>
            <Button
              icon={<CloudSyncOutlined />}
              loading={syncAllMutation.isPending}
              onClick={() => syncAllMutation.mutate()}
            >
              同步全部
            </Button>
            <Button icon={<PlusOutlined />} type="primary" onClick={() => setOpen(true)}>
              新增店铺
            </Button>
          </Space>
        </div>
      </div>
      <EntityTable<ShopMonitor>
        title="监控店铺"
        data={query.data}
        loading={query.isLoading}
        onRefresh={() => query.refetch()}
        columns={[
          { title: "店铺", dataIndex: "name", fixed: "left" },
          {
            title: "链接",
            dataIndex: "shop_url",
            render: (value: string) => (
              <a href={value} target="_blank" rel="noreferrer">
                {value}
              </a>
            )
          },
          {
            title: "状态",
            dataIndex: "last_sync_status",
            render: (value: string, record) => (
              <Tooltip title={record.last_sync_message || undefined}>{syncStatusTag(value)}</Tooltip>
            )
          },
          { title: "商品数", dataIndex: "products", render: (value: ShopProduct[]) => value.length },
          {
            title: "缺货数",
            dataIndex: "products",
            render: (value: ShopProduct[]) => value.filter((item) => item.is_out_of_stock).length
          },
          { title: "最后同步", dataIndex: "last_synced_at", render: dateTime },
          {
            title: "操作",
            fixed: "right",
            render: (_, record) => (
              <Button
                size="small"
                icon={<SyncOutlined />}
                loading={syncOneMutation.isPending}
                onClick={() => syncOneMutation.mutate(record.id)}
              >
                同步
              </Button>
            )
          }
        ]}
      />
      <EntityTable<ProductRow>
        title="商品快照"
        data={filteredProductRows}
        loading={query.isLoading}
        onRefresh={() => query.refetch()}
        extra={
          <Space wrap size={8}>
            <Input.Search
              allowClear
              placeholder="搜索商品/店铺"
              style={{ width: 180 }}
              value={productKeyword}
              onChange={(event) => setProductKeyword(event.target.value)}
            />
            <Select
              allowClear
              placeholder="筛选分类"
              optionFilterProp="label"
              options={categoryOptions}
              showSearch
              style={{ width: 150 }}
              value={categoryFilter}
              onChange={setCategoryFilter}
            />
            <Select
              allowClear
              placeholder="筛选店铺"
              optionFilterProp="label"
              options={monitorOptions}
              showSearch
              style={{ width: 150 }}
              value={monitorFilter}
              onChange={setMonitorFilter}
            />
            <Select
              allowClear
              placeholder="库存状态"
              options={[
                { value: "in_stock", label: "有货" },
                { value: "out_of_stock", label: "缺货" }
              ]}
              style={{ width: 120 }}
              value={stockFilter}
              onChange={setStockFilter}
            />
            <Button icon={<ClearOutlined />} onClick={resetProductFilters}>
              重置
            </Button>
          </Space>
        }
        columns={[
          { title: "商品", dataIndex: "name", fixed: "left", width: 360 },
          { title: "店铺", dataIndex: "monitor_name" },
          {
            title: "分类",
            dataIndex: "category_name",
            render: (value?: string | null) => value || "-"
          },
          {
            title: "类型",
            dataIndex: "goods_type",
            render: (value: string) => goodsTypeLabels[value] ?? value
          },
          { title: "价格", dataIndex: "price", render: money },
          { title: "库存", dataIndex: "stock_count" },
          {
            title: "库存状态",
            dataIndex: "is_out_of_stock",
            render: (value: boolean) =>
              value ? <Tag color="red">缺货</Tag> : <Tag color="green">有货</Tag>
          },
          { title: "最后同步", dataIndex: "last_synced_at", render: dateTime },
          {
            title: "操作",
            fixed: "right",
            render: (_, record) => (
              <Button
                href={shopItemUrl(record.platform, record.external_product_id)}
                icon={<ExportOutlined />}
                rel="noreferrer"
                size="small"
                target="_blank"
              >
                跳转
              </Button>
            )
          }
        ]}
      />
      <Modal
        title="新增店铺监控"
        open={open}
        onCancel={() => {
          setOpen(false);
          form.resetFields();
        }}
        onOk={() => form.submit()}
        confirmLoading={createMutation.isPending}
        destroyOnHidden
      >
        <Form form={form} layout="vertical" onFinish={(values) => createMutation.mutate(values)}>
          <Form.Item name="shop_url" label="店铺 URL" rules={[{ required: true }]}>
            <Input placeholder="https://pay.ldxp.cn/shop/DD6LGP2Z 或 https://catfk.com/shop/666666" />
          </Form.Item>
          <Form.Item name="name" label="显示名称">
            <Input placeholder="留空时使用店铺 token，首次同步后会更新为店铺名称" />
          </Form.Item>
          <Form.Item name="supplier_id" label="关联供应商">
            <Select allowClear showSearch optionFilterProp="label" options={supplierOptions} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
