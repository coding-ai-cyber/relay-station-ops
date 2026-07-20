# Relay Station Ops 中转站运营管理系统

Relay Station Ops 是面向中转站业务的运营管理后台，用于统一管理供应商、采购记录、账号资产、服务器资产、IP 地址池、店铺监控、账号测评、收入、成本、盈亏报表和平台配置。

系统设计目标是支持接入多种中转站平台，不限定于某一个实现。当前版本已内置一套中转站管理接口适配能力，后续可以继续扩展其他平台适配器。

## 1. 配置文件

首次部署前复制配置模板：

```bash
cp .env.example .env
cp backend/.env.example backend/.env
```

必须修改 `backend/.env` 中的密钥：

```text
APP_SECRET_KEY=<随机长密钥>
APP_FIELD_ENCRYPTION_KEY=<随机长密钥>
```

`APP_FIELD_ENCRYPTION_KEY` 用于加密账号密码、供应商凭证、平台凭证等敏感字段。迁移到新机器时必须保持一致，否则旧数据无法解密。

## 2. Docker 部署

推荐服务器使用 Docker 部署：

```bash
./deploy.sh docker
```

创建管理员：

```bash
docker compose -p relay-station-ops -f docker-compose.prod.yml exec backend \
  python -m app.scripts.create_admin --username <admin-user> --password <strong-password> --reset-password
```

默认访问地址：

```text
http://127.0.0.1:8080
```

可在 `.env` 中修改 `APP_PORT`。

## 3. Docker 镜像部署

如果使用 GitHub Container Registry 镜像部署：

```bash
docker compose -p relay-station-ops -f docker-compose.image.yml pull
docker compose -p relay-station-ops -f docker-compose.image.yml up -d
```

默认镜像地址：

```text
ghcr.io/838530761/relay-station-ops-backend:latest
ghcr.io/838530761/relay-station-ops-frontend:latest
```

如果镜像是私有包，服务器需要先登录：

```bash
docker login ghcr.io
```

## 4. 非 Docker 部署

非 Docker 部署需要服务器已安装 PostgreSQL、Python 3.12+、Node.js 22+、npm。

编辑 `backend/.env`，配置数据库连接：

```text
DATABASE_URL=postgresql+psycopg://<user>:<password>@<host>:5432/<database>
```

执行：

```bash
./deploy.sh native
```

创建管理员：

```bash
cd backend
python -m app.scripts.create_admin --username <admin-user> --password <strong-password> --reset-password
```

启动后端：

```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

前端构建产物在 `frontend/dist`，使用 Nginx 或其他静态服务托管，并将 `/api` 反向代理到后端。

## 5. 数据导出

导出内容包含业务数据库和上传附件，默认不导出审计日志。

Docker 部署：

```bash
docker compose -p relay-station-ops -f docker-compose.prod.yml exec backend \
  python -m app.scripts.export_data --output /tmp/backup.zip
docker compose -p relay-station-ops -f docker-compose.prod.yml cp backend:/tmp/backup.zip ./backup.zip
```

非 Docker 部署：

```bash
cd backend
python -m app.scripts.export_data --output ../backups/backup.zip
```

也可以在后台页面进入：

```text
系统维护 -> 创建备份 -> 下载备份
```

## 6. 数据导入

新机器部署完成，并配置好相同的 `APP_FIELD_ENCRYPTION_KEY` 后执行导入。

Docker 部署：

```bash
docker compose -p relay-station-ops -f docker-compose.prod.yml cp backup.zip backend:/tmp/backup.zip
docker compose -p relay-station-ops -f docker-compose.prod.yml exec backend \
  python -m app.scripts.import_data --input /tmp/backup.zip
```

非 Docker 部署：

```bash
cd backend
python -m app.scripts.import_data --input ../backups/backup.zip
```

也可以在后台页面进入：

```text
系统维护 -> 导入备份
```

如果加密密钥指纹不一致，导入会拒绝执行。只有确认接受加密字段可能不可读时，才使用 `--force`。

## 7. 升级

升级前脚本会尝试创建备份。

Docker 部署：

```bash
./scripts/upgrade.sh docker
```

非 Docker 部署：

```bash
./scripts/upgrade.sh native
```

镜像部署：

```bash
git pull
docker compose -p relay-station-ops -f docker-compose.image.yml pull
docker compose -p relay-station-ops -f docker-compose.image.yml up -d
```

后台页面也会展示升级命令：

```text
系统维护 -> 升级命令
```

## 8. 系统入口

登录后台后，主要功能入口包括：

- 仪表盘
- 供应商
- 采购记录
- 中转站配置
- 账号资产
- 服务器资产
- IP 地址池资产
- 店铺监控
- 账号测评
- 收入管理
- 成本管理
- 盈亏报表
- 平台配置
- 系统维护
