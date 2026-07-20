# 采购账号 JSON 绑定与 Sub2API 运营闭环设计

## 目标

把“采购记录、采购生成的账号资产、采购后拿到的 Sub2API JSON 凭据、Sub2API 分组导入、状态监测和异常标注”串成一条可追踪链路。

核心目标：

- 一笔账号采购可以按数量生成多条账号资产，而不是只生成一条合并资产。
- 多账号 JSON 文件可以绑定到这笔采购生成的账号资产上，补全邮箱、凭据、远端账号 ID 和原始数据。
- 绑定后的账号资产可以按采购批次一键导入到指定 Sub2API 实例和分组。
- 平台可以按采购批次或导入批次检测 Sub2API 上的账号状态。
- 账号异常时记录首次异常时间、最近检测结果、存活时长和人工标注，支撑后续采购质量分析。

## 当前基础

系统已经有这些能力：

- `purchases` 表和采购页面可以记录账号采购。
- `accounts.purchase_id` 已经能关联采购记录。
- `POST /api/purchases/{purchase_id}/create-assets` 可以从采购生成资产，但当前账号采购只生成 1 条合并账号资产。
- `accounts.raw_payload` 保存原始 JSON 脱敏内容。
- `accounts.raw_credentials_encrypted` 加密保存 JSON 中的凭据。
- `POST /api/accounts/bulk-import` 可以批量导入账号。
- `POST /api/sub2api-imports` 可以把账号导入 Sub2API 分组。
- `POST /api/accounts/sub2api-checks/auto` 可以通过 Sub2API 管理接口检测账号状态。
- `accounts` 已有 `first_seen_alive_at`、`last_seen_alive_at`、`first_abnormal_at`、`survival_seconds`、`available_days` 等状态追踪字段。

## 用户流程

### 1. 录入采购

用户录入一笔账号采购：

- `purchase_type = account`
- `product_name = K12`
- `quantity = 20`
- `total_price = 本批总金额`
- `product_type` 可填账号平台或产品分类，例如 `openai`、`k12`。

系统继续自动生成采购成本项。

### 2. 生成账号资产

用户点击“生成账号资产”。

系统按采购数量生成多条账号资产：

- `PO-20260716-XXXXXX-A001`
- `PO-20260716-XXXXXX-A002`
- 直到采购数量对应的末尾编号。

每条账号资产写入：

- `purchase_id`
- `supplier_id`
- `account_type`
- `name`
- `status = pending_test`
- `include_real_cost`
- `cost_unit_price = total_price / quantity`
- `raw_payload.source = purchase_asset_generation`
- `remark = Generated from purchase ...`

如果这笔采购已经生成过账号资产，接口返回跳过原因，不重复生成。

### 3. 绑定 JSON 凭据

用户在采购页或账号资产页选择“导入 JSON 凭据到本采购资产”，上传类似 `sub2api-import.json` 的文件。

系统识别多账号结构：

```json
{
  "accounts": [
    {
      "name": "account-name",
      "platform": "openai",
      "type": "oauth",
      "credentials": {
        "access_token": "...",
        "expires_at": 1780000000,
        "email": "user@example.com",
        "plan_type": "plus",
        "chatgpt_account_id": "...",
        "account_id": "..."
      },
      "concurrency": 10,
      "priority": 1,
      "rate_multiplier": 1
    }
  ]
}
```

绑定规则：

- 默认按 JSON 中 `accounts[]` 顺序绑定到该采购下尚未绑定凭据的账号资产。
- 如果后续需要更严格匹配，可以增加按邮箱或账号编号匹配；第一版保持顺序匹配，简单可控。
- JSON 账号数量不能大于可绑定的空资产数量；如果小于资产数量，剩余资产保持待补全状态。
- 如果某条资产已经有 `raw_credentials_encrypted`，默认不覆盖；用户选择“覆盖已有凭据”时才更新。

每个绑定成功的账号资产更新：

