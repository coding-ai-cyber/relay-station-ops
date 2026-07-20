# Sub2API Ops 经营管理系统

Sub2API Ops 是面向中转站业务的内部经营管理后台，用于统一管理供应商、采购记录、账号资产、服务器资产、IP 地址池、店铺监控、账号测评、收入、成本、盈亏报表和平台配置。

## 数据持久化

- 业务数据存储在 PostgreSQL。
- 上传附件存储在 `backend/storage/uploads`，Docker 部署时会映射到独立 volume。
- 敏感字段使用 `APP_FIELD_ENCRYPTION_KEY` 加密。迁移到新机器时必须保留这个密钥，否则旧的账号密码、供应商密码、平台凭证等字段无法解密。

## Docker 一键部署

推荐服务器使用 Docker 部署。

```bash
cp .env.example .env
cp backend/.env.example backend/.env
./deploy.sh docker
```

首次部署后创建管理员：

```bash
docker compose -p sub2api-ops -f docker-compose.prod.yml exec backend \
  python -m app.scripts.create_admin --username <admin-user> --password <strong-password> --reset-password
```

访问地址默认是：

```text
http://127.0.0.1:8080
```

可以在 `.env` 中修改 `APP_PORT`。

## 直接拉取 Docker 镜像部署

项目推送到 GitHub 后，GitHub Actions 会构建镜像并推送到 GitHub Container Registry。

镜像地址：

```text
ghcr.io/838530761/relay-station-ops-backend:latest
ghcr.io/838530761/relay-station-ops-frontend:latest
```

服务器首次部署：

```bash
git clone https://github.com/838530761/relay-station-ops.git
cd relay-station-ops
cp .env.example .env
cp backend/.env.example backend/.env
```

编辑 `.env` 和 `backend/.env` 后启动：

```bash
docker compose -p relay-station-ops -f docker-compose.image.yml pull
docker compose -p relay-station-ops -f docker-compose.image.yml up -d
```

后续升级镜像：

```bash
git pull
docker compose -p relay-station-ops -f docker-compose.image.yml pull
docker compose -p relay-station-ops -f docker-compose.image.yml up -d
```

如果仓库或镜像包保持私有，服务器需要先登录 GHCR：

```bash
docker login ghcr.io
```

## 非 Docker 部署

非 Docker 部署需要本机已有 PostgreSQL、Python 3.12+、Node.js 22+、npm。

```bash
cp backend/.env.example backend/.env
```

编辑 `backend/.env`，至少填写：

```text
APP_SECRET_KEY=<random-secret>
APP_FIELD_ENCRYPTION_KEY=<random-field-encryption-key>
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

前端构建产物在 `frontend/dist`，可用 Nginx 或其他静态服务托管，并将 `/api` 反向代理到后端。

## 数据导出

导出包含业务数据库和上传附件，默认排除审计日志 `audit_logs`。

Docker 部署：

```bash
docker compose -p sub2api-ops -f docker-compose.prod.yml exec backend \
  python -m app.scripts.export_data --output /tmp/backup.zip
docker compose -p sub2api-ops -f docker-compose.prod.yml cp backend:/tmp/backup.zip ./backup.zip
```

非 Docker 部署：

```bash
cd backend
python -m app.scripts.export_data --output ../backups/backup.zip
```

## 数据导入

新机器部署好并配置好相同的 `APP_FIELD_ENCRYPTION_KEY` 后执行导入。

Docker 部署：

```bash
docker compose -p sub2api-ops -f docker-compose.prod.yml cp backup.zip backend:/tmp/backup.zip
docker compose -p sub2api-ops -f docker-compose.prod.yml exec backend \
  python -m app.scripts.import_data --input /tmp/backup.zip
```

非 Docker 部署：

```bash
cd backend
python -m app.scripts.import_data --input ../backups/backup.zip
```

如果密钥指纹不一致，导入会拒绝执行。只有在确认接受加密字段可能不可读时，才使用 `--force`。

## 升级已部署项目

升级前脚本会尝试创建备份。

Docker：

```bash
./scripts/upgrade.sh docker
```

非 Docker：

```bash
./scripts/upgrade.sh native
```

升级流程包括：

- 备份业务数据和上传附件
- 拉取新代码
- 安装依赖
- 执行 Alembic 数据库迁移
- 重新构建前端
- 重启或提示重启服务

## 推送 GitHub 前清理

公开仓库前执行：

```bash
./scripts/preflight-public.sh
```

不要提交：

- `.env`、`backend/.env`
- 数据库 dump、备份 zip、日志
- `backend/storage/uploads`
- 真实账号、密码、token、Sub2API key
- 任何供应商、采购、资产、收入、成本等业务数据

## 本地开发

启动本地 PostgreSQL：

```bash
docker compose -p sub2api-ops up -d postgres
```

后端：

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m alembic -c ../alembic.ini upgrade head
python -m uvicorn app.main:app --reload
```

前端：

```bash
cd frontend
npm ci
npm run dev
```
