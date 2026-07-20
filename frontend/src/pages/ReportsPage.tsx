import { DownloadOutlined, RobotOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { Button, DatePicker, InputNumber, Table, Tag, Tooltip } from "antd";
import type { ColumnsType } from "antd/es/table";
import dayjs, { Dayjs } from "dayjs";
import * as echarts from "echarts";
import { useEffect, useRef, useState } from "react";

import {
  getAIPricingRecommendations,
  getAccountTypeProfitReport,
  getMonthlyProfitReport,
  getPurchaseBatchProfitReport,
  getSupplierMultiplierReport
} from "../api/endpoints";
import type {
  AccountTypeProfitRow,
  AIPricingRecommendationRow,
  MonthlyProfitRow,
  PurchaseBatchProfitRow,
  SupplierMultiplierRow
} from "../api/types";
import { PageHeader } from "../components/PageHeader";
import { exportCsv } from "../utils/csv";
import { money } from "../utils/format";

const { RangePicker } = DatePicker;

function chartAmount(value: number | string | null | undefined) {
  return Number(value ?? 0).toFixed(2);
}

function chartMoney(value: number | string | null | undefined) {
  return `¥${chartAmount(value)}`;
}

function riskTag(value: string) {
  const color = value === "stable" ? "green" : value === "observing" ? "gold" : "red";
  const label = value === "stable" ? "稳定" : value === "observing" ? "观察中" : "高风险";
  return <Tag color={color}>{label}</Tag>;
}

function useMonthlyChart(rows: MonthlyProfitRow[] | undefined) {
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!ref.current) {
      return;
    }

    const chart = echarts.init(ref.current);
    const data = rows ?? [];
    const rounded = (field: keyof Omit<MonthlyProfitRow, "month">) =>
      data.map((item) => Number(Number(item[field] ?? 0).toFixed(2)));

    chart.setOption({
      tooltip: {
        trigger: "axis",
        valueFormatter: (value: number | string) => chartMoney(value)
      },
      legend: {
        top: 0,
        data: ["收入", "所有成本", "真实成本", "利润", "真实利润", "测试损耗"]
      },
      grid: { top: 48, left: 48, right: 24, bottom: 36 },
      xAxis: {
        type: "category",
        data: data.map((item) => item.month)
      },
      yAxis: {
        type: "value",
        axisLabel: {
          formatter: (value: number) => chartMoney(value)
        }
      },
      series: [
        { name: "收入", type: "line", smooth: true, data: rounded("revenue") },
        { name: "所有成本", type: "line", smooth: true, data: rounded("all_cost") },
        { name: "真实成本", type: "line", smooth: true, data: rounded("real_cost") },
        { name: "利润", type: "bar", data: rounded("profit") },
        { name: "真实利润", type: "bar", data: rounded("real_profit") },
        { name: "测试损耗", type: "line", smooth: true, data: rounded("test_loss") }
      ]
    });

    const resize = () => chart.resize();
    window.addEventListener("resize", resize);

    return () => {
      window.removeEventListener("resize", resize);
      chart.dispose();
    };
  }, [rows]);

  return ref;
}

