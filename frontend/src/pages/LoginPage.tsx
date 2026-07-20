import { LockOutlined, UserOutlined } from "@ant-design/icons";
import { Button, Form, Input, Typography, message } from "antd";
import { useState } from "react";

import { useAuth } from "../auth/AuthContext";

export function LoginPage() {
  const { login } = useAuth();
  const [loading, setLoading] = useState(false);

  return (
    <div className="login-page">
      <div className="login-panel">
        <div className="login-form-wrap">
          <div className="login-brand">
            <span className="login-brand-mark">S</span>
            <span>Relay Station Ops</span>
          </div>
          <Typography.Title level={1} className="login-title">
            经营管理系统
          </Typography.Title>
          <Typography.Paragraph className="login-desc">
            统一记录供应商、采购、资产、测评、收入和真实利润。
          </Typography.Paragraph>
          <Form
            layout="vertical"
            onFinish={async (values) => {
              setLoading(true);
              try {
                await login(values.username, values.password);
              } catch (error) {
                message.error(error instanceof Error ? error.message : "登录失败");
              } finally {
                setLoading(false);
              }
            }}
          >
            <Form.Item name="username" label="用户名" rules={[{ required: true }]}>
              <Input prefix={<UserOutlined />} autoComplete="username" />
            </Form.Item>
            <Form.Item name="password" label="密码" rules={[{ required: true }]}>
              <Input.Password prefix={<LockOutlined />} autoComplete="current-password" />
            </Form.Item>
            <Button type="primary" htmlType="submit" block loading={loading}>
              登录
            </Button>
          </Form>
        </div>
      </div>
      <div className="login-visual">
        <div className="login-visual-inner">
          <div className="login-kicker">真实成本 · 有效采购 · 稳定货源</div>
          <Typography.Title level={2} style={{ color: "#fff", marginTop: 0 }}>
            经营数据，采购决策，真实利润
          </Typography.Title>
          <Typography.Paragraph style={{ color: "#d7e3ef", fontSize: 18 }}>
            把供应商、采购、账号资产、测评、收入和成本统一到一条可追踪的经营链路里。
          </Typography.Paragraph>
          <div className="login-feature-grid">
            <div>本月利润</div>
            <div>测评有效率</div>
            <div>供应商排行</div>
            <div>成本倍率建议</div>
          </div>
        </div>
      </div>
    </div>
  );
}