- `raw_payload`: 单个账号 JSON，敏感字段脱敏保存。
- `raw_credentials_encrypted`: 完整 `credentials` 加密保存。
- `login_account`: `credentials.email`
- `authorized_email`: `credentials.email`
- `sub2api_account_id`: 优先 `credentials.account_id`，其次 `credentials.chatgpt_account_id`
- `account_type`: `platform`
- `plan_type`: `credentials.plan_type`
- `import_file_id`: 上传文件 ID
- `import_batch_no`: 本次绑定批次号，例如 `JSON-20260716213000`
- `status`: 保持 `pending_test`，除非用户选择绑定后设为待导入状态。

### 4. 导入到 Sub2API 分组

用户可以从采购批次直接发起“导入到 Sub2API”：

- 选择 Sub2API 实例。
- 选择一个或多个远端分组。
- 选择重复策略：跳过已有账号或更新已有账号。
- 默认导入该采购下已绑定凭据的账号资产。

后端复用现有 `run_sub2api_import`：

- 从 `raw_credentials_encrypted` 解密凭据。
- 按 `platform` 匹配远端分组。
- 调用 Sub2API 管理接口创建或更新账号。
- 成功后写回 `sub2api_instance_id` 和 `sub2api_account_id`。
- 逐条记录导入成功、失败、跳过和失败原因。

### 5. 监控 Sub2API 状态

用户可以按采购批次检测账号：

- 在采购页点击“检测本采购账号”。
- 或在账号资产页筛选采购批次后点击“一键检测”。

检测范围支持：

- `purchase_id`
- `import_batch_no`
- `sub2api_instance_id`
- `account_type`
- 只检测参与运营账号。

检测结果更新账号资产：

- 可用账号写入 `available`、首次可用时间、最近可用时间。
- 异常账号写入 `api_401`、`api_403`、`api_429`、`unavailable` 或 `check_failed`。
- 首次异常时写入 `first_abnormal_at`。
- 每次检测写入 `last_checked_at`、`last_sub2api_status_code`、`last_sub2api_error_code`、`last_sub2api_message`。
- 按首次可用时间或创建时间计算 `survival_seconds` 和 `available_days`。
- 每次检测保留 `AccountCheckRecord` 明细，便于回看历史。

### 6. 异常标注

检测发现异常后，用户可以在账号资产上手动标注：

- 风控
- 封禁
- 已退款
- 已废弃
- 不计入真实成本
- 备注原因

人工标注不会删除自动检测历史。自动检测字段记录 Sub2API 事实状态，人工状态和备注记录运营判断。

## 后端设计

### 账号资产生成

调整 `POST /api/purchases/{purchase_id}/create-assets`：

- 当 `purchase_type = account` 时，根据 `quantity` 生成多条账号资产。
- `quantity` 必须转换为正整数；非整数采购数量拒绝生成账号资产，并返回清晰错误。
- 账号编号格式：`{purchase_no}-A{序号三位}`。
- 成本单价：`total_price / quantity`。
- 结果返回实际创建账号数量。

### JSON 绑定接口

新增接口：

```text
POST /api/purchases/{purchase_id}/accounts/bind-json
```

请求体：

```json
{
  "file_id": "上传文件 ID，可为空",
  "payload": {},
  "overwrite_existing": false,
  "remark": "备注，可为空"
}
```

响应体包含：

- `purchase_id`
- `import_batch_no`
- `total_json_accounts`
- `bound_count`
- `skipped_count`
- `failed_count`
- `items[]`

每个 item 包含：

- `account_id`
- `account_no`
- `email`
- `status`
- `message`

### JSON 解析服务

新增服务模块，例如 `app.services.purchase_account_json.py`。

职责：

- 从根对象提取账号数组，支持 `accounts`、`data.accounts`、根数组。
- 提取邮箱：优先 `credentials.email`，其次顶层 `email`、`account`、`username`。
- 提取远端 ID：优先 `credentials.account_id`，其次 `credentials.chatgpt_account_id`，再其次顶层 `id`。
- 提取平台：优先顶层 `platform`。
- 提取类型：顶层 `type`。
- 提取套餐：优先 `credentials.plan_type`，其次顶层 `plan_type`。
- 调用现有 `prepare_raw_payload` 做脱敏和凭据加密，保持敏感字段不进前端明文。

