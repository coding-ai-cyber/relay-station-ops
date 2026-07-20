# Sub2API 账号批量导入设计

## 目标

在账号资产页将选中账号或当前全部账号批量导入指定 Sub2API 实例，并绑定一个或多个与账号平台匹配的远端分组。系统记录批次和逐账号结果，支持失败项重试。

## 用户流程

1. 用户在账号表格勾选账号，或选择当前全部账号。
2. 点击“导入到 Sub2API”。
3. 选择 Sub2API 实例、远端分组和重复处理策略。
4. 系统从后端读取远端分组并按平台匹配。
5. 后端解密账号凭证，调用 Sub2API 管理接口批量创建或更新账号。
6. 页面展示成功、失败、跳过统计和逐账号错误，可对失败项重试。

## 数据与安全

- 原始 JSON 中的 `credentials` 是首选凭证来源。
- 没有原始凭证时，保存的 Sub2API Key 映射为 `apikey` 类型的 `api_key`。
- 登录密码不直接映射为 Sub2API 凭证。
- 管理员 Key 和账号密钥只在后端解密，不返回浏览器，不写入导入日志。
- 本地保存远端账号 ID、动作、状态和错误，不保存远端请求中的凭证明文。

## 远端接口

- `GET /api/v1/admin/groups/all`：读取分组，兼容 `/api/admin/groups/all`。
- `GET /api/v1/admin/accounts`：识别已有账号。
- `POST /api/v1/admin/accounts/batch`：批量创建账号。
- `PUT /api/v1/admin/accounts/{id}`：重复策略为更新时更新账号和分组。
- 写请求携带 `Idempotency-Key`。

## 本地接口

- `GET /api/sub2api-instances/{id}/groups`
- `POST /api/sub2api-imports`
- `GET /api/sub2api-imports`
- `GET /api/sub2api-imports/{id}/items`
- `POST /api/sub2api-imports/{id}/retry`

## 错误处理

- 远端不可连接或管理员 Key 无效：返回网关错误，不发送账号凭证。
- 分组与账号平台不匹配：该账号失败并记录原因。
- 缺少可导入凭证：该账号失败并记录原因。
- 重复策略 `skip`：远端已存在时记录跳过。
- 重复策略 `update`：更新已有账号；更新失败只影响该账号。

## 验证

- 单元测试覆盖平台、凭证和分组映射。
- Alembic 升级到最新版本。
- 前端生产构建通过。
- 浏览器验证账号选择、分组加载、导入结果和失败重试。
