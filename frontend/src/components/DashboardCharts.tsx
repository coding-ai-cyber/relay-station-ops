import { Empty, Skeleton } from "antd";
import * as echarts from "echarts";
import type { EChartsOption } from "echarts";
import { useEffect, useMemo, useRef } from "react";

import type { MonthlyProfitRow, SupplierRankingRow } from "../api/types";

function compactMoney(value: number) {
  return new Intl.NumberFormat("zh-CN", {
    notation: "compact",
    maximumFractionDigits: 1
  }).format(value);
}

function useDashboardChart(option: EChartsOption) {
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!ref.current) {
      return;
    }

    const chart = echarts.init(ref.current, undefined, { renderer: "canvas" });
    chart.setOption(option);

    const resizeObserver = new ResizeObserver(() => chart.resize());
    resizeObserver.observe(ref.current);

    return () => {
      resizeObserver.disconnect();
      chart.dispose();
    };
  }, [option]);

  return ref;
}

function ChartLoading() {
  return (
    <div className="dashboard-chart-loading" aria-label="图表加载中">
      <Skeleton active title={false} paragraph={{ rows: 6, width: ["94%", "86%", "91%", "72%", "80%", "64%"] }} />
    </div>
  );
}

export function MonthlyTrendChart({
  rows,
  loading
}: {
  rows?: MonthlyProfitRow[];
  loading?: boolean;
}) {
  const option = useMemo<EChartsOption>(() => {
    const data = rows ?? [];
    return {
      animationDuration: 350,
      aria: {
        enabled: true,
        decal: { show: true }
      },
      color: ["#8b5cf6", "#22d3ee", "#34d399"],
      tooltip: {
        trigger: "axis",
        backgroundColor: "rgba(9, 12, 27, 0.96)",
        borderColor: "rgba(167, 139, 250, 0.28)",
        borderWidth: 1,
        textStyle: { color: "#edf4ff" },
        valueFormatter: (value) => `¥${Number(value).toLocaleString("zh-CN", { maximumFractionDigits: 2 })}`
      },
      legend: {
        top: 0,
        left: 0,
        itemWidth: 18,
        itemHeight: 8,
        textStyle: { color: "#9aa8c7", fontSize: 12 },
        data: ["收入", "所有成本", "真实利润"]
      },
      grid: { top: 42, left: 14, right: 14, bottom: 6, containLabel: true },
      xAxis: {
        type: "category",
        boundaryGap: false,
        data: data.map((item) => item.month.slice(5) + "月"),
        axisLine: { lineStyle: { color: "rgba(167, 139, 250, 0.24)" } },
        axisTick: { show: false },
        axisLabel: { color: "#93a4c7", fontSize: 11 }
      },
      yAxis: {
        type: "value",
        splitNumber: 4,
        axisLabel: {
          color: "#8090b5",
          fontSize: 11,
          formatter: (value: number) => compactMoney(value)
        },
        splitLine: { lineStyle: { color: "rgba(148, 163, 184, 0.13)", type: "dashed" } }
      },
      series: [
        {
          name: "收入",
          type: "line",
          smooth: 0.25,
          symbol: "circle",
          symbolSize: 6,
          lineStyle: {
            width: 4,
            shadowBlur: 18,
            shadowColor: "rgba(139, 92, 246, 0.55)"
          },
          areaStyle: {
            color: {
              type: "linear",
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: "rgba(139, 92, 246, 0.34)" },
                { offset: 1, color: "rgba(34, 211, 238, 0.01)" }
              ]
            }
          },
          data: data.map((item) => item.revenue)
        },
        {
          name: "所有成本",
          type: "line",
          smooth: 0.25,
          symbol: "emptyCircle",
          symbolSize: 6,
          lineStyle: { width: 2, type: "dashed", shadowBlur: 10, shadowColor: "rgba(34, 211, 238, 0.4)" },
          data: data.map((item) => item.all_cost)
        },
        {
          name: "真实利润",
          type: "line",
          smooth: 0.25,
          symbol: "diamond",
          symbolSize: 7,
          lineStyle: { width: 3, shadowBlur: 14, shadowColor: "rgba(52, 211, 153, 0.42)" },
          data: data.map((item) => item.real_profit)
        }
      ]
    };
  }, [rows]);
  const chartRef = useDashboardChart(option);

  if (loading) {
    return <ChartLoading />;
  }

  if (!rows?.length) {
    return (
      <div className="dashboard-chart-empty">
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无月度经营数据" />
      </div>
    );
  }

  return <div ref={chartRef} className="dashboard-chart" role="img" aria-label="近六个月收入、所有成本和真实利润趋势" />;
}

export function SupplierRankingChart({
  rows,
  loading
}: {
  rows?: SupplierRankingRow[];
  loading?: boolean;
}) {
  const rankedRows = useMemo(
    () => [...(rows ?? [])].sort((a, b) => Number(b.all_cost) - Number(a.all_cost)).slice(0, 5).reverse(),
    [rows]
  );
  const option = useMemo<EChartsOption>(() => ({
    animationDuration: 350,
    aria: { enabled: true, decal: { show: true } },
    color: ["#8b5cf6", "#22d3ee"],
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      backgroundColor: "rgba(9, 12, 27, 0.96)",
      borderColor: "rgba(167, 139, 250, 0.28)",
      borderWidth: 1,
      textStyle: { color: "#edf4ff" },
      valueFormatter: (value) => `¥${Number(value).toLocaleString("zh-CN", { maximumFractionDigits: 2 })}`
    },
    legend: {
      top: 0,
      left: 0,
      itemWidth: 12,
      itemHeight: 8,
      textStyle: { color: "#9aa8c7", fontSize: 12 },
      data: ["所有成本", "真实成本"]
    },
    grid: { top: 38, left: 12, right: 42, bottom: 4, containLabel: true },
    xAxis: {
      type: "value",
      axisLabel: { show: false },
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: "rgba(148, 163, 184, 0.13)", type: "dashed" } }
    },
    yAxis: {
      type: "category",
      data: rankedRows.map((item) => item.supplier_name),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        color: "#a8b3cf",
        fontSize: 11,
        width: 76,
        overflow: "truncate"
      }
    },
    series: [
      {
        name: "所有成本",
        type: "bar",
        barMaxWidth: 12,
        itemStyle: {
          borderRadius: [0, 8, 8, 0],
          shadowBlur: 12,
          shadowColor: "rgba(139, 92, 246, 0.28)"
        },
        label: {
          show: true,
          position: "right",
          color: "#9aa8c7",
          fontSize: 10,
          formatter: (params) => compactMoney(Number(params.value))
        },
        data: rankedRows.map((item) => item.all_cost)
      },
      {
        name: "真实成本",
        type: "bar",
        barMaxWidth: 12,
        itemStyle: {
          borderRadius: [0, 8, 8, 0],
          shadowBlur: 12,
          shadowColor: "rgba(34, 211, 238, 0.24)"
        },
        data: rankedRows.map((item) => item.real_cost)
      }
    ]
  }), [rankedRows]);
  const chartRef = useDashboardChart(option);

  if (loading) {
    return <ChartLoading />;
  }

  if (!rankedRows.length) {
    return (
      <div className="dashboard-chart-empty">
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无供应商成本数据" />
      </div>
    );
  }

  return <div ref={chartRef} className="dashboard-chart" role="img" aria-label="供应商所有成本与真实成本排行" />;
}
