import { useQuery } from "@tanstack/react-query";
import { Typography } from "antd";

import { listAuditLogs } from "../api/endpoints";
import type { AuditLog } from "../api/types";
import { EntityTable } from "../components/EntityTable";
import { PageHeader } from "../components/PageHeader";
import { auditActionLabel, auditDetailLabel, auditResourceTypeLabel } from "../utils/labels";

function formatDetail(detail: Record<string, unknown> | null | undefined): string {
  if (!detail) {
    return "-";
  }
  const translated = Object.fromEntries(Object.entries(detail).map(([key, value]) => [auditDetailLabel(key), value]));
  return JSON.stringify(translated);
}

export function AuditLogsPage() {
  const query = useQuery({ queryKey: ["audit-logs"], queryFn: listAuditLogs });

  return (
    <>
      <PageHeader title="审计日志" subtitle="记录敏感字段查看等高风险操作。" />
      <div className="content-section" style={{ marginBottom: 16 }}>
        <Typography.Paragraph style={{ margin: 0, color: "#617086" }}>
          当前仅管理员可查看审计日志。查看供应商密钥、账号密码等操作会写入这里。
        </Typography.Paragraph>
      </div>
      <EntityTable<AuditLog>
        title="审计记录"
        data={query.data}
        loading={query.isLoading}
        onRefresh={() => query.refetch()}
        columns={[
          { title: "时间", dataIndex: "created_at", fixed: "left" },
          { title: "动作", dataIndex: "action", render: auditActionLabel },
          { title: "资源", dataIndex: "resource_type", render: auditResourceTypeLabel },
          { title: "资源 ID", dataIndex: "resource_id" },
          { title: "用户 ID", dataIndex: "user_id" },
          { title: "IP", dataIndex: "ip_address" },
          {
            title: "详情",
            dataIndex: "detail",
            render: formatDetail
          }
        ]}
      />
    </>
  );
}
