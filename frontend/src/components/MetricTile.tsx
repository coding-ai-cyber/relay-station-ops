import {
  ArrowDownOutlined,
  ArrowUpOutlined,
  MinusOutlined
} from "@ant-design/icons";
import { Skeleton } from "antd";

type MetricTileProps = {
  label: string;
  value: string | number;
  tone?: "normal" | "good" | "bad" | "warn";
  description?: string;
  delta?: number | null;
  inverseTrend?: boolean;
  loading?: boolean;
  icon?: React.ReactNode;
};

const toneLabels = {
  normal: "经营指标",
  good: "表现稳健",
  bad: "需关注",
  warn: "持续观察"
};

function trendTone(delta: number, inverseTrend: boolean) {
  if (delta === 0) {
    return "neutral";
  }
  const favorable = inverseTrend ? delta < 0 : delta > 0;
  return favorable ? "positive" : "negative";
}

export function MetricTile({
  label,
  value,
  tone = "normal",
  description,
  delta,
  inverseTrend = false,
  loading = false,
  icon
}: MetricTileProps) {
  const hasDelta = delta !== null && delta !== undefined && Number.isFinite(delta);
  const TrendIcon = hasDelta
    ? delta > 0
      ? ArrowUpOutlined
      : delta < 0
        ? ArrowDownOutlined
        : MinusOutlined
    : null;

  return (
    <div className={`metric-tile metric-tile-${tone}`}>
      <span className="metric-aura" aria-hidden="true" />
      <div className="metric-tile-head">
        <div className="metric-label-wrap">
          {icon ? <span className="metric-icon">{icon}</span> : null}
          <div className="metric-label">{label}</div>
        </div>
        <span className="metric-badge">{toneLabels[tone]}</span>
      </div>
      {loading ? (
        <Skeleton.Input className="metric-skeleton" active size="small" />
      ) : (
        <div className="metric-value">{value}</div>
      )}
      <div className="metric-foot">
        <span className="metric-description">{description}</span>
        {hasDelta && TrendIcon ? (
          <span className={`metric-trend metric-trend-${trendTone(delta, inverseTrend)}`}>
            <TrendIcon /> {Math.abs(delta).toFixed(1)}%
            <span className="metric-trend-label">较上月</span>
          </span>
        ) : (
          <span className="metric-trend metric-trend-neutral">暂无环比</span>
        )}
      </div>
    </div>
  );
}
