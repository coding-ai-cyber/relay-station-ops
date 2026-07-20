import { CloudDownloadOutlined, CloudUploadOutlined, DatabaseOutlined, ReloadOutlined } from "@ant-design/icons";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Alert, Button, Card, Checkbox, Form, Input, Space, Tag, Upload, Typography, message } from "antd";
import type { UploadFile } from "antd";
import { useState } from "react";

import {
  createSystemBackup,
  downloadSystemBackup,
  getSystemMaintenanceStatus,
  importSystemBackup
} from "../api/endpoints";
import type { BackupCreateResult } from "../api/types";
import { PageHeader } from "../components/PageHeader";

function formatBytes(value: number) {
  if (!value) {
    return "0 B";
  }
  const units = ["B", "KB", "MB", "GB"];
  let size = value;
  let index = 0;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  return `${size.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export function SystemMaintenancePage() {
  const [backup, setBackup] = useState<BackupCreateResult | null>(null);
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [forceImport, setForceImport] = useState(false);

  const statusQuery = useQuery({
    queryKey: ["system-maintenance", "status"],
    queryFn: getSystemMaintenanceStatus
  });

  const backupMutation = useMutation({
    mutationFn: createSystemBackup,
    onSuccess: (payload) => {
      setBackup(payload);
      message.success("备份已创建");
    },
    onError: (error) => message.error(error.message)
  });

  const downloadMutation = useMutation({
    mutationFn: async (filename: string) => {
      const blob = await downloadSystemBackup(filename);
      saveBlob(blob, filename);
    },
    onError: (error) => message.error(error.message)
  });

  const importMutation = useMutation({
    mutationFn: async () => {
      const file = fileList[0]?.originFileObj;
      if (!file) {
        throw new Error("请选择备份 zip 文件");
      }
      return importSystemBackup(file, forceImport);
    },
    onSuccess: () => {
      message.success("备份导入完成，请刷新页面检查数据");
      setFileList([]);
    },
    onError: (error) => message.error(error.message)
  });

  const status = statusQuery.data;

  return (
    <>
      <PageHeader
        title="系统维护"
        subtitle="管理备份导出、备份导入，并查看服务器升级命令。"
      />

      <div className="content-section">
        <div className="toolbar">
          <div>
            <strong className="section-title">运行状态</strong>
            <div className="section-subtitle">当前环境、数据库迁移版本和备份目录</div>
          </div>
          <Button icon={<ReloadOutlined />} onClick={() => statusQuery.refetch()}>
            刷新
          </Button>
        </div>
        <Space wrap size={12}>
          <Tag color="blue">{status?.app_name ?? "Sub2API Ops"}</Tag>
          <Tag color={status?.app_env === "production" ? "green" : "gold"}>
            {status?.app_env ?? "-"}
          </Tag>
          <Tag color="purple">Alembic: {status?.alembic_head ?? "-"}</Tag>
        </Space>
        <Typography.Paragraph style={{ marginTop: 12, marginBottom: 0 }}>
          备份目录：<Typography.Text code>{status?.backup_dir ?? "-"}</Typography.Text>
        </Typography.Paragraph>
      </div>

      <div className="dashboard-grid">
        <Card
          title={
            <Space>
              <DatabaseOutlined />
              <span>导出备份</span>
            </Space>
          }
        >
          <Typography.Paragraph type="secondary">
            导出业务数据和上传文件，审计日志不导出。导出后可以直接下载 zip。
          </Typography.Paragraph>
          <Space wrap>
            <Button
              type="primary"
              icon={<CloudDownloadOutlined />}
              loading={backupMutation.isPending}
              onClick={() => backupMutation.mutate()}
            >
              创建备份
            </Button>
            <Button
              disabled={!backup}
              loading={downloadMutation.isPending}
              onClick={() => backup && downloadMutation.mutate(backup.filename)}
            >
              下载备份
            </Button>
          </Space>
          {backup ? (
            <Alert
              style={{ marginTop: 16 }}
              type="success"
              showIcon
              message={backup.filename}
              description={`大小：${formatBytes(backup.size_bytes)}`}
            />
          ) : null}
        </Card>

        <Card
          title={
            <Space>
              <CloudUploadOutlined />
              <span>导入备份</span>
            </Space>
          }
        >
          <Alert
            type="warning"
            showIcon
            message="导入会覆盖当前数据库和上传文件"
            description="请先确认已经保存当前备份，并确保 APP_FIELD_ENCRYPTION_KEY 与原机器一致。"
            style={{ marginBottom: 16 }}
          />
          <Form layout="vertical">
            <Form.Item label="备份文件">
              <Upload
                accept=".zip"
                maxCount={1}
                beforeUpload={() => false}
                fileList={fileList}
                onChange={({ fileList: next }) => setFileList(next)}
              >
                <Button icon={<CloudUploadOutlined />}>选择 zip</Button>
              </Upload>
            </Form.Item>
            <Form.Item>
              <Checkbox checked={forceImport} onChange={(event) => setForceImport(event.target.checked)}>
                强制导入，忽略加密密钥指纹不一致
              </Checkbox>
            </Form.Item>
            <Button
              danger
              type="primary"
              loading={importMutation.isPending}
              onClick={() => importMutation.mutate()}
            >
              导入备份
            </Button>
          </Form>
        </Card>
      </div>

      <div className="content-section">
        <div className="toolbar">
          <div>
            <strong className="section-title">升级命令</strong>
            <div className="section-subtitle">Web 页面暂不直接执行升级，避免误操作导致服务中断</div>
          </div>
        </div>
        <Space direction="vertical" style={{ width: "100%" }}>
          <Input addonBefore="Docker" value={status?.upgrade_commands.docker ?? "./scripts/upgrade.sh docker"} readOnly />
          <Input addonBefore="非 Docker" value={status?.upgrade_commands.native ?? "./scripts/upgrade.sh native"} readOnly />
        </Space>
      </div>
    </>
  );
}
