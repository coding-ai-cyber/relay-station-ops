import {
  ArrowRightOutlined,
  CalendarOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  DollarOutlined,
  ExclamationCircleOutlined,
  FundOutlined,
  InfoCircleOutlined,
  ShoppingCartOutlined,
  WarningOutlined
} from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { Button, DatePicker, Empty, Progress, Table, Tag } from "antd";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import type { Dayjs } from "dayjs";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import {
  getAbnormalAccounts,
  getDashboardOverview,
  getExpiringAssets,
  getMonthlyProfitReport,
  getRecentPurchases,
  getSupplierRanking
} from "../api/endpoints";
import type { ExpiringAssetRow, MonthlyProfitRow, Purchase } from "../api/types";
import { MonthlyTrendChart, SupplierRankingChart } from "../components/DashboardCharts";
import { MetricTile } from "../components/MetricTile";
import { PageHeader } from "../components/PageHeader";
import { dateOnly, money } from "../utils/format";
import { costStatusLabel, purchaseTypeLabel } from "../utils/labels";

const { RangePicker } = DatePicker;

function percentageDelta(current: number | undefined, previous: number | undefined) {
  if (current === undefined || previous === undefined) {
    return null;
  }
  if (previous === 0) {
    return current === 0 ? 0 : null;
  }
  return ((current - previous) / Math.abs(previous)) * 100;
}

function costStatusTag(status: string) {
  const statusMap: Record<string, { color: string; label: string }> = {
    testing: { color: "gold", label: costStatusLabel("testing") },
    valid: { color: "green", label: costStatusLabel("valid") },
    partial_valid: { color: "orange", label: costStatusLabel("partial_valid") },
    invalid: { color: "red", label: costStatusLabel("invalid") },
    refunded: { color: "blue", label: costStatusLabel("refunded") },
    scrapped: { color: "default", label: costStatusLabel("scrapped") },
    confirmed: { color: "green", label: "已确认" },
    excluded: { color: "default", label: "已排除" }
  };
  const config = statusMap[status] ?? { color: "blue", label: status || "待处理" };
  return <Tag color={config.color}>{config.label}</Tag>;
}

function DashboardEmpty({
  title,
  description,
  action
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <Empty
      className="dashboard-empty"
      image={Empty.PRESENTED_IMAGE_SIMPLE}
      description={
        <div>
          <strong>{title}</strong>
          <span>{description}</span>
        </div>
      }
    >
      {action}
    </Empty>
  );
}

function assetTypeLabel(type: string) {
  if (type === "account") {
    return "账号";
  }
  if (type === "server") {
    return "服务器";
  }
  if (type === "proxy_pool") {
    return "IP地址池";
  }
  return type;
}

function assetLink(asset: ExpiringAssetRow) {
  if (asset.asset_type === "account") {
    return "/accounts";
  }
  if (asset.asset_type === "server") {
    return "/servers";
  }
  if (asset.asset_type === "proxy_pool") {
    return "/proxy-pools";
  }
  return "/";
}

