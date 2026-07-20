import { ReloadOutlined } from "@ant-design/icons";
import { Button, Table } from "antd";
import type { TableProps } from "antd";
import type { ColumnsType } from "antd/es/table";

type EntityTableProps<T extends { id: string }> = {
  title: string;
  columns: ColumnsType<T>;
  data?: T[];
  loading?: boolean;
  onRefresh: () => void;
  extra?: React.ReactNode;
  rowSelection?: TableProps<T>["rowSelection"];
};

export function EntityTable<T extends { id: string }>({
  title,
  columns,
  data,
  loading,
  onRefresh,
  extra,
  rowSelection
}: EntityTableProps<T>) {
  return (
    <div className="content-section">
      <div className="toolbar">
        <div>
          <strong className="section-title">{title}</strong>
          <div className="section-subtitle">共 {data?.length ?? 0} 条记录</div>
        </div>
        <div className="table-actions">
          {extra}
          <Button icon={<ReloadOutlined />} onClick={onRefresh}>
            刷新
          </Button>
        </div>
      </div>
      <Table
        className="entity-table"
        size="middle"
        rowKey="id"
        columns={columns}
        dataSource={data ?? []}
        loading={loading}
        rowSelection={rowSelection}
        pagination={{ pageSize: 10, showSizeChanger: false }}
        scroll={{ x: "max-content" }}
      />
    </div>
  );
}