export function ReportsPage() {
  const now = dayjs();
  const [range, setRange] = useState<[Dayjs, Dayjs]>([
    now.startOf("year"),
    now
  ]);
  const [targetMargin, setTargetMargin] = useState(35);

  const query = useQuery({
    queryKey: [
      "monthly-profit",
      range[0].year(),
      range[0].month() + 1,
      range[1].year(),
      range[1].month() + 1
    ],
    queryFn: () =>
      getMonthlyProfitReport({
        start_year: range[0].year(),
        start_month: range[0].month() + 1,
        end_year: range[1].year(),
        end_month: range[1].month() + 1
      })
  });

  const chartRef = useMonthlyChart(query.data);
  const multiplierQuery = useQuery({
    queryKey: ["supplier-multiplier", targetMargin],
    queryFn: () => getSupplierMultiplierReport(targetMargin)
  });
  const aiRecommendationQuery = useQuery({
    queryKey: ["ai-pricing-recommendations", targetMargin],
    queryFn: () => getAIPricingRecommendations(targetMargin)
  });
  const accountTypeQuery = useQuery({
    queryKey: ["account-type-profit"],
    queryFn: getAccountTypeProfitReport
  });
  const purchaseBatchQuery = useQuery({
    queryKey: ["purchase-batch-profit"],
    queryFn: getPurchaseBatchProfitReport
  });

  const columns: ColumnsType<MonthlyProfitRow> = [
    { title: "月份", dataIndex: "month", fixed: "left" },
    { title: "收入", dataIndex: "revenue", render: money },
    { title: "所有成本", dataIndex: "all_cost", render: money },
    { title: "真实成本", dataIndex: "real_cost", render: money },
    {
      title: "利润",
      dataIndex: "profit",
      render: (value: number) => (
        <span style={{ color: value >= 0 ? "#1f7a4d" : "#b42318" }}>{money(value)}</span>
      )
    },
    {
      title: "真实利润",
      dataIndex: "real_profit",
      render: (value: number) => (
        <span style={{ color: value >= 0 ? "#1f7a4d" : "#b42318" }}>{money(value)}</span>
      )
    },
    { title: "测试损耗", dataIndex: "test_loss", render: money }
  ];
  const aiRecommendationColumns: ColumnsType<AIPricingRecommendationRow> = [
    { title: "账号类型", dataIndex: "account_type", fixed: "left" },
    {
      title: "风险",
      dataIndex: "risk_level",
      render: riskTag
    },
    { title: "有效账号", dataIndex: "effective_account_count" },
    {
      title: "有效率",
      dataIndex: "effective_rate",
      render: (value: number) => `${value.toFixed(2)}%`
    },
    { title: "真实有效成本", dataIndex: "real_effective_unit_cost", render: money },
    {
      title: "建议倍率",
      dataIndex: "recommended_multiplier",
      render: (value: number) => <strong>{value.toFixed(2)}x</strong>
    },
    { title: "建议售价", dataIndex: "suggested_sale_price", render: money },
    { title: "预测收入", dataIndex: "projected_revenue", render: money },
    {
      title: "预测利润",
      dataIndex: "projected_profit",
      render: (value: number) => (
        <span style={{ color: value >= 0 ? "#1f7a4d" : "#b42318" }}>{money(value)}</span>
      )
    },
    {
      title: "预测利润率",
      dataIndex: "projected_margin",
      render: (value: number) => `${value.toFixed(2)}%`
    },
    { title: "研判依据", dataIndex: "reason" }
  ];
  const multiplierColumns: ColumnsType<SupplierMultiplierRow> = [
    { title: "供应商", dataIndex: "supplier_name", fixed: "left" },
    { title: "批次数", dataIndex: "batch_count" },
    { title: "采购账号", dataIndex: "purchase_quantity" },
    { title: "有效账号", dataIndex: "effective_account_count" },
    {
      title: "有效率",
      dataIndex: "effective_rate",
      render: (value: number) => `${value.toFixed(2)}%`
    },
    { title: "平均评分", dataIndex: "avg_score" },
    {
      title: "真实有效成本",
      dataIndex: "real_effective_unit_cost",
      render: money
    },
    {
      title: "建议倍率",
      dataIndex: "recommended_multiplier",
      render: (value: number) => `${value.toFixed(2)}x`
    },
    {
      title: "倍率构成",
      render: (_, row) => (
        <Tooltip
          title={`基础 ${row.base_multiplier.toFixed(2)}x + 风险 ${row.risk_buffer.toFixed(2)}x + 损耗 ${row.loss_buffer.toFixed(2)}x + 评分 ${row.score_buffer.toFixed(2)}x`}
        >
          <span style={{ color: "#31527a" }}>
            {row.base_multiplier.toFixed(2)} + {row.risk_buffer.toFixed(2)} +{" "}
            {row.loss_buffer.toFixed(2)} + {row.score_buffer.toFixed(2)}
          </span>
        </Tooltip>
      )
    },
    {
      title: "建议售价",
      dataIndex: "suggested_sale_price",
      render: money
    },
    {
      title: "稳定等级",
      dataIndex: "stability_level",
      render: (value: string) => {
        const color = value === "stable" ? "green" : value === "observing" ? "gold" : "red";
        const label = value === "stable" ? "长期稳定" : value === "observing" ? "观察中" : "高风险";
        return <Tag color={color}>{label}</Tag>;
      }
    },
    { title: "原因", dataIndex: "reason" }
  ];
  const accountTypeColumns: ColumnsType<AccountTypeProfitRow> = [
    { title: "账号类型", dataIndex: "account_type", fixed: "left" },
    { title: "批次数", dataIndex: "batch_count" },
    { title: "采购数量", dataIndex: "purchase_quantity" },
    { title: "有效数量", dataIndex: "effective_account_count" },
    {
      title: "有效率",
      dataIndex: "effective_rate",
      render: (value: number) => `${value.toFixed(2)}%`
    },
    { title: "所有成本", dataIndex: "all_cost", render: money },
    { title: "有效面值成本", dataIndex: "effective_cost", render: money },
    { title: "测试损耗", dataIndex: "test_loss", render: money },
    { title: "真实有效单价", dataIndex: "real_effective_unit_cost", render: money },
    { title: "平均评分", dataIndex: "avg_score", render: (value?: number | null) => value ?? "-" }
  ];
  const purchaseBatchColumns: ColumnsType<PurchaseBatchProfitRow> = [
    { title: "测评批次", dataIndex: "batch_no", fixed: "left" },
    { title: "供应商", dataIndex: "supplier_name", render: (value?: string | null) => value ?? "-" },
    { title: "账号类型", dataIndex: "account_type" },
    { title: "采购数量", dataIndex: "purchase_quantity" },
    { title: "有效数量", dataIndex: "effective_account_count" },
    {
      title: "有效率",
      dataIndex: "effective_rate",
      render: (value: number) => `${value.toFixed(2)}%`
    },
    { title: "采购总价", dataIndex: "purchase_total_price", render: money },
    { title: "表面单价", dataIndex: "nominal_unit_price", render: money },
    { title: "真实有效单价", dataIndex: "real_effective_unit_price", render: money },
    { title: "测试损耗", dataIndex: "test_loss", render: money },
    { title: "评分", dataIndex: "overall_score", render: (value?: number | null) => value ?? "-" },
    { title: "结论", dataIndex: "conclusion", render: (value?: string | null) => value ?? "-" }
  ];

  return (
    <>
      <PageHeader title="盈亏报表" subtitle="按月查看收入、成本、利润、真实利润和测试损耗。" />
      <div className="content-section" style={{ marginTop: 0 }}>
        <div className="toolbar">
          <strong>月度趋势</strong>
          <RangePicker
            picker="month"
            value={range}
            allowClear={false}
            onChange={(value) => {
              if (value?.[0] && value?.[1]) {
                setRange([value[0], value[1]]);
              }
            }}
          />
        </div>
        <div ref={chartRef} style={{ width: "100%", height: 340 }} />
      </div>
      <div className="content-section">
        <div className="toolbar">
          <strong>月度盈亏明细</strong>
          <Button
            icon={<DownloadOutlined />}
            onClick={() =>
              exportCsv("月度盈亏明细.csv", query.data ?? [], [
                { title: "月份", value: "month" },
                { title: "收入", value: "revenue" },
                { title: "所有成本", value: "all_cost" },
                { title: "真实成本", value: "real_cost" },
                { title: "利润", value: "profit" },
                { title: "真实利润", value: "real_profit" },
                { title: "测试损耗", value: "test_loss" }
              ])
            }
          >
            导出 CSV
          </Button>
        </div>
        <Table
          rowKey="month"
          size="middle"
          loading={query.isLoading}
          columns={columns}
          dataSource={query.data ?? []}
          pagination={false}
          scroll={{ x: "max-content" }}
        />
      </div>
      <div className="content-section ai-recommendation-section">
        <div className="toolbar">
          <div>
            <strong><RobotOutlined /> AI智能研判</strong>
            <div className="section-subtitle">
              根据真实有效成本、有效率、测试损耗和目标毛利率，估算各账号类型的建议倍率与预测收益。
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ color: "#617086" }}>目标毛利率</span>
            <InputNumber
              min={0}
              max={80}
              value={targetMargin}
              formatter={(value) => `${value}%`}
              parser={(value) => Number(value?.replace("%", "") ?? 0)}
              onChange={(value) => setTargetMargin(Number(value ?? 35))}
            />
            <Button
              icon={<DownloadOutlined />}
              onClick={() =>
                exportCsv("AI智能研判.csv", aiRecommendationQuery.data ?? [], [
                  { title: "账号类型", value: "account_type" },
                  { title: "风险", value: "risk_level" },
                  { title: "有效账号", value: "effective_account_count" },
                  { title: "有效率", value: "effective_rate" },
                  { title: "真实有效成本", value: "real_effective_unit_cost" },
                  { title: "建议倍率", value: "recommended_multiplier" },
                  { title: "建议售价", value: "suggested_sale_price" },
                  { title: "预测收入", value: "projected_revenue" },
                  { title: "预测利润", value: "projected_profit" },
                  { title: "预测利润率", value: "projected_margin" },
                  { title: "研判依据", value: "reason" }
                ])
              }
            >
              导出 CSV
            </Button>
          </div>
        </div>
        <Table
          rowKey="account_type"
          size="middle"
          loading={aiRecommendationQuery.isLoading}
          columns={aiRecommendationColumns}
          dataSource={aiRecommendationQuery.data ?? []}
          pagination={false}
          scroll={{ x: "max-content" }}
        />
      </div>
      <div className="content-section">
        <div className="toolbar">
          <div>
            <strong>稳定货源成本倍率建议</strong>
            <div style={{ color: "#617086", fontSize: 12, marginTop: 4 }}>
              建议倍率 = 基础毛利倍率 + 稳定风险缓冲 + 无效率损耗缓冲 + 评分风险缓冲
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Button
              icon={<DownloadOutlined />}
              onClick={() =>
                exportCsv("稳定货源成本倍率建议.csv", multiplierQuery.data ?? [], [
                  { title: "供应商", value: "supplier_name" },
                  { title: "批次数", value: "batch_count" },
                  { title: "采购账号", value: "purchase_quantity" },
                  { title: "有效账号", value: "effective_account_count" },
                  { title: "有效率", value: "effective_rate" },
                  { title: "平均评分", value: "avg_score" },
                  { title: "真实有效成本", value: "real_effective_unit_cost" },
                  { title: "建议倍率", value: "recommended_multiplier" },
                  { title: "建议售价", value: "suggested_sale_price" },
                  { title: "稳定等级", value: "stability_level" },
                  { title: "原因", value: "reason" }
                ])
              }
            >
              导出 CSV
            </Button>
            <span style={{ color: "#617086" }}>目标毛利率</span>
            <InputNumber
              min={0}
              max={80}
              value={targetMargin}
              formatter={(value) => `${value}%`}
              parser={(value) => Number(value?.replace("%", "") ?? 0)}
              onChange={(value) => setTargetMargin(Number(value ?? 35))}
            />
          </div>
        </div>
        <Table
          rowKey="supplier_id"
          size="middle"
          loading={multiplierQuery.isLoading}
          columns={multiplierColumns}
          dataSource={multiplierQuery.data ?? []}
          pagination={false}
          scroll={{ x: "max-content" }}
        />
      </div>
      <div className="content-section">
        <div className="toolbar">
          <div>
            <strong>账号类型真实成本排行</strong>
            <div style={{ color: "#617086", fontSize: 12, marginTop: 4 }}>
              当前按测评批次统计成本、有效率和损耗；收入分摊接入 sub2api 后可升级为真实利润排行。
            </div>
          </div>
          <Button
            icon={<DownloadOutlined />}
            onClick={() =>
              exportCsv("账号类型真实成本排行.csv", accountTypeQuery.data ?? [], [
                { title: "账号类型", value: "account_type" },
                { title: "批次数", value: "batch_count" },
                { title: "采购数量", value: "purchase_quantity" },
                { title: "有效数量", value: "effective_account_count" },
                { title: "有效率", value: "effective_rate" },
                { title: "所有成本", value: "all_cost" },
                { title: "有效面值成本", value: "effective_cost" },
                { title: "测试损耗", value: "test_loss" },
                { title: "真实有效单价", value: "real_effective_unit_cost" },
                { title: "平均评分", value: "avg_score" }
              ])
            }
          >
            导出 CSV
          </Button>
        </div>
        <Table
          rowKey="account_type"
          size="middle"
          loading={accountTypeQuery.isLoading}
          columns={accountTypeColumns}
          dataSource={accountTypeQuery.data ?? []}
          pagination={false}
          scroll={{ x: "max-content" }}
        />
      </div>
      <div className="content-section">
        <div className="toolbar">
          <strong>采购批次有效成本排行</strong>
          <Button
            icon={<DownloadOutlined />}
            onClick={() =>
              exportCsv("采购批次有效成本排行.csv", purchaseBatchQuery.data ?? [], [
                { title: "测评批次", value: "batch_no" },
                { title: "供应商", value: "supplier_name" },
                { title: "账号类型", value: "account_type" },
                { title: "采购数量", value: "purchase_quantity" },
                { title: "有效数量", value: "effective_account_count" },
                { title: "有效率", value: "effective_rate" },
                { title: "采购总价", value: "purchase_total_price" },
                { title: "表面单价", value: "nominal_unit_price" },
                { title: "真实有效单价", value: "real_effective_unit_price" },
                { title: "测试损耗", value: "test_loss" },
                { title: "评分", value: "overall_score" },
                { title: "结论", value: "conclusion" }
              ])
            }
          >
            导出 CSV
          </Button>
        </div>
        <Table
          rowKey="batch_id"
          size="middle"
          loading={purchaseBatchQuery.isLoading}
          columns={purchaseBatchColumns}
          dataSource={purchaseBatchQuery.data ?? []}
          pagination={false}
          scroll={{ x: "max-content" }}
        />
      </div>
    </>
  );
}