export function DashboardPage() {
  const now = dayjs();
  const [selectedRange, setSelectedRange] = useState<[Dayjs, Dayjs]>([
    now.startOf("month"),
    now.endOf("month")
  ]);
  const rangeStart = selectedRange[0].startOf("month");
  const rangeEnd = selectedRange[1].endOf("month");
  const overviewQuery = useQuery({
    queryKey: ["dashboard", rangeStart.format("YYYY-MM-DD"), rangeEnd.format("YYYY-MM-DD")],
    queryFn: () => getDashboardOverview({
      start_date: rangeStart.format("YYYY-MM-DD"),
      end_date: rangeEnd.format("YYYY-MM-DD")
    })
  });
  const trendQuery = useQuery({
    queryKey: [
      "dashboard",
      "monthly-trend",
      rangeStart.year(),
      rangeStart.month() + 1,
      rangeEnd.year(),
      rangeEnd.month() + 1
    ],
    queryFn: () => getMonthlyProfitReport({
      start_year: rangeStart.year(),
      start_month: rangeStart.month() + 1,
      end_year: rangeEnd.year(),
      end_month: rangeEnd.month() + 1
    })
  });
  const supplierRanking = useQuery({
    queryKey: ["supplier-ranking"],
    queryFn: getSupplierRanking
  });
  const recentPurchases = useQuery({
    queryKey: ["dashboard", "recent-purchases"],
    queryFn: getRecentPurchases
  });
  const abnormalAccounts = useQuery({
    queryKey: ["dashboard", "abnormal-accounts"],
    queryFn: getAbnormalAccounts
  });
  const expiringAssets = useQuery({
    queryKey: ["dashboard", "expiring-assets"],
    queryFn: () => getExpiringAssets(30)
  });

  const data = overviewQuery.data;
  const currentMonth = trendQuery.data?.at(-1);
  const previousMonth = trendQuery.data?.at(-2);
  const totalAccounts = (data?.available_accounts ?? 0) + (data?.unavailable_accounts ?? 0);
  const accountHealth = totalAccounts > 0
    ? Math.round(((data?.available_accounts ?? 0) / totalAccounts) * 100)
    : 0;
  const lossRate = (data?.all_cost ?? 0) > 0
    ? ((data?.test_loss ?? 0) / (data?.all_cost ?? 1)) * 100
    : 0;
  const profitMargin = (data?.revenue ?? 0) > 0
    ? ((data?.profit ?? 0) / (data?.revenue ?? 1)) * 100
    : 0;
  const operatingSignal = !data || (data.revenue === 0 && data.all_cost === 0)
    ? "等待数据"
    : data.profit < 0
      ? "利润预警"
      : lossRate >= 20
        ? "损耗偏高"
        : "稳定盈利";

  const insight = useMemo(() => {
    if (!data || (data.revenue === 0 && data.all_cost === 0)) {
      return "当前统计区间尚未产生经营数据，录入收入或采购后将自动形成趋势。";
    }
    if (data.profit < 0) {
      return `当前统计区间经营利润为负，收入与所有成本相差 ¥${money(Math.abs(data.profit))}。`;
    }
    if (lossRate >= 20) {
      return `测试损耗占所有成本 ${lossRate.toFixed(1)}%，建议优先复核高损耗采购批次。`;
    }
    return `当前统计区间经营利润 ¥${money(data.profit)}，测试损耗率 ${lossRate.toFixed(1)}%。`;
  }, [data, lossRate]);

  const purchaseColumns: ColumnsType<Purchase> = [
    {
      title: "采购单",
      dataIndex: "purchase_no",
      render: (value: string, record) => (
        <div className="purchase-primary-cell">
          <strong>{record.product_name}</strong>
          <span>{value}</span>
        </div>
      )
    },
    { title: "类型", dataIndex: "purchase_type", responsive: ["md"], render: purchaseTypeLabel },
    {
      title: "总价",
      dataIndex: "total_price",
      align: "right",
      render: (value) => <span className="table-money">¥{money(value)}</span>
    },
    { title: "采购日期", dataIndex: "purchased_at", render: dateOnly, responsive: ["sm"] },
    { title: "成本状态", dataIndex: "cost_status", render: costStatusTag, responsive: ["sm"] }
  ];

  const metricRows: Array<{
    label: string;
    value: number | undefined;
    field: keyof Pick<MonthlyProfitRow, "revenue" | "all_cost" | "real_cost" | "profit" | "real_profit" | "test_loss">;
    tone: "normal" | "good" | "bad" | "warn";
    description: string;
    inverseTrend?: boolean;
    icon: React.ReactNode;
  }> = [
    { label: "区间收入", value: data?.revenue, field: "revenue", tone: "normal", description: "已确认经营收入", icon: <DollarOutlined /> },
    { label: "所有成本", value: data?.all_cost, field: "all_cost", tone: "warn", description: "统计区间经营总投入", inverseTrend: true, icon: <ShoppingCartOutlined /> },
    { label: "真实成本", value: data?.real_cost, field: "real_cost", tone: "normal", description: "已确认有效成本", inverseTrend: true, icon: <CheckCircleOutlined /> },
    { label: "经营利润", value: data?.profit, field: "profit", tone: (data?.profit ?? 0) >= 0 ? "good" : "bad", description: "收入减所有成本", icon: <FundOutlined /> },
    { label: "真实利润", value: data?.real_profit, field: "real_profit", tone: (data?.real_profit ?? 0) >= 0 ? "good" : "bad", description: "收入减真实成本", icon: <FundOutlined /> },
    { label: "测试损耗", value: data?.test_loss, field: "test_loss", tone: lossRate >= 20 ? "bad" : "warn", description: `占所有成本 ${lossRate.toFixed(1)}%`, inverseTrend: true, icon: <WarningOutlined /> }
  ];

  return (
    <>
      <PageHeader
        title="经营仪表盘"
        subtitle="AI 经营信号、利润曲线与资产风险的实时决策屏。"
        meta={
          <span><ClockCircleOutlined /> 数据更新于 {overviewQuery.dataUpdatedAt ? dayjs(overviewQuery.dataUpdatedAt).format("HH:mm:ss") : "--:--:--"}</span>
        }
        extra={
          <div className="dashboard-month-filter">
            <CalendarOutlined />
            <span>统计区间</span>
            <RangePicker
              picker="month"
              format="YYYY年MM月"
              allowClear={false}
              value={selectedRange}
              onChange={(value) => {
                if (value?.[0] && value?.[1]) {
                  setSelectedRange([value[0], value[1]]);
                }
              }}
            />
          </div>
        }
      />

      <section className="aurora-hero" aria-label="经营信号总览">
        <div className="aurora-hero-copy">
          <div className="aurora-kicker">
            <span className="aurora-pulse" />
            Aurora Intelligence
          </div>
          <h2>{operatingSignal}</h2>
          <p>{insight}</p>
          <div className="aurora-signal-grid">
            <div>
              <span>利润率</span>
              <strong>{profitMargin.toFixed(1)}%</strong>
            </div>
            <div>
              <span>损耗率</span>
              <strong>{lossRate.toFixed(1)}%</strong>
            </div>
            <div>
              <span>资产健康</span>
              <strong>{accountHealth}%</strong>
            </div>
          </div>
        </div>
        <div className="aurora-orbit" aria-hidden="true">
          <div className="orbit-ring orbit-ring-one" />
          <div className="orbit-ring orbit-ring-two" />
          <div className="orbit-core">
            <span>REAL PROFIT</span>
            <strong>¥{money(data?.real_profit)}</strong>
          </div>
        </div>
      </section>

      <div className="metric-grid" aria-busy={overviewQuery.isLoading}>
        {metricRows.map((metric) => (
          <MetricTile
            key={metric.field}
            label={metric.label}
            value={`¥${money(metric.value)}`}
            tone={metric.tone}
            description={metric.description}
            delta={percentageDelta(currentMonth?.[metric.field], previousMonth?.[metric.field])}
            inverseTrend={metric.inverseTrend}
            loading={overviewQuery.isLoading || trendQuery.isLoading}
            icon={metric.icon}
          />
        ))}
      </div>

      <div className={`dashboard-insight ${data && data.profit < 0 ? "dashboard-insight-danger" : ""}`}>
        <InfoCircleOutlined />
        <strong>经营判断</strong>
        <span>{insight}</span>
      </div>

      <div className="dashboard-main-grid">
        <section className="content-section dashboard-panel dashboard-trend-panel">
          <div className="toolbar">
            <div>
              <h2 className="section-title">区间经营趋势</h2>
              <div className="section-subtitle">收入、所有成本与真实利润</div>
            </div>
            <Button type="link" className="section-link">
              <Link to="/reports">查看报表 <ArrowRightOutlined /></Link>
            </Button>
          </div>
          <MonthlyTrendChart rows={trendQuery.data} loading={trendQuery.isLoading} />
        </section>

        <section className="content-section dashboard-panel">
          <div className="toolbar">
            <div>
              <h2 className="section-title">供应商成本排行</h2>
              <div className="section-subtitle">按累计所有成本排序</div>
            </div>
          </div>
          <SupplierRankingChart rows={supplierRanking.data} loading={supplierRanking.isLoading} />
          {!supplierRanking.isLoading && !supplierRanking.data?.length ? (
            <div className="chart-empty-action">
              <Button size="small"><Link to="/purchases">录入采购</Link></Button>
            </div>
          ) : null}
        </section>
      </div>

      <div className="dashboard-secondary-grid">
        <section className="content-section dashboard-panel recent-purchases-panel">
          <div className="toolbar">
            <div>
              <h2 className="section-title">最近采购</h2>
              <div className="section-subtitle">最新 {Math.min(recentPurchases.data?.length ?? 0, 5)} 笔记录</div>
            </div>
            <Button type="link" className="section-link">
              <Link to="/purchases">全部采购 <ArrowRightOutlined /></Link>
            </Button>
          </div>
          <Table
            className="dashboard-table"
            rowKey="id"
            size="small"
            loading={recentPurchases.isLoading}
            columns={purchaseColumns}
            dataSource={(recentPurchases.data ?? []).slice(0, 5)}
            pagination={false}
            scroll={{ x: "max-content" }}
            locale={{
              emptyText: (
                <DashboardEmpty
                  title="暂无采购记录"
                  description="新增采购后，成本会自动汇总到仪表盘。"
                  action={<Button type="primary" size="small"><Link to="/purchases">新增第一笔采购</Link></Button>}
                />
              )
            }}
          />
        </section>

        <section className="content-section dashboard-panel risk-panel" id="expiry-risk">
          <div className="toolbar">
            <div>
              <h2 className="section-title">资产健康</h2>
              <div className="section-subtitle">账号可用性与近期风险</div>
            </div>
            <Tag color={accountHealth >= 90 ? "green" : accountHealth >= 70 ? "gold" : "red"}>
              {totalAccounts > 0 ? `${accountHealth}% 可用` : "暂无资产"}
            </Tag>
          </div>

          <div className="health-summary">
            <div>
              <span>可用账号</span>
              <strong>{data?.available_accounts ?? 0}</strong>
            </div>
            <div>
              <span>不可用账号</span>
              <strong>{data?.unavailable_accounts ?? 0}</strong>
            </div>
          </div>
          <Progress
            percent={accountHealth}
            showInfo={false}
            strokeColor={accountHealth >= 90 ? "#15803d" : accountHealth >= 70 ? "#d97706" : "#dc2626"}
            railColor="#e8edf4"
          />

          <div className="risk-list">
            <Link to="/accounts" className="risk-row">
              <span className="risk-icon risk-icon-danger"><ExclamationCircleOutlined /></span>
              <span><strong>异常账号</strong><small>等待复核或处置</small></span>
              <b>{abnormalAccounts.data?.length ?? 0}</b>
              <ArrowRightOutlined />
            </Link>
            <Link to="/servers" className="risk-row">
              <span className="risk-icon risk-icon-warning"><CalendarOutlined /></span>
              <span><strong>30 天内到期</strong><small>账号、服务器与IP地址池</small></span>
              <b>{expiringAssets.data?.length ?? 0}</b>
              <ArrowRightOutlined />
            </Link>
          </div>

          {expiringAssets.data?.length ? (
            <div className="expiry-list">
              <div className="expiry-list-title">即将到期资产</div>
              {expiringAssets.data.slice(0, 5).map((asset) => (
                <Link to={assetLink(asset)} className="expiry-row" key={`${asset.asset_type}-${asset.asset_id}`}>
                  <span>
                    <strong>{asset.name}</strong>
                    <small>{assetTypeLabel(asset.asset_type)} / {dateOnly(asset.expired_at)}</small>
                  </span>
                  <Tag color={asset.days_left <= 7 ? "red" : "gold"}>
                    {asset.days_left} 天
                  </Tag>
                </Link>
              ))}
            </div>
          ) : null}

          {!abnormalAccounts.isLoading && !expiringAssets.isLoading &&
          !abnormalAccounts.data?.length && !expiringAssets.data?.length ? (
            <div className="risk-clear"><CheckCircleOutlined /> 当前没有待处理的资产风险</div>
          ) : null}
        </section>
      </div>
    </>
  );
}