### 检测接口扩展

扩展 `Sub2APIAutoCheckRequest` 和相关选择逻辑：

- 增加 `purchase_id`
- 保留现有 `instance_id`，用于指定 Sub2API 实例。
- 与 `account_type`、`import_batch_no`、`include_only_operation` 组合过滤。

## 前端设计

### 采购页

在账号采购行增加操作：

- 生成账号资产
- 导入 JSON 凭据
- 导入本采购账号到 Sub2API
- 检测本采购账号

采购表展示：

- 已生成账号数量
- 已绑定凭据数量
- 已导入 Sub2API 数量
- 异常账号数量

### JSON 绑定弹窗

弹窗流程：

1. 上传 JSON。
2. 展示解析预览：账号数、识别邮箱数、目标空资产数、可能跳过数。
3. 选择是否覆盖已有凭据。
4. 确认绑定。

预览不展示 access token 等敏感内容，只展示邮箱、平台、套餐、远端 ID 的脱敏或非敏感摘要。

### 账号资产页

保留现有 JSON 导入能力，但文案区分：

- “导入新账号”：创建新的账号资产。
- “绑定到采购资产”：把 JSON 凭据写入已有采购账号资产。

账号列表增加或强化筛选：

- 采购批次
- Sub2API 实例
- 导入批次
- 状态
- 是否有原始凭据

## 错误处理

- JSON 不是合法对象或数组：返回“JSON 格式无效”。
- 找不到账号数组：返回“未识别到 accounts 数组”。
- JSON 账号数量超过可绑定空资产数量且未允许覆盖：返回冲突，并提示数量差异。
- 单条 JSON 缺少 credentials：允许绑定基础信息，但标记该条缺少可导入凭据。
- Sub2API 导入失败：不回滚本地 JSON 绑定，只在导入批次明细记录失败原因。
- 检测失败：写入检测记录和账号最近错误，不清除既有凭据。

## 安全要求

- `credentials`、`access_token`、`refresh_token`、`api_key` 等敏感字段只加密保存。
- 前端和日志只展示脱敏后的 `raw_payload`。
- 导入 Sub2API 时只在后端解密凭据。
- 异常消息继续经过敏感字段清洗，避免 token 出现在错误日志。
- 查看敏感字段仍必须走已有 reveal 接口和审计日志。

## 测试计划

后端测试：

- 账号采购按数量生成多条资产。
- 非整数或小于 1 的采购数量不能生成账号资产。
- Sub2API 多账号 JSON 可以按顺序绑定到采购资产。
- 邮箱从 `credentials.email` 提取。
- 远端 ID 从 `credentials.account_id` 或 `credentials.chatgpt_account_id` 提取。
- 已有凭据默认不覆盖。
- 覆盖模式可以更新已有绑定。
- 按 `purchase_id` 过滤自动检测账号。
- 异常检测会更新存活时间和首次异常时间。

前端测试：

- 采购页操作按钮在账号采购上可见。
- JSON 绑定弹窗能展示解析统计。
- 绑定成功后账号列表刷新并显示邮箱、导入批次、凭据状态。
- 从采购批次发起 Sub2API 导入时只导入该采购下账号。
- 从采购批次发起检测时带上 `purchase_id`。

浏览器验证：

- 上传示例 `sub2api-import.json` 后预览账号数量和邮箱识别数正确。
- 绑定后账号资产页能看到对应邮箱。
- 导入到 Sub2API 后批次明细显示成功、失败或跳过。
- 检测后异常账号展示状态、最近 HTTP、存活时长和检测历史。

## 非目标

- 第一版不做复杂自动匹配，例如根据邮箱反查已有资产再乱序绑定。
- 第一版不把 Sub2API 远端分组同步成长期本地分组模型，只在导入时实时读取。
- 第一版不做定时任务调度；先提供手动一键检测，后续再接自动化监控。
- 第一版不展示敏感凭据明文预览。
